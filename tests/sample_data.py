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
