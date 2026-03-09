"""Tests for discovery tools."""

from __future__ import annotations

from mcp_proxmox.tools.discovery import (
    get_guest_status,
    list_containers,
    list_nodes,
    list_vms,
)
from tests.sample_data import (
    SAMPLE_CLUSTER_RESOURCES,
    SAMPLE_NODES,
)


def test_list_nodes(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES

    result = list_nodes(mock_client)

    assert len(result) == 1
    assert result[0]["node"] == "pve"
    assert result[0]["status"] == "online"
    assert result[0]["cpu_cores"] == 8
    assert "15.0%" in result[0]["cpu_usage"]
    assert result[0]["uptime"] == "10d"


def test_list_vms(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = list_vms(mock_client)

    assert len(result) == 2  # only qemu type
    assert result[0]["vmid"] == 100
    assert result[0]["name"] == "ubuntu-server"
    assert result[1]["vmid"] == 102
    assert result[1]["status"] == "stopped"


def test_list_vms_with_status_filter(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = list_vms(mock_client, status_filter="running")

    assert len(result) == 1
    assert result[0]["vmid"] == 100


def test_list_vms_with_node_filter(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = list_vms(mock_client, node="nonexistent")

    assert len(result) == 0


def test_list_containers(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = list_containers(mock_client)

    assert len(result) == 1
    assert result[0]["vmid"] == 101
    assert result[0]["name"] == "nginx-proxy"


def test_get_guest_status_vm(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes("pve").qemu(100).status.current.get.return_value = {
        "status": "running",
        "name": "ubuntu-server",
        "cpus": 4,
        "cpu": 0.05,
        "mem": 2147483648,
        "maxmem": 8589934592,
        "uptime": 432000,
        "pid": 12345,
        "qemu": "9.0.2",
    }
    mock_client._api.nodes("pve").qemu(100).config.get.return_value = {
        "name": "ubuntu-server",
        "cores": 4,
        "description": "Main server",
    }

    result = get_guest_status(mock_client, 100)

    assert result["vmid"] == 100
    assert result["type"] == "VM"
    assert result["status"] == "running"
    assert result["description"] == "Main server"
    assert result["qemu_version"] == "9.0.2"


def test_get_guest_status_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = get_guest_status(mock_client, 999)

    assert "error" in result
    assert "999" in result["error"]
