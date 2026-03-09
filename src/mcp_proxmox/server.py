"""MCP server for Proxmox VE management."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_proxmox.client import ProxmoxClient
from mcp_proxmox.config import ProxmoxConfig
from mcp_proxmox.tools import discovery, lifecycle, monitoring, snapshots

mcp = FastMCP("mcp-proxmox")  # type: ignore[call-arg]

_client: ProxmoxClient | None = None


def _get_client() -> ProxmoxClient:
    """Get or create the Proxmox client singleton."""
    global _client
    if _client is None:
        config = ProxmoxConfig.from_env()
        _client = ProxmoxClient(config)
    return _client


def _to_text(data: Any) -> str:
    """Convert tool output to formatted text for the LLM."""
    return json.dumps(data, indent=2, default=str)


# --- Discovery Tools ---


@mcp.tool()
def list_nodes() -> str:
    """List all nodes in the Proxmox cluster with status, CPU, memory, and uptime."""
    return _to_text(discovery.list_nodes(_get_client()))


@mcp.tool()
def get_node_status(node: str) -> str:
    """Get detailed status for a specific node including CPU model, memory, disk, and versions.

    Args:
        node: Name of the Proxmox node (e.g. 'pve', 'node1').
    """
    return _to_text(discovery.get_node_status(_get_client(), node))


@mcp.tool()
def list_vms(node: str | None = None, status: str | None = None) -> str:
    """List all QEMU virtual machines across the cluster.

    Args:
        node: Optional. Filter by node name.
        status: Optional. Filter by status ('running', 'stopped').
    """
    return _to_text(discovery.list_vms(_get_client(), node, status))


@mcp.tool()
def list_containers(node: str | None = None, status: str | None = None) -> str:
    """List all LXC containers across the cluster.

    Args:
        node: Optional. Filter by node name.
        status: Optional. Filter by status ('running', 'stopped').
    """
    return _to_text(discovery.list_containers(_get_client(), node, status))


@mcp.tool()
def get_guest_status(vmid: int) -> str:
    """Get detailed status of a VM or container by VMID. Auto-detects type and node.

    Args:
        vmid: The numeric ID of the VM or container (e.g. 100, 200).
    """
    return _to_text(discovery.get_guest_status(_get_client(), vmid))


# --- Lifecycle Tools ---


@mcp.tool()
def start_guest(vmid: int) -> str:
    """Start a stopped VM or container.

    Args:
        vmid: The numeric ID of the VM or container to start.
    """
    return _to_text(lifecycle.start_guest(_get_client(), vmid))


@mcp.tool()
def stop_guest(vmid: int, confirm: bool = False) -> str:
    """Force-stop a running VM or container. WARNING: May cause data loss.

    Args:
        vmid: The numeric ID of the VM or container to stop.
        confirm: Must be true to execute. First call without confirm shows a warning.
    """
    return _to_text(lifecycle.stop_guest(_get_client(), vmid, confirm))


@mcp.tool()
def shutdown_guest(vmid: int) -> str:
    """Gracefully shut down a VM or container via ACPI signal (VMs) or init (containers).

    Args:
        vmid: The numeric ID of the VM or container to shut down.
    """
    return _to_text(lifecycle.shutdown_guest(_get_client(), vmid))


@mcp.tool()
def reboot_guest(vmid: int, confirm: bool = False) -> str:
    """Reboot a running VM or container.

    Args:
        vmid: The numeric ID of the VM or container to reboot.
        confirm: Must be true to execute. First call without confirm shows a warning.
    """
    return _to_text(lifecycle.reboot_guest(_get_client(), vmid, confirm))


# --- Snapshot Tools ---


@mcp.tool()
def list_snapshots(vmid: int) -> str:
    """List all snapshots for a VM or container.

    Args:
        vmid: The numeric ID of the VM or container.
    """
    return _to_text(snapshots.list_snapshots(_get_client(), vmid))


@mcp.tool()
def create_snapshot(vmid: int, name: str, description: str = "") -> str:
    """Create a new snapshot for a VM or container.

    Args:
        vmid: The numeric ID of the VM or container.
        name: Snapshot name (alphanumeric, hyphens, underscores).
        description: Optional description for the snapshot.
    """
    return _to_text(snapshots.create_snapshot(_get_client(), vmid, name, description))


@mcp.tool()
def rollback_snapshot(vmid: int, name: str, confirm: bool = False) -> str:
    """Rollback a VM or container to a previous snapshot.

    WARNING: All changes since the snapshot will be LOST.

    Args:
        vmid: The numeric ID of the VM or container.
        name: Name of the snapshot to rollback to.
        confirm: Must be true to execute. First call without confirm shows a warning.
    """
    return _to_text(snapshots.rollback_snapshot(_get_client(), vmid, name, confirm))


# --- Monitoring Tools ---


@mcp.tool()
def get_guest_metrics(vmid: int, timeframe: str = "hour") -> str:
    """Get resource usage metrics (CPU, memory, network, disk I/O) for a VM or container.

    Args:
        vmid: The numeric ID of the VM or container.
        timeframe: Time range for metrics. Options: 'hour', 'day', 'week', 'month', 'year'.
    """
    return _to_text(monitoring.get_guest_metrics(_get_client(), vmid, timeframe))


@mcp.tool()
def list_tasks(node: str, limit: int = 20, status: str | None = None) -> str:
    """List recent tasks on a Proxmox node (backups, migrations, snapshots, etc.).

    Args:
        node: Name of the Proxmox node.
        limit: Maximum number of tasks to return (default 20, max 100).
        status: Optional. Filter by task status ('ok', 'error', 'running').
    """
    return _to_text(monitoring.list_tasks(_get_client(), node, limit, status))


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
