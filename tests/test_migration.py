"""Tests for migration tools."""

from __future__ import annotations

from mcp_proxmox.tools.migration import migrate_guest
from tests.sample_data import SAMPLE_CLUSTER_RESOURCES, SAMPLE_NODES

# Add a second node for migration tests
MULTI_NODE_RESOURCES = [
    *SAMPLE_CLUSTER_RESOURCES,
    {
        "vmid": 200,
        "name": "db-server",
        "node": "pve2",
        "type": "qemu",
        "status": "running",
        "cpu": 0.10,
        "maxcpu": 4,
        "mem": 4294967296,
        "maxmem": 17179869184,
        "uptime": 100000,
    },
]

MULTI_NODES = [
    *SAMPLE_NODES,
    {
        "node": "pve2",
        "status": "online",
        "cpu": 0.20,
        "maxcpu": 8,
        "mem": 17179869184,
        "maxmem": 34359738368,
        "uptime": 500000,
    },
]


def test_migrate_requires_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = MULTI_NODE_RESOURCES
    mock_client._api.nodes.get.return_value = MULTI_NODES

    result = migrate_guest(mock_client, vmid=100, target_node="pve2")

    assert "warning" in result
    assert "confirm=true" in result["warning"]
    assert result["source_node"] == "pve"
    assert result["target_node"] == "pve2"
    assert result["migration_type"] == "live (online)"


def test_migrate_with_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = MULTI_NODE_RESOURCES
    mock_client._api.nodes.get.return_value = MULTI_NODES
    mock_client._api.nodes("pve").qemu(
        100
    ).migrate.post.return_value = "UPID:pve:00001234:00000000:65F00000:qmmigrate:100:test@pam:"

    result = migrate_guest(mock_client, vmid=100, target_node="pve2", confirm=True)

    assert result["success"] is True
    assert result["source_node"] == "pve"
    assert result["target_node"] == "pve2"
    assert "task_id" in result


def test_migrate_offline(mock_client):
    mock_client._api.cluster.resources.get.return_value = MULTI_NODE_RESOURCES
    mock_client._api.nodes.get.return_value = MULTI_NODES

    result = migrate_guest(mock_client, vmid=100, target_node="pve2", online=False)

    assert "warning" in result
    assert result["migration_type"] == "offline"


def test_migrate_guest_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = MULTI_NODE_RESOURCES

    result = migrate_guest(mock_client, vmid=999, target_node="pve2")

    assert "error" in result
    assert "not found" in result["error"]


def test_migrate_already_on_target(mock_client):
    mock_client._api.cluster.resources.get.return_value = MULTI_NODE_RESOURCES

    result = migrate_guest(mock_client, vmid=100, target_node="pve")

    assert "error" in result
    assert "already on node" in result["error"]


def test_migrate_target_node_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = MULTI_NODE_RESOURCES
    mock_client._api.nodes.get.return_value = MULTI_NODES

    result = migrate_guest(mock_client, vmid=100, target_node="nonexistent")

    assert "error" in result
    assert "not found" in result["error"]
    assert "pve" in result["error"]  # Should list available nodes


def test_migrate_lxc_container(mock_client):
    mock_client._api.cluster.resources.get.return_value = MULTI_NODE_RESOURCES
    mock_client._api.nodes.get.return_value = MULTI_NODES
    mock_client._api.nodes("pve").lxc(
        101
    ).migrate.post.return_value = "UPID:pve:00001234:00000000:65F00000:vzmigrate:101:test@pam:"

    result = migrate_guest(mock_client, vmid=101, target_node="pve2", confirm=True)

    assert result["success"] is True
    assert result["type"] == "container"
