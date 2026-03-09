# mcp-proxmox

MCP server for managing Proxmox VE clusters through AI assistants like Claude, Cursor, and Cline.

Query nodes, VMs, and containers. Start, stop, and snapshot guests. Monitor resource usage. All through natural language.

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
   - `VM.Audit` — read VM/CT status
   - `VM.PowerMgmt` — start/stop/shutdown/reboot
   - `VM.Snapshot` — create/rollback snapshots
   - `Sys.Audit` — read node status and tasks
   - `VM.Monitor` — access QEMU monitor (for metrics)

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

### Snapshots

| Tool | Description |
|------|-------------|
| `list_snapshots` | List all snapshots for a VM/CT |
| `create_snapshot` | Create a new snapshot |
| `rollback_snapshot` | Rollback to a snapshot (requires confirmation) |

### Monitoring

| Tool | Description |
|------|-------------|
| `get_guest_metrics` | CPU, memory, network, disk I/O over time |
| `list_tasks` | Recent tasks on a node (backups, migrations, etc.) |

### Safety

Destructive operations (`stop_guest`, `reboot_guest`, `rollback_snapshot`) require explicit `confirm=true`. The first call returns a warning describing the impact; only a second call with confirmation executes the action.

## Examples

Once connected, you can ask your AI assistant:

- "List all my VMs and their status"
- "How much memory is VM 100 using?"
- "Shut down container 105"
- "Create a snapshot of VM 200 called before-upgrade"
- "Show me the CPU usage of VM 100 over the last day"
- "What tasks ran on node pve recently?"
- "Which VMs are stopped?"

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
