"""Tests for snapshot tools."""

from __future__ import annotations

from mcp_proxmox.tools.snapshots import (
    create_snapshot,
    list_snapshots,
    rollback_snapshot,
)
from tests.sample_data import SAMPLE_CLUSTER_RESOURCES, SAMPLE_SNAPSHOTS


def test_list_snapshots(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes("pve").qemu(100).snapshot.get.return_value = SAMPLE_SNAPSHOTS

    result = list_snapshots(mock_client, 100)

    assert result["vmid"] == 100
    assert result["snapshot_count"] == 2  # excludes "current"
    assert result["snapshots"][0]["name"] == "before-upgrade"
    assert result["snapshots"][1]["name"] == "clean-state"


def test_list_snapshots_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = list_snapshots(mock_client, 999)

    assert "error" in result


def test_create_snapshot(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes("pve").qemu(
        100
    ).snapshot.post.return_value = "UPID:pve:00001234:00000000:65F00000:qmsnapshot:100:test@pam:"

    result = create_snapshot(mock_client, 100, "test-snap", "Test snapshot")

    assert result["success"] is True
    assert result["snapshot_name"] == "test-snap"


def test_create_snapshot_invalid_name(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = create_snapshot(mock_client, 100, "invalid name!")

    assert "error" in result
    assert "alphanumeric" in result["error"]


def test_rollback_requires_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes("pve").qemu(100).snapshot.get.return_value = SAMPLE_SNAPSHOTS

    result = rollback_snapshot(mock_client, 100, "before-upgrade")

    assert "warning" in result
    assert "LOST" in result["warning"]


def test_rollback_with_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes("pve").qemu(100).snapshot.get.return_value = SAMPLE_SNAPSHOTS
    rollback = mock_client._api.nodes("pve").qemu(100).snapshot("before-upgrade").rollback
    rollback.post.return_value = "UPID:pve:00001234:00000000:65F00000:qmrollback:100:test@pam:"

    result = rollback_snapshot(mock_client, 100, "before-upgrade", confirm=True)

    assert result["success"] is True
    assert result["snapshot_name"] == "before-upgrade"


def test_rollback_snapshot_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes("pve").qemu(100).snapshot.get.return_value = SAMPLE_SNAPSHOTS

    result = rollback_snapshot(mock_client, 100, "nonexistent", confirm=True)

    assert "error" in result
    assert "not found" in result["error"]
    assert "before-upgrade" in result["error"]  # suggests available snapshots
