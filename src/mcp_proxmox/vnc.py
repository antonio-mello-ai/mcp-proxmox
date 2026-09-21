"""Minimal VNC (RFB) client for capturing console screenshots over Proxmox VNC tunnels.

Implements just enough of RFC 6455 (WebSocket) and the RFB 3.7/3.8 protocol
to connect to the tunnel created by the Proxmox ``vncproxy``/``vncwebsocket``
API calls, request a full raw framebuffer update, and encode it as PNG.

Only the Python standard library is used (socket, ssl, zlib, struct,
base64, hashlib, os) — no extra dependencies.
"""

from __future__ import annotations

import base64
import hashlib
import os
import socket
import ssl
import struct
import zlib

_RECV_SIZE = 65536
_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

# --- Minimal pure-Python DES (ECB) for VNC Authentication (RFC 6143 §7.2.2) ---

# Initial and final permutations
_IP = (
    58,
    50,
    42,
    34,
    26,
    18,
    10,
    2,
    60,
    52,
    44,
    36,
    28,
    20,
    12,
    4,
    62,
    54,
    46,
    38,
    30,
    22,
    14,
    6,
    64,
    56,
    48,
    40,
    32,
    24,
    16,
    8,
    57,
    49,
    41,
    33,
    25,
    17,
    9,
    1,
    59,
    51,
    43,
    35,
    27,
    19,
    11,
    3,
    61,
    53,
    45,
    37,
    29,
    21,
    13,
    5,
    63,
    55,
    47,
    39,
    31,
    23,
    15,
    7,
)
_FP = (
    40,
    8,
    48,
    16,
    56,
    24,
    64,
    32,
    39,
    7,
    47,
    15,
    55,
    23,
    63,
    31,
    38,
    6,
    46,
    14,
    54,
    22,
    62,
    30,
    37,
    5,
    45,
    13,
    53,
    21,
    61,
    29,
    36,
    4,
    44,
    12,
    52,
    20,
    60,
    28,
    35,
    3,
    43,
    11,
    51,
    19,
    59,
    27,
    34,
    2,
    42,
    10,
    50,
    18,
    58,
    26,
    33,
    1,
    41,
    9,
    49,
    17,
    57,
    25,
)
# Expansion
_E = (
    32,
    1,
    2,
    3,
    4,
    5,
    4,
    5,
    6,
    7,
    8,
    9,
    8,
    9,
    10,
    11,
    12,
    13,
    12,
    13,
    14,
    15,
    16,
    17,
    16,
    17,
    18,
    19,
    20,
    21,
    20,
    21,
    22,
    23,
    24,
    25,
    24,
    25,
    26,
    27,
    28,
    29,
    28,
    29,
    30,
    31,
    32,
    1,
)
# Permutation P
_P = (
    16,
    7,
    20,
    21,
    29,
    12,
    28,
    17,
    1,
    15,
    23,
    26,
    5,
    18,
    31,
    10,
    2,
    8,
    24,
    14,
    32,
    27,
    3,
    9,
    19,
    13,
    30,
    6,
    22,
    11,
    4,
    25,
)
# Permutation choice 1 (PC-1): 56 bits from 64-bit key
_PC1 = (
    57,
    49,
    41,
    33,
    25,
    17,
    9,
    1,
    58,
    50,
    42,
    34,
    26,
    18,
    10,
    2,
    59,
    51,
    43,
    35,
    27,
    19,
    11,
    3,
    60,
    52,
    44,
    36,
    63,
    55,
    47,
    39,
    31,
    23,
    15,
    7,
    62,
    54,
    46,
    38,
    30,
    22,
    14,
    6,
    61,
    53,
    45,
    37,
    29,
    21,
    13,
    5,
    28,
    20,
    12,
    4,
)
# Permutation choice 2 (PC-2): 48 bits from 56-bit rotated key
_PC2 = (
    14,
    17,
    11,
    24,
    1,
    5,
    3,
    28,
    15,
    6,
    21,
    10,
    23,
    19,
    12,
    4,
    26,
    8,
    16,
    7,
    27,
    20,
    13,
    2,
    41,
    52,
    31,
    37,
    47,
    55,
    30,
    40,
    51,
    45,
    33,
    48,
    44,
    49,
    39,
    56,
    34,
    53,
    46,
    42,
    50,
    36,
    29,
    32,
)
# Number of left shifts per round
_SHIFTS = (1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1)
# S-boxes
_SBOX: tuple[tuple[int, ...], ...] = (
    (
        14,
        4,
        13,
        1,
        2,
        15,
        11,
        8,
        3,
        10,
        6,
        12,
        5,
        9,
        0,
        7,
        0,
        15,
        7,
        4,
        14,
        2,
        13,
        1,
        10,
        6,
        12,
        11,
        9,
        5,
        3,
        8,
        4,
        1,
        14,
        8,
        13,
        6,
        2,
        11,
        15,
        12,
        9,
        7,
        3,
        10,
        5,
        0,
        15,
        12,
        8,
        2,
        4,
        9,
        1,
        7,
        5,
        11,
        3,
        14,
        10,
        0,
        6,
        13,
    ),
    (
        15,
        1,
        8,
        14,
        6,
        11,
        3,
        4,
        9,
        7,
        2,
        13,
        12,
        0,
        5,
        10,
        3,
        13,
        4,
        7,
        15,
        2,
        8,
        14,
        12,
        0,
        1,
        10,
        6,
        9,
        11,
        5,
        0,
        14,
        7,
        11,
        10,
        4,
        13,
        1,
        5,
        8,
        12,
        6,
        9,
        3,
        2,
        15,
        13,
        8,
        10,
        1,
        3,
        15,
        4,
        2,
        11,
        6,
        7,
        12,
        0,
        5,
        14,
        9,
    ),
    (
        10,
        0,
        9,
        14,
        6,
        3,
        15,
        5,
        1,
        13,
        12,
        7,
        11,
        4,
        2,
        8,
        13,
        7,
        0,
        9,
        3,
        4,
        6,
        10,
        2,
        8,
        5,
        14,
        12,
        11,
        15,
        1,
        13,
        6,
        4,
        9,
        8,
        15,
        3,
        0,
        11,
        1,
        2,
        12,
        5,
        10,
        14,
        7,
        1,
        10,
        13,
        0,
        6,
        9,
        8,
        7,
        4,
        15,
        14,
        3,
        11,
        5,
        2,
        12,
    ),
    (
        7,
        13,
        14,
        3,
        0,
        6,
        9,
        10,
        1,
        2,
        8,
        5,
        11,
        12,
        4,
        15,
        13,
        8,
        11,
        5,
        6,
        15,
        0,
        3,
        4,
        7,
        2,
        12,
        1,
        10,
        14,
        9,
        10,
        6,
        9,
        0,
        12,
        11,
        7,
        13,
        15,
        1,
        3,
        14,
        5,
        2,
        8,
        4,
        3,
        15,
        0,
        6,
        10,
        1,
        13,
        8,
        9,
        4,
        5,
        11,
        12,
        7,
        2,
        14,
    ),
    (
        2,
        12,
        4,
        1,
        7,
        10,
        11,
        6,
        8,
        5,
        3,
        15,
        13,
        0,
        14,
        9,
        14,
        11,
        2,
        12,
        4,
        7,
        13,
        1,
        5,
        0,
        15,
        10,
        3,
        9,
        8,
        6,
        4,
        2,
        1,
        11,
        10,
        13,
        7,
        8,
        15,
        9,
        12,
        5,
        6,
        3,
        0,
        14,
        11,
        8,
        12,
        7,
        1,
        14,
        2,
        13,
        6,
        15,
        0,
        9,
        10,
        4,
        5,
        3,
    ),
    (
        12,
        1,
        10,
        15,
        9,
        2,
        6,
        8,
        0,
        13,
        3,
        4,
        14,
        7,
        5,
        11,
        10,
        15,
        4,
        2,
        7,
        12,
        9,
        5,
        6,
        1,
        13,
        14,
        0,
        11,
        3,
        8,
        9,
        14,
        15,
        5,
        2,
        8,
        12,
        3,
        7,
        0,
        4,
        10,
        1,
        13,
        11,
        6,
        4,
        3,
        2,
        12,
        9,
        5,
        15,
        10,
        11,
        14,
        1,
        7,
        6,
        0,
        8,
        13,
    ),
    (
        4,
        11,
        2,
        14,
        15,
        0,
        8,
        13,
        3,
        12,
        9,
        7,
        5,
        10,
        6,
        1,
        13,
        0,
        11,
        7,
        4,
        9,
        1,
        10,
        14,
        3,
        5,
        12,
        2,
        15,
        8,
        6,
        1,
        4,
        11,
        13,
        12,
        3,
        7,
        14,
        10,
        15,
        6,
        8,
        0,
        5,
        9,
        2,
        6,
        11,
        13,
        8,
        1,
        4,
        10,
        7,
        9,
        5,
        0,
        15,
        14,
        2,
        3,
        12,
    ),
    (
        13,
        2,
        8,
        4,
        6,
        15,
        11,
        1,
        10,
        9,
        3,
        14,
        5,
        0,
        12,
        7,
        1,
        15,
        13,
        8,
        10,
        3,
        7,
        4,
        12,
        5,
        6,
        11,
        0,
        14,
        9,
        2,
        7,
        11,
        4,
        1,
        9,
        12,
        14,
        2,
        0,
        6,
        10,
        13,
        15,
        3,
        5,
        8,
        2,
        1,
        14,
        7,
        4,
        10,
        8,
        13,
        15,
        12,
        9,
        0,
        3,
        5,
        6,
        11,
    ),
)


def _bits(data: bytes) -> list[int]:
    """Convert bytes to a list of bits (MSB first)."""
    return [(byte >> (7 - i)) & 1 for byte in data for i in range(8)]


def _from_bits(bits: list[int]) -> bytes:
    """Convert a list of bits (MSB first) back to bytes."""
    out = bytearray(len(bits) // 8)
    for i, bit in enumerate(bits):
        out[i // 8] |= bit << (7 - (i % 8))
    return bytes(out)


def _permute(bits: list[int], table: tuple[int, ...]) -> list[int]:
    """Apply a bit permutation."""
    return [bits[i - 1] for i in table]


def _left_shift(bits: list[int], n: int) -> list[int]:
    """Rotate a bit list left by n positions."""
    return bits[n:] + bits[:n]


def _f(r_bits: list[int], subkey: list[int]) -> list[int]:
    """Feistel function of DES."""
    expanded = _permute(r_bits, _E)  # 48 bits
    xored = [a ^ b for a, b in zip(expanded, subkey, strict=True)]
    sbox_out: list[int] = []
    for i in range(8):
        chunk = xored[i * 6 : (i + 1) * 6]
        row = (chunk[0] << 1) | chunk[5]
        col = (chunk[1] << 3) | (chunk[2] << 2) | (chunk[3] << 1) | chunk[4]
        val = _SBOX[i][row * 16 + col]
        sbox_out += [(val >> 3) & 1, (val >> 2) & 1, (val >> 1) & 1, val & 1]
    return _permute(sbox_out, _P)


def _des_subkeys(key_bits: list[int]) -> list[list[int]]:
    """Derive the 16 48-bit subkeys from a 56-bit key (already PC-1 applied)."""
    c = key_bits[:28]
    d = key_bits[28:]
    subkeys = []
    for shift in _SHIFTS:
        c = _left_shift(c, shift)
        d = _left_shift(d, shift)
        subkeys.append(_permute(c + d, _PC2))
    return subkeys


def _des_block(block: bytes, subkeys: list[list[int]]) -> bytes:
    """Encrypt one 8-byte block with DES using precomputed subkeys."""
    bits = _permute(_bits(block), _IP)
    left, right = bits[:32], bits[32:]
    for subkey in subkeys:
        left, right = right, [a ^ b for a, b in zip(left, _f(right, subkey), strict=True)]
    # Final swap and inverse initial permutation
    return _from_bits(_permute(right + left, _FP))


def _vnc_auth_encrypt(challenge: bytes, password: str) -> bytes:
    """Encrypt the 16-byte VNC challenge with DES using the VNC password.

    VNC Auth (RFC 6143 §7.2.2): the key is the first 8 bytes of the password
    with the bits of each byte reversed, and the challenge is encrypted as
    two DES-ECB blocks. We only need encryption (not decryption) — the client
    sends back the encrypted challenge.

    Args:
        challenge: 16-byte challenge from the server.
        password: VNC password string.

    Returns:
        16-byte encrypted response.
    """
    # Take up to 8 bytes of the password, pad with zeros
    pw = password.encode("utf-8")[:8].ljust(8, b"\x00")
    # Reverse bits in each byte (VNC quirk)
    reversed_key = bytes(int(f"{byte:08b}"[::-1], 2) for byte in pw)
    key_bits = _permute(_bits(reversed_key), _PC1)
    subkeys = _des_subkeys(key_bits)
    return _des_block(challenge[:8], subkeys) + _des_block(challenge[8:], subkeys)


class VNCError(Exception):
    """Raised when a VNC screenshot capture fails."""


class _WebSocketClient:
    """Minimal RFC 6455 WebSocket client (no extensions, no compression)."""

    def __init__(self, sock: socket.socket) -> None:
        self._sock = sock
        self._buf = b""

    @classmethod
    def connect(
        cls,
        host: str,
        port: int,
        use_ssl: bool,
        timeout: float,
        path: str = "/",
        extra_headers: dict[str, str] | None = None,
        verify_ssl: bool = True,
    ) -> _WebSocketClient:
        """Open a TCP (optionally TLS) connection and perform the WS upgrade.

        Args:
            host: Target hostname.
            port: Target port.
            use_ssl: Wrap the socket in TLS.
            timeout: Socket timeout in seconds.
            path: Request path including query string.
            extra_headers: Optional extra HTTP headers (e.g. Authorization).
            verify_ssl: Verify the TLS certificate and hostname when TLS is enabled.
        """
        raw = socket.create_connection((host, port), timeout=timeout)
        sock: socket.socket = raw
        try:
            if use_ssl:
                context = (
                    ssl.create_default_context() if verify_ssl else ssl._create_unverified_context()
                )
                sock = context.wrap_socket(raw, server_hostname=host)

            key = base64.b64encode(os.urandom(16)).decode()
            headers = {
                "Host": f"{host}:{port}",
                "Upgrade": "websocket",
                "Connection": "Upgrade",
                "Sec-WebSocket-Key": key,
                "Sec-WebSocket-Version": "13",
            }
            if extra_headers:
                headers.update(extra_headers)
            request = f"GET {path} HTTP/1.1\r\n" + "".join(
                f"{name}: {value}\r\n" for name, value in headers.items()
            )
            sock.sendall(request.encode("latin-1") + b"\r\n")

            header = b""
            while b"\r\n\r\n" not in header:
                chunk = sock.recv(_RECV_SIZE)
                if not chunk:
                    raise VNCError("Connection closed during WebSocket handshake")
                header += chunk
            header, _, rest = header.partition(b"\r\n\r\n")
            status_line, *header_lines = header.split(b"\r\n")
            if b" 101 " not in status_line:
                raise VNCError(
                    f"WebSocket handshake failed: {status_line.decode(errors='replace')}"
                )

            response_headers = {
                name.strip().lower(): value.strip()
                for line in header_lines
                if b":" in line
                for name, value in (line.split(b":", 1),)
            }
            expected_accept = base64.b64encode(
                hashlib.sha1((key + _WS_GUID).encode("ascii")).digest()
            )
            if response_headers.get(b"sec-websocket-accept") != expected_accept:
                raise VNCError("WebSocket handshake returned an invalid Sec-WebSocket-Accept")

            client = cls(sock)
            client._buf = rest
            return client
        except Exception:
            sock.close()
            if sock is not raw:
                raw.close()
            raise

    def close(self) -> None:
        """Close the underlying transport."""
        self._sock.close()

    def send(self, payload: bytes) -> None:
        """Send one masked binary frame (client frames must be masked)."""
        frame = bytearray([0x82])  # FIN + binary
        length = len(payload)
        if length < 126:
            frame.append(0x80 | length)
        elif length < 65536:
            frame.append(0x80 | 126)
            frame += struct.pack(">H", length)
        else:
            frame.append(0x80 | 127)
            frame += struct.pack(">Q", length)
        mask = os.urandom(4)
        frame += mask
        frame += bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self._sock.sendall(bytes(frame))

    def _recv_exact(self, n: int) -> bytes:
        while len(self._buf) < n:
            chunk = self._sock.recv(_RECV_SIZE)
            if not chunk:
                raise VNCError("Connection closed by remote")
            self._buf += chunk
        data, self._buf = self._buf[:n], self._buf[n:]
        return data

    def read(self) -> bytes:
        """Read the next complete data message (handles ping/pong and fragments)."""
        message = b""
        fragmented = False
        while True:
            b1, b2 = self._recv_exact(2)
            fin = bool(b1 & 0x80)
            opcode = b1 & 0x0F
            masked = bool(b2 & 0x80)
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._recv_exact(8))[0]
            mask = self._recv_exact(4) if masked else None
            payload = self._recv_exact(length)
            if mask is not None:
                raise VNCError("Received a masked WebSocket frame from the server")
            if opcode >= 0x8 and (not fin or length > 125):
                raise VNCError("Received an invalid WebSocket control frame")
            if opcode == 0x8:  # close
                raise VNCError("WebSocket closed by remote")
            if opcode == 0x9:  # ping -> pong
                self._send_pong(payload)
                continue
            if opcode == 0xA:  # pong
                continue
            if opcode == 0x0:
                if not fragmented:
                    raise VNCError("Unexpected WebSocket continuation frame")
                message += payload
                if fin:
                    return message
            elif opcode in (0x1, 0x2):
                if fragmented:
                    raise VNCError("Received a new WebSocket message before final fragment")
                message = payload
                if fin:
                    return message
                fragmented = True
            else:
                raise VNCError(f"Unsupported WebSocket opcode {opcode}")

    def _send_pong(self, payload: bytes) -> None:
        frame = bytearray([0x8A])
        length = len(payload)
        if length < 126:
            frame.append(0x80 | length)
        else:
            frame.append(0x80 | 126)
            frame += struct.pack(">H", length)
        mask = os.urandom(4)
        frame += mask
        frame += bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self._sock.sendall(bytes(frame))


class _RFBStream:
    """Byte-stream reader over WebSocket data messages for RFB protocol parsing."""

    def __init__(self, ws: _WebSocketClient) -> None:
        self._ws = ws
        self._buf = b""

    def read_exact(self, n: int) -> bytes:
        while len(self._buf) < n:
            self._buf += self._ws.read()
        data, self._buf = self._buf[:n], self._buf[n:]
        return data


def _encode_png(width: int, height: int, rgb: bytes) -> bytes:
    """Encode raw RGB bytes (3 bytes per pixel) into a PNG image."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    stride = width * 3
    raw = b"".join(b"\x00" + rgb[y * stride : (y + 1) * stride] for y in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


def capture_vnc_screenshot(
    host: str,
    ws_port: int,
    use_ssl: bool = True,
    timeout: float = 15.0,
    api_port: int | None = None,
    api_path: str | None = None,
    auth_header: str | None = None,
    password: str | None = None,
    verify_ssl: bool = True,
) -> bytes:
    """Connect to a Proxmox VNC websocket tunnel and capture a full framebuffer.

    Args:
        host: Hostname/IP of the websocket endpoint (the Proxmox API host).
        ws_port: Tunnel port returned by the ``vncwebsocket`` API call.
        use_ssl: Whether the websocket endpoint uses TLS (pveproxy does).
        timeout: Socket timeout in seconds.
        api_port: Port of the pveproxy endpoint to connect to. When provided,
            the websocket is opened through pveproxy (like noVNC does in the
            web UI) instead of the raw tunnel port.
        api_path: Request path (with query string) for the pveproxy websocket.
        auth_header: Optional 'Authorization' header value for pveproxy.
        password: Password for VNC Authentication (security type 2). For
            Proxmox tunnels this is the ticket returned by ``vncproxy``
            (starting with ``PVEVNC:``).
        verify_ssl: Verify the TLS certificate and hostname when TLS is enabled.

    Returns:
        PNG-encoded screenshot bytes.

    Raises:
        VNCError: On any handshake, protocol, or transport failure.
    """
    headers: dict[str, str] | None = None
    if auth_header:
        headers = {"Authorization": auth_header}

    if api_port is not None and api_path is not None:
        # Connect through pveproxy, like the web UI's noVNC client does
        ws = _WebSocketClient.connect(
            host,
            api_port,
            use_ssl,
            timeout,
            path=api_path,
            extra_headers=headers,
            verify_ssl=verify_ssl,
        )
    else:
        # Direct connection to the tunnel port (e.g. local on the node)
        ws = _WebSocketClient.connect(host, ws_port, use_ssl, timeout, verify_ssl=verify_ssl)
    try:
        return _capture_vnc_session(ws, password)
    finally:
        ws.close()


def _capture_vnc_session(ws: _WebSocketClient, password: str | None) -> bytes:
    """Perform one RFB screenshot exchange over an open WebSocket."""
    stream = _RFBStream(ws)

    # --- RFB version handshake ---
    version = stream.read_exact(12)
    if not version.startswith(b"RFB "):
        raise VNCError(f"Not a VNC server (got {version[:12]!r})")
    ws.send(version)  # accept the server's version (QEMU speaks RFB 003.008)

    # --- Security handshake (RFB 3.7+: [count:1][types:count]) ---
    count = stream.read_exact(1)[0]
    if count == 0:
        reason_len = struct.unpack(">I", stream.read_exact(4))[0]
        reason = stream.read_exact(reason_len).decode(errors="replace") if reason_len else ""
        raise VNCError(f"VNC connection refused: {reason}")
    sec_types = stream.read_exact(count)
    if 1 in sec_types:
        # No authentication
        ws.send(b"\x01")
    elif 2 in sec_types and password:
        # VNC Authentication (RFC 6143 §7.2.2): DES-encrypt the 16-byte challenge
        ws.send(b"\x02")
        challenge = stream.read_exact(16)
        ws.send(_vnc_auth_encrypt(challenge, password))
    else:
        raise VNCError(
            f"VNC server requires authentication (security types: {sorted(sec_types)}) "
            "and no password was provided"
        )
    result = struct.unpack(">I", stream.read_exact(4))[0]
    if result != 0:
        # RFB 3.8: failed result is followed by [length:4][reason]
        detail = ""
        try:
            reason_len = struct.unpack(">I", stream.read_exact(4))[0]
            if reason_len:
                detail = f": {stream.read_exact(reason_len).decode(errors='replace')}"
        except VNCError:
            pass
        raise VNCError(f"VNC security handshake failed (result={result}){detail}")

    # --- ClientInit / ServerInit ---
    ws.send(b"\x01")  # shared flag
    server_init = stream.read_exact(24)
    width, height = struct.unpack(">HH", server_init[:4])
    name_len = struct.unpack(">I", server_init[20:24])[0]
    if name_len > 0:
        stream.read_exact(name_len)
    if not width or not height:
        raise VNCError(f"Invalid framebuffer size {width}x{height}")

    # --- Force pixel format: 32bpp / depth 24 / little-endian / true color ---
    pixel_format = struct.pack(">BBBBHHHBBB3x", 32, 24, 0, 1, 255, 255, 255, 16, 8, 0)
    ws.send(b"\x00\x00\x00\x00" + pixel_format)  # SetPixelFormat
    ws.send(struct.pack(">BBHi", 2, 0, 1, 0))  # SetEncodings: Raw only
    ws.send(struct.pack(">BBHHHH", 3, 0, 0, 0, width, height))  # Full update request

    framebuffer = bytearray(width * height * 4)
    coverage = bytearray(width * height)

    while not all(coverage):
        msg_type = stream.read_exact(1)[0]
        if msg_type == 0:  # FramebufferUpdate
            stream.read_exact(1)  # padding
            n_rects = struct.unpack(">H", stream.read_exact(2))[0]
            for _ in range(n_rects):
                x, y, w, h = struct.unpack(">HHHH", stream.read_exact(8))
                encoding = struct.unpack(">i", stream.read_exact(4))[0]
                if encoding != 0:
                    raise VNCError(f"Unsupported rectangle encoding {encoding}")
                if not w or not h or x + w > width or y + h > height:
                    raise VNCError(
                        f"Invalid framebuffer rectangle {x},{y} {w}x{h} "
                        f"for framebuffer {width}x{height}"
                    )
                data = stream.read_exact(w * h * 4)
                src_row = w * 4
                for row in range(h):
                    dst = ((y + row) * width + x) * 4
                    src = row * src_row
                    framebuffer[dst : dst + src_row] = data[src : src + src_row]
                    cov_off = (y + row) * width + x
                    coverage[cov_off : cov_off + w] = b"\x01" * w
        elif msg_type == 1:  # SetColourMapEntries: [pad:1][first:2][n:2][n*6]
            n_colours = struct.unpack(">H", stream.read_exact(5)[3:5])[0]
            stream.read_exact(n_colours * 6)
        elif msg_type == 2:  # Bell
            continue
        elif msg_type == 3:  # ServerCutText: [pad:3][len:4][data]
            length = struct.unpack(">I", stream.read_exact(7)[3:7])[0]
            stream.read_exact(length)
        else:
            raise VNCError(f"Unexpected RFB message type {msg_type}")

    # Convert BGRA (little-endian: byte0=b, byte1=g, byte2=r) to RGB via fast slicing
    b = bytes(framebuffer[0::4])
    g = bytes(framebuffer[1::4])
    r = bytes(framebuffer[2::4])
    rgb = bytearray(width * height * 3)
    rgb[0::3] = r
    rgb[1::3] = g
    rgb[2::3] = b

    return _encode_png(width, height, bytes(rgb))
