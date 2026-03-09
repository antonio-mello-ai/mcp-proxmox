"""Discovery tools: list and inspect nodes, VMs, and containers."""

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


def _format_uptime(seconds: int | float) -> str:
    """Format seconds into human-readable uptime string."""
    seconds = int(seconds)
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    return " ".join(parts) or "0m"


def list_nodes(client: ProxmoxClient) -> list[dict[str, Any]]:
    """List all nodes in the Proxmox cluster with their status and resource usage."""
    nodes = client.get_nodes()
    result = []
    for node in nodes:
        maxmem = node.get("maxmem", 0)
        mem = node.get("mem", 0)
        maxcpu = node.get("maxcpu", 0)
        cpu = node.get("cpu", 0)
        result.append(
            {
                "node": node.get("node"),
                "status": node.get("status"),
                "cpu_usage": f"{cpu * 100:.1f}%",
                "cpu_cores": maxcpu,
                "memory_used": _format_bytes(mem),
                "memory_total": _format_bytes(maxmem),
                "memory_usage": f"{(mem / maxmem * 100):.1f}%" if maxmem else "N/A",
                "uptime": _format_uptime(node.get("uptime", 0)),
            }
        )
    return result


def get_node_status(client: ProxmoxClient, node: str) -> dict[str, Any]:
    """Get detailed status and metrics for a specific node."""
    status = client.get_node_status(node)
    cpu_info = status.get("cpuinfo", {})
    memory = status.get("memory", {})
    rootfs = status.get("rootfs", {})

    return {
        "node": node,
        "uptime": _format_uptime(status.get("uptime", 0)),
        "kernel_version": status.get("kversion", "unknown"),
        "pve_version": status.get("pveversion", "unknown"),
        "cpu": {
            "model": cpu_info.get("model", "unknown"),
            "cores": cpu_info.get("cores"),
            "cpus": cpu_info.get("cpus"),
            "sockets": cpu_info.get("sockets"),
            "usage": f"{status.get('cpu', 0) * 100:.1f}%",
            "load_average": status.get("loadavg", []),
        },
        "memory": {
            "total": _format_bytes(memory.get("total", 0)),
            "used": _format_bytes(memory.get("used", 0)),
            "free": _format_bytes(memory.get("free", 0)),
            "usage": (
                f"{(memory.get('used', 0) / memory.get('total', 1) * 100):.1f}%"
                if memory.get("total")
                else "N/A"
            ),
        },
        "rootfs": {
            "total": _format_bytes(rootfs.get("total", 0)),
            "used": _format_bytes(rootfs.get("used", 0)),
            "free": _format_bytes(rootfs.get("avail", 0)),
        },
    }


def list_vms(
    client: ProxmoxClient,
    node: str | None = None,
    status_filter: str | None = None,
) -> list[dict[str, Any]]:
    """List all QEMU VMs across the cluster, optionally filtered by node or status."""
    resources = client.get_cluster_resources("vm")
    result = []
    for r in resources:
        if r.get("type") != "qemu":
            continue
        if node and r.get("node") != node:
            continue
        if status_filter and r.get("status") != status_filter:
            continue
        maxmem = r.get("maxmem", 0)
        mem = r.get("mem", 0)
        maxcpu = r.get("maxcpu", 0)
        cpu = r.get("cpu", 0)
        result.append(
            {
                "vmid": r.get("vmid"),
                "name": r.get("name", ""),
                "node": r.get("node"),
                "status": r.get("status"),
                "cpu_usage": f"{cpu * 100:.1f}%",
                "cpu_cores": maxcpu,
                "memory_used": _format_bytes(mem),
                "memory_total": _format_bytes(maxmem),
                "uptime": _format_uptime(r.get("uptime", 0)),
            }
        )
    return sorted(result, key=lambda x: x["vmid"])


def list_containers(
    client: ProxmoxClient,
    node: str | None = None,
    status_filter: str | None = None,
) -> list[dict[str, Any]]:
    """List all LXC containers across the cluster, optionally filtered by node or status."""
    resources = client.get_cluster_resources("vm")
    result = []
    for r in resources:
        if r.get("type") != "lxc":
            continue
        if node and r.get("node") != node:
            continue
        if status_filter and r.get("status") != status_filter:
            continue
        maxmem = r.get("maxmem", 0)
        mem = r.get("mem", 0)
        maxcpu = r.get("maxcpu", 0)
        cpu = r.get("cpu", 0)
        result.append(
            {
                "vmid": r.get("vmid"),
                "name": r.get("name", ""),
                "node": r.get("node"),
                "status": r.get("status"),
                "cpu_usage": f"{cpu * 100:.1f}%",
                "cpu_cores": maxcpu,
                "memory_used": _format_bytes(mem),
                "memory_total": _format_bytes(maxmem),
                "uptime": _format_uptime(r.get("uptime", 0)),
            }
        )
    return sorted(result, key=lambda x: x["vmid"])


def get_guest_status(client: ProxmoxClient, vmid: int) -> dict[str, Any]:
    """Get detailed status of a VM or container by VMID (auto-detects type and node)."""
    guest = client.find_guest(vmid)
    if not guest:
        return {"error": f"Guest with VMID {vmid} not found in cluster"}

    node = guest["node"]
    guest_type = guest["type"]
    status = client.get_guest_status(node, vmid, guest_type)
    config = client.get_guest_config(node, vmid, guest_type)

    maxmem = status.get("maxmem", 0)
    mem = status.get("mem", 0)

    result: dict[str, Any] = {
        "vmid": vmid,
        "name": status.get("name", config.get("name", "")),
        "type": "VM" if guest_type == "qemu" else "Container",
        "node": node,
        "status": status.get("status"),
        "cpu_cores": status.get("cpus", config.get("cores", 0)),
        "cpu_usage": f"{status.get('cpu', 0) * 100:.1f}%",
        "memory_used": _format_bytes(mem),
        "memory_total": _format_bytes(maxmem),
        "memory_usage": f"{(mem / maxmem * 100):.1f}%" if maxmem else "N/A",
        "uptime": _format_uptime(status.get("uptime", 0)),
        "pid": status.get("pid"),
    }

    if guest_type == "qemu":
        result["qemu_version"] = status.get("qemu", "")
    if config.get("description"):
        result["description"] = config["description"]

    return result
