"""WeChat iLink Adapter — 腾讯官方个人微信 Bot API.

基于 wechat-link (腾讯 OpenClaw/iLink Bot API v2026).
零逆向 · 零Docker · 零封号风险.
一次扫码 · 持久登录 · 重启无需重新扫码.

架构: 微信消息 → iLink长轮询 → AgentLoop(LLM) → iLink发送 → 微信回复
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("sclerotium.wechat.ilink")

# Shared state
_client = None
_listening = False
_listen_thread = None
_msg_callback: Callable | None = None
_ilink_user_id: str = ""
_context_token: str = ""
_bot_token: str = ""
_stats = {"received": 0, "sent": 0, "errors": 0}
_qr_data: dict = {}
_last_sender: str = ""

# Thread-safe outgoing message queue — decouples scheduler threads from iLink
_outbox: queue.Queue = queue.Queue()
_outbox_thread: threading.Thread | None = None
_send_lock = threading.Lock()

# Persistent storage
_STATE_FILE = Path("./data/wechat_ilink_state.json")


def _save_state():
    """Save login state to disk so restart doesn't need QR scan."""
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "ilink_user_id": _ilink_user_id,
        "bot_token": _bot_token,
        "saved_at": time.time(),
    }
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    logger.info("WeChat iLink state saved: %s", _STATE_FILE)


def _load_state() -> dict | None:
    """Try to load saved login state."""
    if not _STATE_FILE.exists():
        return None
    try:
        with open(_STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        # Check if saved within 24 hours (bot_token validity window)
        age = time.time() - state.get("saved_at", 0)
        if age > 259200:  # 3 days
            logger.info("WeChat iLink state expired (%.1fh old)", age / 3600)
            return None
        logger.info("WeChat iLink state loaded (%.1fh old)", age / 3600)
        return state
    except Exception:
        return None


def get_status() -> dict:
    return {
        "connected": _client is not None and bool(_ilink_user_id),
        "user_id": _ilink_user_id,
        "listening": _listening,
        "persisted": _STATE_FILE.exists(),
        "stats": dict(_stats),
    }


def try_auto_login() -> bool:
    """Try to reconnect using saved credentials. Returns True if successful."""
    global _client, _ilink_user_id, _bot_token
    state = _load_state()
    if not state:
        return False

    import wechat_link
    _client = wechat_link.Client()
    _ilink_user_id = state.get("ilink_user_id", "")
    _bot_token = state.get("bot_token", "")
    if _bot_token:
        _client.bot_token = _bot_token

    # Verify the token is still valid by making a call
    try:
        _client.get_updates(cursor="")
        logger.info("WeChat iLink auto-reconnected as %s", _ilink_user_id)
        print(f"[菌核微信] 自动登录成功! (无需扫码)")
        return True
    except Exception as e:
        logger.info("WeChat iLink saved token expired: %s", e)
        _ilink_user_id = ""
        _bot_token = ""
        return False


def get_qr_code() -> dict:
    """Get login QR code. Only called if auto-login fails."""
    global _client, _qr_data
    import wechat_link
    _client = wechat_link.Client()
    qr = _client.get_bot_qrcode(bot_type=3)
    _qr_data = {"qrcode": qr.qrcode, "url": qr.qrcode_img_content, "ret": qr.ret}
    try:
        _client.print_qrcode_terminal(qr.qrcode_img_content)
    except Exception:
        pass
    print(f"[菌核微信] 或用浏览器: {qr.qrcode_img_content}")
    return _qr_data


def wait_for_login(timeout: float = 120) -> dict:
    """Poll until user scans QR code. Returns login info."""
    global _ilink_user_id, _bot_token, _client
    if not _client:
        return {"success": False, "error": "Call get_qr_code() first"}

    start = time.time()
    while time.time() - start < timeout:
        time.sleep(2)
        status = _client.get_qrcode_status(_qr_data["qrcode"])
        uid = getattr(status, 'ilink_user_id', None)
        token = getattr(status, 'bot_token', None)
        if uid:
            _ilink_user_id = uid
            _bot_token = token or ""
            if _bot_token:
                _client.bot_token = _bot_token
            _save_state()  # PERSIST for next restart
            logger.info("WeChat iLink logged in + state saved: %s", uid)
            print(f"\n[菌核微信] 登录成功并已保存! 下次启动无需扫码.")
            return {"success": True, "user_id": uid, "bot_token": bool(_bot_token)}

    return {"success": False, "error": "timeout"}


def send_text(to_user_id: str, text: str) -> bool:
    """Send text message to a WeChat user."""
    global _client, _context_token, _stats
    if not _client or not _ilink_user_id:
        return False

    try:
        token = _context_token or _bot_token
        _client.send_text(to_user_id=str(to_user_id), text=text, context_token=token)
        _stats["sent"] += 1
        return True
    except Exception as e:
        logger.error("iLink send failed: %s", e)
        _stats["errors"] += 1
        return False


def track_sender(sender: str) -> None:
    """Track the last WeChat sender for system-initiated notifications."""
    global _last_sender
    if sender:
        _last_sender = sender


def _start_outbox_drainer() -> None:
    """Start background thread that drains the outbox queue.

    All send_text calls go through this single thread, avoiding
    thread-safety issues with the iLink client's internal state.
    """
    global _outbox_thread
    if _outbox_thread is not None and _outbox_thread.is_alive():
        return

    def _drain():
        while _listening:
            try:
                to_user, text = _outbox.get(timeout=5)
                with _send_lock:
                    send_text(to_user, text)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Outbox drain error: {e}")

    _outbox_thread = threading.Thread(target=_drain, daemon=True)
    _outbox_thread.start()
    logger.info("Outbox drainer started")


def notify_system_result(message: str) -> bool:
    """Enqueue a system notification for delivery via the outbox drainer.

    Thread-safe — can be called from any thread (scheduler, integration, etc.).
    The outbox drainer serializes all send_text calls in a single thread,
    avoiding race conditions with iLink's internal polling state.
    """
    global _last_sender
    if not _last_sender:
        return False
    if not message:
        return False
    prefix = "[任务] "
    _outbox.put((_last_sender, prefix + message[:1200]))
    return True


def get_last_sender() -> str:
    """Get the ID of the last WeChat user who sent a message."""
    return _last_sender


def start_listening(callback: Callable[[dict], Any] | None = None, server_url: str = "http://localhost:18789"):
    """Start background listener for incoming WeChat messages."""
    global _listening, _listen_thread, _msg_callback
    if _listening:
        return

    _msg_callback = callback
    _listening = True
    _listen_thread = threading.Thread(
        target=_listen_loop, args=(server_url,), daemon=True
    )
    _listen_thread.start()
    _start_outbox_drainer()  # Thread-safe message delivery for scheduler/notifications
    logger.info("WeChat iLink listener started")


def stop_listening():
    global _listening
    _listening = False


def _listen_loop(server_url: str):
    global _client, _context_token, _stats
    cursor = ""

    while _listening:
        try:
            updates = _client.get_updates(cursor=cursor)
            cursor = updates.next_cursor or ""

            msgs = getattr(updates, 'messages', None) or []

            if not msgs:
                time.sleep(2)
                continue

            ctx = getattr(updates, 'context_token', None) or updates.__dict__.get('context_token', None)
            if ctx:
                _context_token = ctx

            for msg in msgs:
                sender = getattr(msg, 'from_user_id', None) or msg.__dict__.get('from_user_id', '')

                # Concatenate ALL text items (long messages split across items)
                text = ""
                item_list = getattr(msg, 'item_list', None) or msg.__dict__.get('item_list', [])
                if item_list:
                    for item in item_list:
                        text_item = item.get('text_item', {}) if isinstance(item, dict) else getattr(item, 'text_item', None)
                        if isinstance(text_item, dict):
                            text += text_item.get('text', '')
                        elif text_item:
                            text += getattr(text_item, 'text', '') or (text_item.__dict__.get('text', '') if hasattr(text_item, '__dict__') else '')

                ctx = getattr(msg, 'context_token', None) or msg.__dict__.get('context_token', '')
                if ctx:
                    _context_token = ctx

                if not sender or not text:
                    continue

                _stats["received"] += 1
                track_sender(sender)  # Track for system notifications
                print(f"\n[微信] {sender}: {text[:200]}")
                logger.info("WeChat msg from %s: %s", sender, text[:100])

                if _msg_callback:
                    try:
                        _msg_callback({"sender": sender, "text": text, "raw": msg})
                    except Exception as e:
                        logger.error("Callback error: %s", e)
                else:
                    reply = _call_llm(server_url, sender, text)
                    if reply:
                        send_text(sender, reply)
                        print(f"[微信] 已回复: {reply[:80]}")

        except Exception as e:
            logger.debug("iLink poll error: %s", e)
            time.sleep(3)


def _call_llm(server_url: str, sender: str, text: str) -> str:
    """Route message to Sclerotium LLM agent."""
    import urllib.request

    cmd = text.strip().lower()
    if cmd in ("/help", "help", "帮助"):
        return "[菌核] 命令: /status /genome /skills /tools /memory /help"
    if cmd in ("/status", "状态"):
        try:
            data = json.loads(urllib.request.urlopen(f"{server_url}/data/health", timeout=5).read())
            evo = data.get("evolution", {})
            cache = data.get("cache", {})
            mem = data.get("memory", {})
            lines = [
                f"[菌核] v{data.get('version', '5.2')} | 运行 {data.get('uptime_seconds', 0):.0f}s",
                f"进化: Gen {evo.get('generation', 0)} | 适应度 {evo.get('fitness', 0):.4f} | {evo.get('status', '?')}",
                f"缓存: {cache.get('status', '?')} | 记忆: {mem.get('total_memories', 0)}条",
                f"技能: {data.get('skills', {}).get('count', 0)} | 会话: {data.get('sessions', {}).get('sessions', 0)}",
                f"CPU: {data.get('resources', {}).get('cpu_percent', 0)}% | RAM: {data.get('resources', {}).get('memory_mb', 0)}MB",
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"[菌核] 服务器未响应: {e}"

    try:
        # Send session_id so server-side SessionManager handles persistence (OpenClaw pattern)
        full_text = text

        payload = json.dumps({
            "message": full_text,
            "history": [],  # Server manages history via SessionManager
            "sender": sender,  # session_id for persistence
        }).encode()
        req = urllib.request.Request(
            f"{server_url}/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        # 5小时超时: 支持长时间自主任务 (was 120s which caused spurious timeout)
        resp = urllib.request.urlopen(req, timeout=18000)
        data = json.loads(resp.read())
        reply = data.get("content", "")
        # 如果LLM没有返回文本内容, 从工具调用结果中提取摘要
        if not reply or not reply.strip():
            tool_results = data.get("tool_results", [])
            if tool_results:
                parts = [f"已执行 {len(tool_results)} 个工具:"]
                for tr in tool_results[-5:]:
                    parts.append(f"  • {tr.get('tool', '?')}: {str(tr.get('result', ''))[:120]}")
                reply = "\n".join(parts)
            else:
                turns = data.get("turns", 0)
                reply = f"处理完成 (共 {turns} 轮, 未产生文本输出)"
        return reply
    except Exception as e:
        return f"[菌核] 处理失败: {e}"
