"""MCP server for Proxmox VE management."""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_proxmox.client import ProxmoxClient
from mcp_proxmox.config import ProxmoxConfig
from mcp_proxmox.tools import (
    backup,
    discovery,
    execute,
    lifecycle,
    monitoring,
    provisioning,
    snapshots,
    storage,
)

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


@mcp.tool()
def delete_snapshot(vmid: int, name: str, confirm: bool = False) -> str:
    """Delete a snapshot from a VM or container.

    Args:
        vmid: The numeric ID of the VM or container.
        name: Name of the snapshot to delete.
        confirm: Must be true to execute. First call without confirm shows a warning.
    """
    return _to_text(snapshots.delete_snapshot(_get_client(), vmid, name, confirm))


# --- Storage Tools ---


@mcp.tool()
def list_storages(node: str | None = None) -> str:
    """List storage pools across the cluster with capacity and usage info.

    Args:
        node: Optional. Filter by node name.
    """
    return _to_text(storage.list_storages(_get_client(), node))


@mcp.tool()
def list_storage_content(node: str, storage_name: str, content_type: str | None = None) -> str:
    """List content of a storage pool (ISOs, templates, backups, disk images).

    Args:
        node: Name of the Proxmox node.
        storage_name: Name of the storage pool (e.g. 'local', 'local-lvm').
        content_type: Optional. Filter by type: 'iso', 'vztmpl', 'backup', 'images', 'rootdir'.
    """
    return _to_text(storage.list_storage_content(_get_client(), node, storage_name, content_type))


# --- Provisioning Tools ---


@mcp.tool()
def create_vm(
    node: str,
    name: str,
    cores: int = 1,
    memory: int = 2048,
    disk_size: str = "32G",
    storage_pool: str = "local-lvm",
    iso: str | None = None,
    os_type: str = "l26",
    net_bridge: str = "vmbr0",
    start_after_create: bool = False,
    vmid: int | None = None,
) -> str:
    """Create a new QEMU virtual machine.

    The VM is created stopped by default. Use start_after_create=true to auto-start.

    Args:
        node: Target node name (e.g. 'pve').
        name: VM name.
        cores: Number of CPU cores (default 1).
        memory: Memory in MB (default 2048).
        disk_size: Disk size with unit (default '32G'). Examples: '10G', '100G', '1T'.
        storage_pool: Storage for disk (default 'local-lvm').
        iso: Optional ISO volume ID for installation (e.g. 'local:iso/ubuntu-24.04.iso').
        os_type: OS type (default 'l26' for Linux). Options: l26, l24, win11, win10, other.
        net_bridge: Network bridge (default 'vmbr0').
        start_after_create: Start VM after creation (default false).
        vmid: Optional specific VMID. Auto-assigned if not provided.
    """
    return _to_text(
        provisioning.create_vm(
            _get_client(),
            node=node,
            name=name,
            cores=cores,
            memory=memory,
            disk_size=disk_size,
            storage=storage_pool,
            iso=iso,
            os_type=os_type,
            net_bridge=net_bridge,
            start_after_create=start_after_create,
            vmid=vmid,
        )
    )


@mcp.tool()
def create_container(
    node: str,
    name: str,
    template: str,
    cores: int = 1,
    memory: int = 512,
    disk_size: int = 8,
    storage_pool: str = "local-lvm",
    net_bridge: str = "vmbr0",
    password: str | None = None,
    ssh_public_keys: str | None = None,
    start_after_create: bool = False,
    vmid: int | None = None,
) -> str:
    """Create a new LXC container from a template.

    Args:
        node: Target node name (e.g. 'pve').
        name: Container hostname.
        template: Template volume ID (e.g. 'local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst').
            Use list_storage_content with content_type='vztmpl' to find available templates.
        cores: Number of CPU cores (default 1).
        memory: Memory in MB (default 512).
        disk_size: Root disk size in GB (default 8).
        storage_pool: Storage for rootfs (default 'local-lvm').
        net_bridge: Network bridge (default 'vmbr0').
        password: Optional root password.
        ssh_public_keys: Optional SSH public keys for root access.
        start_after_create: Start container after creation (default false).
        vmid: Optional specific VMID. Auto-assigned if not provided.
    """
    return _to_text(
        provisioning.create_container(
            _get_client(),
            node=node,
            name=name,
            template=template,
            cores=cores,
            memory=memory,
            disk_size=disk_size,
            storage=storage_pool,
            net_bridge=net_bridge,
            password=password,
            ssh_public_keys=ssh_public_keys,
            start_after_create=start_after_create,
            vmid=vmid,
        )
    )


@mcp.tool()
def clone_guest(
    vmid: int,
    new_name: str | None = None,
    target_node: str | None = None,
    full_clone: bool = True,
    target_storage: str | None = None,
    new_vmid: int | None = None,
) -> str:
    """Clone an existing VM or container. Auto-detects type and node.

    Creates a full (independent) clone by default. Set full_clone=false for a linked clone.

    Args:
        vmid: Source VM/container VMID to clone.
        new_name: Optional name for the clone.
        target_node: Optional target node for the clone (for cross-node cloning).
        full_clone: Full clone (true, default) or linked clone (false).
        target_storage: Optional target storage for the clone's disks.
        new_vmid: Optional VMID for the clone. Auto-assigned if not provided.
    """
    return _to_text(
        provisioning.clone_guest(
            _get_client(),
            vmid=vmid,
            new_name=new_name,
            target_node=target_node,
            full_clone=full_clone,
            target_storage=target_storage,
            new_vmid=new_vmid,
        )
    )


@mcp.tool()
def delete_guest(vmid: int, confirm: bool = False) -> str:
    """Permanently delete a VM or container. IRREVERSIBLE.

    The guest must be stopped before deletion. All disk images will be destroyed.

    Args:
        vmid: The numeric ID of the VM or container to delete.
        confirm: Must be true to execute. First call without confirm shows a warning.
    """
    return _to_text(provisioning.delete_guest(_get_client(), vmid, confirm))


# --- Backup Tools ---


@mcp.tool()
def list_backups(
    node: str | None = None,
    storage_name: str | None = None,
    vmid: int | None = None,
) -> str:
    """List backup files across storages.

    Args:
        node: Optional. Filter by node name.
        storage_name: Optional. Filter by storage name.
        vmid: Optional. Filter by VMID to see backups of a specific guest.
    """
    return _to_text(backup.list_backups(_get_client(), node, storage_name, vmid))


@mcp.tool()
def create_backup(
    vmid: int,
    storage_name: str = "local",
    mode: str = "snapshot",
    compress: str = "zstd",
    notes: str = "",
) -> str:
    """Create a backup (vzdump) of a VM or container.

    Args:
        vmid: The numeric ID of the VM or container to back up.
        storage_name: Target storage for the backup (default 'local').
        mode: Backup mode: 'snapshot' (no downtime, default), 'suspend', or 'stop'.
        compress: Compression: 'zstd' (default), 'lzo', 'gzip', or '0' (none).
        notes: Optional notes/description for the backup.
    """
    return _to_text(backup.create_backup(_get_client(), vmid, storage_name, mode, compress, notes))


@mcp.tool()
def restore_backup(
    volid: str,
    node: str,
    vmid: int | None = None,
    storage_pool: str = "local-lvm",
    guest_type: str = "vm",
    confirm: bool = False,
) -> str:
    """Restore a VM or container from a backup file.

    Args:
        volid: Volume ID of the backup (e.g. 'local:backup/vzdump-qemu-100-2024_03_04.vma.zst').
            Use list_backups to find available backups.
        node: Target node for the restored guest.
        vmid: Optional VMID for the restored guest. Auto-assigned if not provided.
        storage_pool: Storage for restored disks (default 'local-lvm').
        guest_type: Type of guest: 'vm' or 'container'.
        confirm: Must be true to execute. First call without confirm shows a warning.
    """
    return _to_text(
        backup.restore_backup(_get_client(), volid, node, vmid, storage_pool, guest_type, confirm)
    )


# --- Command Execution Tools ---


@mcp.tool()
def exec_command(vmid: int, command: str, timeout: int = 30) -> str:
    """Execute a command inside a QEMU VM via the guest agent.

    Requires qemu-guest-agent to be installed and running inside the VM.
    Not supported for LXC containers.

    Args:
        vmid: The numeric ID of the VM.
        command: The command to execute (e.g. 'hostname', 'df -h', 'systemctl status nginx').
        timeout: Max seconds to wait for command completion (default 30, max 300).
    """
    return _to_text(execute.exec_command(_get_client(), vmid, command, timeout))


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
