"""MCP Mode Tool — neuromodulation profile switching."""

from __future__ import annotations

from typing import Any

from mcp.server import ToolRegistry
from kernel.stg.neuromodulator import Neuromodulator

_nm = Neuromodulator()


async def _mode_switch(profile: str) -> dict:
    return _nm.switch(profile)


def register_mode_tools(registry: ToolRegistry) -> None:
    registry.register(
        name="mode_switch",
        description="Switch neuromodulation profile: work, sleep, game, meeting, or creative. Reconfigures notification level, evolution, LLM routing, scan frequency, and auto-reply.",
        parameters={
            "type": "object",
            "properties": {
                "profile": {
                    "type": "string",
                    "description": "Profile name",
                    "enum": ["work", "sleep", "game", "meeting", "creative"],
                },
            },
            "required": ["profile"],
        },
        handler=_mode_switch,
        category="system",
    )
