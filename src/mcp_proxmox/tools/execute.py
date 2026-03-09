"""Command execution tools: run commands inside VMs and containers."""

from __future__ import annotations

import time
from typing import Any

from mcp_proxmox.client import ProxmoxClient

_MAX_WAIT_SECONDS = 30
_POLL_INTERVAL = 1.0


def exec_command(
    client: ProxmoxClient,
    vmid: int,
    command: str,
    timeout: int = 30,
) -> dict[str, Any]:
    """Execute a command inside a VM via QEMU guest agent.

    Requires the QEMU guest agent to be installed and running inside the VM.
    Only supported for QEMU VMs (not LXC containers).
    """
    if not command.strip():
        return {"error": "Command cannot be empty"}

    if timeout < 1 or timeout > 300:
        return {"error": "Timeout must be between 1 and 300 seconds"}

    guest = client.find_guest(vmid)
    if not guest:
        return {"error": f"Guest with VMID {vmid} not found in cluster"}

    guest_type = guest["type"]
    if guest_type != "qemu":
        return {
            "error": f"Command execution is only supported for QEMU VMs, "
            f"not LXC containers. VMID {vmid} is an LXC container.",
        }

    node = guest["node"]
    guest_name = guest.get("name", f"VMID {vmid}")
    current_status = guest.get("status", "unknown")

    if current_status != "running":
        return {"error": f"VM '{guest_name}' ({vmid}) is not running (status: {current_status})"}

    try:
        exec_result = client.exec_qemu_agent(node, vmid, command)
    except Exception as e:
        error_msg = str(e)
        if "not running" in error_msg.lower() or "agent" in error_msg.lower():
            return {
                "error": f"QEMU guest agent is not responding on VM '{guest_name}' ({vmid}). "
                "Ensure qemu-guest-agent is installed and running inside the VM.",
            }
        return {"error": f"Failed to execute command: {error_msg}"}

    pid = exec_result.get("pid", 0)
    if not pid:
        return {"error": "Failed to get execution PID from guest agent"}

    # Poll for result
    wait_time = min(timeout, _MAX_WAIT_SECONDS)
    elapsed = 0.0
    while elapsed < wait_time:
        time.sleep(_POLL_INTERVAL)
        elapsed += _POLL_INTERVAL
        try:
            status = client.exec_qemu_agent_status(node, vmid, pid)
            if status.get("exited"):
                exit_code = status.get("exitcode", -1)
                stdout = status.get("out-data", "")
                stderr = status.get("err-data", "")

                result: dict[str, Any] = {
                    "vmid": vmid,
                    "name": guest_name,
                    "command": command,
                    "exit_code": exit_code,
                    "success": exit_code == 0,
                }
                if stdout:
                    result["stdout"] = stdout
                if stderr:
                    result["stderr"] = stderr
                return result
        except Exception:
            continue

    return {
        "vmid": vmid,
        "name": guest_name,
        "command": command,
        "pid": pid,
        "status": "running",
        "message": (
            f"Command still running after {wait_time}s. PID {pid} on VM '{guest_name}' ({vmid})."
        ),
    }
