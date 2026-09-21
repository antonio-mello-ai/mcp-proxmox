"""Tests for QEMU console tools and client integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from mcp_proxmox.client import ProxmoxClient
from mcp_proxmox.config import ProxmoxConfig
from mcp_proxmox.tools.console import vm_send_key, vm_send_text
from tests.sample_data import SAMPLE_CLUSTER_RESOURCES


def test_send_key_requires_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = vm_send_key(mock_client, 100, "enter")

    assert "confirm=true" in result["warning"]
    mock_client._api.nodes("pve").qemu(100).sendkey.put.assert_not_called()


def test_send_key_with_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = vm_send_key(mock_client, 100, "enter", confirm=True)

    assert result["success"] is True
    mock_client._api.nodes("pve").qemu(100).sendkey.put.assert_called_once_with(key="ret")


def test_send_text_requires_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = vm_send_text(mock_client, 100, "Hi!")

    assert "confirm=true" in result["warning"]
    mock_client._api.nodes("pve").qemu(100).sendkey.put.assert_not_called()


def test_send_text_validates_all_characters_before_sending(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    with pytest.raises(ToolError, match="Unsupported character"):
        vm_send_text(mock_client, 100, "oké", delay=0, confirm=True)

    mock_client._api.nodes("pve").qemu(100).sendkey.put.assert_not_called()


def test_send_text_with_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = vm_send_text(mock_client, 100, "A!", delay=0, confirm=True)

    assert result["text_sent"] == "A!"
    assert result["characters_sent"] == 2
    endpoint = mock_client._api.nodes("pve").qemu(100).sendkey.put
    assert endpoint.call_args_list[0].kwargs == {"key": "shift-a"}
    assert endpoint.call_args_list[1].kwargs == {"key": "shift-1"}


def test_screenshot_preserves_tls_verification_and_encodes_ticket():
    config = ProxmoxConfig(
        host="pve.example.com",
        token_id="test@pam!token",
        token_secret="secret",
        port=8006,
        verify_ssl=True,
    )
    client = ProxmoxClient(config)
    client._api = api = MagicMock()
    api.nodes("pve").qemu(100).vncproxy.post.return_value = {
        "port": 5900,
        "ticket": "PVEVNC:ticket/with+special=chars",
    }

    with patch("mcp_proxmox.vnc.capture_vnc_screenshot", return_value=b"png") as capture:
        assert client.screenshot_vm("pve", 100) == b"png"

    kwargs = capture.call_args.kwargs
    assert kwargs["use_ssl"] is True
    assert kwargs["verify_ssl"] is True
    assert "ticket%2Fwith%2Bspecial%3Dchars" in kwargs["api_path"]
