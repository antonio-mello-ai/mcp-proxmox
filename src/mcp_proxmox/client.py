"""Proxmox VE API client wrapper."""

from __future__ import annotations

from typing import Any

from proxmoxer import ProxmoxAPI

from mcp_proxmox.config import ProxmoxConfig


class ProxmoxClient:
    """Thin wrapper around proxmoxer providing typed access to Proxmox VE API.

    Handles connection lifecycle and provides helper methods for common
    operations like resolving a VMID to its node.
    """

    def __init__(self, config: ProxmoxConfig) -> None:
        self._config = config
        self._api: ProxmoxAPI | None = None

    @property
    def api(self) -> ProxmoxAPI:
        """Lazy-initialize and return the Proxmox API connection."""
        if self._api is None:
            self._api = ProxmoxAPI(
                self._config.host,
                port=self._config.port,
                user=self._config.token_id.split("!")[0],
                token_name=self._config.token_id.split("!")[-1],
                token_value=self._config.token_secret,
                verify_ssl=self._config.verify_ssl,
                timeout=30,
            )
        return self._api

    def get_nodes(self) -> list[dict[str, Any]]:
        """List all nodes in the cluster."""
        return self.api.nodes.get()

    def get_node_status(self, node: str) -> dict[str, Any]:
        """Get detailed status for a specific node."""
        return self.api.nodes(node).status.get()

    def get_cluster_resources(self, resource_type: str | None = None) -> list[dict[str, Any]]:
        """Get cluster resources, optionally filtered by type (vm, storage, node)."""
        if resource_type:
            return self.api.cluster.resources.get(type=resource_type)
        return self.api.cluster.resources.get()

    def find_guest(self, vmid: int) -> dict[str, Any] | None:
        """Find a VM or container by VMID across all nodes.

        Returns a dict with 'node', 'type' ('qemu' or 'lxc'), and 'vmid',
        or None if not found.
        """
        for resource in self.get_cluster_resources():
            if resource.get("vmid") == vmid and resource.get("type") in ("qemu", "lxc"):
                return resource
        return None

    def get_guest_status(self, node: str, vmid: int, guest_type: str) -> dict[str, Any]:
        """Get current status of a VM or container."""
        if guest_type == "qemu":
            return self.api.nodes(node).qemu(vmid).status.current.get()
        return self.api.nodes(node).lxc(vmid).status.current.get()

    def get_guest_config(self, node: str, vmid: int, guest_type: str) -> dict[str, Any]:
        """Get configuration of a VM or container."""
        if guest_type == "qemu":
            return self.api.nodes(node).qemu(vmid).config.get()
        return self.api.nodes(node).lxc(vmid).config.get()

    def guest_action(self, node: str, vmid: int, guest_type: str, action: str) -> str:
        """Execute a lifecycle action (start, stop, shutdown, reboot) on a guest.

        Returns the UPID of the task.
        """
        if guest_type == "qemu":
            endpoint = getattr(self.api.nodes(node).qemu(vmid).status, action)
        else:
            endpoint = getattr(self.api.nodes(node).lxc(vmid).status, action)
        return endpoint.post()

    def get_snapshots(self, node: str, vmid: int, guest_type: str) -> list[dict[str, Any]]:
        """List snapshots for a VM or container."""
        if guest_type == "qemu":
            return self.api.nodes(node).qemu(vmid).snapshot.get()
        return self.api.nodes(node).lxc(vmid).snapshot.get()

    def create_snapshot(
        self,
        node: str,
        vmid: int,
        guest_type: str,
        name: str,
        description: str = "",
    ) -> str:
        """Create a snapshot. Returns the UPID of the task."""
        params: dict[str, Any] = {"snapname": name}
        if description:
            params["description"] = description
        if guest_type == "qemu":
            return self.api.nodes(node).qemu(vmid).snapshot.post(**params)
        return self.api.nodes(node).lxc(vmid).snapshot.post(**params)

    def rollback_snapshot(self, node: str, vmid: int, guest_type: str, name: str) -> str:
        """Rollback to a snapshot. Returns the UPID of the task."""
        if guest_type == "qemu":
            return self.api.nodes(node).qemu(vmid).snapshot(name).rollback.post()
        return self.api.nodes(node).lxc(vmid).snapshot(name).rollback.post()

    def get_tasks(self, node: str, limit: int = 20) -> list[dict[str, Any]]:
        """List recent tasks on a node."""
        return self.api.nodes(node).tasks.get(limit=limit)

    def get_task_status(self, node: str, upid: str) -> dict[str, Any]:
        """Get status of a specific task."""
        return self.api.nodes(node).tasks(upid).status.get()

    def get_rrd_data(
        self, node: str, vmid: int, guest_type: str, timeframe: str = "hour"
    ) -> list[dict[str, Any]]:
        """Get RRD metrics data for a guest. Timeframe: hour, day, week, month, year."""
        if guest_type == "qemu":
            return self.api.nodes(node).qemu(vmid).rrddata.get(timeframe=timeframe)
        return self.api.nodes(node).lxc(vmid).rrddata.get(timeframe=timeframe)
