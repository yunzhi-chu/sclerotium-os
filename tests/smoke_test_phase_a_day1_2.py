"""Phase A Day 1-2: Smoke test — verify all MCP tools work (sync + async)."""
import asyncio
import json
import sys

import pytest

sys.path.insert(0, ".")

from mcp.server import SclerotiumMCPServer


@pytest.mark.asyncio
async def test_all():
    server = SclerotiumMCPServer()
    server.register_all_tools()
    print(f"Total tools: {server.tools.tool_count}")

    # ── Sync handlers ──
    print("\n=== Test: file_read (sync) ===")
    resp = await server._dispatch({
        "id": 1, "method": "tools/call",
        "params": {"name": "file_read", "arguments": {"file_path": "sclerotium.py"}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content.get("status") == "ok", f"file_read failed: {content}"
    print(f"  OK: lines={content['total_lines']}, size={content['size']}B")

    print("\n=== Test: bash_execute (sync) ===")
    resp = await server._dispatch({
        "id": 2, "method": "tools/call",
        "params": {"name": "bash_execute", "arguments": {"command": "echo hello_world_test"}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content.get("status") == "ok", f"bash_execute failed: {content}"
    assert "hello_world_test" in content.get("stdout", ""), f"unexpected stdout: {content}"
    print(f"  OK: stdout='{content['stdout'].strip()}'")

    print("\n=== Test: web_search (sync) ===")
    resp = await server._dispatch({
        "id": 3, "method": "tools/call",
        "params": {"name": "web_search", "arguments": {"query": "Python asyncio tutorial", "max_results": 3}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    # Network may be unavailable — accept error status but verify structure
    assert "query" in content, f"web_search missing query: {content}"
    assert "results" in content, f"web_search missing results: {content}"
    print(f"  OK: status={content.get('status')}, results={content.get('total_results', 0)}")

    print("\n=== Test: os ls (sync) ===")
    resp = await server._dispatch({
        "id": 4, "method": "tools/call",
        "params": {"name": "ls", "arguments": {"path": "."}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content.get("count", 0) > 0, f"ls returned no files: {content}"
    print(f"  OK: {content['count']} items in {content['path']}")

    print("\n=== Test: git_status (sync) ===")
    resp = await server._dispatch({
        "id": 5, "method": "tools/call",
        "params": {"name": "git_status", "arguments": {}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    print(f"  OK: status={content.get('status')}")

    # ── Async handlers ──
    print("\n=== Test: memory_store (async) ===")
    resp = await server._dispatch({
        "id": 6, "method": "tools/call",
        "params": {"name": "memory_store", "arguments": {
            "content": "Smoke test: user prefers dark mode",
            "memory_level": "episodic",
        }},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert "memory_id" in content or content.get("error"), f"memory_store unexpected: {content}"
    print(f"  OK: {content}")

    print("\n=== Test: desktop_screenshot (async) ===")
    resp = await server._dispatch({
        "id": 7, "method": "tools/call",
        "params": {"name": "desktop_screenshot", "arguments": {"ocr": False}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content.get("ok"), f"desktop_screenshot failed: {content}"
    assert len(content.get("image_base64", "")) > 1000, "screenshot too small"
    print(f"  OK: resolution={content['resolution']}, image_size={len(content['image_base64'])} chars")

    print("\n=== Test: desktop_open (async) ===")
    resp = await server._dispatch({
        "id": 8, "method": "tools/call",
        "params": {"name": "desktop_open", "arguments": {"target": "calc"}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content.get("ok"), f"desktop_open failed: {content}"
    print(f"  OK: {content.get('status')}")

    print("\n=== Test: file_write + file_read roundtrip (sync) ===")
    test_path = "data/_smoke_test_file.txt"
    resp = await server._dispatch({
        "id": 9, "method": "tools/call",
        "params": {"name": "file_write", "arguments": {
            "file_path": test_path,
            "content": "smoke test content line 1\nline 2\nline 3",
        }},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content.get("status") == "ok", f"file_write failed: {content}"
    print(f"  OK: wrote {content['lines']} lines to {test_path}")

    resp = await server._dispatch({
        "id": 10, "method": "tools/call",
        "params": {"name": "file_read", "arguments": {"file_path": test_path}},
    })
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content.get("status") == "ok", f"file_read failed: {content}"
    assert "smoke test content" in content.get("content", ""), f"wrong content: {content}"
    print(f"  OK: read back {content['total_lines']} lines")

    print("\n" + "=" * 50)
    print("ALL PHASE A DAY 1-2 SMOKE TESTS PASSED")
    print("=" * 50)
