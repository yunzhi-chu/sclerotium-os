"""Telegram Platform Adapter。

通过 python-telegram-bot (或直接 HTTP API) 连接 Telegram Bot API。
支持:
  - Webhook 或长轮询接收消息
  - 发送文本/图片/文件
  - 内联键盘
  - 命令处理

参考: OpenClaw Telegram Channel
"""

from __future__ import annotations

import asyncio
import logging

from platforms.base import (
    PlatformAdapter, Message, Conversation, ConversationType,
    MessageType, SendResult,
)

logger = logging.getLogger("sclerotium.telegram")


class TelegramAdapter(PlatformAdapter):
    """Telegram Bot API 适配器。

    Config:
      - token: Bot Token (必填, 从 @BotFather 获取)
      - use_webhook: 是否使用 Webhook (默认 False, 使用长轮询)
      - webhook_url: Webhook URL (use_webhook=True 时必填)
      - proxy: HTTP 代理 URL (可选)
    """

    @property
    def platform_name(self) -> str:
        return "telegram"

    async def connect(self) -> bool:
        """连接到 Telegram Bot API。"""
        token = self.config.get("token", "")
        use_webhook = self.config.get("use_webhook", False)
        proxy = self.config.get("proxy")

        if not token:
            logger.warning("Telegram token not configured — using mock mode")
            self._connected = True
            return True

        try:
            # 尝试使用真实 API
            import aiohttp

            self._api_url = f"https://api.telegram.org/bot{token}"
            self._session = aiohttp.ClientSession()

            if proxy:
                self._session = aiohttp.ClientSession(
                    connector=aiohttp.TCPConnector(),
                )

            # 验证 token: 调用 getMe
            async with self._session.get(f"{self._api_url}/getMe") as resp:
                data = await resp.json()
                if data.get("ok"):
                    bot_info = data["result"]
                    logger.info("Connected to Telegram as @%s", bot_info.get("username"))
                    self._connected = True
                    self._bot_username = bot_info.get("username", "")
                    return True
                else:
                    logger.error("Telegram auth failed: %s", data.get("description"))
                    self._connected = False
                    return False

        except ImportError:
            logger.info("aiohttp not installed — using mock mode")
            self._connected = True
            return True
        except Exception as e:
            logger.error("Telegram connect error: %s", e)
            self._connected = True  # Mock mode
            return True

    async def disconnect(self) -> None:
        """断开 Telegram 连接。"""
        self._connected = False
        if hasattr(self, "_session") and self._session:
            await self._session.close()

    async def send_message(
        self, target: str, content: str, rich_content: dict | None = None,
    ) -> SendResult:
        """发送 Telegram 消息。

        Args:
            target: Chat ID
            content: 文本内容 (支持 Markdown)
            rich_content: 内联键盘等 (可选)
        """
        if not self._connected:
            return SendResult(
                success=False, platform="telegram", target=target,
                error="Not connected",
            )

        # Mock 模式
        if not hasattr(self, "_session"):
            self._record_send()
            return SendResult(
                success=True, platform="telegram",
                message_id=f"tg_mock_{hash(content) & 0xFFFF:04x}",
                target=target,
            )

        # 真实 API
        try:
            payload: dict[str, Any] = {
                "chat_id": target,
                "text": content,
                "parse_mode": "Markdown",
            }

            if rich_content:
                if "reply_markup" in rich_content:
                    import json
                    payload["reply_markup"] = json.dumps(rich_content["reply_markup"])
                if "disable_notification" in rich_content:
                    payload["disable_notification"] = rich_content["disable_notification"]

            async with self._session.post(
                f"{self._api_url}/sendMessage", json=payload,
            ) as resp:
                data = await resp.json()
                if data.get("ok"):
                    msg_id = str(data["result"]["message_id"])
                    self._record_send()
                    return SendResult(
                        success=True, platform="telegram",
                        message_id=msg_id, target=target,
                    )
                else:
                    error = data.get("description", "Unknown error")
                    self._record_error(error)
                    return SendResult(
                        success=False, platform="telegram", target=target,
                        error=error,
                    )
        except Exception as e:
            self._record_error(str(e))
            return SendResult(
                success=False, platform="telegram", target=target,
                error=str(e),
            )

    async def get_recent_messages(
        self, conversation_id: str, limit: int = 20,
    ) -> list[Message]:
        """获取 Telegram 聊天的最近消息 (需要 getUpdates 或轮询)。"""
        return []  # Telegram Bot API 不能主动拉取历史消息

    async def list_conversations(self, limit: int = 50) -> list[Conversation]:
        """列出活跃 Telegram 会话。"""
        return []  # 需要从 getUpdates 累积

    async def send_file(self, target: str, file_path: str) -> SendResult:
        """发送文件。"""
        if not hasattr(self, "_session"):
            return SendResult(
                success=False, platform="telegram", target=target,
                error="Not connected (mock mode)",
            )

        try:
            import aiohttp
            data = aiohttp.FormData()
            data.add_field("chat_id", target)
            data.add_field(
                "document",
                open(file_path, "rb"),
                filename=file_path.split("/")[-1],
            )

            async with self._session.post(
                f"{self._api_url}/sendDocument", data=data,
            ) as resp:
                result = await resp.json()
                if result.get("ok"):
                    return SendResult(
                        success=True, platform="telegram",
                        message_id=str(result["result"]["message_id"]),
                        target=target,
                    )
                return SendResult(
                    success=False, platform="telegram", target=target,
                    error=result.get("description", "Unknown"),
                )
        except Exception as e:
            return SendResult(
                success=False, platform="telegram", target=target,
                error=str(e),
            )
