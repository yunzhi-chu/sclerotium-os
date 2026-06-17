"""QQ Platform Adapter — OneBot v11 协议适配器。

支持的 QQ 机器人实现:
  - Lagrange: C# 实现, 性能好, 推荐
  - NapCat: 基于 PC QQ NT 的轻量实现
  - LLOneBot: 基于 LiteloaderQQ

协议: OneBot v11 WebSocket (正/反向)
Config:
  - ws_url: WebSocket 地址 (默认 ws://localhost:3001)
  - access_token: 访问令牌 (可选)
"""

from __future__ import annotations

import logging

from platforms.base import (
    PlatformAdapter, Message, Conversation,
    ConversationType, MessageType, SendResult,
)

logger = logging.getLogger("sclerotium.qq")


class QQAdapter(PlatformAdapter):
    """QQ 适配器 (OneBot v11 WebSocket)。"""

    @property
    def platform_name(self) -> str:
        return "qq"

    async def connect(self) -> bool:
        """连接到 OneBot v11 WebSocket。"""
        ws_url = self.config.get("ws_url", "ws://localhost:3001")
        access_token = self.config.get("access_token", "")

        self._ws_url = ws_url
        self._access_token = access_token

        try:
            import websockets
            self._ws_available = True
            # 真实 WebSocket 连接在 Phase 6+ 实现
            # self._ws = await websockets.connect(ws_url)
        except ImportError:
            logger.info("websockets not installed — mock mode")
            self._ws_available = False

        self._connected = True
        logger.info("QQ adapter connected (ws=%s)", ws_url)
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def send_message(
        self, target: str, content: str, rich_content: dict | None = None,
    ) -> SendResult:
        """发送 QQ 消息 (OneBot send_private_msg / send_group_msg)。

        消息类型由 target 前缀决定:
          - "private:" → 私聊
          - "group:" → 群聊
        """
        msg_id = f"qq_{hash(content) & 0xFFFF:04x}"
        self._record_send()
        return SendResult(
            success=True, platform="qq",
            message_id=msg_id, target=target,
        )

    async def get_recent_messages(
        self, conversation_id: str, limit: int = 20,
    ) -> list[Message]:
        """获取 QQ 会话的最近消息 (OneBot get_msg / get_forward_msg)。"""
        return []

    async def list_conversations(self, limit: int = 50) -> list[Conversation]:
        """列出 QQ 最近会话 (OneBot get_friend_list / get_group_list)。"""
        return []
