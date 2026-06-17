"""Sclerotium OS — MCP Server.

Model Context Protocol server that exposes all Sclerotium OS capabilities
as MCP tools consumable by LLMs (Claude, DeepSeek, etc.).

The server bridges LLM "consciousness" (mycelium.md system prompt) with
the Python "body" (fungal-cortex + MiroFish evolution engine).
"""

from .server import SclerotiumMCPServer, ToolRegistry

__all__ = ["SclerotiumMCPServer", "ToolRegistry"]
