"""Tests for template and cloud-init tools."""

from __future__ import annotations

from mcp_proxmox.tools.templates import configure_cloud_init, create_template, list_templates
from tests.sample_data import SAMPLE_CLUSTER_RESOURCES

# Add a template to the sample resources
RESOURCES_WITH_TEMPLATE = [
    *SAMPLE_CLUSTER_RESOURCES,
    {
        "vmid": 9000,
        "name": "ubuntu-cloud-template",
        "node": "pve",
        "type": "qemu",
        "status": "stopped",
        "template": 1,
        "cpu": 0,
        "maxcpu": 2,
        "mem": 0,
        "maxmem": 4294967296,
        "uptime": 0,
    },
]


# --- list_templates ---


def test_list_templates(mock_client):
    mock_client._api.cluster.resources.get.return_value = RESOURCES_WITH_TEMPLATE

    result = list_templates(mock_client)

    assert len(result) == 1
    assert result[0]["vmid"] == 9000
    assert result[0]["name"] == "ubuntu-cloud-template"
    assert result[0]["node"] == "pve"


def test_list_templates_empty(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = list_templates(mock_client)

    assert result == []


# --- create_template ---


def test_create_template_requires_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    # VM 102 is stopped — valid candidate
    result = create_template(mock_client, vmid=102)

    assert "warning" in result
    assert "confirm=true" in result["warning"]
    assert result["vmid"] == 102


def test_create_template_with_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = create_template(mock_client, vmid=102, confirm=True)

    assert result["success"] is True
    assert result["vmid"] == 102
    mock_client._api.nodes("pve").qemu(102).template.post.assert_called_once()


def test_create_template_guest_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = create_template(mock_client, vmid=999)

    assert "error" in result
    assert "not found" in result["error"]


def test_create_template_running_vm(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    # VM 100 is running
    result = create_template(mock_client, vmid=100)

    assert "error" in result
    assert "stopped" in result["error"]


def test_create_template_lxc_rejected(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    # 101 is LXC
    result = create_template(mock_client, vmid=101)

    assert "error" in result
    assert "LXC" in result["error"]


def test_create_template_already_template(mock_client):
    mock_client._api.cluster.resources.get.return_value = RESOURCES_WITH_TEMPLATE

    result = create_template(mock_client, vmid=9000)

    assert "error" in result
    assert "already a template" in result["error"]


# --- configure_cloud_init ---


def test_configure_cloud_init_user(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = configure_cloud_init(mock_client, vmid=100, user="admin")

    assert result["success"] is True
    assert "ciuser" in result["configured"]
    mock_client._api.nodes("pve").qemu(100).config.put.assert_called_once_with(ciuser="admin")


def test_configure_cloud_init_multiple_params(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = configure_cloud_init(
        mock_client,
        vmid=100,
        user="admin",
        ip_config="ip=dhcp",
        nameserver="8.8.8.8",
    )

    assert result["success"] is True
    assert set(result["configured"]) == {"ciuser", "ipconfig0", "nameserver"}


def test_configure_cloud_init_no_params(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = configure_cloud_init(mock_client, vmid=100)

    assert "error" in result
    assert "At least one" in result["error"]


def test_configure_cloud_init_guest_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = configure_cloud_init(mock_client, vmid=999, user="admin")

    assert "error" in result
    assert "not found" in result["error"]


def test_configure_cloud_init_lxc_rejected(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = configure_cloud_init(mock_client, vmid=101, user="admin")

    assert "error" in result
    assert "LXC" in result["error"]
