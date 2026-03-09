"""Network tools: list network interfaces and bridges."""

from __future__ import annotations

from typing import Any

from mcp_proxmox.client import ProxmoxClient


def list_networks(client: ProxmoxClient, node: str) -> dict[str, Any]:
    """List network interfaces, bridges, and bonds on a node."""
    nodes = client.get_nodes()
    if not any(n.get("node") == node for n in nodes):
        return {"error": f"Node '{node}' not found in cluster"}

    interfaces = client.get_networks(node)

    result: list[dict[str, Any]] = []
    for iface in interfaces:
        entry: dict[str, Any] = {
            "name": iface.get("iface", ""),
            "type": iface.get("type", ""),
            "active": bool(iface.get("active", 0)),
        }
        if iface.get("address"):
            entry["address"] = iface["address"]
        if iface.get("netmask"):
            entry["netmask"] = iface["netmask"]
        if iface.get("gateway"):
            entry["gateway"] = iface["gateway"]
        if iface.get("cidr"):
            entry["cidr"] = iface["cidr"]
        if iface.get("bridge_ports"):
            entry["bridge_ports"] = iface["bridge_ports"]
        if iface.get("bridge_stp"):
            entry["bridge_stp"] = iface["bridge_stp"]
        if iface.get("slaves"):
            entry["bond_slaves"] = iface["slaves"]
        if iface.get("comments"):
            entry["comments"] = iface["comments"]
        if iface.get("autostart"):
            entry["autostart"] = bool(iface["autostart"])

        result.append(entry)

    # Group by type for cleaner output
    bridges = [i for i in result if i["type"] == "bridge"]
    bonds = [i for i in result if i["type"] == "bond"]
    eths = [i for i in result if i["type"] == "eth"]
    others = [i for i in result if i["type"] not in ("bridge", "bond", "eth")]

    return {
        "node": node,
        "total": len(result),
        "bridges": bridges,
        "bonds": bonds,
        "physical": eths,
        "other": others,
    }
