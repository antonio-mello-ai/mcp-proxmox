"""Configuration for mcp-proxmox via environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class ProxmoxConfig:
    """Proxmox VE connection configuration.

    All values are read from environment variables or a .env file.

    Required:
        PROXMOX_HOST: Hostname or IP of the Proxmox VE server.
        PROXMOX_TOKEN_ID: API token ID in the format 'user@realm!tokenid'.
        PROXMOX_TOKEN_SECRET: API token secret (UUID).

    Optional:
        PROXMOX_PORT: API port (default: 8006).
        PROXMOX_VERIFY_SSL: Whether to verify SSL certificates (default: false).
    """

    host: str
    token_id: str
    token_secret: str
    port: int = 8006
    verify_ssl: bool = False

    @classmethod
    def from_env(cls) -> ProxmoxConfig:
        """Load configuration from environment variables."""
        load_dotenv()

        host = os.environ.get("PROXMOX_HOST", "")
        token_id = os.environ.get("PROXMOX_TOKEN_ID", "")
        token_secret = os.environ.get("PROXMOX_TOKEN_SECRET", "")

        if not all([host, token_id, token_secret]):
            missing = []
            if not host:
                missing.append("PROXMOX_HOST")
            if not token_id:
                missing.append("PROXMOX_TOKEN_ID")
            if not token_secret:
                missing.append("PROXMOX_TOKEN_SECRET")
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "See README.md for configuration instructions."
            )

        port = int(os.environ.get("PROXMOX_PORT", "8006"))
        verify_ssl = os.environ.get("PROXMOX_VERIFY_SSL", "false").lower() in (
            "true",
            "1",
            "yes",
        )

        return cls(
            host=host,
            token_id=token_id,
            token_secret=token_secret,
            port=port,
            verify_ssl=verify_ssl,
        )
