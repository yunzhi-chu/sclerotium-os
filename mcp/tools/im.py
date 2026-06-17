"""MCP IM Tools — 8 general + 8 WeChat-specific messaging tools.

OpenClaw equivalent: gateway tools + channel-tools.ts
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from mcp.server import ToolRegistry

logger = logging.getLogger("sclerotium.im")

# iLink adapter wrapper
class _ILinkAdapter:
    """Minimal adapter wrapping wechat_ilink for MCP tool compatibility."""
    platform_name = "wechat"
    is_connected = True

    def connect(self): return True
    async def disconnect(self): pass

    async def send_message(self, target: str, content: str, rich_content=None):
        from platforms.wechat_ilink import send_text
        ok = send_text(target, content)
        from platforms.base import SendResult
        return SendResult(success=ok, platform="wechat", message_id="", target=target)

    async def get_recent_messages(self, conversation_id: str, limit: int = 20):
        """Get recent messages from session manager (real chat history)."""
        try:
            from agent.session import SessionManager
            mgr = SessionManager("./data/sessions")
            msgs = mgr.get_history(conversation_id, limit=limit)
            return [{"role": m.get("role", ""), "content": str(m.get("content", ""))[:200], "timestamp": m.get("timestamp", "")} for m in msgs]
        except Exception:
            return []

    async def list_conversations(self, limit: int = 50):
        """List recent conversations from session manager."""
        try:
            from agent.session import SessionManager
            mgr = SessionManager("./data/sessions")
            sessions = mgr.list_sessions()
            return [{"id": s.get("session_id", ""), "title": s.get("title", ""), "message_count": s.get("message_count", 0), "model": s.get("model", "")} for s in sessions[:limit]]
        except Exception:
            return []

    async def send_file(self, target: str, file_path: str):
        from platforms.wechat_ilink import send_text
        ok = send_text(target, f"[文件] {file_path}")
        from platforms.base import SendResult
        return SendResult(success=ok, platform="wechat", message_id="", target=target)

    def get_tools(self): return []
    def on_message(self, cb): pass

# Global adapter cache (lazy init)
_adapters: dict[str, Any] = {}
_adapter_lock = asyncio.Lock()


async def _get_adapter(platform: str) -> Any:
    """Get or create platform adapter (lazy)."""
    if platform in _adapters:
        return _adapters[platform]

    async with _adapter_lock:
        if platform in _adapters:
            return _adapters[platform]

        if platform == "wechat":
            from platforms.wechat_ilink import get_status, send_text
            adapter = _ILinkAdapter()
            adapter.connect()
            _adapters[platform] = adapter

        elif platform == "feishu":
            from platforms.feishu import FeishuAdapter
            adapter = FeishuAdapter()
            await adapter.connect()
            _adapters[platform] = adapter

        elif platform == "qq":
            from platforms.qq import QQAdapter
            adapter = QQAdapter()
            await adapter.connect()
            _adapters[platform] = adapter

        elif platform == "telegram":
            from platforms.telegram import TelegramAdapter
            adapter = TelegramAdapter()
            await adapter.connect()
            _adapters[platform] = adapter

        else:
            from platforms.base import MockPlatformAdapter
            adapter = MockPlatformAdapter(platform=platform)
            await adapter.connect()
            _adapters[platform] = adapter

        return _adapters[platform]


# ═══════════════════════════════════════════════════════════════
# Generic IM Tools (8: cross-platform)
# ═══════════════════════════════════════════════════════════════

async def _im_send(platform: str, target: str, content: str, rich_content: dict | None = None) -> dict:
    """Send a message to any IM platform."""
    adapter = await _get_adapter(platform)
    result = await adapter.send_message(target, content, rich_content)
    return {
        "success": result.success,
        "message_id": result.message_id,
        "platform": platform,
        "target": target,
        "error": result.error if not result.success else "",
    }


async def _im_receive(platform: str, conversation_id: str, limit: int = 20) -> dict:
    """Get recent messages from a conversation."""
    adapter = await _get_adapter(platform)
    msgs = await adapter.get_recent_messages(conversation_id, limit)
    return {
        "platform": platform,
        "conversation_id": conversation_id,
        "messages": [
            {
                "message_id": m.message_id,
                "sender": m.sender_id,
                "sender_name": m.sender_name,
                "content": m.content[:500],
                "timestamp": m.timestamp,
                "type": m.message_type.value,
                "is_mention": m.is_mention,
            }
            for m in msgs
        ],
        "count": len(msgs),
    }


async def _im_search(platform: str, query: str, conversation_id: str = "") -> dict:
    """Search message history (limited support)."""
    return {"platform": platform, "query": query, "results": [], "note": "Real-time message search not supported; use memory_search for stored transcripts"}


async def _im_summarize(platform: str, conversation_ids: list[str] | None = None) -> dict:
    """Summarize unread messages."""
    adapter = await _get_adapter(platform)
    # For now, just list conversations as summary
    convos = await adapter.list_conversations(50)
    unread_total = sum(c.unread_count for c in convos)
    return {
        "platform": platform,
        "total_unread": unread_total,
        "conversations": [
            {"id": c.conversation_id, "name": c.name, "unread": c.unread_count, "type": c.conversation_type.value}
            for c in convos[:20]
        ],
    }


async def _im_react(platform: str, message_id: str, reaction: str) -> dict:
    """Add emoji reaction to a message."""
    adapter = await _get_adapter(platform)
    ok = await adapter.react(message_id, reaction)
    return {"status": "ok" if ok else "unsupported", "reaction": reaction, "note": "WeChat does not support native reactions" if not ok else ""}


async def _im_send_file(platform: str, target: str, file_path: str) -> dict:
    """Send a file via IM."""
    adapter = await _get_adapter(platform)
    import os
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}
    result = await adapter.send_file(target, file_path)
    return {"success": result.success, "message_id": result.message_id, "platform": platform, "error": result.error}


async def _im_list_conversations(platform: str, limit: int = 50) -> dict:
    """List recent conversations."""
    adapter = await _get_adapter(platform)
    convos = await adapter.list_conversations(limit)
    return {
        "platform": platform,
        "conversations": [
            {
                "conversation_id": c.conversation_id,
                "name": c.name,
                "type": c.conversation_type.value,
                "unread": c.unread_count,
                "member_count": c.member_count,
            }
            for c in convos
        ],
        "count": len(convos),
    }


async def _im_create_group(platform: str, name: str, member_ids: list[str]) -> dict:
    """Create a group chat."""
    adapter = await _get_adapter(platform)
    group_id = await adapter.create_group(name, member_ids)
    if group_id:
        return {"success": True, "group_id": group_id, "name": name, "member_count": len(member_ids)}
    return {"success": False, "error": f"Failed to create group on {platform}"}


# ═══════════════════════════════════════════════════════════════
# WeChat-Specific Tools (8: platform-native)
# ═══════════════════════════════════════════════════════════════

async def _wechat_qrcode() -> dict:
    """Get WeChat login QR code."""
    adapter = await _get_adapter("wechat")
    if not hasattr(adapter, 'get_qrcode'):
        return {"error": "QR code login not supported for this adapter"}
    return await adapter.get_qrcode()


async def _wechat_contacts() -> dict:
    """Get WeChat contact list."""
    adapter = await _get_adapter("wechat")
    if not hasattr(adapter, 'get_contacts'):
        return {"contacts": [], "error": "Not supported"}
    contacts = await adapter.get_contacts()
    return {"contacts": contacts, "count": len(contacts)}


async def _wechat_groups() -> dict:
    """Get WeChat group list."""
    adapter = await _get_adapter("wechat")
    if not hasattr(adapter, 'get_groups'):
        return {"groups": [], "error": "Not supported"}
    groups = await adapter.get_groups()
    return {"groups": groups, "count": len(groups)}


async def _wechat_group_members(chatroom_id: str) -> dict:
    """Get WeChat group member list."""
    adapter = await _get_adapter("wechat")
    if not hasattr(adapter, 'get_group_members'):
        return {"members": [], "error": "Not supported"}
    members = await adapter.get_group_members(chatroom_id)
    return {"chatroom_id": chatroom_id, "members": members, "count": len(members)}


async def _wechat_profile() -> dict:
    """Get own WeChat profile."""
    adapter = await _get_adapter("wechat")
    if not hasattr(adapter, 'get_profile'):
        return {"error": "Not supported"}
    return await adapter.get_profile()


async def _wechat_accept_friend(encrypt_username: str, ticket: str) -> dict:
    """Accept WeChat friend request."""
    adapter = await _get_adapter("wechat")
    if not hasattr(adapter, 'accept_friend'):
        return {"success": False, "error": "Not supported"}
    ok = await adapter.accept_friend(encrypt_username, ticket)
    return {"success": ok}


async def _wechat_set_remark(wxid: str, remark: str) -> dict:
    """Set remark for a WeChat contact."""
    adapter = await _get_adapter("wechat")
    if not hasattr(adapter, 'set_remark'):
        return {"success": False, "error": "Not supported"}
    ok = await adapter.set_remark(wxid, remark)
    return {"success": ok}


async def _wechat_create_group(name: str, member_ids: list[str]) -> dict:
    """Create a WeChat group chat."""
    adapter = await _get_adapter("wechat")
    group_id = await adapter.create_group(name, member_ids)
    if group_id:
        return {"success": True, "group_id": group_id, "name": name}
    return {"success": False, "error": "Failed to create group"}


# ═══════════════════════════════════════════════════════════════
# Tool Registration
# ═══════════════════════════════════════════════════════════════

def register_im_tools(registry: ToolRegistry) -> None:
    """Register all IM tools (generic + WeChat-specific).

    Total: 16 tools (8 generic + 8 WeChat)
    """
    generic_tools = [
        ("im_send", "Send a message to any IM platform (wechat/feishu/qq/telegram).",
         {"platform": "string", "target": "string", "content": "string"},
         ["platform", "target", "content"], _im_send),
        ("im_receive", "Get recent messages from a conversation.",
         {"platform": "string", "conversation_id": "string", "limit": "integer"},
         ["platform", "conversation_id"], _im_receive),
        ("im_search", "Search message history.",
         {"platform": "string", "query": "string", "conversation_id": "string"},
         ["platform", "query"], _im_search),
        ("im_summarize", "Summarize unread messages.",
         {"platform": "string", "conversation_ids": "array"},
         ["platform"], _im_summarize),
        ("im_react", "Add emoji reaction to a message.",
         {"platform": "string", "message_id": "string", "reaction": "string"},
         ["platform", "message_id", "reaction"], _im_react),
        ("im_send_file", "Send a file via IM platform.",
         {"platform": "string", "target": "string", "file_path": "string"},
         ["platform", "target", "file_path"], _im_send_file),
        ("im_list_conversations", "List recent conversations from a platform.",
         {"platform": "string", "limit": "integer"},
         ["platform"], _im_list_conversations),
        ("im_create_group", "Create a group chat on a platform.",
         {"platform": "string", "name": "string", "member_ids": "array"},
         ["platform", "name", "member_ids"], _im_create_group),
    ]

    for name, desc, props, required, handler in generic_tools:
        params = {"type": "object", "properties": {}, "required": required}
        for k, v in props.items():
            if v == "string":
                params["properties"][k] = {"type": "string"}
            elif v == "integer":
                params["properties"][k] = {"type": "integer", "default": 20}
            elif v == "array":
                params["properties"][k] = {"type": "array", "items": {"type": "string"}}
        registry.register(name=name, description=desc, parameters=params, handler=handler, category="im")

    wechat_tools = [
        ("wechat_qrcode", "Get WeChat login QR code for scanning.",
         {}, [], _wechat_qrcode),
        ("wechat_contacts", "List all WeChat contacts (nickname, remark, wxid).",
         {}, [], _wechat_contacts),
        ("wechat_groups", "List all WeChat group chats with member counts.",
         {}, [], _wechat_groups),
        ("wechat_group_members", "List members of a WeChat group chat.",
         {"chatroom_id": "string"}, ["chatroom_id"], _wechat_group_members),
        ("wechat_profile", "Get own WeChat profile (wxid, nickname, avatar).",
         {}, [], _wechat_profile),
        ("wechat_accept_friend", "Accept a pending WeChat friend request.",
         {"encrypt_username": "string", "ticket": "string"},
         ["encrypt_username", "ticket"], _wechat_accept_friend),
        ("wechat_set_remark", "Set a remark/alias for a WeChat contact.",
         {"wxid": "string", "remark": "string"},
         ["wxid", "remark"], _wechat_set_remark),
        ("wechat_create_group", "Create a new WeChat group chat.",
         {"name": "string", "member_ids": "array"},
         ["member_ids"], _wechat_create_group),
    ]

    for name, desc, props, required, handler in wechat_tools:
        params = {"type": "object", "properties": {}, "required": required}
        for k, v in props.items():
            if v == "string":
                params["properties"][k] = {"type": "string"}
            elif v == "integer":
                params["properties"][k] = {"type": "integer", "default": 20}
            elif v == "array":
                params["properties"][k] = {"type": "array", "items": {"type": "string"}}
        registry.register(name=name, description=desc, parameters=params, handler=handler, category="im")

    logger.info("Registered 16 IM tools (8 generic + 8 WeChat)")
