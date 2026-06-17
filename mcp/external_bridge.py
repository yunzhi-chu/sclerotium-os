"""External MCP Bridge — 动态接入外部 MCP Server (Claude Code 式扩展).

支持两种接入方式:
  1. Stdio MCP Server: 启动子进程，通过 stdin/stdout JSON-RPC 通信
  2. HTTP MCP Server: 连接远程 HTTP SSE 端点

接入后，外部工具自动注册到 Sclerotium ToolRegistry，
AI 大模型可像内置工具一样调用它们。

Usage:
    bridge = ExternalMCPBridge(registry)

    # 接入外部 MCP Server (stdio 模式)
    await bridge.connect_stdio("gsap-master",
        command="npx", args=["bruzethegreat-gsap-master-mcp-server@latest"])

    # 接入外部 MCP Server (HTTP 模式)
    await bridge.connect_http("figma-mcp", url="http://localhost:3333/mcp")

    # 列出所有外部工具
    tools = bridge.list_external_tools()

    # 断开
    await bridge.disconnect("gsap-master")
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.external_mcp")


@dataclass
class ExternalMCPServer:
    """Connected external MCP server."""
    name: str
    mode: str  # "stdio" | "http"
    process: Any = None       # asyncio subprocess
    session: Any = None       # aiohttp session
    url: str = ""
    tools: list[dict[str, Any]] = field(default_factory=list)
    connected: bool = False


class ExternalMCPBridge:
    """Bridge to connect external MCP servers into Sclerotium ToolRegistry.

    Every external tool gets registered as "ext/<server>/<tool_name>"
    and is callable by the AI like any built-in tool.
    """

    def __init__(self, registry: Any) -> None:
        self._registry = registry
        self._servers: dict[str, ExternalMCPServer] = {}
        self._tool_map: dict[str, tuple[str, str]] = {}  # tool_name → (server, original_name)

    # ── Connect ──────────────────────────────────────────────────────────

    async def connect_stdio(
        self, name: str, command: str, args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> bool:
        """Connect to an MCP server via stdio subprocess.

        Args:
            name: Server alias (e.g. "gsap-master")
            command: Executable (e.g. "npx", "python")
            args: Command arguments
            env: Environment variables

        Returns:
            True if connected and tools registered
        """
        if name in self._servers:
            logger.warning("Server '%s' already connected", name)
            return False

        try:
            full_args = [command] + (args or [])
            merged_env = {**os.environ, **(env or {})}

            process = await asyncio.create_subprocess_exec(
                *full_args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=merged_env,
            )

            # Initialize MCP handshake
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "1.0",
                    "clientInfo": {"name": "SclerotiumOS", "version": "5.2.0"},
                    "capabilities": {},
                },
            }

            response = await self._send_stdio(process, init_request)
            if response is None:
                logger.error("MCP init failed for %s", name)
                process.kill()
                return False

            # List tools
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            }
            tools_response = await self._send_stdio(process, tools_request)
            if tools_response is None:
                process.kill()
                return False

            tools = tools_response.get("result", {}).get("tools", [])

            # Register server
            server = ExternalMCPServer(
                name=name,
                mode="stdio",
                process=process,
                tools=tools,
                connected=True,
            )
            self._servers[name] = server

            # Register all tools into the registry
            for tool in tools:
                ext_name = f"ext_{name}_{tool['name']}"
                self._tool_map[ext_name] = (name, tool["name"])
                self._register_external_tool(ext_name, tool, name)

            logger.info("Connected to MCP server '%s': %d tools", name, len(tools))
            return True

        except Exception as e:
            logger.error("Failed to connect MCP server '%s': %s", name, e)
            return False

    async def connect_http(self, name: str, url: str) -> bool:
        """Connect to an MCP server via HTTP SSE.

        Args:
            name: Server alias
            url: HTTP endpoint URL

        Returns:
            True if connected
        """
        if name in self._servers:
            return False

        try:
            import aiohttp

            session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))

            # Initialize
            async with session.post(
                f"{url}/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                    "protocolVersion": "1.0",
                    "clientInfo": {"name": "SclerotiumOS", "version": "5.2.0"},
                    "capabilities": {},
                }},
            ) as resp:
                await resp.json()

            # List tools
            async with session.post(
                f"{url}/mcp",
                json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            ) as resp:
                data = await resp.json()
                tools = data.get("result", {}).get("tools", [])

            server = ExternalMCPServer(
                name=name,
                mode="http",
                session=session,
                url=url,
                tools=tools,
                connected=True,
            )
            self._servers[name] = server

            for tool in tools:
                ext_name = f"ext_{name}_{tool['name']}"
                self._tool_map[ext_name] = (name, tool["name"])
                self._register_external_tool(ext_name, tool, name)

            logger.info("Connected to HTTP MCP '%s': %d tools", name, len(tools))
            return True

        except Exception as e:
            logger.error("Failed to connect HTTP MCP '%s': %s", name, e)
            return False

    # ── Disconnect ───────────────────────────────────────────────────────

    async def disconnect(self, name: str) -> bool:
        """Disconnect an external MCP server and unregister its tools."""
        server = self._servers.pop(name, None)
        if server is None:
            return False

        # Unregister tools
        ext_prefix = f"ext_{name}_"
        to_remove = [tn for tn in self._tool_map if tn.startswith(ext_prefix)]
        for tn in to_remove:
            self._tool_map.pop(tn, None)
            # Note: ToolRegistry doesn't support unregister yet
            # In practice, tools persist until server restart

        # Clean up
        if server.mode == "stdio" and server.process:
            try:
                server.process.kill()
                await server.process.wait()
            except Exception:
                pass

        if server.session:
            await server.session.close()

        logger.info("Disconnected MCP server '%s'", name)
        return True

    async def disconnect_all(self) -> None:
        for name in list(self._servers.keys()):
            await self.disconnect(name)

    # ── Tool execution ───────────────────────────────────────────────────

    async def call_external_tool(
        self, tool_name: str, arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool on an external MCP server."""
        if tool_name not in self._tool_map:
            return {"error": f"Unknown external tool: {tool_name}"}

        server_name, original_name = self._tool_map[tool_name]
        server = self._servers.get(server_name)
        if server is None:
            return {"error": f"Server disconnected: {server_name}"}

        request = {
            "jsonrpc": "2.0",
            "id": uuid.uuid4().int % 10000,
            "method": "tools/call",
            "params": {"name": original_name, "arguments": arguments},
        }

        if server.mode == "stdio":
            response = await self._send_stdio(server.process, request)
            if response is None:
                return {"error": "MCP call failed"}
            return response.get("result", {})

        else:  # HTTP
            try:
                async with server.session.post(
                    f"{server.url}/mcp", json=request,
                ) as resp:
                    return await resp.json()
            except Exception as e:
                return {"error": str(e)}

    # ── List ─────────────────────────────────────────────────────────────

    def list_external_tools(self) -> list[dict[str, Any]]:
        """List all tools from all connected external MCP servers."""
        tools = []
        for name, server in self._servers.items():
            for tool in server.tools:
                ext_name = f"ext_{name}_{tool['name']}"
                tools.append({
                    "name": ext_name,
                    "description": tool.get("description", ""),
                    "server": name,
                    "original_name": tool["name"],
                })
        return tools

    def list_servers(self) -> list[dict[str, Any]]:
        """List connected servers with tool counts."""
        return [
            {"name": s.name, "mode": s.mode, "tools": len(s.tools), "connected": s.connected}
            for s in self._servers.values()
        ]

    @property
    def server_count(self) -> int:
        return len(self._servers)

    @property
    def external_tool_count(self) -> int:
        return sum(len(s.tools) for s in self._servers.values())

    # ── Internal ─────────────────────────────────────────────────────────

    async def _send_stdio(self, process: Any, request: dict) -> dict | None:
        """Send JSON-RPC request to stdio MCP server and read response.

        Supports both newline-delimited and Content-Length-prefixed MCP protocols.
        """
        try:
            line = json.dumps(request, ensure_ascii=False) + "\n"
            process.stdin.write(line.encode())
            await process.stdin.drain()

            # Try Content-Length prefixed format first (MCP spec standard)
            header_line = await asyncio.wait_for(
                process.stdout.readline(), timeout=30,
            )
            header = header_line.decode().strip()

            if header.startswith("Content-Length:"):
                try:
                    length = int(header.split(":")[1].strip())
                    # Read the empty line after header
                    await process.stdout.readline()
                    # Read exact content length
                    body = await asyncio.wait_for(
                        process.stdout.readexactly(length), timeout=30,
                    )
                    return json.loads(body.decode())
                except (ValueError, asyncio.TimeoutError):
                    pass

            # Fallback: newline-delimited JSON
            if header:
                try:
                    return json.loads(header)
                except json.JSONDecodeError:
                    pass

            # Last resort: read more data
            try:
                chunk = await asyncio.wait_for(
                    process.stdout.read(65536), timeout=10,
                )
                text = (header + "\n" + chunk.decode()).strip()
                return json.loads(text)
            except (json.JSONDecodeError, Exception):
                return None

        except asyncio.TimeoutError:
            logger.error("MCP stdio timeout for %s", request.get("method"))
            return None
        except Exception as e:
            logger.error("MCP stdio error: %s", e)
            return None

    def _register_external_tool(
        self, ext_name: str, tool_def: dict[str, Any], server_name: str,
    ) -> None:
        """Register an external tool into the ToolRegistry."""
        original_name = tool_def["name"]
        description = tool_def.get("description", "")
        parameters = tool_def.get("parameters", tool_def.get("inputSchema", {}))

        # Create async handler that forwards to external server
        async def external_handler(**kwargs: Any) -> dict[str, Any]:
            return await self.call_external_tool(ext_name, kwargs)

        try:
            self._registry.register(
                name=ext_name,
                description=f"[ext:{server_name}] {description}",
                parameters=parameters,
                handler=external_handler,
                category=f"external/{server_name}",
            )
        except Exception as e:
            logger.warning("Failed to register external tool %s: %s", ext_name, e)
