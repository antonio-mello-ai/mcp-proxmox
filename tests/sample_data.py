"""Sample data for tests."""

from __future__ import annotations

from typing import Any

SAMPLE_NODES = [
    {
        "node": "pve",
        "status": "online",
        "cpu": 0.15,
        "maxcpu": 8,
        "mem": 8589934592,  # 8 GB
        "maxmem": 34359738368,  # 32 GB
        "uptime": 864000,  # 10 days
    },
]

SAMPLE_CLUSTER_RESOURCES = [
    {
        "vmid": 100,
        "name": "ubuntu-server",
        "node": "pve",
        "type": "qemu",
        "status": "running",
        "cpu": 0.05,
        "maxcpu": 4,
        "mem": 2147483648,
        "maxmem": 8589934592,
        "uptime": 432000,
    },
    {
        "vmid": 101,
        "name": "nginx-proxy",
        "node": "pve",
        "type": "lxc",
        "status": "running",
        "cpu": 0.02,
        "maxcpu": 2,
        "mem": 268435456,
        "maxmem": 1073741824,
        "uptime": 864000,
    },
    {
        "vmid": 102,
        "name": "test-vm",
        "node": "pve",
        "type": "qemu",
        "status": "stopped",
        "cpu": 0,
        "maxcpu": 2,
        "mem": 0,
        "maxmem": 4294967296,
        "uptime": 0,
    },
]

SAMPLE_NODE_STATUS: dict[str, Any] = {
    "uptime": 864000,
    "cpu": 0.15,
    "kversion": "Linux 6.8.12-5-pve",
    "pveversion": "pve-manager/8.3.2",
    "cpuinfo": {
        "model": "Intel(R) Core(TM) i7-12700",
        "cores": 12,
        "cpus": 20,
        "sockets": 1,
    },
    "memory": {
        "total": 34359738368,
        "used": 8589934592,
        "free": 25769803776,
    },
    "rootfs": {
        "total": 107374182400,
        "used": 21474836480,
        "avail": 85899345920,
    },
    "loadavg": ["0.45", "0.38", "0.32"],
}

SAMPLE_STORAGES: list[dict[str, Any]] = [
    {
        "storage": "local",
        "type": "dir",
        "content": "iso,vztmpl,backup",
        "enabled": 1,
        "shared": 0,
        "total": 107374182400,
        "used": 21474836480,
        "avail": 85899345920,
    },
    {
        "storage": "local-lvm",
        "type": "lvmthin",
        "content": "images,rootdir",
        "enabled": 1,
        "shared": 0,
        "total": 536870912000,
        "used": 107374182400,
        "avail": 429496729600,
    },
    {
        "storage": "zfs-pool",
        "type": "zfspool",
        "content": "images,rootdir",
        "enabled": 1,
        "shared": 0,
        "total": 1099511627776,
        "used": 214748364800,
        "avail": 884763262976,
    },
]

SAMPLE_STORAGE_CONTENT: list[dict[str, Any]] = [
    {
        "volid": "local:iso/ubuntu-24.04-live-server-amd64.iso",
        "content": "iso",
        "format": "iso",
        "size": 2415919104,
        "ctime": 1709510400,
    },
    {
        "volid": "local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst",
        "content": "vztmpl",
        "format": "tzst",
        "size": 126877696,
        "ctime": 1709424000,
    },
    {
        "volid": "local:backup/vzdump-qemu-100-2024_03_04-03_00_01.vma.zst",
        "content": "backup",
        "format": "vma.zst",
        "size": 5368709120,
        "ctime": 1709524800,
        "vmid": 100,
        "notes": "Scheduled backup",
    },
]

SAMPLE_NETWORKS: list[dict[str, Any]] = [
    {
        "iface": "vmbr0",
        "type": "bridge",
        "active": 1,
        "address": "192.168.1.100",
        "netmask": "255.255.255.0",
        "gateway": "192.168.1.1",
        "cidr": "192.168.1.100/24",
        "bridge_ports": "enp3s0",
        "bridge_stp": "off",
        "autostart": 1,
    },
    {
        "iface": "enp3s0",
        "type": "eth",
        "active": 1,
    },
    {
        "iface": "vlan10",
        "type": "vlan",
        "active": 1,
        "address": "10.10.10.1",
        "netmask": "255.255.255.0",
        "cidr": "10.10.10.1/24",
        "autostart": 1,
        "comments": "Management VLAN",
    },
]

SAMPLE_SNAPSHOTS = [
    {
        "name": "before-upgrade",
        "description": "Snapshot before system upgrade",
        "snaptime": 1709510400,
        "parent": "",
    },
    {
        "name": "clean-state",
        "description": "",
        "snaptime": 1709424000,
        "parent": "before-upgrade",
    },
    {"name": "current", "description": "You are here!", "parent": "clean-state"},
]
