# mcp-proxmox — Roadmap

## Current (v1.1.0)
26 tools: discovery, lifecycle, snapshots, storage, network, resize, monitoring, firewall, migration

## v1.2.0 — Templates & Cloud-init
- [ ] `create_template` — convert VM to template
- [ ] `list_templates` — list available templates
- [ ] `configure_cloud_init` — set IP, SSH keys, user-data on a VM

## v1.3.0 — Disk Management
- [ ] `add_disk` — attach new disk to VM/CT
- [ ] `remove_disk` — detach disk from VM/CT (confirm required)
- [ ] `move_disk` — move disk between storages

## Future Ideas
- ACL/permissions management (list_permissions, add_permission)
- Cluster status (nodes, quorum, corosync health)
- SPICE/VNC console URL generation
- Ceph storage management
- Bulk operations (snapshot all VMs, start/stop by tag)
- Prometheus metrics export
