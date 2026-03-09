"""Tests for provisioning tools."""

from __future__ import annotations

from mcp_proxmox.tools.provisioning import (
    clone_guest,
    create_container,
    create_vm,
    delete_guest,
)
from tests.sample_data import SAMPLE_CLUSTER_RESOURCES, SAMPLE_NODES


def test_create_vm(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.cluster.nextid.get.return_value = 200
    mock_client._api.nodes(
        "pve"
    ).qemu.post.return_value = "UPID:pve:00001234:00000000:65F00000:qmcreate:200:test@pam:"

    result = create_vm(mock_client, "pve", "new-vm", cores=2, memory=4096)

    assert result["success"] is True
    assert result["vmid"] == 200
    assert result["name"] == "new-vm"
    assert result["type"] == "VM"


def test_create_vm_with_specific_vmid(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes(
        "pve"
    ).qemu.post.return_value = "UPID:pve:00001234:00000000:65F00000:qmcreate:500:test@pam:"

    result = create_vm(mock_client, "pve", "vm-500", vmid=500)

    assert result["success"] is True
    assert result["vmid"] == 500


def test_create_vm_vmid_exists(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = create_vm(mock_client, "pve", "duplicate", vmid=100)

    assert "error" in result
    assert "already exists" in result["error"]


def test_create_vm_node_not_found(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES

    result = create_vm(mock_client, "nonexistent", "vm")

    assert "error" in result
    assert "not found" in result["error"]


def test_create_container(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.cluster.nextid.get.return_value = 201
    mock_client._api.nodes(
        "pve"
    ).lxc.post.return_value = "UPID:pve:00001234:00000000:65F00000:vzcreate:201:test@pam:"

    result = create_container(
        mock_client,
        "pve",
        "my-ct",
        template="local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst",
    )

    assert result["success"] is True
    assert result["vmid"] == 201
    assert result["type"] == "Container"


def test_create_container_vmid_exists(mock_client):
    mock_client._api.nodes.get.return_value = SAMPLE_NODES
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = create_container(
        mock_client,
        "pve",
        "dup-ct",
        template="local:vztmpl/debian-12.tar.zst",
        vmid=101,
    )

    assert "error" in result
    assert "already exists" in result["error"]


def test_clone_guest(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.cluster.nextid.get.return_value = 300
    mock_client._api.nodes("pve").qemu(
        100
    ).clone.post.return_value = "UPID:pve:00001234:00000000:65F00000:qmclone:100:test@pam:"

    result = clone_guest(mock_client, 100, new_name="ubuntu-clone")

    assert result["success"] is True
    assert result["source_vmid"] == 100
    assert result["new_vmid"] == 300
    assert result["new_name"] == "ubuntu-clone"
    assert result["clone_type"] == "full"


def test_clone_guest_linked(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.cluster.nextid.get.return_value = 301
    mock_client._api.nodes("pve").qemu(
        100
    ).clone.post.return_value = "UPID:pve:00001234:00000000:65F00000:qmclone:100:test@pam:"

    result = clone_guest(mock_client, 100, full_clone=False)

    assert result["success"] is True
    assert result["clone_type"] == "linked"


def test_clone_guest_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = clone_guest(mock_client, 999)

    assert "error" in result
    assert "not found" in result["error"]


def test_clone_container(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.cluster.nextid.get.return_value = 302
    mock_client._api.nodes("pve").lxc(
        101
    ).clone.post.return_value = "UPID:pve:00001234:00000000:65F00000:vzclone:101:test@pam:"

    result = clone_guest(mock_client, 101, new_name="nginx-clone")

    assert result["success"] is True
    assert result["source_vmid"] == 101
    assert result["type"] == "Container"


def test_delete_guest_requires_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = delete_guest(mock_client, 102)  # stopped VM

    assert "warning" in result
    assert "PERMANENTLY DELETE" in result["warning"]
    assert "confirm=true" in result["warning"]


def test_delete_guest_with_confirmation(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES
    mock_client._api.nodes("pve").qemu(
        102
    ).delete.return_value = "UPID:pve:00001234:00000000:65F00000:qmdestroy:102:test@pam:"

    result = delete_guest(mock_client, 102, confirm=True)

    assert result["success"] is True
    assert result["vmid"] == 102


def test_delete_running_guest(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = delete_guest(mock_client, 100, confirm=True)  # running VM

    assert "error" in result
    assert "running" in result["error"].lower()
    assert "Stop it first" in result["error"]


def test_delete_guest_not_found(mock_client):
    mock_client._api.cluster.resources.get.return_value = SAMPLE_CLUSTER_RESOURCES

    result = delete_guest(mock_client, 999, confirm=True)

    assert "error" in result
    assert "not found" in result["error"]
