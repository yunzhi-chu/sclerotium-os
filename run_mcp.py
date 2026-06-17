#!/usr/bin/env python3
"""Sclerotium OS — MCP Server Entry Point.

Starts the MCP server on stdio, exposing all Sclerotium OS tools to LLMs.

Usage:
  python run_mcp.py                  # stdio mode (Claude Desktop etc.)
  python run_mcp.py --test           # run self-test
  python run_mcp.py --init-all       # test with bridge initialization
  python run_mcp.py --list-tools     # print registered tools
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


async def _init_bridges() -> dict[str, bool]:
    """Initialize all bridges. Returns status per bridge."""
    status: dict[str, bool] = {}

    # Fungal Bridge
    try:
        from bridges.fungal_bridge import FungalBridge
        fungal = FungalBridge()
        await fungal.initialize()
        status["fungal_bridge"] = True
        # Inject into tools that need it
        import mcp.tools.evolution as evo
        evo._fungal_bridge = fungal
    except Exception as e:
        status["fungal_bridge"] = False
        status["fungal_error"] = str(e)[:100]

    # MiroFish Bridge
    try:
        from bridges.mirofish_bridge import MiroFishBridge
        mirofish = MiroFishBridge()
        await mirofish.initialize()
        status["mirofish_bridge"] = True
        # Inject into evolution tools
        import mcp.tools.evolution as evo
        evo.set_bridge(mirofish)
    except Exception as e:
        status["mirofish_bridge"] = False
        status["mirofish_error"] = str(e)[:100]

    return status


async def run_server() -> None:
    from mcp.server import SclerotiumMCPServer

    server = SclerotiumMCPServer()
    server.register_all_tools()

    print(f"[Sclerotium OS MCP] {server.tools.tool_count} tools registered", file=sys.stderr)

    # Initialize bridges
    bridge_status = await _init_bridges()
    for name, ok in bridge_status.items():
        if not name.endswith("_error"):
            state = "OK" if ok else "FAIL"
            print(f"[Sclerotium OS MCP] Bridge {name}: {state}", file=sys.stderr)

    print("[Sclerotium OS MCP] Ready", file=sys.stderr)
    await server.run()


async def run_test(init_bridges: bool = False) -> None:
    from mcp.server import SclerotiumMCPServer

    server = SclerotiumMCPServer()
    server.register_all_tools()

    print(f"[OK] {server.tools.tool_count} tools registered\n")

    if init_bridges:
        print("--- Bridge Initialization ---")
        status = await _init_bridges()
        for name, ok in status.items():
            state = "OK" if ok else "FAIL"
            print(f"  {name}: {state}")

    # List tools
    for tool in server.tools.list_tools()[:5]:
        desc = tool['description'][:60]
        print(f"  - {tool['name']}: {desc}")
    print(f"  ... ({server.tools.tool_count} total)\n")

    # Call system_status
    print("--- system_status() ---")
    handler = server.tools.get_handler("system_status")
    if handler:
        result = await handler()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    # Call evolution_status (will be idle without bridge)
    print("\n--- evolution_status() ---")
    handler = server.tools.get_handler("evolution_status")
    if handler:
        result = await handler()
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    print("\n[OK] MCP Server self-test passed")


def list_tools() -> None:
    from mcp.server import SclerotiumMCPServer
    server = SclerotiumMCPServer()
    server.register_all_tools()
    print(f"{server.tools.tool_count} tools registered:\n")
    for tool in server.tools.list_tools():
        print(f"  [{tool['category']}] {tool['name']}")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--test" in args:
        init = "--init-all" in args
        asyncio.run(run_test(init_bridges=init))
    elif "--init-all" in args:
        asyncio.run(run_test(init_bridges=True))
    elif "--list-tools" in args:
        list_tools()
    else:
        asyncio.run(run_server())
