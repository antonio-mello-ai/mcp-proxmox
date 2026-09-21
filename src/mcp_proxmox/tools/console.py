"""Console interaction tools: screenshots and keyboard input for QEMU VMs."""

from __future__ import annotations

import time
from typing import Any

from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.fastmcp.utilities.types import Image

from mcp_proxmox.client import ProxmoxClient


def _resolve_running_qemu(client: ProxmoxClient, vmid: int, action: str) -> tuple[str, str]:
    """Validate that the guest is a running QEMU VM and return (node, name).

    Args:
        client: ProxmoxClient instance.
        vmid: The numeric ID of the guest.
        action: Action name for error messages (e.g. 'capture screenshot').

    Returns:
        Tuple of (node name, guest name).

    Raises:
        ToolError: If the guest is not found, is an LXC container, or is not running.
    """
    guest = client.find_guest(vmid)
    if not guest:
        raise ToolError(f"Guest with VMID {vmid} not found in cluster")

    guest_type = guest["type"]
    if guest_type != "qemu":
        raise ToolError(f"VMID {vmid} is an LXC container; {action} is only supported for QEMU VMs")

    node = guest["node"]
    guest_name = guest.get("name", f"VMID {vmid}")
    current_status = guest.get("status", "unknown")

    if current_status != "running":
        raise ToolError(
            f"VM '{guest_name}' ({vmid}) is not running (status: {current_status}). "
            f"Cannot {action}."
        )

    return node, guest_name


def vm_screenshot(
    client: ProxmoxClient,
    vmid: int,
) -> Image:
    """Capture a PNG screenshot of a QEMU VM's display.

    Opens a VNC websocket tunnel through the Proxmox API (the same mechanism
    the web UI's noVNC console uses), requests a full framebuffer update, and
    encodes it as PNG. The VM must be running.

    Requires the 'VM.Console' privilege on the VM.

    Args:
        client: ProxmoxClient instance.
        vmid: The numeric ID of the QEMU VM.

    Returns:
        Image object (PNG).

    Raises:
        ToolError: If the VM is not found, not running, or capture fails.
    """
    node, guest_name = _resolve_running_qemu(client, vmid, "capture screenshot")

    try:
        image_data = client.screenshot_vm(node, vmid)
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Failed to capture screenshot of VM '{guest_name}' ({vmid}): {e}") from e

    if not image_data:
        raise ToolError("Screenshot capture returned empty data")

    return Image(data=image_data, format="png")


def vm_send_key(
    client: ProxmoxClient,
    vmid: int,
    key: str,
    confirm: bool = False,
) -> dict[str, Any]:
    """Send a key or key combination to a QEMU VM's console.

    Uses the Proxmox sendkey endpoint. The VM must be running.
    Key names are human-readable and auto-converted to QEMU Monitor key codes.

    Common keys and combos:
        - 'enter' or 'ret' — Enter key
        - 'esc' — Escape key
        - 'tab' — Tab key
        - 'space' or 'spc' — Space bar
        - 'backspace' — Backspace
        - 'delete' or 'del' — Delete key
        - 'up', 'down', 'left', 'right' — Arrow keys
        - 'home', 'end', 'pageup', 'pagedown' — Navigation keys
        - 'f1'-'f12' — Function keys
        - 'ctrl-alt-delete' — Ctrl+Alt+Del
        - 'ctrl-c' — Ctrl+C
        - 'win-r' — Win+R (opens Run dialog on Windows)
        - 'a'-'z', '0'-'9' — Single character keys

    Args:
        client: ProxmoxClient instance.
        vmid: The numeric ID of the QEMU VM.
        key: Key name or hyphen-separated combo (e.g. 'enter', 'ctrl-alt-delete').
        confirm: Must be true to send the key to the VM console.

    Returns:
        Dict with success status and details.

    Raises:
        ToolError: If the VM is not found, not running, or key send fails.
    """
    if not key.strip():
        raise ToolError("Key cannot be empty")

    node, guest_name = _resolve_running_qemu(client, vmid, "send keys")

    if not confirm:
        return {
            "warning": f"This will send key '{key}' to VM '{guest_name}' ({vmid}). "
            "Call again with confirm=true to proceed.",
            "vmid": vmid,
            "name": guest_name,
            "key": key,
        }

    try:
        client.sendkey_vm(node, vmid, key)
    except Exception as e:
        raise ToolError(f"Failed to send key '{key}' to VM '{guest_name}' ({vmid}): {e}") from e

    return {
        "vmid": vmid,
        "name": guest_name,
        "key_sent": key,
        "success": True,
        "message": f"Key '{key}' sent to VM '{guest_name}' ({vmid})",
    }


def vm_send_text(
    client: ProxmoxClient,
    vmid: int,
    text: str,
    delay: float = 0.05,
    confirm: bool = False,
) -> dict[str, Any]:
    """Type a text string into a QEMU VM's console, character by character.

    Each character is sent as an individual keypress via the Proxmox sendkey
    endpoint. This allows typing login credentials, commands, etc.

    Only printable ASCII (US keyboard layout) is supported: letters, digits,
    and all symbols mapped via Shift (e.g. '@' becomes 'shift-2'). Unicode
    characters like Cyrillic are not supported by the sendkey protocol.

    Args:
        client: ProxmoxClient instance.
        vmid: The numeric ID of the QEMU VM.
        text: Text string to type into the VM console.
        delay: Delay between keypresses in seconds (default 0.05).
        confirm: Must be true to type the text into the VM console.

    Returns:
        Dict with success status and number of characters typed.

    Raises:
        ToolError: If the VM is not found, not running, or a key send fails.
    """
    if not text:
        raise ToolError("Text cannot be empty")
    if delay < 0:
        raise ToolError("Delay cannot be negative")

    node, guest_name = _resolve_running_qemu(client, vmid, "send text")

    # Map special characters to QEMU key names (US layout)
    char_map: dict[str, str] = {
        "\n": "ret",
        "\r": "ret",
        "\t": "tab",
        " ": "spc",
    }
    # Printable ASCII that map 1:1 to QEMU key names
    plain_keys: dict[str, str] = {
        "-": "minus",
        "=": "equal",
        "[": "bracket_left",
        "]": "bracket_right",
        "\\": "backslash",
        ";": "semicolon",
        "'": "apostrophe",
        "`": "grave_accent",
        ",": "comma",
        ".": "dot",
        "/": "slash",
    }
    # Printable ASCII that require Shift on a US layout
    shift_keys: dict[str, str] = {
        "!": "shift-1",
        "@": "shift-2",
        "#": "shift-3",
        "$": "shift-4",
        "%": "shift-5",
        "^": "shift-6",
        "&": "shift-7",
        "*": "shift-8",
        "(": "shift-9",
        ")": "shift-0",
        "_": "shift-minus",
        "+": "shift-equal",
        "{": "shift-bracket_left",
        "}": "shift-bracket_right",
        "|": "shift-backslash",
        ":": "shift-semicolon",
        '"': "shift-apostrophe",
        "~": "shift-grave_accent",
        "<": "shift-comma",
        ">": "shift-dot",
        "?": "shift-slash",
    }

    keys: list[tuple[str, str]] = []
    for char in text:
        if char in char_map:
            qemu_key = char_map[char]
        elif char in shift_keys:
            qemu_key = shift_keys[char]
        elif char in plain_keys:
            qemu_key = plain_keys[char]
        elif ("a" <= char <= "z") or ("0" <= char <= "9"):
            qemu_key = char
        elif "A" <= char <= "Z":
            qemu_key = f"shift-{char.lower()}"
        else:
            raise ToolError(f"Unsupported character (US layout ASCII only): {char!r}")

        keys.append((char, qemu_key))

    if not confirm:
        return {
            "warning": f"This will type {len(text)} character(s) into VM "
            f"'{guest_name}' ({vmid}). Call again with confirm=true to proceed.",
            "vmid": vmid,
            "name": guest_name,
            "characters": len(text),
        }

    sent_count = 0
    for char, qemu_key in keys:
        try:
            client.sendkey_vm(node, vmid, qemu_key)
            sent_count += 1
            if delay > 0:
                time.sleep(delay)
        except Exception as e:
            raise ToolError(
                f"Failed to send character {char!r} (key '{qemu_key}') to VM "
                f"'{guest_name}' ({vmid}) after {sent_count} characters: {e}"
            ) from e

    result: dict[str, Any] = {
        "vmid": vmid,
        "name": guest_name,
        "text_sent": text,
        "characters_sent": sent_count,
        "total_characters": len(text),
        "success": True,
    }
    return result
