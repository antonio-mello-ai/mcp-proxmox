"""Lifecycle tools: start, stop, shutdown, and reboot VMs and containers."""

from __future__ import annotations

from typing import Any

from mcp_proxmox.client import ProxmoxClient

VALID_ACTIONS = ("start", "stop", "shutdown", "reboot")


def _execute_action(
    client: ProxmoxClient,
    vmid: int,
    action: str,
    confirm: bool = False,
) -> dict[str, Any]:
    """Execute a lifecycle action on a guest with safety checks."""
    if action not in VALID_ACTIONS:
        return {"error": f"Invalid action '{action}'. Must be one of: {', '.join(VALID_ACTIONS)}"}

    guest = client.find_guest(vmid)
    if not guest:
        return {"error": f"Guest with VMID {vmid} not found in cluster"}

    node = guest["node"]
    guest_type = guest["type"]
    guest_name = guest.get("name", f"VMID {vmid}")
    current_status = guest.get("status", "unknown")
    type_label = "VM" if guest_type == "qemu" else "Container"

    if action == "start" and current_status == "running":
        return {"error": f"{type_label} '{guest_name}' ({vmid}) is already running"}

    if action in ("stop", "shutdown", "reboot") and current_status == "stopped":
        return {"error": f"{type_label} '{guest_name}' ({vmid}) is already stopped"}

    if action in ("stop", "reboot") and not confirm:
        warning = (
            f"stop forcefully terminates the {type_label}"
            if action == "stop"
            else f"reboot will restart the {type_label}"
        )
        return {
            "warning": f"This will {action} {type_label} '{guest_name}' ({vmid}) "
            f"on node '{node}'. Note: {warning}. "
            f"Call again with confirm=true to proceed.",
            "action": action,
            "vmid": vmid,
            "name": guest_name,
            "current_status": current_status,
        }

    upid = client.guest_action(node, vmid, guest_type, action)

    return {
        "success": True,
        "action": action,
        "vmid": vmid,
        "name": guest_name,
        "type": type_label,
        "node": node,
        "task_id": upid,
        "message": f"{action.capitalize()} initiated for {type_label} '{guest_name}' ({vmid})",
    }


def start_guest(client: ProxmoxClient, vmid: int) -> dict[str, Any]:
    """Start a stopped VM or container."""
    return _execute_action(client, vmid, "start")


def stop_guest(client: ProxmoxClient, vmid: int, confirm: bool = False) -> dict[str, Any]:
    """Force-stop a VM or container. Requires confirm=true (data loss risk)."""
    return _execute_action(client, vmid, "stop", confirm=confirm)


def shutdown_guest(client: ProxmoxClient, vmid: int) -> dict[str, Any]:
    """Gracefully shut down a VM or container via ACPI/init."""
    return _execute_action(client, vmid, "shutdown")


def reboot_guest(client: ProxmoxClient, vmid: int, confirm: bool = False) -> dict[str, Any]:
    """Reboot a VM or container. Requires confirm=true."""
    return _execute_action(client, vmid, "reboot", confirm=confirm)
