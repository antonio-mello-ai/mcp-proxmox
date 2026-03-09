"""Tests for command execution tools."""

from __future__ import annotations

from unittest.mock import patch

from mcp_proxmox.tools.execute import exec_command
from tests.sample_data import SAMPLE_CLUSTER_RESOURCES


def test_exec_command_success(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes("pve").qemu(100).agent.exec.post.return_value = {"pid": 42}
    mock_client._api.nodes("pve").qemu(100).agent("exec-status").get.return_value = {
        "exited": 1,
        "exitcode": 0,
        "out-data": "ubuntu-server\n",
        "err-data": "",
    }

    with patch("mcp_proxmox.tools.execute.time.sleep"):
        result = exec_command(mock_client, 100, "hostname")

    assert result["success"] is True
    assert result["exit_code"] == 0
    assert "ubuntu-server" in result["stdout"]


def test_exec_command_with_error_output(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes("pve").qemu(100).agent.exec.post.return_value = {"pid": 43}
    mock_client._api.nodes("pve").qemu(100).agent("exec-status").get.return_value = {
        "exited": 1,
        "exitcode": 1,
        "out-data": "",
        "err-data": "command not found\n",
    }

    with patch("mcp_proxmox.tools.execute.time.sleep"):
        result = exec_command(mock_client, 100, "nonexistent-cmd")

    assert result["success"] is False
    assert result["exit_code"] == 1
    assert "command not found" in result["stderr"]


def test_exec_command_empty(mock_client):
    result = exec_command(mock_client, 100, "   ")

    assert "error" in result
    assert "empty" in result["error"].lower()


def test_exec_command_invalid_timeout(mock_client):
    result = exec_command(mock_client, 100, "hostname", timeout=999)

    assert "error" in result
    assert "timeout" in result["error"].lower()


def test_exec_command_guest_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = exec_command(mock_client, 999, "hostname")

    assert "error" in result
    assert "not found" in result["error"]


def test_exec_command_lxc_not_supported(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = exec_command(mock_client, 101, "hostname")  # 101 is LXC

    assert "error" in result
    assert "LXC" in result["error"]


def test_exec_command_vm_not_running(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = exec_command(mock_client, 102, "hostname")  # 102 is stopped

    assert "error" in result
    assert "not running" in result["error"]


def test_exec_command_agent_not_responding(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes("pve").qemu(100).agent.exec.post.side_effect = Exception(
        "QEMU guest agent is not running"
    )

    result = exec_command(mock_client, 100, "hostname")

    assert "error" in result
    assert "agent" in result["error"].lower()


def test_exec_command_timeout(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes("pve").qemu(100).agent.exec.post.return_value = {"pid": 44}
    # Never finishes - exited stays false
    mock_client._api.nodes("pve").qemu(100).agent("exec-status").get.return_value = {
        "exited": 0,
    }

    with (
        patch("mcp_proxmox.tools.execute.time.sleep"),
        patch("mcp_proxmox.tools.execute._MAX_WAIT_SECONDS", 2),
        patch("mcp_proxmox.tools.execute._POLL_INTERVAL", 1.0),
    ):
        result = exec_command(mock_client, 100, "long-running-cmd", timeout=2)

    assert result["status"] == "running"
    assert result["pid"] == 44
