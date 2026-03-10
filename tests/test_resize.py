"""Tests for resize tools."""

from __future__ import annotations

from mcp_proxmox.tools.resize import resize_guest
from tests.sample_data import SAMPLE_CLUSTER_RESOURCES


def test_resize_cores(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = resize_guest(mock_client, 100, cores=4, confirm=True)

    assert result["success"] is True
    assert "cores: 4" in result["changes"]
    mock_client._api.nodes("pve").qemu(100).config.put.assert_called_once_with(cores=4)


def test_resize_memory(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = resize_guest(mock_client, 100, memory=4096, confirm=True)

    assert result["success"] is True
    assert "memory: 4096 MB" in result["changes"]
    mock_client._api.nodes("pve").qemu(100).config.put.assert_called_once_with(memory=4096)


def test_resize_disk(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = resize_guest(mock_client, 100, disk_size="+10G", confirm=True)

    assert result["success"] is True
    assert "disk scsi0: +10G" in result["changes"]
    mock_client._api.nodes("pve").qemu(100).resize.put.assert_called_once_with(
        disk="scsi0", size="+10G"
    )


def test_resize_all(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = resize_guest(mock_client, 100, cores=8, memory=16384, disk_size="+50G", confirm=True)

    assert result["success"] is True
    assert len(result["changes"]) == 3
    mock_client._api.nodes("pve").qemu(100).config.put.assert_called_once_with(
        cores=8, memory=16384
    )
    mock_client._api.nodes("pve").qemu(100).resize.put.assert_called_once_with(
        disk="scsi0", size="+50G"
    )


def test_resize_requires_confirm(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = resize_guest(mock_client, 100, cores=4)

    assert "warning" in result
    assert result["vmid"] == 100
    mock_client._api.nodes("pve").qemu(100).config.put.assert_not_called()


def test_resize_no_params(mock_client):
    result = resize_guest(mock_client, 100)

    assert "error" in result
    assert "At least one" in result["error"]


def test_resize_guest_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = resize_guest(mock_client, 999, cores=4, confirm=True)

    assert "error" in result
    assert "not found" in result["error"]


def test_resize_invalid_cores(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = resize_guest(mock_client, 100, cores=0, confirm=True)

    assert "error" in result
    assert "at least 1" in result["error"]


def test_resize_invalid_memory(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = resize_guest(mock_client, 100, memory=64, confirm=True)

    assert "error" in result
    assert "at least 128" in result["error"]


def test_resize_invalid_disk_size(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = resize_guest(mock_client, 100, disk_size="invalid", confirm=True)

    assert "error" in result
    assert "Invalid disk_size" in result["error"]


def test_resize_lxc_disk_remaps(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = resize_guest(mock_client, 101, disk_size="+5G", confirm=True)

    assert result["success"] is True
    mock_client._api.nodes("pve").lxc(101).resize.put.assert_called_once_with(
        disk="rootfs", size="+5G"
    )


def test_resize_lxc_config(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = resize_guest(mock_client, 101, cores=2, memory=1024, confirm=True)

    assert result["success"] is True
    mock_client._api.nodes("pve").lxc(101).config.put.assert_called_once_with(cores=2, memory=1024)
