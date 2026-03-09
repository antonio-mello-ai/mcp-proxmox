"""Tests for backup tools."""

from __future__ import annotations

from mcp_proxmox.tools.backup import create_backup, list_backups, restore_backup
from tests.sample_data import (
    SAMPLE_CLUSTER_RESOURCES,
    SAMPLE_NODES,
    SAMPLE_STORAGE_CONTENT,
    SAMPLE_STORAGES,
)


def test_list_backups(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES
    mock_client._api.nodes("pve").storage.get.return_value = SAMPLE_STORAGES
    # Only "local" storage has backup content type
    mock_client._api.nodes("pve").storage("local").content.get.return_value = [
        SAMPLE_STORAGE_CONTENT[2]  # backup item
    ]

    result = list_backups(mock_client)

    assert result["total"] == 1
    assert result["backups"][0]["vmid"] == 100
    assert "vzdump" in result["backups"][0]["volid"]


def test_list_backups_filter_by_vmid(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES
    mock_client._api.nodes("pve").storage.get.return_value = SAMPLE_STORAGES
    mock_client._api.nodes("pve").storage("local").content.get.return_value = [
        SAMPLE_STORAGE_CONTENT[2]
    ]

    result = list_backups(mock_client, vmid=999)

    assert result["total"] == 0


def test_list_backups_node_not_found(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES

    result = list_backups(mock_client, node="nonexistent")

    assert "error" in result


def test_create_backup(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes(
        "pve"
    ).vzdump.post.return_value = "UPID:pve:00001234:00000000:65F00000:vzdump:100:test@pam:"

    result = create_backup(mock_client, 100, storage="local")

    assert result["success"] is True
    assert result["vmid"] == 100
    assert result["mode"] == "snapshot"
    assert result["compress"] == "zstd"


def test_create_backup_invalid_mode(mock_client):
    result = create_backup(mock_client, 100, mode="invalid")

    assert "error" in result
    assert "mode" in result["error"].lower()


def test_create_backup_invalid_compress(mock_client):
    result = create_backup(mock_client, 100, compress="bzip2")

    assert "error" in result
    assert "compress" in result["error"].lower()


def test_create_backup_guest_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = create_backup(mock_client, 999)

    assert "error" in result
    assert "not found" in result["error"]


def test_restore_backup_requires_confirmation(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.cluster.nextid.get.return_value = 200

    result = restore_backup(
        mock_client,
        "local:backup/vzdump-qemu-100-2024_03_04.vma.zst",
        "pve",
    )

    assert "warning" in result
    assert "confirm=true" in result["warning"]
    assert result["vmid"] == 200


def test_restore_backup_with_confirmation(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.cluster.nextid.get.return_value = 200
    mock_client._api.nodes(
        "pve"
    ).qemu.post.return_value = "UPID:pve:00001234:00000000:65F00000:qmrestore:200:test@pam:"

    result = restore_backup(
        mock_client,
        "local:backup/vzdump-qemu-100-2024_03_04.vma.zst",
        "pve",
        confirm=True,
    )

    assert result["success"] is True
    assert result["vmid"] == 200
    assert result["type"] == "VM"


def test_restore_container_backup(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.cluster.nextid.get.return_value = 201
    mock_client._api.nodes(
        "pve"
    ).lxc.post.return_value = "UPID:pve:00001234:00000000:65F00000:vzrestore:201:test@pam:"

    result = restore_backup(
        mock_client,
        "local:backup/vzdump-lxc-101-2024_03_04.tar.zst",
        "pve",
        guest_type="container",
        confirm=True,
    )

    assert result["success"] is True
    assert result["type"] == "Container"


def test_restore_vmid_exists(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = restore_backup(
        mock_client,
        "local:backup/vzdump-qemu-100.vma.zst",
        "pve",
        vmid=100,
        confirm=True,
    )

    assert "error" in result
    assert "already exists" in result["error"]


def test_restore_node_not_found(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES

    result = restore_backup(
        mock_client,
        "local:backup/vzdump.vma.zst",
        "nonexistent",
        confirm=True,
    )

    assert "error" in result
    assert "not found" in result["error"]


def test_restore_invalid_guest_type(mock_client):
    result = restore_backup(
        mock_client,
        "local:backup/vzdump.vma.zst",
        "pve",
        guest_type="invalid",
        confirm=True,
    )

    assert "error" in result
    assert "guest_type" in result["error"]
