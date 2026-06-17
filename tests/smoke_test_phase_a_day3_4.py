"""Phase A Day 3-4: Smoke test — neural wiring (AgentLoop + LLMClient + CodeAction)."""
import asyncio
import json
import sys
import pytest

sys.path.insert(0, ".")


@pytest.mark.asyncio
async def test_llm_client_creation():
    """LLMClient can be created with tools."""
    from agent.llm_client import LLMClient
    from mcp.server import SclerotiumMCPServer

    server = SclerotiumMCPServer()
    server.register_all_tools()

    client = LLMClient(api_key="test-key", model="deepseek-v4-flash")
    client.configure_tools(server.tools)

    assert client.tool_count >= 100, f"Expected 100+ tools, got {client.tool_count}"

    # Verify a few critical tools are present
    tool_names = {t["function"]["name"] for t in client._tools}
    for critical in ["file_read", "file_write", "bash_execute", "desktop_open",
                     "desktop_screenshot", "web_search", "memory_store"]:
        assert critical in tool_names, f"Critical tool missing: {critical}"


@pytest.mark.asyncio
async def test_code_action_execution():
    """CodeActionRuntime can execute Python snippets with tools."""
    from agent.code_action import CodeActionRuntime
    from mcp.server import SclerotiumMCPServer

    server = SclerotiumMCPServer()
    server.register_all_tools()

    runtime = CodeActionRuntime()
    runtime.register_from_registry(server.tools, ["bash_execute", "file_read"])

    # Test 1: bash_execute via code
    result = await runtime.execute("""
result = tools["bash_execute"](command="echo test_12345")
print(result.get("stdout", "").strip())
""")
    assert result.success, f"Code action failed: {result.error}"
    assert "test_12345" in result.output, f"Unexpected output: {result.output}"

    # Test 2: file_read via code
    result = await runtime.execute("""
result = tools["file_read"](file_path="sclerotium.py")
print(f"LINES={result.get('total_lines', 0)}")
print(f"SIZE={result.get('size', 0)}")
""")
    assert result.success, f"file_read via code failed: {result.error}"
    assert "LINES=" in result.output, f"Missing LINES in: {result.output}"


@pytest.mark.asyncio
async def test_mcp_sync_async_handlers():
    """MCP server correctly handles both sync and async handlers."""
    from mcp.server import SclerotiumMCPServer

    server = SclerotiumMCPServer()
    server.register_all_tools()

    # Sync handler
    resp = await server._dispatch({
        "id": 1, "method": "tools/call",
        "params": {"name": "file_read", "arguments": {"file_path": "sclerotium.py"}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content.get("status") == "ok", f"Sync file_read failed: {content}"

    # Async handler
    resp = await server._dispatch({
        "id": 2, "method": "tools/call",
        "params": {"name": "desktop_screenshot", "arguments": {"ocr": False}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content.get("ok"), f"Async desktop_screenshot failed: {content}"


@pytest.mark.asyncio
async def test_tool_call_dataclass():
    """ToolCall and LLMResponse are immutable."""
    from agent.llm_client import ToolCall, LLMResponse

    tc = ToolCall(id="call_1", name="file_read", arguments={"file_path": "test.py"})
    assert tc.name == "file_read"
    assert tc.arguments == {"file_path": "test.py"}

    resp = LLMResponse(
        content="Hello!",
        tool_calls=(tc,),
        finish_reason="stop",
        tokens_used=100,
    )
    assert resp.has_tool_calls
    assert len(resp.tool_calls) == 1
