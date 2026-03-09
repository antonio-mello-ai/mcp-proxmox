"""Backup tools: list, create, and restore backups."""

from __future__ import annotations

from typing import Any

from mcp_proxmox.client import ProxmoxClient


def _format_bytes(value: int | float) -> str:
    """Format bytes into human-readable string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"


def list_backups(
    client: ProxmoxClient,
    node: str | None = None,
    storage: str | None = None,
    vmid: int | None = None,
) -> dict[str, Any]:
    """List backup files across storages, optionally filtered by node, storage, or VMID."""
    nodes = client.get_nodes()
    if node:
        nodes = [n for n in nodes if n.get("node") == node]
        if not nodes:
            return {"error": f"Node '{node}' not found in cluster"}

    all_backups: list[dict[str, Any]] = []

    for n in nodes:
        node_name = n.get("node", "")
        storages = client.get_storages(node_name)
        for s in storages:
            storage_name = s.get("storage", "")
            content_types = s.get("content", "")
            if "backup" not in content_types:
                continue
            if storage and storage_name != storage:
                continue

            content = client.get_storage_content(node_name, storage_name, "backup")
            for item in content:
                item_vmid = item.get("vmid")
                if vmid is not None and item_vmid != vmid:
                    continue
                all_backups.append(
                    {
                        "volid": item.get("volid", ""),
                        "vmid": item_vmid,
                        "size": _format_bytes(item.get("size", 0)),
                        "format": item.get("format", ""),
                        "created": item.get("ctime"),
                        "notes": item.get("notes", ""),
                        "node": node_name,
                        "storage": storage_name,
                    }
                )

    return {
        "total": len(all_backups),
        "backups": sorted(all_backups, key=lambda x: x.get("created") or 0, reverse=True),
    }


def create_backup(
    client: ProxmoxClient,
    vmid: int,
    storage: str = "local",
    mode: str = "snapshot",
    compress: str = "zstd",
    notes: str = "",
) -> dict[str, Any]:
    """Create a backup (vzdump) of a VM or container.

    mode: 'snapshot' (default, no downtime), 'suspend', or 'stop'.
    compress: 'zstd' (default), 'lzo', 'gzip', or '0' (none).
    """
    valid_modes = ("snapshot", "suspend", "stop")
    if mode not in valid_modes:
        return {"error": f"Invalid mode '{mode}'. Must be one of: {', '.join(valid_modes)}"}

    valid_compress = ("zstd", "lzo", "gzip", "0")
    if compress not in valid_compress:
        return {
            "error": f"Invalid compress '{compress}'. Must be one of: {', '.join(valid_compress)}"
        }

    guest = client.find_guest(vmid)
    if not guest:
        return {"error": f"Guest with VMID {vmid} not found in cluster"}

    node = guest["node"]
    guest_name = guest.get("name", f"VMID {vmid}")
    guest_type = guest["type"]
    type_label = "VM" if guest_type == "qemu" else "Container"

    params: dict[str, Any] = {
        "storage": storage,
        "mode": mode,
        "compress": compress,
    }
    if notes:
        params["notes-template"] = notes

    upid = client.create_backup(node, vmid, **params)

    return {
        "success": True,
        "vmid": vmid,
        "name": guest_name,
        "type": type_label,
        "node": node,
        "storage": storage,
        "mode": mode,
        "compress": compress,
        "task_id": upid,
        "message": (
            f"Backup of {type_label} '{guest_name}' ({vmid}) started "
            f"on storage '{storage}' (mode={mode}, compress={compress})"
        ),
    }


def restore_backup(
    client: ProxmoxClient,
    volid: str,
    node: str,
    vmid: int | None = None,
    storage: str = "local-lvm",
    guest_type: str = "vm",
    confirm: bool = False,
) -> dict[str, Any]:
    """Restore a VM or container from a backup.

    guest_type: 'vm' or 'container'. Determines how the backup is restored.
    """
    if guest_type not in ("vm", "container"):
        return {"error": "guest_type must be 'vm' or 'container'"}

    nodes = client.get_nodes()
    if not any(n.get("node") == node for n in nodes):
        return {"error": f"Node '{node}' not found in cluster"}

    if vmid is None:
        vmid = client.get_next_vmid()

    existing = client.find_guest(vmid)
    if existing:
        return {"error": f"VMID {vmid} already exists on node '{existing['node']}'"}

    type_label = "VM" if guest_type == "vm" else "Container"

    if not confirm:
        return {
            "warning": (
                f"This will restore {type_label} from backup '{volid}' "
                f"as VMID {vmid} on node '{node}' (storage: {storage}). "
                "Call again with confirm=true to proceed."
            ),
            "volid": volid,
            "vmid": vmid,
            "node": node,
            "type": type_label,
        }

    if guest_type == "vm":
        upid = client.restore_vm(node, vmid, volid, storage=storage)
    else:
        upid = client.restore_container(node, vmid, volid, storage=storage)

    return {
        "success": True,
        "vmid": vmid,
        "type": type_label,
        "node": node,
        "volid": volid,
        "storage": storage,
        "task_id": upid,
        "message": (f"{type_label} restore from '{volid}' started as VMID {vmid} on node '{node}'"),
    }
