"""Focused protocol tests for the minimal WebSocket/RFB client."""

from __future__ import annotations

import base64
import hashlib
import struct
from unittest.mock import MagicMock

import pytest

from mcp_proxmox import vnc


class FakeSocket:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.sent: list[bytes] = []
        self.closed = False

    def recv(self, _size: int) -> bytes:
        return self.chunks.pop(0) if self.chunks else b""

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)

    def close(self) -> None:
        self.closed = True


class FakeWebSocket:
    def __init__(self, messages: list[bytes]) -> None:
        self.messages = messages
        self.sent: list[bytes] = []
        self.closed = False

    def read(self) -> bytes:
        if not self.messages:
            raise vnc.VNCError("test stream exhausted")
        return self.messages.pop(0)

    def send(self, data: bytes) -> None:
        self.sent.append(data)

    def close(self) -> None:
        self.closed = True


def _upgrade_response(key_bytes: bytes, accept: bytes | None = None) -> bytes:
    key = base64.b64encode(key_bytes).decode()
    expected = base64.b64encode(hashlib.sha1((key + vnc._WS_GUID).encode()).digest())
    return (
        b"HTTP/1.1 101 Switching Protocols\r\n"
        b"Upgrade: websocket\r\n"
        b"Connection: Upgrade\r\n"
        b"Sec-WebSocket-Accept: " + (expected if accept is None else accept) + b"\r\n\r\n"
    )


def test_websocket_handshake_verifies_tls_hostname_and_accept(monkeypatch):
    key_bytes = b"k" * 16
    sock = FakeSocket([_upgrade_response(key_bytes)])
    context = MagicMock()
    context.wrap_socket.return_value = sock
    monkeypatch.setattr(vnc.socket, "create_connection", lambda *_args, **_kwargs: sock)
    monkeypatch.setattr(vnc.ssl, "create_default_context", lambda: context)
    monkeypatch.setattr(vnc.os, "urandom", lambda size: key_bytes[:size])

    client = vnc._WebSocketClient.connect(
        "pve.example.com", 8006, use_ssl=True, timeout=1, verify_ssl=True
    )

    context.wrap_socket.assert_called_once_with(sock, server_hostname="pve.example.com")
    assert b"Sec-WebSocket-Key: a2tra2tra2tra2tra2traw==" in sock.sent[0]
    client.close()
    assert sock.closed is True


def test_websocket_handshake_rejects_bad_accept_and_closes(monkeypatch):
    key_bytes = b"k" * 16
    sock = FakeSocket([_upgrade_response(key_bytes, accept=b"wrong")])
    monkeypatch.setattr(vnc.socket, "create_connection", lambda *_args, **_kwargs: sock)
    monkeypatch.setattr(vnc.os, "urandom", lambda size: key_bytes[:size])

    with pytest.raises(vnc.VNCError, match="invalid Sec-WebSocket-Accept"):
        vnc._WebSocketClient.connect("pve", 8006, use_ssl=False, timeout=1)

    assert sock.closed is True


def test_websocket_reassembles_fragments_and_answers_ping(monkeypatch):
    sock = FakeSocket([b"\x02\x02he", b"\x89\x01!", b"\x80\x03llo"])
    monkeypatch.setattr(vnc.os, "urandom", lambda size: b"m" * size)
    client = vnc._WebSocketClient(sock)  # type: ignore[arg-type]

    assert client.read() == b"hello"
    assert sock.sent[0][0] == 0x8A


def test_websocket_rejects_masked_server_frame():
    sock = FakeSocket([b"\x82\x81maskx"])
    client = vnc._WebSocketClient(sock)  # type: ignore[arg-type]

    with pytest.raises(vnc.VNCError, match="masked WebSocket frame"):
        client.read()


def _one_pixel_rfb_stream(
    security_type: int = 1,
    challenge: bytes = b"",
) -> bytes:
    server_init = struct.pack(">HH", 1, 1) + (b"\x00" * 16) + struct.pack(">I", 0)
    rectangle = struct.pack(">HHHHi", 0, 0, 1, 1, 0) + b"\x01\x02\x03\x00"
    framebuffer_update = b"\x00\x00" + struct.pack(">H", 1) + rectangle
    security = bytes((1, security_type)) + challenge + (b"\x00" * 4)
    return b"RFB 003.008\n" + security + server_init + framebuffer_update


def test_rfb_handshake_capture_and_cleanup(monkeypatch):
    ws = FakeWebSocket([_one_pixel_rfb_stream()])
    connect = MagicMock(return_value=ws)
    monkeypatch.setattr(vnc._WebSocketClient, "connect", connect)

    image = vnc.capture_vnc_screenshot("pve", 5900, api_port=8006, api_path="/vnc", verify_ssl=True)

    assert image.startswith(b"\x89PNG\r\n\x1a\n")
    assert ws.sent[0] == b"RFB 003.008\n"
    assert ws.sent[1] == b"\x01"
    assert ws.closed is True
    assert connect.call_args.kwargs["verify_ssl"] is True


def test_rfb_protocol_error_still_closes_websocket(monkeypatch):
    ws = FakeWebSocket([b"not-vnc-data"])
    monkeypatch.setattr(vnc._WebSocketClient, "connect", MagicMock(return_value=ws))

    with pytest.raises(vnc.VNCError, match="Not a VNC server"):
        vnc.capture_vnc_screenshot("pve", 5900, use_ssl=False)

    assert ws.closed is True


def test_rfb_vnc_authentication_handshake(monkeypatch):
    challenge = bytes(range(16))
    ws = FakeWebSocket([_one_pixel_rfb_stream(security_type=2, challenge=challenge)])
    monkeypatch.setattr(vnc._WebSocketClient, "connect", MagicMock(return_value=ws))

    image = vnc.capture_vnc_screenshot("pve", 5900, use_ssl=False, password="PVEVNC:ticket")

    assert image.startswith(b"\x89PNG")
    assert ws.sent[1] == b"\x02"
    assert ws.sent[2] == vnc._vnc_auth_encrypt(challenge, "PVEVNC:ticket")
    assert ws.closed is True
