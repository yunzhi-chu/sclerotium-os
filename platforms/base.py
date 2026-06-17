"""Platform Adapter base — 章鱼触手抽象接口。

每个 IM 平台 (飞书/QQ/微信/Telegram) 实现此接口，
触手可独立收发消息，不依赖中央大脑。

章鱼联邦神经模型:
  - 每个触手有本地智能 (消息归一化、格式转换、重连)
  - 触手间可通过 EventBus 直连 (interbrachial commissure)
  - 中央 (MessageRouter) 只做战略路由，不介入每次交互

使用方式:
    adapter = WeChatAdapter(config={"api_url": "..."})
    await adapter.connect()
    msg_id = await adapter.send_message("user123", "Hello!")
    messages = await adapter.get_recent_messages("conv_456")
    await adapter.disconnect()
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("sclerotium.platforms")


# ═══════════════════════════════════════════════════════════════
# 数据类 (不可变)
# ═══════════════════════════════════════════════════════════════

class MessageType(Enum):
    """消息类型。"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    RICH = "rich"       # 富文本/卡片
    EVENT = "event"     # 系统事件 (加入群组等)
    UNKNOWN = "unknown"


class ConversationType(Enum):
    """会话类型。"""
    PRIVATE = "private"
    GROUP = "group"
    CHANNEL = "channel"


@dataclass(frozen=True)
class Message:
    """跨平台归一化消息 (不可变)。

    每个平台的原始消息被转化为统一格式，
    下游 (AgentLoop/EventBus) 不需要关心消息来源。
    """
    platform: str               # "wechat"/"qq"/"feishu"/"telegram"
    message_id: str
    conversation_id: str
    sender_id: str
    sender_name: str = ""
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    message_type: MessageType = MessageType.TEXT
    is_mention: bool = False    # 是否 @了机器人
    reply_to: str = ""          # 回复的消息 ID
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_command(self) -> bool:
        """是否为命令消息 (以 / 开头)。"""
        return self.content.strip().startswith("/")


@dataclass(frozen=True)
class Conversation:
    """跨平台归一化会话 (不可变)。"""
    conversation_id: str
    platform: str = ""
    name: str = ""
    conversation_type: ConversationType = ConversationType.PRIVATE
    unread_count: int = 0
    last_message: str = ""
    member_count: int = 0
    members: tuple[str, ...] = ()
    updated_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class SendResult:
    """消息发送结果 (不可变)。"""
    success: bool
    platform: str = ""
    message_id: str = ""
    target: str = ""
    error: str = ""
    sent_at: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# PlatformAdapter 抽象基类
# ═══════════════════════════════════════════════════════════════

class PlatformAdapter(ABC):
    """IM 平台适配器抽象基类。

    每个触手适配器的生命周期:
      connect → [send/receive/poll] → disconnect

    子类需要实现:
      - platform_name: 平台唯一标识
      - connect(): 建立连接
      - disconnect(): 断开连接
      - send_message(): 发送消息
      - get_recent_messages(): 获取最近消息
      - list_conversations(): 列出会话
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._connected = False
        self._message_callbacks: list[Callable[[Message], Any]] = []
        self._lock = threading.Lock()
        self._message_count: int = 0
        self._send_count: int = 0
        self._error_count: int = 0
        self._last_error: str = ""

    # ═══════════════════════════════════════════════════
    # 抽象方法
    # ═══════════════════════════════════════════════════

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台唯一标识 (如 "wechat", "feishu")。"""
        ...

    @abstractmethod
    async def connect(self) -> bool:
        """建立与平台的连接。返回是否成功。"""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接。"""
        ...

    @abstractmethod
    async def send_message(
        self, target: str, content: str, rich_content: dict | None = None,
    ) -> SendResult:
        """发送消息。

        Args:
            target: 目标 (用户ID/群ID)
            content: 文本内容
            rich_content: 富文本/卡片内容 (可选)

        Returns:
            SendResult
        """
        ...

    @abstractmethod
    async def get_recent_messages(
        self, conversation_id: str, limit: int = 20,
    ) -> list[Message]:
        """获取会话的最近消息。"""
        ...

    @abstractmethod
    async def list_conversations(self, limit: int = 50) -> list[Conversation]:
        """列出最近会话。"""
        ...

    # ═══════════════════════════════════════════════════════
    # 可选方法 (子类可覆盖)
    # ═══════════════════════════════════════════════════════

    async def send_file(self, target: str, file_path: str) -> SendResult:
        """发送文件。"""
        return SendResult(
            success=False,
            platform=self.platform_name,
            target=target,
            error=f"{self.platform_name} 不支持文件发送",
        )

    async def react(self, message_id: str, reaction: str) -> bool:
        """对消息做出反应 (emoji)。"""
        return False

    async def create_group(self, name: str, member_ids: list[str]) -> str:
        """创建群组。返回群 ID。"""
        return ""

    async def health_check(self) -> bool:
        """健康检查 (连接是否存活)。"""
        return self._connected

    def get_tools(self) -> list[dict[str, Any]]:
        """Return MCP tool definitions contributed by this platform adapter (Gap 12).

        Each platform can expose its own tools (e.g., wechat_send, telegram_poll).
        These are aggregated by the platform router and registered with MCP.
        """
        return []

    # ═══════════════════════════════════════════════════════
    # 消息回调
    # ═══════════════════════════════════════════════════════

    def on_message(self, callback: Callable[[Message], Any]) -> None:
        """注册消息回调 (当收到新消息时触发)。

        每个触手可注册多个回调, 用于:
          - EventBus 发布 "message.received"
          - MessageRouter 路由到 AgentLoop
          - 日志/监控
        """
        with self._lock:
            self._message_callbacks.append(callback)

    def _notify_message(self, message: Message) -> None:
        """通知所有消息回调 (子类在收到消息时调用)。"""
        self._message_count += 1
        for cb in self._message_callbacks:
            try:
                result = cb(message)
                # 支持同步和异步回调
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as e:
                logger.debug("Message callback error on %s: %s",
                             self.platform_name, e)

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def stats(self) -> dict[str, Any]:
        """获取适配器统计。"""
        return {
            "platform": self.platform_name,
            "connected": self._connected,
            "messages_received": self._message_count,
            "messages_sent": self._send_count,
            "errors": self._error_count,
            "last_error": self._last_error,
            "callbacks": len(self._message_callbacks),
        }

    def _record_send(self) -> None:
        self._send_count += 1

    def _record_error(self, error: str) -> None:
        self._error_count += 1
        self._last_error = error


# ═══════════════════════════════════════════════════════════════
# MockPlatformAdapter — 测试和开发用
# ═══════════════════════════════════════════════════════════════

class MockPlatformAdapter(PlatformAdapter):
    """Mock 平台适配器 — 无需真实 API 密钥即可测试。

    支持:
      - 可编程的消息序列 (预设回复)
      - 消息历史模拟
      - 延迟/错误注入
      - 连接状态控制

    使用方式:
        mock = MockPlatformAdapter(platform="test_im")
        await mock.connect()
        mock.inject_message(Message(
            platform="test_im", message_id="1",
            conversation_id="c1", sender_id="u1",
            content="帮我看看电脑",
        ))
        # 消息将通过回调传递到 EventBus/AgentLoop
    """

    def __init__(
        self,
        platform: str = "mock",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(config)
        self._platform = platform
        self._messages: list[Message] = []       # 所有消息
        self._conversations: list[Conversation] = []
        self._send_history: list[SendResult] = []
        self._injected: list[Message] = []       # 待投递的消息队列
        self._should_fail_connect: bool = False
        self._should_fail_send: bool = False
        self._send_delay: float = 0.0

    # ═══════════════════════════════════════════════════
    # PlatformAdapter 实现
    # ═══════════════════════════════════════════════════

    @property
    def platform_name(self) -> str:
        return self._platform

    async def connect(self) -> bool:
        if self._should_fail_connect:
            self._connected = False
            return False
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def send_message(
        self, target: str, content: str, rich_content: dict | None = None,
    ) -> SendResult:
        if self._should_fail_send:
            result = SendResult(
                success=False, platform=self._platform, target=target,
                error="Mock send failure",
            )
            self._send_history.append(result)
            self._record_error("Mock send failure")
            return result

        if self._send_delay > 0:
            await asyncio.sleep(self._send_delay)

        msg_id = f"mock_{self._platform}_{len(self._send_history):04x}"
        result = SendResult(
            success=True, platform=self._platform,
            message_id=msg_id, target=target,
        )
        self._send_history.append(result)
        self._record_send()

        # 同时存入消息历史
        self._messages.append(Message(
            platform=self._platform,
            message_id=msg_id,
            conversation_id=target,
            sender_id="self",
            content=content,
            message_type=MessageType.TEXT,
        ))
        return result

    async def get_recent_messages(
        self, conversation_id: str, limit: int = 20,
    ) -> list[Message]:
        msgs = [m for m in self._messages
                if m.conversation_id == conversation_id]
        return msgs[-limit:]

    async def list_conversations(self, limit: int = 50) -> list[Conversation]:
        return self._conversations[-limit:]

    # ═══════════════════════════════════════════════════════
    # 测试辅助方法
    # ═══════════════════════════════════════════════════════

    def inject_message(self, message: Message) -> None:
        """注入一条模拟消息 (触发回调)。"""
        self._messages.append(message)
        self._notify_message(message)

    def inject_messages(self, messages: list[Message]) -> None:
        """批量注入消息。"""
        for msg in messages:
            self.inject_message(msg)

    def add_conversation(self, conversation: Conversation) -> None:
        """添加模拟会话。"""
        self._conversations.append(conversation)

    def set_fail_connect(self, fail: bool = True) -> None:
        """设置连接是否失败。"""
        self._should_fail_connect = fail

    def set_fail_send(self, fail: bool = True) -> None:
        """设置发送是否失败。"""
        self._should_fail_send = fail

    def set_send_delay(self, delay: float) -> None:
        """设置发送延迟。"""
        self._send_delay = delay

    def get_send_history(self) -> list[SendResult]:
        """获取发送历史。"""
        return list(self._send_history)
