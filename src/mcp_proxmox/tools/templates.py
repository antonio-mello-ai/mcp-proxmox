"""Template and cloud-init tools."""

from __future__ import annotations

from typing import Any

from mcp_proxmox.client import ProxmoxClient


def list_templates(client: ProxmoxClient) -> list[dict[str, Any]]:
    """List all VM templates across the cluster."""
    templates = []
    for resource in client.get_cluster_resources():
        if resource.get("type") == "qemu" and resource.get("template", 0) == 1:
            templates.append(
                {
                    "vmid": resource["vmid"],
                    "name": resource.get("name", ""),
                    "node": resource["node"],
                    "status": resource.get("status", "unknown"),
                    "maxcpu": resource.get("maxcpu", 0),
                    "maxmem": resource.get("maxmem", 0),
                }
            )
    templates.sort(key=lambda t: t["vmid"])
    return templates


def create_template(
    client: ProxmoxClient,
    vmid: int,
    confirm: bool = False,
) -> dict[str, Any]:
    """Convert a stopped VM into a template. IRREVERSIBLE.

    The VM must be stopped before conversion. Once converted, the VM
    can no longer be started directly — it can only be cloned.
    """
    guest = client.find_guest(vmid)
    if not guest:
        return {"error": f"Guest {vmid} not found."}

    if guest["type"] != "qemu":
        return {"error": f"Only QEMU VMs can be converted to templates. Guest {vmid} is LXC."}

    if guest.get("status") == "running":
        return {"error": f"VM {vmid} must be stopped before converting to a template."}

    if guest.get("template", 0) == 1:
        return {"error": f"VM {vmid} is already a template."}

    guest_name = guest.get("name", str(vmid))
    node = guest["node"]

    if not confirm:
        return {
            "warning": f"This will IRREVERSIBLY convert VM '{guest_name}' ({vmid}) "
            f"into a template. The VM will no longer be startable — "
            f"it can only be cloned. Call again with confirm=true to proceed.",
            "vmid": vmid,
            "name": guest_name,
            "node": node,
        }

    client.convert_to_template(node, vmid)
    return {
        "success": True,
        "vmid": vmid,
        "name": guest_name,
        "node": node,
        "message": f"VM '{guest_name}' ({vmid}) has been converted to a template.",
    }


def configure_cloud_init(
    client: ProxmoxClient,
    vmid: int,
    user: str | None = None,
    password: str | None = None,
    ssh_keys: str | None = None,
    ip_config: str | None = None,
    nameserver: str | None = None,
    searchdomain: str | None = None,
) -> dict[str, Any]:
    """Configure cloud-init parameters on a VM.

    At least one parameter must be provided.
    Changes are applied to the VM config and take effect on next boot
    (cloud-init runs on first boot or when regenerated).
    """
    guest = client.find_guest(vmid)
    if not guest:
        return {"error": f"Guest {vmid} not found."}

    if guest["type"] != "qemu":
        return {"error": f"Cloud-init is only supported on QEMU VMs. Guest {vmid} is LXC."}

    params: dict[str, Any] = {}
    if user is not None:
        params["ciuser"] = user
    if password is not None:
        params["cipassword"] = password
    if ssh_keys is not None:
        params["sshkeys"] = ssh_keys
    if ip_config is not None:
        params["ipconfig0"] = ip_config
    if nameserver is not None:
        params["nameserver"] = nameserver
    if searchdomain is not None:
        params["searchdomain"] = searchdomain

    if not params:
        return {"error": "At least one cloud-init parameter must be provided."}

    node = guest["node"]
    guest_name = guest.get("name", str(vmid))

    client.update_guest_config(node, vmid, "qemu", **params)

    return {
        "success": True,
        "vmid": vmid,
        "name": guest_name,
        "node": node,
        "configured": list(params.keys()),
        "message": f"Cloud-init configured on VM '{guest_name}' ({vmid}). "
        f"Parameters set: {', '.join(params.keys())}. "
        f"Changes take effect on next boot.",
    }
