"""MCP Auto-Installer Tool — self-acquire MCP, skills, software."""
from __future__ import annotations
from typing import Any
from mcp.server import ToolRegistry


async def _auto_acquire(url_or_name: str = "", search_query: str = "") -> dict[str, Any]:
    """Search and install MCP servers, skills, or software."""
    from kernel.auto_installer import auto_acquire, search_github, search_web
    if url_or_name:
        return auto_acquire(url_or_name)
    if search_query:
        gh = search_github(search_query)
        web = search_web(search_query)
        return {"ok": True, "github": gh[:5], "web": web[:5]}
    return {"ok": False, "error": "Provide url_or_name or search_query"}


def register_installer_tools(registry: ToolRegistry) -> None:
    registry.register(
        name="auto_install",
        description="Search/install MCP servers, skills, or software. Give a URL to install, or a name to search GitHub + web.",
        parameters={
            "type": "object",
            "properties": {
                "url_or_name": {"type": "string", "default": "", "description": "URL or name to install"},
                "search_query": {"type": "string", "default": "", "description": "Search query for GitHub + web"},
            },
            "required": [],
        },
        handler=_auto_acquire,
        category="installer",
    )
