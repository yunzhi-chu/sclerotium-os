"""WeChat Bot (UIA) — 用菌核的 UIA 控制器实现微信双向 AI 控制.

零 Docker · 零 DLL 注入 · 任何微信版本通用.

用户 → 微信 → 菌核UIA监听 → AgentLoop(LLM) → 微信回复
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import threading
from typing import Any

logger = logging.getLogger("sclerotium.wechat.bot")


class WeChatBot:
    """微信 AI 机器人 — UIA 操控 + LLM 大脑.

    启动后:
      1. 用户在微信发消息给菌核
      2. 菌核通过 UIA 检测新消息
      3. Agent Loop 处理 (LLM + 工具)
      4. 回复通过微信发回
    """

    def __init__(
        self,
        monitor_chats: list[str] | None = None,
        poll_interval: float = 3.0,
    ):
        from platforms.wechat_uia import WeChatUIA
        self._wx = WeChatUIA()
        self._monitor_chats = monitor_chats or ["文件传输助手"]
        self._poll_interval = poll_interval
        self._running = False
        self._listen_thread = None
        self._contexts: dict[str, list[dict]] = {}
        self._max_context = 10
        self._msg_sent = 0
        self._msg_received = 0
        self._started_at = 0.0

    # ═══════════════════════════════════════════════════════
    # Lifecycle
    # ═══════════════════════════════════════════════════════

    def start(self) -> dict:
        """Start the WeChat bot."""
        if not self._wx.connect():
            return {"success": False, "error": "Cannot connect to WeChat window"}

        self._running = True
        self._started_at = time.time()
        self._listen_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._listen_thread.start()

        logger.info("WeChat Bot started, monitoring: %s", self._monitor_chats)
        print(f"\n[菌核微信] 已上线!")
        print(f"  监控会话: {', '.join(self._monitor_chats)}")
        print(f"  现在在微信上给菌核发消息，会自动回复.\n")
        return {"success": True}

    def stop(self):
        """Stop the bot."""
        self._running = False
        if self._listen_thread:
            self._listen_thread.join(timeout=5)
        self._wx.cleanup()

    # ═══════════════════════════════════════════════════════
    # Message Polling Loop
    # ═══════════════════════════════════════════════════════

    def _poll_loop(self):
        """Background loop: poll for new messages using clipboard read."""
        last_seen = {}  # chat_name -> last message text

        while self._running:
            try:
                for chat in self._monitor_chats:
                    current = self._wx.get_last_message(chat)
                    if not current or len(current) < 2:
                        continue

                    # Skip if same as last seen
                    if chat in last_seen and last_seen[chat] == current:
                        continue

                    # Skip our own replies (contain [菌核] prefix)
                    if current.startswith("[菌核]"):
                        last_seen[chat] = current
                        continue

                    last_seen[chat] = current
                    self._msg_received += 1
                    logger.info("WeChat msg from %s: %s", chat, current[:100])

                    # Process and reply
                    reply = self._process_message(chat, current)
                    if reply:
                        self._wx.send_text(chat, reply)
                        self._msg_sent += 1

            except Exception as e:
                logger.debug("Poll error: %s", e)

            time.sleep(self._poll_interval)

    # ═══════════════════════════════════════════════════════
    # Message Processing
    # ═══════════════════════════════════════════════════════

    def _process_message(self, chat: str, content: str) -> str:
        """Process a WeChat message and generate reply."""
        # Check built-in commands
        cmd = self._handle_command(content)
        if cmd:
            return cmd

        # Route to LLM
        try:
            return self._call_llm(chat, content)
        except Exception as e:
            logger.error("LLM failed: %s", e)
            return f"[菌核] 处理失败: {e}\n试试 /help 查看命令."

    def _handle_command(self, content: str) -> str | None:
        """Handle slash commands."""
        cmd = content.strip().lower()

        if cmd in ("/help", "帮助", "help"):
            return (
                "[菌核] 命令:\n"
                "/status - 系统状态\n"
                "/genome - 进化状态\n"
                "/skills - 技能列表\n"
                "/tools  - 工具统计\n"
                "/memory - 记忆统计\n"
                "/help   - 此帮助\n\n"
                "也可以直接说话，菌核用AI回复。"
            )

        if cmd in ("/status", "状态"):
            try:
                import urllib.request
                data = json.loads(urllib.request.urlopen(
                    "http://localhost:18789/data/health", timeout=5
                ).read())
                return f"[菌核] {data.get('status')} | 工具:{data.get('tool_count')} | v{data.get('version')}"
            except Exception as e:
                return f"[菌核] 服务器未运行: {e}"

        if cmd in ("/genome", "进化"):
            try:
                import urllib.request
                data = json.loads(urllib.request.urlopen(
                    "http://localhost:18789/data/genome", timeout=5
                ).read())
                return f"[菌核] Gen {data.get('generation')} | 适应度:{data.get('total_fitness', 0):.3f} | {data.get('source', '')}"
            except Exception:
                return "[菌核] 获取失败"

        if cmd in ("/skills", "技能"):
            try:
                import urllib.request
                data = json.loads(urllib.request.urlopen(
                    "http://localhost:18789/data/skills", timeout=5
                ).read())
                return f"[菌核] {data.get('total')} 个技能已加载"
            except Exception:
                return "[菌核] 获取失败"

        return None

    def _call_llm(self, chat: str, content: str) -> str:
        """Call LLM via Sclerotium web API."""
        import urllib.request

        # Maintain context per chat
        if chat not in self._contexts:
            self._contexts[chat] = []
        history = self._contexts[chat][-self._max_context:]

        payload = json.dumps({
            "message": content,
            "history": history,
        }).encode()

        req = urllib.request.Request(
            "http://localhost:18789/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=18000)
        data = json.loads(resp.read())

        reply = data.get("content", "")
        if not reply or not reply.strip() or reply == "Done.":
            tool_results = data.get("tool_results", [])
            if tool_results:
                parts = [f"已执行 {len(tool_results)} 个工具:"]
                for tr in tool_results[-5:]:
                    parts.append(f"  • {tr.get('tool', '?')}: {str(tr.get('result', ''))[:120]}")
                reply = "\n".join(parts)
            else:
                turns = data.get("turns", 0)
                reply = f"处理完成 (共 {turns} 轮)"

        # Update context
        self._contexts[chat].append({"role": "user", "content": content})
        self._contexts[chat].append({"role": "assistant", "content": reply})
        if len(self._contexts[chat]) > self._max_context * 2:
            self._contexts[chat] = self._contexts[chat][-self._max_context * 2:]

        return reply

    # ═══════════════════════════════════════════════════════
    # Proactive Send
    # ═══════════════════════════════════════════════════════

    def send_to(self, who: str, content: str) -> bool:
        """Send a proactive message."""
        return self._wx.send_text(who, content)

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def stats(self) -> dict:
        return {
            "running": self._running,
            "received": self._msg_received,
            "sent": self._msg_sent,
            "chats": len(self._contexts),
            "uptime": time.time() - self._started_at if self._started_at else 0,
        }


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("[菌核] 微信 UIA 机器人启动...")
    bot = WeChatBot(monitor_chats=["文件传输助手"])
    result = bot.start()
    if not result["success"]:
        print(f"[FAIL] {result['error']}")
        exit(1)
    try:
        while True:
            time.sleep(60)
            print(f"[菌核] 运行中... 收{bot._msg_received}/发{bot._msg_sent}")
    except KeyboardInterrupt:
        print("\n[菌核] 关闭...")
    finally:
        bot.stop()
