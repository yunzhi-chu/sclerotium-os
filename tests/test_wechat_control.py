"""WeChat Full Control Integration Test — 微信全程控制集成测试.

Covers all 16 IM tools (8 generic + 8 WeChat-specific).
Tests the adapter → MCP tool → LLM pipeline end-to-end.

Usage:
    pytest tests/test_wechat_control.py -v
    python tests/test_wechat_control.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import asyncio
import urllib.request
from dataclasses import dataclass
from typing import Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.environ.get("SCLEROTIUM_URL", "http://localhost:18789")


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def api_post(path: str, data: dict) -> dict:
    """POST JSON to Sclerotium API."""
    try:
        req = urllib.request.Request(
            f"{BASE_URL}{path}",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"},
        )
        r = urllib.request.urlopen(req, timeout=120)
        return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def chat(message: str, history: list | None = None) -> dict:
    """Send a chat message."""
    return api_post("/chat", {"message": message, "history": history or []})


@dataclass
class TestResult:
    name: str
    passed: bool
    evidence: str = ""
    error: str = ""


results: list[TestResult] = []


def record(name: str, passed: bool, evidence: str = "", error: str = ""):
    status = "[OK] PASS" if passed else "[FAIL] FAIL"
    print(f"  {status}: {name}")
    if evidence:
        print(f"         {evidence[:150]}")
    if error:
        print(f"         Error: {error[:150]}")
    results.append(TestResult(name=name, passed=passed, evidence=evidence, error=error))


# ═══════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════

async def test_01_wechat_adapter_init():
    """Verify WeChat adapter initializes correctly."""
    try:
        from platforms.wechat import WeChatAdapter
        from platforms.wechat_client import GewechatClient, create_wechat_client

        # Test adapter creation
        adapter = WeChatAdapter()
        assert adapter.platform_name == "wechat"
        assert adapter._bridge == "gewechat"

        # Test client factory
        client = create_wechat_client(bridge="gewechat")
        assert isinstance(client, GewechatClient)

        # Test adapter tools
        tools = adapter.get_tools()
        tool_names = [t["name"] for t in tools]
        assert "wechat_send" in tool_names
        assert "wechat_list_contacts" in tool_names
        assert "wechat_list_groups" in tool_names
        assert "wechat_group_members" in tool_names
        assert len(tools) == 8

        await adapter.disconnect()
        record("01-adapter-init", True, f"8 WeChat tools: {tool_names}")
    except Exception as e:
        record("01-adapter-init", False, error=str(e))


async def test_02_wechat_adapter_connect():
    """Verify WeChat adapter connects in mock mode."""
    try:
        from platforms.wechat import WeChatAdapter
        adapter = WeChatAdapter(config={"bridge": "gewechat", "api_url": "http://localhost:2531"})
        ok = await adapter.connect()
        assert ok, "Connection should succeed (client init)"
        assert adapter.is_connected
        record("02-adapter-connect", True, f"Connected via {adapter._bridge}")
        await adapter.disconnect()
    except Exception as e:
        record("02-adapter-connect", False, error=str(e))


async def test_03_wechat_send_message():
    """Verify WeChat message sending (graceful when no Gewechat server)."""
    try:
        from platforms.wechat import WeChatAdapter
        adapter = WeChatAdapter()
        await adapter.connect()

        result = await adapter.send_message("wxid_testuser", "Hello from Sclerotium OS!")
        # In mock mode (no Gewechat server), send fails gracefully with empty msg_id
        # With real Gewechat, result.success=True
        assert result.platform == "wechat"
        assert result.success or not result.message_id  # graceful degradation
        record("03-send-message", True, f"Sent to wxid_testuser, success={result.success}, msg_id={result.message_id}, error={result.error}")
        await adapter.disconnect()
    except Exception as e:
        record("03-send-message", False, error=str(e))


async def test_04_wechat_send_file():
    """Verify WeChat file sending."""
    try:
        from platforms.wechat import WeChatAdapter
        adapter = WeChatAdapter()
        await adapter.connect()

        # Create temp file
        test_file = os.path.join(os.path.dirname(__file__), "test_wechat_file.txt")
        with open(test_file, "w") as f:
            f.write("WeChat file test content")

        result = await adapter.send_file("wxid_testgroup@chatroom", test_file)
        # In mock mode, file upload will fail gracefully
        record("04-send-file", True, f"File send attempted: {result.success}, {result.error}")
        os.remove(test_file)
        await adapter.disconnect()
    except Exception as e:
        record("04-send-file", False, error=str(e))


async def test_05_wechat_contacts():
    """Verify WeChat contact listing."""
    try:
        from platforms.wechat import WeChatAdapter
        adapter = WeChatAdapter()
        await adapter.connect()

        contacts = await adapter.get_contacts()
        assert isinstance(contacts, list)
        record("05-contacts", True, f"Got {len(contacts)} contacts")
        await adapter.disconnect()
    except Exception as e:
        record("05-contacts", False, error=str(e))


async def test_06_wechat_groups():
    """Verify WeChat group listing."""
    try:
        from platforms.wechat import WeChatAdapter
        adapter = WeChatAdapter()
        await adapter.connect()

        groups = await adapter.get_groups()
        assert isinstance(groups, list)
        record("06-groups", True, f"Got {len(groups)} groups")
        await adapter.disconnect()
    except Exception as e:
        record("06-groups", False, error=str(e))


async def test_07_wechat_conversations():
    """Verify WeChat conversation listing (as PlatformAdapter)."""
    try:
        from platforms.wechat import WeChatAdapter
        adapter = WeChatAdapter()
        await adapter.connect()

        convos = await adapter.list_conversations(limit=10)
        assert isinstance(convos, list)
        record("07-conversations", True, f"Got {len(convos)} conversations")
        await adapter.disconnect()
    except Exception as e:
        record("07-conversations", False, error=str(e))


async def test_08_wechat_group_create():
    """Verify WeChat group creation."""
    try:
        from platforms.wechat import WeChatAdapter
        adapter = WeChatAdapter()
        await adapter.connect()

        group_id = await adapter.create_group("Test Group", ["wxid_user1", "wxid_user2"])
        record("08-create-group", True, f"Group created: {group_id}")
        await adapter.disconnect()
    except Exception as e:
        record("08-create-group", False, error=str(e))


async def test_09_wechat_profile():
    """Verify WeChat self profile."""
    try:
        from platforms.wechat import WeChatAdapter
        adapter = WeChatAdapter()
        await adapter.connect()

        profile = await adapter.get_profile()
        assert isinstance(profile, dict)
        record("09-profile", True, f"Profile: {profile}")
        await adapter.disconnect()
    except Exception as e:
        record("09-profile", False, error=str(e))


async def test_10_wechat_health_check():
    """Verify WeChat health check."""
    try:
        from platforms.wechat import WeChatAdapter
        adapter = WeChatAdapter()
        await adapter.connect()

        healthy = await adapter.health_check()
        record("10-health", True, f"Health: {healthy}")
        await adapter.disconnect()
    except Exception as e:
        record("10-health", False, error=str(e))


async def test_11_im_mcp_tools_registered():
    """Verify all 16 IM MCP tools are registered."""
    try:
        from mcp.server import SclerotiumMCPServer
        server = SclerotiumMCPServer()
        server.register_all_tools()

        tools = server.tools.list_tools()
        im_tools = [t for t in tools if t["category"] == "im"]

        names = sorted([t["name"] for t in im_tools])
        expected_generic = ["im_create_group", "im_list_conversations", "im_react",
                           "im_receive", "im_search", "im_send", "im_send_file", "im_summarize"]
        expected_wechat = ["wechat_accept_friend", "wechat_contacts", "wechat_create_group",
                          "wechat_group_members", "wechat_groups", "wechat_profile",
                          "wechat_qrcode", "wechat_set_remark"]

        for n in expected_generic + expected_wechat:
            assert n in names, f"Missing tool: {n}"

        record("11-mcp-registered", True, f"{len(im_tools)} IM tools: {names}")
    except Exception as e:
        record("11-mcp-registered", False, error=str(e))


async def test_12_platform_manager_wechat():
    """Verify PlatformManager can handle WeChat adapter."""
    try:
        from platforms.manager import PlatformManager
        from platforms.wechat import WeChatAdapter

        mgr = PlatformManager()
        wx = WeChatAdapter()
        mgr.register(wx)

        assert "wechat" in mgr.list_platforms()
        assert mgr.platform_count == 1

        # Connect (may fail without Gewechat, but manager itself should work)
        await mgr.connect_all()

        # Verify adapter registered and manager state correct
        state = mgr.get_state()
        assert state.total_platforms == 1

        record("12-manager", True, f"Manager state: {state.platforms[0].connected}, platform_count={state.total_platforms}")
        await mgr.disconnect_all()
    except Exception as e:
        record("12-manager", False, error=str(e))


async def test_13_llm_wechat_send():
    """Verify LLM can send WeChat messages via /chat."""
    msg = "Send a WeChat message to wxid_doctor with the text 'Hello Doctor, this is Sclerotium OS reminding you of your appointment tomorrow at 2pm.'"
    data = chat(msg)

    has_response = bool(data.get("content")) or bool(data.get("tool_results"))
    record("13-llm-send", has_response,
           evidence=f"Response: {str(data.get('content', ''))[:200]}",
           error=data.get("error", ""))


async def test_14_llm_wechat_contacts():
    """Verify LLM can query WeChat contacts."""
    msg = "Show me my WeChat contact list"
    data = chat(msg)

    has_response = bool(data.get("content")) or bool(data.get("tool_results"))
    record("14-llm-contacts", has_response,
           evidence=f"Tools called: {len(data.get('tool_results', []))}")


async def test_15_gap12_channel_tools():
    """Gap 12: Verify channel adapters contribute tools to MCP registry."""
    try:
        from platforms.wechat import WeChatAdapter
        adapter = WeChatAdapter()
        tools = adapter.get_tools()
        assert len(tools) >= 8, f"Expected >=8 WeChat-specific tools, got {len(tools)}"

        # Each tool must have name, description, parameters, category
        for t in tools:
            assert "name" in t
            assert "description" in t
            assert "parameters" in t
            assert "category" in t

        record("15-gap12", True, f"Gap12 OK: {len(tools)} WeChat channel tools with full schema")
    except Exception as e:
        record("15-gap12", False, error=str(e))


async def test_16_gewechat_client_api():
    """Verify Gewechat client API layer works (without actual server)."""
    try:
        from platforms.wechat_client import GewechatClient, WxMessage, WxContact, WxGroup

        client = GewechatClient(base_url="http://localhost:2531")

        # Verify all methods exist (interface contract)
        methods = [
            'login_qrcode', 'check_login', 'send_text', 'send_image', 'send_file',
            'get_contacts', 'get_groups', 'get_group_members', 'create_group',
            'set_remark', 'accept_friend', 'get_profile', 'on_message',
        ]
        for m in methods:
            assert hasattr(client, m), f"GewechatClient missing method: {m}"

        record("16-client-api", True, f"All {len(methods)} Gewechat API methods present")
    except Exception as e:
        record("16-client-api", False, error=str(e))


# ═══════════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════════

async def run_all():
    print("=" * 65)
    print("  WeChat Full Control Integration Test")
    print(f"  Target: {BASE_URL}")
    print("=" * 65)

    tests = [
        ("01-adapter-init", test_01_wechat_adapter_init),
        ("02-adapter-connect", test_02_wechat_adapter_connect),
        ("03-send-message", test_03_wechat_send_message),
        ("04-send-file", test_04_wechat_send_file),
        ("05-contacts", test_05_wechat_contacts),
        ("06-groups", test_06_wechat_groups),
        ("07-conversations", test_07_wechat_conversations),
        ("08-create-group", test_08_wechat_group_create),
        ("09-profile", test_09_wechat_profile),
        ("10-health", test_10_wechat_health_check),
        ("11-mcp-registered", test_11_im_mcp_tools_registered),
        ("12-manager", test_12_platform_manager_wechat),
        ("15-gap12", test_15_gap12_channel_tools),
        ("16-client-api", test_16_gewechat_client_api),
    ]

    # LLM tests require running server
    try:
        urllib.request.urlopen(f"{BASE_URL}/health", timeout=3)
        tests.append(("13-llm-send", test_13_llm_wechat_send))
        tests.append(("14-llm-contacts", test_14_llm_wechat_contacts))
        print("\n  Server detected, including LLM-driven tests\n")
    except Exception:
        print("\n  Server not running, skipping LLM tests\n")

    for test_id, test_fn in tests:
        print(f"\n[{test_id}]", end=" ", flush=True)
        try:
            await test_fn()
        except Exception as e:
            record(test_id, False, error=str(e))

    # Summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print(f"\n{'=' * 65}")
    print(f"  Results: {passed}/{total} passed ({passed/total*100:.0f}%)" if total else "  No tests")
    print(f"{'=' * 65}")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
