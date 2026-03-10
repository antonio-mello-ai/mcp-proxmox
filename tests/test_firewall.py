"""Tests for firewall tools."""

from __future__ import annotations

from mcp_proxmox.tools.firewall import (
    add_firewall_rule,
    delete_firewall_rule,
    list_firewall_rules,
)
from tests.sample_data import SAMPLE_CLUSTER_RESOURCES

SAMPLE_FIREWALL_RULES = [
    {
        "pos": 0,
        "action": "ACCEPT",
        "type": "in",
        "proto": "tcp",
        "dport": "22",
        "enable": 1,
        "comment": "Allow SSH",
    },
    {
        "pos": 1,
        "action": "DROP",
        "type": "in",
        "enable": 1,
        "comment": "Drop all other incoming",
    },
]


# --- list_firewall_rules ---


def test_list_cluster_rules(mock_client):
    mock_client._api.cluster.firewall.rules.get.return_value = SAMPLE_FIREWALL_RULES

    result = list_firewall_rules(mock_client)

    assert result["level"] == "cluster"
    assert result["count"] == 2
    assert len(result["rules"]) == 2


def test_list_node_rules(mock_client):
    mock_client._api.nodes("pve").firewall.rules.get.return_value = SAMPLE_FIREWALL_RULES

    result = list_firewall_rules(mock_client, node="pve")

    assert result["node"] == "pve"
    assert result["count"] == 2


def test_list_guest_rules(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes("pve").qemu(100).firewall.rules.get.return_value = [
        SAMPLE_FIREWALL_RULES[0]
    ]

    result = list_firewall_rules(mock_client, vmid=100)

    assert result["vmid"] == 100
    assert result["name"] == "ubuntu-server"
    assert result["count"] == 1


def test_list_guest_rules_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = list_firewall_rules(mock_client, vmid=999)

    assert "error" in result
    assert "not found" in result["error"]


# --- add_firewall_rule ---


def test_add_cluster_rule(mock_client):
    result = add_firewall_rule(mock_client, action="ACCEPT", type_="in", proto="tcp", dport="443")

    assert result["success"] is True
    assert result["level"] == "cluster"
    assert result["rule"]["action"] == "ACCEPT"
    assert result["rule"]["proto"] == "tcp"
    assert result["rule"]["dport"] == "443"
    mock_client._api.cluster.firewall.rules.post.assert_called_once()


def test_add_node_rule(mock_client):
    result = add_firewall_rule(
        mock_client, action="DROP", type_="in", node="pve", proto="tcp", dport="8006"
    )

    assert result["success"] is True
    assert result["level"] == "node"
    assert result["node"] == "pve"
    mock_client._api.nodes("pve").firewall.rules.post.assert_called_once()


def test_add_guest_rule(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = add_firewall_rule(
        mock_client, action="ACCEPT", type_="in", vmid=100, proto="tcp", dport="80"
    )

    assert result["success"] is True
    assert result["level"] == "guest"
    assert result["vmid"] == 100
    assert result["name"] == "ubuntu-server"


def test_add_guest_rule_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = add_firewall_rule(mock_client, action="ACCEPT", type_="in", vmid=999)

    assert "error" in result


def test_add_rule_with_all_options(mock_client):
    result = add_firewall_rule(
        mock_client,
        action="REJECT",
        type_="out",
        proto="udp",
        dport="53",
        sport="1024-65535",
        source="10.0.0.0/8",
        dest="8.8.8.8",
        iface="net0",
        enable=False,
        comment="Block DNS",
        pos=0,
    )

    assert result["success"] is True
    assert result["rule"]["enable"] == 0
    assert result["rule"]["comment"] == "Block DNS"
    assert result["rule"]["pos"] == 0


# --- delete_firewall_rule ---


def test_delete_cluster_rule_requires_confirmation(mock_client):
    result = delete_firewall_rule(mock_client, pos=0)

    assert "warning" in result
    assert "confirm=true" in result["warning"]
    assert result["pos"] == 0


def test_delete_cluster_rule_with_confirmation(mock_client):
    result = delete_firewall_rule(mock_client, pos=0, confirm=True)

    assert result["success"] is True
    assert result["level"] == "cluster"
    mock_client._api.cluster.firewall.rules(0).delete.assert_called_once()


def test_delete_node_rule_with_confirmation(mock_client):
    result = delete_firewall_rule(mock_client, pos=1, node="pve", confirm=True)

    assert result["success"] is True
    assert result["level"] == "node"
    mock_client._api.nodes("pve").firewall.rules(1).delete.assert_called_once()


def test_delete_guest_rule_with_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = delete_firewall_rule(mock_client, pos=0, vmid=100, confirm=True)

    assert result["success"] is True
    assert result["level"] == "guest"


def test_delete_guest_rule_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = delete_firewall_rule(mock_client, pos=0, vmid=999, confirm=True)

    assert "error" in result
