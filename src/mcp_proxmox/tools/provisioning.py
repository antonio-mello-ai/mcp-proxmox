"""Provisioning tools: create, clone, and delete VMs and containers."""

from __future__ import annotations

from typing import Any

from mcp_proxmox.client import ProxmoxClient


def create_vm(
    client: ProxmoxClient,
    node: str,
    name: str,
    cores: int = 1,
    memory: int = 2048,
    disk_size: str = "32G",
    storage: str = "local-lvm",
    iso: str | None = None,
    os_type: str = "l26",
    net_bridge: str = "vmbr0",
    start_after_create: bool = False,
    vmid: int | None = None,
) -> dict[str, Any]:
    """Create a new QEMU virtual machine.

    Returns task info on success. The VM is created stopped by default.
    """
    nodes = client.get_nodes()
    if not any(n.get("node") == node for n in nodes):
        return {"error": f"Node '{node}' not found in cluster"}

    if vmid is None:
        vmid = client.get_next_vmid()

    existing = client.find_guest(vmid)
    if existing:
        return {"error": f"VMID {vmid} already exists on node '{existing['node']}'"}

    params: dict[str, Any] = {
        "name": name,
        "cores": cores,
        "memory": memory,
        "ostype": os_type,
        "net0": f"virtio,bridge={net_bridge}",
        "scsihw": "virtio-scsi-single",
        "scsi0": f"{storage}:{disk_size}",
    }
    if iso:
        params["ide2"] = f"{iso},media=cdrom"
        params["boot"] = "order=ide2;scsi0"
    else:
        params["boot"] = "order=scsi0"

    if start_after_create:
        params["start"] = 1

    upid = client.create_vm(node, vmid, **params)

    return {
        "success": True,
        "vmid": vmid,
        "name": name,
        "node": node,
        "type": "VM",
        "task_id": upid,
        "message": f"VM '{name}' (VMID {vmid}) creation started on node '{node}'",
    }


def create_container(
    client: ProxmoxClient,
    node: str,
    name: str,
    template: str,
    cores: int = 1,
    memory: int = 512,
    disk_size: int = 8,
    storage: str = "local-lvm",
    net_bridge: str = "vmbr0",
    password: str | None = None,
    ssh_public_keys: str | None = None,
    start_after_create: bool = False,
    vmid: int | None = None,
) -> dict[str, Any]:
    """Create a new LXC container from a template.

    template should be a volume ID like 'local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst'.
    """
    nodes = client.get_nodes()
    if not any(n.get("node") == node for n in nodes):
        return {"error": f"Node '{node}' not found in cluster"}

    if vmid is None:
        vmid = client.get_next_vmid()

    existing = client.find_guest(vmid)
    if existing:
        return {"error": f"VMID {vmid} already exists on node '{existing['node']}'"}

    params: dict[str, Any] = {
        "hostname": name,
        "ostemplate": template,
        "cores": cores,
        "memory": memory,
        "rootfs": f"{storage}:{disk_size}",
        "net0": f"name=eth0,bridge={net_bridge},ip=dhcp",
    }
    if password:
        params["password"] = password
    if ssh_public_keys:
        params["ssh-public-keys"] = ssh_public_keys
    if start_after_create:
        params["start"] = 1

    upid = client.create_container(node, vmid, **params)

    return {
        "success": True,
        "vmid": vmid,
        "name": name,
        "node": node,
        "type": "Container",
        "template": template,
        "task_id": upid,
        "message": f"Container '{name}' (VMID {vmid}) creation started on node '{node}'",
    }


def clone_guest(
    client: ProxmoxClient,
    vmid: int,
    new_name: str | None = None,
    target_node: str | None = None,
    full_clone: bool = True,
    target_storage: str | None = None,
    new_vmid: int | None = None,
) -> dict[str, Any]:
    """Clone an existing VM or container.

    Creates a full clone by default (independent copy). Set full_clone=false for linked clone.
    """
    guest = client.find_guest(vmid)
    if not guest:
        return {"error": f"Guest with VMID {vmid} not found in cluster"}

    node = guest["node"]
    guest_type = guest["type"]
    guest_name = guest.get("name", f"VMID {vmid}")
    type_label = "VM" if guest_type == "qemu" else "Container"

    if new_vmid is None:
        new_vmid = client.get_next_vmid()

    existing = client.find_guest(new_vmid)
    if existing:
        return {"error": f"Target VMID {new_vmid} already exists on node '{existing['node']}'"}

    params: dict[str, Any] = {"full": 1 if full_clone else 0}
    if new_name:
        params["name"] = new_name
    if target_node:
        params["target"] = target_node
    if target_storage:
        params["storage"] = target_storage

    upid = client.clone_guest(node, vmid, guest_type, new_vmid, **params)

    clone_name = new_name or f"clone-of-{guest_name}"
    return {
        "success": True,
        "source_vmid": vmid,
        "source_name": guest_name,
        "new_vmid": new_vmid,
        "new_name": clone_name,
        "type": type_label,
        "clone_type": "full" if full_clone else "linked",
        "node": node,
        "target_node": target_node or node,
        "task_id": upid,
        "message": (
            f"{type_label} '{guest_name}' ({vmid}) clone started as "
            f"'{clone_name}' (VMID {new_vmid})"
        ),
    }


def delete_guest(
    client: ProxmoxClient,
    vmid: int,
    confirm: bool = False,
) -> dict[str, Any]:
    """Delete a VM or container. Requires confirm=true (irreversible).

    The guest must be stopped before deletion.
    """
    guest = client.find_guest(vmid)
    if not guest:
        return {"error": f"Guest with VMID {vmid} not found in cluster"}

    node = guest["node"]
    guest_type = guest["type"]
    guest_name = guest.get("name", f"VMID {vmid}")
    current_status = guest.get("status", "unknown")
    type_label = "VM" if guest_type == "qemu" else "Container"

    if current_status == "running":
        return {
            "error": f"{type_label} '{guest_name}' ({vmid}) is running. "
            "Stop it first before deleting.",
        }

    if not confirm:
        return {
            "warning": f"This will PERMANENTLY DELETE {type_label} '{guest_name}' ({vmid}) "
            f"on node '{node}'. All data including disk images will be destroyed. "
            "This action CANNOT be undone. Call again with confirm=true to proceed.",
            "vmid": vmid,
            "name": guest_name,
            "type": type_label,
            "node": node,
        }

    upid = client.delete_guest(node, vmid, guest_type)

    return {
        "success": True,
        "vmid": vmid,
        "name": guest_name,
        "type": type_label,
        "node": node,
        "task_id": upid,
        "message": f"{type_label} '{guest_name}' ({vmid}) deletion started on node '{node}'",
    }
