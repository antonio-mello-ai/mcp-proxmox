"""Tests for storage tools."""

from __future__ import annotations

from mcp_proxmox.tools.storage import list_storage_content, list_storages
from tests.sample_data import SAMPLE_NODES, SAMPLE_STORAGE_CONTENT, SAMPLE_STORAGES


def test_list_storages(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES
    mock_client._api.nodes("pve").storage.get.return_value = SAMPLE_STORAGES

    result = list_storages(mock_client)

    assert result["total"] == 3
    names = [s["storage"] for s in result["storages"]]
    assert "local" in names
    assert "local-lvm" in names
    assert "zfs-pool" in names


def test_list_storages_with_node_filter(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES
    mock_client._api.nodes("pve").storage.get.return_value = SAMPLE_STORAGES

    result = list_storages(mock_client, node="pve")

    assert result["total"] == 3


def test_list_storages_node_not_found(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES

    result = list_storages(mock_client, node="nonexistent")

    assert "error" in result


def test_list_storage_content(mock_client):
    mock_client._api.nodes("pve").storage("local").content.get.return_value = SAMPLE_STORAGE_CONTENT

    result = list_storage_content(mock_client, "pve", "local")

    assert result["total"] == 3
    assert result["storage"] == "local"
    volids = [i["volid"] for i in result["items"]]
    assert "local:iso/ubuntu-24.04-live-server-amd64.iso" in volids
    assert "local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst" in volids


def test_list_storage_content_with_type_filter(mock_client):
    mock_client._api.nodes("pve").storage("local").content.get.return_value = [
        SAMPLE_STORAGE_CONTENT[0]  # just the ISO
    ]

    result = list_storage_content(mock_client, "pve", "local", content_type="iso")

    assert result["total"] == 1
    assert result["content_type"] == "iso"


def test_list_storage_content_invalid_type(mock_client):
    result = list_storage_content(mock_client, "pve", "local", content_type="invalid")

    assert "error" in result
    assert "invalid" in result["error"].lower()
