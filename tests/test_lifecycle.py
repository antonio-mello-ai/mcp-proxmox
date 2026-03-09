"""Tests for lifecycle tools."""

from __future__ import annotations

from mcp_proxmox.tools.lifecycle import (
    reboot_guest,
    shutdown_guest,
    start_guest,
    stop_guest,
)
from tests.sample_data import SAMPLE_CLUSTER_RESOURCES


def test_start_guest(mock_client):
    # VM 102 is stopped
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes("pve").qemu(
        102
    ).status.start.post.return_value = "UPID:pve:00001234:00000000:65F00000:qmstart:102:test@pam:"

    result = start_guest(mock_client, 102)

    assert result["success"] is True
    assert result["action"] == "start"
    assert result["vmid"] == 102


def test_start_already_running(mock_client):
    # VM 100 is running
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = start_guest(mock_client, 100)

    assert "error" in result
    assert "already running" in result["error"]


def test_stop_requires_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = stop_guest(mock_client, 100)

    assert "warning" in result
    assert "confirm=true" in result["warning"]


def test_stop_with_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes("pve").qemu(
        100
    ).status.stop.post.return_value = "UPID:pve:00001234:00000000:65F00000:qmstop:100:test@pam:"

    result = stop_guest(mock_client, 100, confirm=True)

    assert result["success"] is True
    assert result["action"] == "stop"


def test_stop_already_stopped(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = stop_guest(mock_client, 102, confirm=True)

    assert "error" in result
    assert "already stopped" in result["error"]


def test_shutdown_guest(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes("pve").qemu(
        100
    ).status.shutdown.post.return_value = (
        "UPID:pve:00001234:00000000:65F00000:qmshutdown:100:test@pam:"
    )

    result = shutdown_guest(mock_client, 100)

    assert result["success"] is True
    assert result["action"] == "shutdown"


def test_reboot_requires_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = reboot_guest(mock_client, 100)

    assert "warning" in result
    assert "confirm=true" in result["warning"]


def test_guest_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = start_guest(mock_client, 999)

    assert "error" in result
    assert "not found" in result["error"]
