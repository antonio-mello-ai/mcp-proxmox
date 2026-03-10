# mcp-proxmox — Roadmap

## Current (v1.0.1)
22 tools: discovery, lifecycle, snapshots, storage, network, resize, monitoring

## v1.1.0 — Firewall & Migration
- [ ] `list_firewall_rules` — list firewall rules for VM/CT/node
- [ ] `add_firewall_rule` — create firewall rule (direction, action, protocol, port, comment)
- [ ] `delete_firewall_rule` — remove firewall rule (confirm required)
- [ ] `migrate_guest` — live migrate VM/CT to another node (confirm required)

## v1.2.0 — Backup & Templates
- [ ] `list_backups` — list existing backups per VM/CT or per storage
- [ ] `create_backup` — trigger vzdump backup for a VM/CT
- [ ] `schedule_backup` — create/list backup schedules
- [ ] `create_template` — convert VM to template
- [ ] `list_templates` — list available templates

## v1.3.0 — Cloud-init & Disk Management
- [ ] `configure_cloud_init` — set IP, SSH keys, user-data on a VM
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
