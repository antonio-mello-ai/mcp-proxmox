"""Tests for network tools."""

from __future__ import annotations

from mcp_proxmox.tools.network import list_networks
from tests.sample_data import SAMPLE_NETWORKS, SAMPLE_NODES


def test_list_networks(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES
    mock_client._api.nodes("pve").network.get.return_value = SAMPLE_NETWORKS

    result = list_networks(mock_client, "pve")

    assert result["node"] == "pve"
    assert result["total"] == 3
    assert len(result["bridges"]) == 1
    assert result["bridges"][0]["name"] == "vmbr0"
    assert result["bridges"][0]["address"] == "192.168.1.100"
    assert len(result["physical"]) == 1
    assert result["physical"][0]["name"] == "enp3s0"
    assert len(result["other"]) == 1  # vlan


def test_list_networks_node_not_found(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES

    result = list_networks(mock_client, "nonexistent")

    assert "error" in result
    assert "not found" in result["error"]


def test_list_networks_bridge_ports(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES
    mock_client._api.nodes("pve").network.get.return_value = SAMPLE_NETWORKS

    result = list_networks(mock_client, "pve")

    bridge = result["bridges"][0]
    assert bridge["bridge_ports"] == "enp3s0"
