"""Monitoring tools: metrics and task tracking."""

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


def get_guest_metrics(
    client: ProxmoxClient,
    vmid: int,
    timeframe: str = "hour",
) -> dict[str, Any]:
    """Get resource usage metrics (CPU, memory, disk, network) for a VM or container.

    Timeframe options: hour, day, week, month, year.
    """
    valid_timeframes = ("hour", "day", "week", "month", "year")
    if timeframe not in valid_timeframes:
        return {"error": f"Invalid timeframe '{timeframe}'. Must be one of: {valid_timeframes}"}

    guest = client.find_guest(vmid)
    if not guest:
        return {"error": f"Guest with VMID {vmid} not found in cluster"}

    node = guest["node"]
    guest_type = guest["type"]
    guest_name = guest.get("name", f"VMID {vmid}")
    rrd_data = client.get_rrd_data(node, vmid, guest_type, timeframe)

    if not rrd_data:
        return {"vmid": vmid, "name": guest_name, "message": "No metrics data available"}

    # Get the most recent data point with valid values
    latest = None
    for point in reversed(rrd_data):
        if point.get("cpu") is not None:
            latest = point
            break

    if not latest:
        return {"vmid": vmid, "name": guest_name, "message": "No recent metrics available"}

    result: dict[str, Any] = {
        "vmid": vmid,
        "name": guest_name,
        "type": "VM" if guest_type == "qemu" else "Container",
        "timeframe": timeframe,
        "current": {
            "cpu_usage": f"{(latest.get('cpu', 0) or 0) * 100:.1f}%",
            "memory_used": _format_bytes(latest.get("mem", 0) or 0),
            "memory_total": _format_bytes(latest.get("maxmem", 0) or 0),
        },
    }

    if latest.get("netin") is not None:
        result["current"]["network_in"] = _format_bytes(latest.get("netin", 0) or 0)
        result["current"]["network_out"] = _format_bytes(latest.get("netout", 0) or 0)

    if latest.get("diskread") is not None:
        result["current"]["disk_read"] = _format_bytes(latest.get("diskread", 0) or 0)
        result["current"]["disk_write"] = _format_bytes(latest.get("diskwrite", 0) or 0)

    # Compute averages over the timeframe
    cpu_values = [p.get("cpu", 0) or 0 for p in rrd_data if p.get("cpu") is not None]
    mem_values = [p.get("mem", 0) or 0 for p in rrd_data if p.get("mem") is not None]

    if cpu_values:
        result["averages"] = {
            "cpu_avg": f"{sum(cpu_values) / len(cpu_values) * 100:.1f}%",
            "cpu_max": f"{max(cpu_values) * 100:.1f}%",
            "memory_avg": _format_bytes(sum(mem_values) / len(mem_values)) if mem_values else "N/A",
            "data_points": len(cpu_values),
        }

    return result


def list_tasks(
    client: ProxmoxClient,
    node: str,
    limit: int = 20,
    status_filter: str | None = None,
) -> dict[str, Any]:
    """List recent tasks on a node, optionally filtered by status (ok, error, running)."""
    tasks = client.get_tasks(node, limit=min(limit, 100))

    result = []
    for task in tasks:
        task_status = task.get("status", "")
        if status_filter and task_status != status_filter:
            continue
        result.append(
            {
                "upid": task.get("upid"),
                "type": task.get("type"),
                "status": task_status,
                "user": task.get("user"),
                "starttime": task.get("starttime"),
                "endtime": task.get("endtime"),
                "node": task.get("node"),
            }
        )

    return {
        "node": node,
        "total": len(result),
        "tasks": result,
    }
