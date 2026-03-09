"""Snapshot tools: list, create, and rollback snapshots."""

from __future__ import annotations

from typing import Any

from mcp_proxmox.client import ProxmoxClient


def list_snapshots(client: ProxmoxClient, vmid: int) -> dict[str, Any]:
    """List all snapshots for a VM or container."""
    guest = client.find_guest(vmid)
    if not guest:
        return {"error": f"Guest with VMID {vmid} not found in cluster"}

    node = guest["node"]
    guest_type = guest["type"]
    guest_name = guest.get("name", f"VMID {vmid}")
    snapshots = client.get_snapshots(node, vmid, guest_type)

    result = []
    for snap in snapshots:
        if snap.get("name") == "current":
            continue
        result.append(
            {
                "name": snap.get("name"),
                "description": snap.get("description", ""),
                "snaptime": snap.get("snaptime"),
                "parent": snap.get("parent", ""),
            }
        )

    return {
        "vmid": vmid,
        "name": guest_name,
        "type": "VM" if guest_type == "qemu" else "Container",
        "snapshot_count": len(result),
        "snapshots": result,
    }


def create_snapshot(
    client: ProxmoxClient,
    vmid: int,
    name: str,
    description: str = "",
) -> dict[str, Any]:
    """Create a new snapshot for a VM or container."""
    guest = client.find_guest(vmid)
    if not guest:
        return {"error": f"Guest with VMID {vmid} not found in cluster"}

    if not name or not name.replace("-", "").replace("_", "").isalnum():
        return {"error": "Snapshot name must be alphanumeric (hyphens and underscores allowed)"}

    node = guest["node"]
    guest_type = guest["type"]
    guest_name = guest.get("name", f"VMID {vmid}")
    type_label = "VM" if guest_type == "qemu" else "Container"

    upid = client.create_snapshot(node, vmid, guest_type, name, description)

    return {
        "success": True,
        "vmid": vmid,
        "guest_name": guest_name,
        "type": type_label,
        "snapshot_name": name,
        "description": description,
        "task_id": upid,
        "message": f"Snapshot '{name}' creation started for {type_label} '{guest_name}' ({vmid})",
    }


def rollback_snapshot(
    client: ProxmoxClient,
    vmid: int,
    name: str,
    confirm: bool = False,
) -> dict[str, Any]:
    """Rollback a VM or container to a named snapshot. Requires confirm=true (destructive)."""
    guest = client.find_guest(vmid)
    if not guest:
        return {"error": f"Guest with VMID {vmid} not found in cluster"}

    node = guest["node"]
    guest_type = guest["type"]
    guest_name = guest.get("name", f"VMID {vmid}")
    type_label = "VM" if guest_type == "qemu" else "Container"

    # Verify snapshot exists
    snapshots = client.get_snapshots(node, vmid, guest_type)
    snapshot_names: list[str] = [
        str(s.get("name")) for s in snapshots if s.get("name") != "current"
    ]
    if name not in snapshot_names:
        return {
            "error": f"Snapshot '{name}' not found for {type_label} '{guest_name}' ({vmid}). "
            f"Available snapshots: {', '.join(snapshot_names) or 'none'}",
        }

    if not confirm:
        return {
            "warning": f"This will rollback {type_label} '{guest_name}' ({vmid}) "
            f"to snapshot '{name}'. All changes since that snapshot will be LOST. "
            "Call again with confirm=true to proceed.",
            "vmid": vmid,
            "name": guest_name,
            "snapshot": name,
        }

    upid = client.rollback_snapshot(node, vmid, guest_type, name)

    return {
        "success": True,
        "vmid": vmid,
        "guest_name": guest_name,
        "type": type_label,
        "snapshot_name": name,
        "task_id": upid,
        "message": (
            f"Rollback to snapshot '{name}' started for {type_label} '{guest_name}' ({vmid})"
        ),
    }
