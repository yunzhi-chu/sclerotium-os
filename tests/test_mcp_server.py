"""Tests for MCP Server core — ToolRegistry + JSON-RPC dispatch."""

from __future__ import annotations

import json
import pytest

from mcp.server import SclerotiumMCPServer, ToolRegistry


# ── ToolRegistry tests ───────────────────────────────────────────────


class TestToolRegistry:
    def test_register(self):
        registry = ToolRegistry()
        async def dummy():
            return {"ok": True}
        registry.register("test", "A test tool", {"type": "object"}, dummy)
        assert registry.tool_count == 1
        assert registry.get_handler("test") is not None

    def test_register_duplicate(self):
        registry = ToolRegistry()
        async def dummy():
            return {}
        registry.register("dup", "first", {}, dummy)
        registry.register("dup", "second", {}, dummy)  # overwrites
        assert registry.tool_count == 1  # still one

    def test_list_tools(self):
        registry = ToolRegistry()
        async def dummy():
            return {}
        registry.register("a", "desc a", {"type": "object"}, dummy, "cat1")
        registry.register("b", "desc b", {"type": "object"}, dummy, "cat2")
        tools = registry.list_tools()
        assert len(tools) == 2
        names = {t["name"] for t in tools}
        assert names == {"a", "b"}
        categories = {t["category"] for t in tools}
        assert categories == {"cat1", "cat2"}

    def test_get_handler_unknown(self):
        registry = ToolRegistry()
        assert registry.get_handler("nonexistent") is None

    def test_get_tool_unknown(self):
        registry = ToolRegistry()
        assert registry.get_tool("nonexistent") is None


# ── MCP Server tests ─────────────────────────────────────────────────


class TestMCPServer:
    def test_server_creation(self):
        server = SclerotiumMCPServer()
        assert server.tools.tool_count == 0
        stats = server.get_stats()
        assert stats["tool_count"] == 0
        assert stats["request_count"] == 0

    def test_register_all_tools(self):
        server = SclerotiumMCPServer()
        server.register_all_tools()
        assert server.tools.tool_count >= 2  # system_status + system_config

    def test_system_status_tool(self):
        server = SclerotiumMCPServer()
        server.register_all_tools()
        handler = server.tools.get_handler("system_status")
        assert handler is not None

    def test_system_config_tool(self):
        server = SclerotiumMCPServer()
        server.register_all_tools()
        handler = server.tools.get_handler("system_config")
        assert handler is not None

    @pytest.mark.asyncio
    async def test_system_status_returns_valid_json(self):
        server = SclerotiumMCPServer()
        server.register_all_tools()
        handler = server.tools.get_handler("system_status")
        result = await handler()
        assert "layers" in result
        assert result["layers"]["mcp"] == "running"
        assert "resources" in result
        assert "uptime_seconds" in result

    @pytest.mark.asyncio
    async def test_system_config_read_all(self):
        server = SclerotiumMCPServer()
        server.register_all_tools()
        handler = server.tools.get_handler("system_config")
        result = await handler()
        assert "config" in result
        assert "evolution.default_generations" in result["config"]

    @pytest.mark.asyncio
    async def test_system_config_read_single(self):
        server = SclerotiumMCPServer()
        server.register_all_tools()
        handler = server.tools.get_handler("system_config")
        result = await handler(key="evolution.default_generations")
        assert result["key"] == "evolution.default_generations"
        assert result["value"] == 10

    @pytest.mark.asyncio
    async def test_system_config_write(self):
        server = SclerotiumMCPServer()
        server.register_all_tools()
        handler = server.tools.get_handler("system_config")
        result = await handler(key="test.key", value=42)
        assert result["status"] == "updated"
        # Read back
        result = await handler(key="test.key")
        assert result["value"] == 42

    def test_stats_tracking(self):
        server = SclerotiumMCPServer()
        server._request_count = 5
        server._error_count = 2
        stats = server.get_stats()
        assert stats["request_count"] == 5
        assert stats["error_count"] == 2


# ── JSON-RPC dispatch tests ──────────────────────────────────────────


class TestDispatch:
    @pytest.mark.asyncio
    async def test_initialize(self):
        server = SclerotiumMCPServer()
        response = await server._dispatch({
            "jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}
        })
        assert response["id"] == 1
        assert response["result"]["protocolVersion"] == "1.0"

    @pytest.mark.asyncio
    async def test_list_tools(self):
        server = SclerotiumMCPServer()
        server.register_all_tools()
        response = await server._dispatch({
            "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}
        })
        assert response["id"] == 2
        assert len(response["result"]["tools"]) >= 2

    @pytest.mark.asyncio
    async def test_call_tool(self):
        server = SclerotiumMCPServer()
        server.register_all_tools()
        response = await server._dispatch({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "system_status", "arguments": {}}
        })
        assert response["id"] == 3
        content = response["result"]["content"][0]["text"]
        data = json.loads(content)
        assert "layers" in data

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self):
        server = SclerotiumMCPServer()
        response = await server._dispatch({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}}
        })
        assert response["id"] == 4
        assert "error" in response

    @pytest.mark.asyncio
    async def test_ping(self):
        server = SclerotiumMCPServer()
        response = await server._dispatch({
            "jsonrpc": "2.0", "id": 5, "method": "ping", "params": {}
        })
        assert response["id"] == 5

    @pytest.mark.asyncio
    async def test_unknown_method(self):
        server = SclerotiumMCPServer()
        response = await server._dispatch({
            "jsonrpc": "2.0", "id": 6, "method": "fly_to_moon", "params": {}
        })
        assert "error" in response
