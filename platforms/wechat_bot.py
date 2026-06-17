"""WeChat Bot — 微信→菌核大脑 完整闭环.

让用户通过微信控制 Sclerotium OS，像 OpenClaw 一样:
  用户在微信发消息 → Gewechat回调 → WeChatBot接收 → AgentLoop处理 → 回复微信

Usage:
    from platforms.wechat_bot import WeChatBot
    bot = WeChatBot(agent_loop=loop, memory=memory, genome=genome)
    await bot.start()  # 输出二维码 → 扫码登录
    # 然后用户在微信发任何消息，菌核都会自动回复
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import json
import time
from typing import Any, Callable

logger = logging.getLogger("sclerotium.wechat.bot")


class WeChatBot:
    """微信 AI 机器人 — 连接微信到菌核大脑.

    架构:
      微信消息 → Gewechat回调 → _on_message → AgentLoop.chat → 微信回复

    支持:
      - 私聊: 菌核直接回复
      - 群聊: 被@时回复 (支持 @菌核 @Sclerotium)
      - 命令: /status /fcpi /genome /skills /help 等
      - 多轮对话: 每个会话独立上下文 (最近10轮)
      - 主动消息: 定时任务/每日摘要可推送到微信
    """

    def __init__(
        self,
        api_url: str = "http://localhost:2531",
        token: str = "",
        callback_port: int = 2532,
        name: str = "菌核",
        mention_names: list[str] | None = None,
    ):
        self._api_url = api_url
        self._token = token
        self._callback_port = callback_port
        self._name = name
        self._mention_names = mention_names or ["菌核", "Sclerotium", "sclerotium", "@菌核"]

        # State
        self._client = None
        self._adapter = None
        self._running = False
        self._wxid: str = ""
        self._nickname: str = ""

        # Conversation context per user (最近N轮对话)
        self._contexts: dict[str, list[dict]] = {}
        self._max_context = 10

        # Stats
        self._msg_received: int = 0
        self._msg_sent: int = 0
        self._error_count: int = 0
        self._started_at: float = 0.0

    # ═══════════════════════════════════════════════════════════════
    # Lifecycle
    # ═══════════════════════════════════════════════════════════════

    async def start(self) -> dict:
        """启动微信机器人.

        流程:
          1. 初始化 Gewechat 客户端
          2. 获取登录二维码
          3. 等待用户扫码登录
          4. 登录成功 → 绑定消息回调 → 注册 EventBus
          5. 返回登录信息
        """
        from platforms.wechat_client import GewechatClient

        logger.info("WeChat Bot starting...")
        self._client = GewechatClient(base_url=self._api_url, token=self._token)

        # Step 1: Get QR code
        qr = await self._client.login_qrcode()
        if "error" in qr:
            return {"success": False, "error": qr.get("error", "Failed to get QR code"), **qr}

        qr_url = qr.get("qrcode_url", "")
        uuid = qr.get("uuid", "")
        logger.info("WeChat QR code: %s", qr_url)

        # Step 2: Wait for scan
        print("\n" + "=" * 50)
        print("  请用微信扫描以下二维码登录菌核:")
        print(f"  QR: {qr_url[:80]}...")
        print("=" * 50 + "\n")

        timeout = 120
        start = time.time()
        while time.time() - start < timeout:
            await asyncio.sleep(2)
            status = await self._client.check_login(uuid)
            st = status.get("status", "")
            if st == "logged_in":
                self._wxid = status.get("wxid", "")
                self._nickname = status.get("nickname", "")
                break
            elif st == "scanned":
                print("  二维码已扫描，请在手机上确认登录...")
            elif st == "confirmed":
                print("  登录确认中...")
            elif st == "error":
                return {"success": False, "error": status.get("msg", "Login failed")}

        if not self._wxid:
            return {"success": False, "error": f"Login timeout ({timeout}s)"}

        # Step 3: Bind message callback
        self._client.on_message(self._on_message)

        # Step 4: Start callback server (for real-time message receiving)
        self._client.start_callback_server(self._callback_port)

        # Step 5: Load initial data
        profile = await self._client.get_profile()
        contacts = await self._client.get_contacts()
        groups = await self._client.get_groups()

        self._running = True
        self._started_at = time.time()

        result = {
            "success": True,
            "wxid": self._wxid,
            "nickname": self._nickname,
            "contacts": len(contacts),
            "groups": len(groups),
            "profile": profile,
        }

        logger.info("WeChat Bot online as %s (%s), %d contacts, %d groups",
                     self._nickname, self._wxid, len(contacts), len(groups))

        print(f"\n  [OK] 菌核微信机器人已上线!")
        print(f"  昵称: {self._nickname}")
        print(f"  wxid: {self._wxid}")
        print(f"  联系人: {len(contacts)} 个")
        print(f"  群聊: {len(groups)} 个")
        print(f"  现在任何人可以在微信上给菌核发消息，菌核会自动回复。\n")

        return result

    async def stop(self) -> None:
        """Stop the WeChat bot."""
        self._running = False
        self._client = None
        logger.info("WeChat Bot stopped")

    # ═══════════════════════════════════════════════════════════════
    # Message Handling
    # ═══════════════════════════════════════════════════════════════

    async def _on_message(self, wx_msg) -> None:
        """Handle incoming WeChat message (Gewechat callback).

        This is the CORE LOOP: 收消息 → 思考 → 回复
        """
        from platforms.wechat_client import WxMessage

        self._msg_received += 1

        # Extract data
        content = wx_msg.content if hasattr(wx_msg, 'content') else str(wx_msg)
        from_user = wx_msg.from_user if hasattr(wx_msg, 'from_user') else ""
        is_group = wx_msg.is_group if hasattr(wx_msg, 'is_group') else False
        group_id = wx_msg.group_id if hasattr(wx_msg, 'group_id') else ""
        msg_id = wx_msg.msg_id if hasattr(wx_msg, 'msg_id') else ""

        # Ignore non-text messages
        msg_type = wx_msg.msg_type if hasattr(wx_msg, 'msg_type') else 1
        if msg_type not in (1,):  # Only handle text messages for now
            logger.debug("WeChat Bot: skipping non-text msg type=%d", msg_type)
            return

        # Determine reply target
        if is_group:
            # Group message: only respond when mentioned
            mentioned = any(name.lower() in content.lower() for name in self._mention_names)
            if not mentioned:
                return
            # Remove mention prefix for cleaner processing
            for name in self._mention_names:
                content = content.replace(f"@{name}", "").replace(name, "").strip()
            reply_target = group_id  # Reply to group
            conv_id = group_id
        else:
            reply_target = from_user
            conv_id = from_user

        logger.info("WeChat Bot: message from %s: %s", conv_id, content[:100])

        # Process message through the Agent
        try:
            reply = await self._process_message(conv_id, content)
        except Exception as e:
            logger.error("WeChat Bot: process error: %s", e)
            self._error_count += 1
            reply = f"[菌核] 处理出错了: {e}"

        # Send reply
        if reply and self._client:
            try:
                await self._client.send_text(reply_target, reply)
                self._msg_sent += 1
            except Exception as e:
                logger.error("WeChat Bot: reply error: %s", e)
                self._error_count += 1

    async def _process_message(self, conv_id: str, content: str) -> str:
        """Process a WeChat message through the Sclerotium Agent.

        Uses the LLM with tool access, just like the web chat.
        Falls back to built-in slash commands.
        """
        # Check for built-in slash commands first
        cmd_response = await self._handle_command(content)
        if cmd_response:
            return cmd_response

        # Route to LLM Agent
        try:
            return await self._chat_with_llm(conv_id, content)
        except Exception as e:
            logger.error("LLM chat failed: %s", e)
            return f"[菌核] LLM调用失败: {e}\n试试 /help 查看可用命令。"

    async def _handle_command(self, content: str) -> str | None:
        """Handle built-in slash commands. Returns None if not a command."""
        cmd = content.strip().lower()

        if cmd in ("/help", "帮助", "help"):
            return (
                "[菌核] 可用命令:\n"
                "/status - 系统状态\n"
                "/fcpi - FCPI进化指标\n"
                "/genome - 8D基因组\n"
                "/skills - 技能列表\n"
                "/tools - 工具统计\n"
                "/memory - 记忆统计\n"
                "/health - 健康检查\n"
                "/digest - 每日摘要\n"
                "/evolve - 执行一代进化\n"
                "/schedule - 定时任务列表\n"
                "/help - 显示此帮助\n\n"
                "也可以直接说话，菌核会用AI回复你。"
            )

        if cmd in ("/status", "状态"):
            return await self._get_status()

        if cmd in ("/health", "健康"):
            import urllib.request, json
            try:
                data = json.loads(urllib.request.urlopen("http://localhost:18789/health", timeout=5).read())
                return f"[菌核] 状态: {data.get('status')}, 工具数: {data.get('tool_count')}, 版本: {data.get('version')}"
            except Exception:
                return "[菌核] 健康检查失败 (服务器未运行?)"

        if cmd in ("/digest", "摘要", "日报"):
            try:
                from kernel.daily_digest import DailyDigest
                digest = DailyDigest()
                return f"[菌核] 每日摘要:\n{digest.generate()}"
            except Exception as e:
                return f"[菌核] 摘要生成失败: {e}"

        return None

    async def _chat_with_llm(self, conv_id: str, content: str) -> str:
        """Route message to LLM Agent (same as web /chat).

        Uses the same prompt_factory_v2 and LLMClient as the web interface.
        Maintains per-conversation context for multi-turn dialogue.
        """
        import os
        api_key = os.environ.get("SCLEROTIUM_API_KEY", os.environ.get("DEEPSEEK_API_KEY", ""))
        if not api_key:
            return "[菌核] 未配置 API Key。设置 SCLEROTIUM_API_KEY 环境变量。\n试试 /help 查看离线命令。"

        from agent.llm_client import LLMClient
        from kernel.prompt_factory_v2 import build_ultimate_prompt
        from mcp.server import SclerotiumMCPServer

        # Get or create MCP server for tool access
        server = _get_mcp_server()
        if not server:
            return "[菌核] MCP服务未初始化。"

        # Maintain conversation context
        if conv_id not in self._contexts:
            self._contexts[conv_id] = []

        history = list(self._contexts[conv_id][-self._max_context:])

        # Build system prompt
        system_prompt = "[微信对话] 你是Sclerotium OS，在微信上回应用户。像贾维斯一样简洁。回复用中文。"

        # Build messages
        msgs = [{"role": "system", "content": system_prompt}]
        msgs.extend(history)
        msgs.append({"role": "user", "content": content})

        # LLM with tools
        llm = LLMClient()
        llm.configure_tools(server.tools)

        try:
            response = await llm.chat(msgs)

            # Execute tool calls if any
            tool_results = []
            if response.has_tool_calls:
                for tc in response.tool_calls:
                    try:
                        tr = await llm.execute_tool(tc)
                        data_str = tr.get("content", str(tr))
                        try:
                            data = json.loads(data_str)
                        except (json.JSONDecodeError, TypeError):
                            data = data_str
                        tool_results.append({"tool": tc.name, "result": data})
                    except Exception as e:
                        tool_results.append({"tool": tc.name, "error": str(e)})

            final_content = response.content or "Done."

            # Update conversation context
            self._contexts[conv_id].append({"role": "user", "content": content})
            self._contexts[conv_id].append({"role": "assistant", "content": final_content})
            # Trim to max context
            if len(self._contexts[conv_id]) > self._max_context * 2:
                self._contexts[conv_id] = self._contexts[conv_id][-self._max_context * 2:]

            return final_content

        finally:
            await llm.close()

    async def _get_status(self) -> str:
        """Get system status summary for WeChat display."""
        try:
            import urllib.request, json
            data = json.loads(urllib.request.urlopen("http://localhost:18789/data/all", timeout=5).read())

            organs = data.get("organs", {})
            genome = data.get("genome", {})
            health = data.get("health", {})
            memory = data.get("memory", {})
            skills = data.get("skills", {})

            lines = [
                f"[菌核] Sclerotium OS v{health.get('version', '5.2')}",
                f"器官: {organs.get('total_organs', '?')} | 工具: {health.get('tool_count', '?')}",
                f"基因组: Gen {genome.get('generation', '?')} | 适应度: {genome.get('total_fitness', 0):.3f}",
                f"记忆: {memory.get('total', '?')} 条 | 技能: {skills.get('total', '?')} 个",
                f"运行时间: {health.get('uptime_seconds', 0)/3600:.1f}h",
                f"微信消息: 收{self._msg_received}/发{self._msg_sent}",
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"[菌核] 系统状态获取失败: {e}"

    # ═══════════════════════════════════════════════════════════════
    # Proactive Messaging
    # ═══════════════════════════════════════════════════════════════

    async def send_to_user(self, wxid: str, content: str) -> bool:
        """Send a proactive message to any WeChat user."""
        if not self._client or not self._running:
            return False
        try:
            msg_id = await self._client.send_text(wxid, content)
            if msg_id:
                self._msg_sent += 1
            return bool(msg_id)
        except Exception as e:
            logger.error("WeChat Bot: proactive send failed: %s", e)
            return False

    async def broadcast_to_all(self, content: str) -> dict[str, bool]:
        """Broadcast a message to all contacts (use sparingly!)."""
        contacts = await self._client.get_contacts() if self._client else []
        results = {}
        for c in contacts:
            results[c.wxid] = await self.send_to_user(c.wxid, content)
        return results

    # ═══════════════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════════════

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def stats(self) -> dict:
        return {
            "wxid": self._wxid,
            "nickname": self._nickname,
            "running": self._running,
            "messages_received": self._msg_received,
            "messages_sent": self._msg_sent,
            "errors": self._error_count,
            "conversations": len(self._contexts),
            "uptime": time.time() - self._started_at if self._started_at else 0,
        }


# ═══════════════════════════════════════════════════════════════
# Shared MCP Server Instance
# ═══════════════════════════════════════════════════════════════

_server = None

def _get_mcp_server():
    """Get or create shared MCP server for WeChat Bot LLM calls."""
    global _server
    if _server is None:
        try:
            from mcp.server import SclerotiumMCPServer
            _server = SclerotiumMCPServer()
            _server.register_all_tools()
        except Exception as e:
            logger.error("Failed to init MCP server for WeChat Bot: %s", e)
    return _server


# ═══════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════

async def run_wechat_bot(api_url: str = "http://localhost:2531"):
    """CLI entry point for WeChat Bot standalone mode.

    Usage:
        python -m platforms.wechat_bot
        python -m platforms.wechat_bot --api-url http://localhost:2531
    """
    print("[菌核] 微信机器人启动中...")
    print(f"[菌核] 连接 Gewechat: {api_url}")

    bot = WeChatBot(api_url=api_url)
    result = await bot.start()

    if not result.get("success"):
        print(f"\n[FAIL] 启动失败: {result.get('error')}")
        return 1

    print("[菌核] 运行中... 按 Ctrl+C 退出")
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("\n[菌核] 正在关闭...")
    finally:
        await bot.stop()

    return 0


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Sclerotium WeChat Bot")
    p.add_argument("--api-url", default="http://localhost:2531")
    args = p.parse_args()
    sys.exit(asyncio.run(run_wechat_bot(args.api_url)))
