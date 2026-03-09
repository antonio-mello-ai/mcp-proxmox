"""Proxmox VE API client wrapper."""

from __future__ import annotations

from typing import Any, cast

from proxmoxer import ProxmoxAPI  # type: ignore[import-untyped]

from mcp_proxmox.config import ProxmoxConfig


class ProxmoxClient:
    """Thin wrapper around proxmoxer providing typed access to Proxmox VE API.

    Handles connection lifecycle and provides helper methods for common
    operations like resolving a VMID to its node.
    """

    def __init__(self, config: ProxmoxConfig) -> None:
        self._config = config
        self._api: Any = None

    @property
    def api(self) -> Any:
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
        return cast(list[dict[str, Any]], self.api.nodes.get())

    def get_node_status(self, node: str) -> dict[str, Any]:
        """Get detailed status for a specific node."""
        return cast(dict[str, Any], self.api.nodes(node).status.get())

    def get_cluster_resources(self, resource_type: str | None = None) -> list[dict[str, Any]]:
        """Get cluster resources, optionally filtered by type (vm, storage, node)."""
        if resource_type:
            return cast(list[dict[str, Any]], self.api.cluster.resources.get(type=resource_type))
        return cast(list[dict[str, Any]], self.api.cluster.resources.get())

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
            return cast(dict[str, Any], self.api.nodes(node).qemu(vmid).status.current.get())
        return cast(dict[str, Any], self.api.nodes(node).lxc(vmid).status.current.get())

    def get_guest_config(self, node: str, vmid: int, guest_type: str) -> dict[str, Any]:
        """Get configuration of a VM or container."""
        if guest_type == "qemu":
            return cast(dict[str, Any], self.api.nodes(node).qemu(vmid).config.get())
        return cast(dict[str, Any], self.api.nodes(node).lxc(vmid).config.get())

    def guest_action(self, node: str, vmid: int, guest_type: str, action: str) -> str:
        """Execute a lifecycle action (start, stop, shutdown, reboot) on a guest.

        Returns the UPID of the task.
        """
        if guest_type == "qemu":
            endpoint = getattr(self.api.nodes(node).qemu(vmid).status, action)
        else:
            endpoint = getattr(self.api.nodes(node).lxc(vmid).status, action)
        return cast(str, endpoint.post())

    def get_snapshots(self, node: str, vmid: int, guest_type: str) -> list[dict[str, Any]]:
        """List snapshots for a VM or container."""
        if guest_type == "qemu":
            return cast(list[dict[str, Any]], self.api.nodes(node).qemu(vmid).snapshot.get())
        return cast(list[dict[str, Any]], self.api.nodes(node).lxc(vmid).snapshot.get())

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
            return cast(str, self.api.nodes(node).qemu(vmid).snapshot.post(**params))
        return cast(str, self.api.nodes(node).lxc(vmid).snapshot.post(**params))

    def rollback_snapshot(self, node: str, vmid: int, guest_type: str, name: str) -> str:
        """Rollback to a snapshot. Returns the UPID of the task."""
        if guest_type == "qemu":
            return cast(str, self.api.nodes(node).qemu(vmid).snapshot(name).rollback.post())
        return cast(str, self.api.nodes(node).lxc(vmid).snapshot(name).rollback.post())

    # --- Storage ---

    def get_storages(self, node: str) -> list[dict[str, Any]]:
        """List storage pools available on a node."""
        return cast(list[dict[str, Any]], self.api.nodes(node).storage.get())

    def get_storage_content(
        self,
        node: str,
        storage: str,
        content_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """List content of a storage pool (ISOs, templates, disk images, backups).

        content_type: 'iso', 'vztmpl', 'backup', 'images', 'rootdir', or None for all.
        """
        params: dict[str, Any] = {}
        if content_type:
            params["content"] = content_type
        return cast(
            list[dict[str, Any]], self.api.nodes(node).storage(storage).content.get(**params)
        )

    # --- Provisioning ---

    def get_next_vmid(self) -> int:
        """Get the next available VMID from the cluster."""
        return cast(int, self.api.cluster.nextid.get())

    def create_vm(self, node: str, vmid: int, **params: Any) -> str:
        """Create a QEMU VM. Returns the UPID of the task."""
        return cast(str, self.api.nodes(node).qemu.post(vmid=vmid, **params))

    def create_container(self, node: str, vmid: int, **params: Any) -> str:
        """Create an LXC container. Returns the UPID of the task."""
        return cast(str, self.api.nodes(node).lxc.post(vmid=vmid, **params))

    def clone_guest(
        self,
        node: str,
        vmid: int,
        guest_type: str,
        newid: int,
        **params: Any,
    ) -> str:
        """Clone a VM or container. Returns the UPID of the task."""
        if guest_type == "qemu":
            return cast(str, self.api.nodes(node).qemu(vmid).clone.post(newid=newid, **params))
        return cast(str, self.api.nodes(node).lxc(vmid).clone.post(newid=newid, **params))

    def delete_guest(self, node: str, vmid: int, guest_type: str) -> str:
        """Delete a VM or container. Returns the UPID of the task."""
        if guest_type == "qemu":
            return cast(str, self.api.nodes(node).qemu(vmid).delete())
        return cast(str, self.api.nodes(node).lxc(vmid).delete())

    def delete_snapshot(self, node: str, vmid: int, guest_type: str, name: str) -> str:
        """Delete a snapshot. Returns the UPID of the task."""
        if guest_type == "qemu":
            return cast(str, self.api.nodes(node).qemu(vmid).snapshot(name).delete())
        return cast(str, self.api.nodes(node).lxc(vmid).snapshot(name).delete())

    # --- Backup ---

    def create_backup(self, node: str, vmid: int, **params: Any) -> str:
        """Create a backup via vzdump. Returns the UPID of the task."""
        return cast(str, self.api.nodes(node).vzdump.post(vmid=vmid, **params))

    def restore_vm(self, node: str, vmid: int, archive: str, **params: Any) -> str:
        """Restore a VM from a backup archive. Returns the UPID of the task."""
        return cast(str, self.api.nodes(node).qemu.post(vmid=vmid, archive=archive, **params))

    def restore_container(self, node: str, vmid: int, archive: str, **params: Any) -> str:
        """Restore a container from a backup archive. Returns the UPID of the task."""
        return cast(
            str,
            self.api.nodes(node).lxc.post(vmid=vmid, ostemplate=archive, restore=1, **params),
        )

    # --- Command Execution ---

    def exec_qemu_agent(self, node: str, vmid: int, command: str) -> dict[str, Any]:
        """Execute a command via QEMU guest agent. Returns the PID."""
        return cast(
            dict[str, Any],
            self.api.nodes(node).qemu(vmid).agent.exec.post(command=command),
        )

    def exec_qemu_agent_status(self, node: str, vmid: int, pid: int) -> dict[str, Any]:
        """Get execution result from QEMU guest agent by PID."""
        return cast(
            dict[str, Any],
            self.api.nodes(node).qemu(vmid).agent("exec-status").get(pid=pid),
        )

    # --- Network ---

    def get_networks(self, node: str) -> list[dict[str, Any]]:
        """List network interfaces/bridges on a node."""
        return cast(list[dict[str, Any]], self.api.nodes(node).network.get())

    # --- Resize ---

    def update_guest_config(
        self, node: str, vmid: int, guest_type: str, **params: Any
    ) -> None:
        """Update VM or container configuration (CPU, memory, etc.)."""
        if guest_type == "qemu":
            self.api.nodes(node).qemu(vmid).config.put(**params)
        else:
            self.api.nodes(node).lxc(vmid).config.put(**params)

    def resize_guest_disk(
        self, node: str, vmid: int, guest_type: str, disk: str, size: str
    ) -> None:
        """Resize a guest disk. size format: '+10G' (relative) or '50G' (absolute)."""
        if guest_type == "qemu":
            self.api.nodes(node).qemu(vmid).resize.put(disk=disk, size=size)
        else:
            self.api.nodes(node).lxc(vmid).resize.put(disk=disk, size=size)

    def get_tasks(self, node: str, limit: int = 20) -> list[dict[str, Any]]:
        """List recent tasks on a node."""
        return cast(list[dict[str, Any]], self.api.nodes(node).tasks.get(limit=limit))

    def get_task_status(self, node: str, upid: str) -> dict[str, Any]:
        """Get status of a specific task."""
        return cast(dict[str, Any], self.api.nodes(node).tasks(upid).status.get())

    def get_rrd_data(
        self, node: str, vmid: int, guest_type: str, timeframe: str = "hour"
    ) -> list[dict[str, Any]]:
        """Get RRD metrics data for a guest. Timeframe: hour, day, week, month, year."""
        if guest_type == "qemu":
            return cast(
                list[dict[str, Any]],
                self.api.nodes(node).qemu(vmid).rrddata.get(timeframe=timeframe),
            )
        return cast(
            list[dict[str, Any]],
            self.api.nodes(node).lxc(vmid).rrddata.get(timeframe=timeframe),
        )
