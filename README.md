# mcp-proxmox

<!-- mcp-name: io.github.antonio-mello-ai/mcp-proxmox -->

<a href="https://glama.ai/mcp/servers/antonio-mello-ai/mcp-proxmox">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/antonio-mello-ai/mcp-proxmox/badge" alt="mcp-proxmox MCP server" />
</a>

MCP server for managing Proxmox VE clusters through AI assistants like Claude, Cursor, and Cline.

Provision, manage, and monitor your entire Proxmox infrastructure through natural language. Create VMs and containers, manage snapshots, browse storage, and more.

## Quick Start

```bash
# Run directly with uvx (no install needed)
uvx mcp-proxmox

# Or install with pip
pip install mcp-proxmox
```

## Configuration

Set these environment variables (or create a `.env` file):

```bash
PROXMOX_HOST=192.168.1.100          # Your Proxmox VE host
PROXMOX_TOKEN_ID=user@pam!mcp       # API token ID
PROXMOX_TOKEN_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx  # API token secret
```

Optional:
```bash
PROXMOX_PORT=8006                   # Default: 8006
PROXMOX_VERIFY_SSL=false            # Default: false
```

### Creating a Proxmox API Token

1. Log into your Proxmox web UI
2. Go to **Datacenter** > **Permissions** > **API Tokens**
3. Click **Add** and create a token for your user
4. **Uncheck** "Privilege Separation" for full access, or assign specific permissions:
   - `VM.Audit` — read VM/CT status and config
   - `VM.PowerMgmt` — start/stop/shutdown/reboot
   - `VM.Snapshot` — create/rollback/delete snapshots
   - `VM.Allocate` — create/delete/clone VMs and containers
   - `VM.Clone` — clone operations
   - `Datastore.Audit` — list storages and browse content
   - `Datastore.AllocateSpace` — allocate disk space for new VMs/CTs
   - `Sys.Audit` — read node status and tasks
   - `VM.Config.Disk` — resize disks
   - `VM.Config.CPU` — change CPU allocation
   - `VM.Config.Memory` — change memory allocation
   - `VM.Monitor` — access QEMU monitor (for metrics)
   - `VM.Migrate` — migrate VMs/CTs between nodes
   - `Sys.Modify` — manage firewall rules
   - `VM.Config.Cloudinit` — configure cloud-init parameters

## Integration

### Claude Desktop

Add to `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "uvx",
      "args": ["mcp-proxmox"],
      "env": {
        "PROXMOX_HOST": "192.168.1.100",
        "PROXMOX_TOKEN_ID": "user@pam!mcp",
        "PROXMOX_TOKEN_SECRET": "your-token-secret"
      }
    }
  }
}
```

### Claude Code

Add to `.claude/settings.json` or `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "proxmox": {
      "command": "uvx",
      "args": ["mcp-proxmox"],
      "env": {
        "PROXMOX_HOST": "192.168.1.100",
        "PROXMOX_TOKEN_ID": "user@pam!mcp",
        "PROXMOX_TOKEN_SECRET": "your-token-secret"
      }
    }
  }
}
```

### Cursor

Add to Cursor Settings > MCP with the same configuration as above.

## Available Tools

### Discovery

| Tool | Description |
|------|-------------|
| `list_nodes` | List all cluster nodes with CPU, memory, and uptime |
| `get_node_status` | Detailed node info: CPU model, memory, disk, versions |
| `list_vms` | List QEMU VMs (filter by node or status) |
| `list_containers` | List LXC containers (filter by node or status) |
| `get_guest_status` | Detailed VM/CT status by VMID (auto-detects type and node) |

### Lifecycle

| Tool | Description |
|------|-------------|
| `start_guest` | Start a stopped VM or container |
| `stop_guest` | Force-stop (requires confirmation) |
| `shutdown_guest` | Graceful ACPI/init shutdown |
| `reboot_guest` | Reboot (requires confirmation) |

### Storage

| Tool | Description |
|------|-------------|
| `list_storages` | List storage pools with capacity and usage (filter by node) |
| `list_storage_content` | Browse ISOs, templates, backups, and disk images |

### Provisioning

| Tool | Description |
|------|-------------|
| `create_vm` | Create a QEMU VM with configurable CPU, memory, disk, ISO, and network |
| `create_container` | Create an LXC container from a template |
| `clone_guest` | Clone a VM or CT (full or linked clone, cross-node support) |
| `delete_guest` | Permanently delete a stopped VM or CT (requires confirmation) |

### Backup & Restore

| Tool | Description |
|------|-------------|
| `list_backups` | List backup files (filter by node, storage, or VMID) |
| `create_backup` | Create a vzdump backup (snapshot/suspend/stop modes, zstd/lzo/gzip) |
| `restore_backup` | Restore a VM or CT from a backup file (requires confirmation) |

### Command Execution

| Tool | Description |
|------|-------------|
| `exec_command` | Run a command inside a QEMU VM via guest agent |

> **Note:** `exec_command` requires `qemu-guest-agent` installed and running inside the VM. Not supported for LXC containers (Proxmox API limitation).

### Snapshots

| Tool | Description |
|------|-------------|
| `list_snapshots` | List all snapshots for a VM/CT |
| `create_snapshot` | Create a new snapshot |
| `rollback_snapshot` | Rollback to a snapshot (requires confirmation) |
| `delete_snapshot` | Delete a snapshot (requires confirmation) |

### Network

| Tool | Description |
|------|-------------|
| `list_networks` | List bridges, bonds, and physical interfaces on a node |

### Resize

| Tool | Description |
|------|-------------|
| `resize_guest` | Resize CPU, memory, and/or disk of a VM or container (requires confirmation) |

### Monitoring

| Tool | Description |
|------|-------------|
| `get_guest_metrics` | CPU, memory, network, disk I/O over time |
| `list_tasks` | Recent tasks on a node (backups, migrations, etc.) |

### Firewall

| Tool | Description |
|------|-------------|
| `list_firewall_rules` | List firewall rules for a VM/CT, node, or the cluster |
| `add_firewall_rule` | Add a firewall rule (action, direction, protocol, port, source/dest) |
| `delete_firewall_rule` | Delete a firewall rule by position (requires confirmation) |

### Migration

| Tool | Description |
|------|-------------|
| `migrate_guest` | Live or offline migrate a VM/CT to another node (requires confirmation) |

### Templates & Cloud-init

| Tool | Description |
|------|-------------|
| `list_templates` | List all VM templates available for cloning |
| `create_template` | Convert a stopped VM into a template (requires confirmation, irreversible) |
| `configure_cloud_init` | Set user, password, SSH keys, IP config, and DNS on a VM |

### Safety

Destructive operations (`stop_guest`, `reboot_guest`, `rollback_snapshot`, `delete_snapshot`, `delete_guest`, `resize_guest`, `restore_backup`, `delete_firewall_rule`, `migrate_guest`, `create_template`) require explicit `confirm=true`. The first call returns a warning describing the impact; only a second call with confirmation executes the action.

## Examples

Once connected, you can ask your AI assistant:

- "List all my VMs and their status"
- "How much memory is VM 100 using?"
- "Shut down container 105"
- "Create a snapshot of VM 200 called before-upgrade"
- "Show me the CPU usage of VM 100 over the last day"
- "What tasks ran on node pve recently?"
- "Which VMs are stopped?"
- "What storage pools do I have and how full are they?"
- "Show me available ISO images"
- "Create a new Ubuntu VM with 4 cores and 8GB RAM"
- "Clone VM 100 as a test environment"
- "Create a Debian container from template"
- "Delete the old test VM 999"
- "Back up VM 100 to the zfs-backup-storage"
- "Show me all backups for VM 200"
- "Restore the latest backup of container 101"
- "Run 'df -h' on VM 100"
- "Check if nginx is running on VM 200"
- "Show me the network bridges on node pve"
- "Give VM 100 more CPU — bump it to 8 cores"
- "Add 50GB of disk to container 101"
- "Show me the firewall rules on VM 100"
- "Allow TCP port 443 on container 101"
- "Migrate VM 200 to node pve2"
- "List all templates in the cluster"
- "Convert VM 102 into a template"
- "Set cloud-init on VM 100: user admin, IP dhcp, DNS 8.8.8.8"

## Development

```bash
git clone https://github.com/antonio-mello-ai/mcp-proxmox.git
cd mcp-proxmox
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/
```

## License

MIT
