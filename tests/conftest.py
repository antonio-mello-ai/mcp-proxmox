"""Test fixtures for mcp-proxmox."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mcp_proxmox.client import ProxmoxClient
from mcp_proxmox.config import ProxmoxConfig


@pytest.fixture
def config() -> ProxmoxConfig:
    """Create a test config."""
    return ProxmoxConfig(
        host="test-proxmox",
        token_id="test@pam!test-token",
        token_secret="00000000-0000-0000-0000-000000000000",
        verify_ssl=False,
    )


@pytest.fixture
def mock_client(config: ProxmoxConfig) -> ProxmoxClient:
    """Create a ProxmoxClient with a mocked API backend."""
    client = ProxmoxClient(config)
    client._api = MagicMock()
    return client
