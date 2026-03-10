"""Live migration tools."""

from __future__ import annotations

from typing import Any

from mcp_proxmox.client import ProxmoxClient


def migrate_guest(
    client: ProxmoxClient,
    vmid: int,
    target_node: str,
    online: bool = True,
    confirm: bool = False,
) -> dict[str, Any]:
    """Live migrate a VM or container to another node."""
    guest = client.find_guest(vmid)
    if not guest:
        return {"error": f"Guest {vmid} not found."}

    source_node = guest["node"]
    guest_type = guest["type"]
    guest_name = guest.get("name", str(vmid))
    type_label = "VM" if guest_type == "qemu" else "container"

    if source_node == target_node:
        return {
            "error": f"{type_label} '{guest_name}' ({vmid}) is already on node '{target_node}'."
        }

    # Check target node exists
    nodes = client.get_nodes()
    node_names = [n["node"] for n in nodes]
    if target_node not in node_names:
        return {
            "error": f"Target node '{target_node}' not found. "
            f"Available nodes: {', '.join(node_names)}"
        }

    migration_type = "live (online)" if online else "offline"

    if not confirm:
        return {
            "warning": f"This will {migration_type} migrate {type_label} "
            f"'{guest_name}' ({vmid}) from node '{source_node}' "
            f"to node '{target_node}'. "
            f"Call again with confirm=true to proceed.",
            "vmid": vmid,
            "name": guest_name,
            "type": type_label,
            "source_node": source_node,
            "target_node": target_node,
            "migration_type": migration_type,
        }

    upid = client.migrate_guest(source_node, vmid, guest_type, target_node, online)
    return {
        "success": True,
        "vmid": vmid,
        "name": guest_name,
        "type": type_label,
        "source_node": source_node,
        "target_node": target_node,
        "migration_type": migration_type,
        "task_id": upid,
    }
