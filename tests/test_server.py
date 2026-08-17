"""Smoke tests for the MCP server module.

The unit tests exercise the tool functions directly, so nothing else imports
``mcp_proxmox.server``. These tests make sure the server module — and the
MCP SDK API it depends on — still imports and registers every tool. This is
what breaks when the ``mcp`` package ships an incompatible major version
(see issue #13: ``mcp`` 2.0.0 removed ``mcp.server.fastmcp``).
"""

from __future__ import annotations

import asyncio

from mcp_proxmox import server


def test_server_module_imports() -> None:
    assert server.mcp.name == "mcp-proxmox"


def test_server_registers_tools() -> None:
    tools = asyncio.run(server.mcp.list_tools())
    names = {tool.name for tool in tools}

    assert len(names) == 34
    for expected in ("list_vms", "exec_command", "create_snapshot", "migrate_guest"):
        assert expected in names
