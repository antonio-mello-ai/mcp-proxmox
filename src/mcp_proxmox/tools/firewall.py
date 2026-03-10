"""Firewall rule management tools."""

from __future__ import annotations

from typing import Any

from mcp_proxmox.client import ProxmoxClient


def list_firewall_rules(
    client: ProxmoxClient,
    vmid: int | None = None,
    node: str | None = None,
) -> dict[str, Any]:
    """List firewall rules for a VM/CT, a node, or the cluster."""
    if vmid is not None:
        guest = client.find_guest(vmid)
        if not guest:
            return {"error": f"Guest {vmid} not found."}
        guest_node = guest["node"]
        guest_type = guest["type"]
        guest_name = guest.get("name", str(vmid))
        rules = client.get_guest_firewall_rules(guest_node, vmid, guest_type)
        return {
            "vmid": vmid,
            "name": guest_name,
            "type": "qemu" if guest_type == "qemu" else "lxc",
            "node": guest_node,
            "rules": rules,
            "count": len(rules),
        }

    if node is not None:
        rules = client.get_node_firewall_rules(node)
        return {"node": node, "rules": rules, "count": len(rules)}

    rules = client.get_cluster_firewall_rules()
    return {"level": "cluster", "rules": rules, "count": len(rules)}


def add_firewall_rule(
    client: ProxmoxClient,
    action: str,
    type_: str,
    vmid: int | None = None,
    node: str | None = None,
    proto: str | None = None,
    dport: str | None = None,
    sport: str | None = None,
    source: str | None = None,
    dest: str | None = None,
    iface: str | None = None,
    enable: bool = True,
    comment: str = "",
    pos: int | None = None,
) -> dict[str, Any]:
    """Add a firewall rule to a guest, node, or cluster."""
    params: dict[str, Any] = {
        "action": action.upper(),
        "type": type_.lower(),
        "enable": 1 if enable else 0,
    }
    if proto:
        params["proto"] = proto
    if dport:
        params["dport"] = dport
    if sport:
        params["sport"] = sport
    if source:
        params["source"] = source
    if dest:
        params["dest"] = dest
    if iface:
        params["iface"] = iface
    if comment:
        params["comment"] = comment
    if pos is not None:
        params["pos"] = pos

    if vmid is not None:
        guest = client.find_guest(vmid)
        if not guest:
            return {"error": f"Guest {vmid} not found."}
        client.add_guest_firewall_rule(guest["node"], vmid, guest["type"], **params)
        return {
            "success": True,
            "level": "guest",
            "vmid": vmid,
            "name": guest.get("name", str(vmid)),
            "rule": params,
        }

    if node is not None:
        client.add_node_firewall_rule(node, **params)
        return {"success": True, "level": "node", "node": node, "rule": params}

    client.add_cluster_firewall_rule(**params)
    return {"success": True, "level": "cluster", "rule": params}


def delete_firewall_rule(
    client: ProxmoxClient,
    pos: int,
    vmid: int | None = None,
    node: str | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    """Delete a firewall rule by position."""
    level = "cluster"
    label = "cluster"

    if vmid is not None:
        guest = client.find_guest(vmid)
        if not guest:
            return {"error": f"Guest {vmid} not found."}
        level = "guest"
        label = f"{guest.get('name', vmid)} ({vmid})"
    elif node is not None:
        level = "node"
        label = node

    if not confirm:
        return {
            "warning": f"This will delete firewall rule at position {pos} "
            f"from {level} '{label}'. "
            f"Call again with confirm=true to proceed.",
            "level": level,
            "pos": pos,
        }

    if vmid is not None:
        guest = client.find_guest(vmid)
        if not guest:
            return {"error": f"Guest {vmid} not found."}
        client.delete_guest_firewall_rule(guest["node"], vmid, guest["type"], pos)
    elif node is not None:
        client.delete_node_firewall_rule(node, pos)
    else:
        client.delete_cluster_firewall_rule(pos)

    return {"success": True, "level": level, "pos": pos, "deleted_from": label}
