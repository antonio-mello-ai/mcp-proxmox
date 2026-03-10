"""Resize tools: modify CPU, memory, and disk of VMs and containers."""

from __future__ import annotations

import re
from typing import Any

from mcp_proxmox.client import ProxmoxClient


def resize_guest(
    client: ProxmoxClient,
    vmid: int,
    cores: int | None = None,
    memory: int | None = None,
    disk_size: str | None = None,
    disk: str = "scsi0",
    confirm: bool = False,
) -> dict[str, Any]:
    """Resize CPU, memory, and/or disk of a VM or container.

    At least one of cores, memory, or disk_size must be provided.
    disk_size uses '+' prefix for relative increase (e.g. '+10G') or absolute (e.g. '50G').
    Disk resize is irreversible — disks can only grow, never shrink.
    """
    if cores is None and memory is None and disk_size is None:
        return {"error": "At least one of cores, memory, or disk_size must be provided"}

    guest = client.find_guest(vmid)
    if not guest:
        return {"error": f"Guest with VMID {vmid} not found in cluster"}

    node = guest["node"]
    guest_type = guest["type"]
    guest_name = guest.get("name", f"VMID {vmid}")
    type_label = "VM" if guest_type == "qemu" else "Container"

    # Validate inputs
    if cores is not None and cores < 1:
        return {"error": "Cores must be at least 1"}

    if memory is not None and memory < 128:
        return {"error": "Memory must be at least 128 MB"}

    if disk_size is not None and not re.match(r"^\+?\d+[GMTK]$", disk_size):
        return {
            "error": f"Invalid disk_size '{disk_size}'. "
            "Use format like '+10G' (relative) or '50G' (absolute). "
            "Supported units: K, M, G, T."
        }

    # Build change description
    changes: list[str] = []
    if cores is not None:
        changes.append(f"cores: {cores}")
    if memory is not None:
        changes.append(f"memory: {memory} MB")
    if disk_size is not None:
        changes.append(f"disk {disk}: {disk_size}")

    if not confirm:
        warning_parts = [
            f"This will resize {type_label} '{guest_name}' ({vmid}):",
            f"  Changes: {', '.join(changes)}",
        ]
        if disk_size is not None:
            warning_parts.append("  WARNING: Disk resize is IRREVERSIBLE (disks can only grow).")
        warning_parts.append("Call again with confirm=true to proceed.")

        return {
            "warning": " ".join(warning_parts),
            "vmid": vmid,
            "name": guest_name,
            "type": type_label,
            "changes": changes,
        }

    # Apply CPU and memory changes
    config_params: dict[str, Any] = {}
    if cores is not None:
        config_params["cores"] = cores
    if memory is not None:
        config_params["memory"] = memory

    if config_params:
        client.update_guest_config(node, vmid, guest_type, **config_params)

    # Apply disk resize separately
    if disk_size is not None:
        disk_name = disk
        if guest_type == "lxc" and disk == "scsi0":
            disk_name = "rootfs"
        client.resize_guest_disk(node, vmid, guest_type, disk_name, disk_size)

    return {
        "success": True,
        "vmid": vmid,
        "name": guest_name,
        "type": type_label,
        "node": node,
        "changes": changes,
        "message": f"{type_label} '{guest_name}' ({vmid}) resized: {', '.join(changes)}",
    }
