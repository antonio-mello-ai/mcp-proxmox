"""Storage tools: list storages, ISOs, templates, and backups."""

from __future__ import annotations

from typing import Any

from mcp_proxmox.client import ProxmoxClient


def _format_bytes(value: int | float) -> str:
    """Format bytes into human-readable string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"


def list_storages(client: ProxmoxClient, node: str | None = None) -> dict[str, Any]:
    """List storage pools across the cluster or for a specific node."""
    nodes = client.get_nodes()
    if node:
        nodes = [n for n in nodes if n.get("node") == node]
        if not nodes:
            return {"error": f"Node '{node}' not found in cluster"}

    all_storages: list[dict[str, Any]] = []
    seen: set[str] = set()

    for n in nodes:
        node_name = n.get("node", "")
        storages = client.get_storages(node_name)
        for s in storages:
            storage_id = f"{node_name}:{s.get('storage', '')}"
            if storage_id in seen:
                continue
            seen.add(storage_id)

            total = s.get("total", 0)
            used = s.get("used", 0)
            avail = s.get("avail", 0)

            all_storages.append(
                {
                    "storage": s.get("storage"),
                    "node": node_name,
                    "type": s.get("type", ""),
                    "content": s.get("content", ""),
                    "enabled": bool(s.get("enabled", 1)),
                    "shared": bool(s.get("shared", 0)),
                    "total": _format_bytes(total) if total else "N/A",
                    "used": _format_bytes(used) if used else "N/A",
                    "available": _format_bytes(avail) if avail else "N/A",
                    "usage": f"{(used / total * 100):.1f}%" if total else "N/A",
                }
            )

    return {
        "total": len(all_storages),
        "storages": sorted(all_storages, key=lambda x: (x["node"], x["storage"])),
    }


def list_storage_content(
    client: ProxmoxClient,
    node: str,
    storage: str,
    content_type: str | None = None,
) -> dict[str, Any]:
    """List content of a storage pool.

    content_type can be: 'iso', 'vztmpl', 'backup', 'images', 'rootdir'.
    """
    valid_types = ("iso", "vztmpl", "backup", "images", "rootdir")
    if content_type and content_type not in valid_types:
        return {
            "error": f"Invalid content type '{content_type}'. "
            f"Must be one of: {', '.join(valid_types)}"
        }

    content = client.get_storage_content(node, storage, content_type)

    items: list[dict[str, Any]] = []
    for item in content:
        entry: dict[str, Any] = {
            "volid": item.get("volid", ""),
            "content": item.get("content", ""),
            "format": item.get("format", ""),
            "size": _format_bytes(item.get("size", 0)),
        }
        if item.get("notes"):
            entry["notes"] = item["notes"]
        if item.get("ctime"):
            entry["created"] = item["ctime"]
        if item.get("vmid"):
            entry["vmid"] = item["vmid"]
        items.append(entry)

    label = content_type or "all"
    return {
        "node": node,
        "storage": storage,
        "content_type": label,
        "total": len(items),
        "items": items,
    }
