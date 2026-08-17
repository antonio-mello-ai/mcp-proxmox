# mcp-proxmox — Roadmap

## Current (v1.2.0)
29 tools: discovery, lifecycle, snapshots, storage, network, resize, monitoring, firewall, migration, templates & cloud-init

### v1.2.0 — Templates & Cloud-init (released)
- [x] `list_templates` — list available templates
- [x] `create_template` — convert VM to template (requires confirmation)
- [x] `configure_cloud_init` — set user, password, SSH keys, IP, DNS on a VM

## v1.3.0 — Disk Management
- [ ] `add_disk` — attach new disk to VM/CT
- [ ] `remove_disk` — detach disk from VM/CT (confirm required)
- [ ] `move_disk` — move disk between storages

## Future Ideas
- Migrate to the MCP Python SDK 2.x API (`mcp.server.fastmcp` was removed in `mcp` 2.0; 1.2.2 pins `mcp<2` as the interim fix)
- ACL/permissions management (list_permissions, add_permission)
- Cluster status (nodes, quorum, corosync health)
- SPICE/VNC console URL generation
- Ceph storage management
- Bulk operations (snapshot all VMs, start/stop by tag)
- Prometheus metrics export
