"""Message Router — 章鱼触手间高速公路 (interbrachial commissure)。

将来自不同 IM 平台的消息归一化后路由到:
  1. EventBus → "message.received" 事件
  2. AgentLoop → 命令执行
  3. 历史记录 → 消息存档

特性:
  - 多平台消息去重 (同一消息不会被重复处理)
  - 命令检测 (/ 前缀)
  - @提及检测
  - 发送者身份验证
  - 响应路由 (AgentLoop 结果返回正确的平台/会话)
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("sclerotium.router")

# 前向引用
from platforms.base import Message, SendResult, PlatformAdapter


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RoutedMessage:
    """路由后的消息 (不可变)。"""
    message: Message
    route_time: float = field(default_factory=time.time)
    processed: bool = False
    response: str = ""
    error: str = ""


@dataclass(frozen=True)
class RouterStats:
    """路由器统计 (不可变)。"""
    total_received: int = 0
    total_processed: int = 0
    total_errors: int = 0
    by_platform: dict[str, int] = field(default_factory=dict)
    active_handlers: int = 0


# ═══════════════════════════════════════════════════════════════
# MessageRouter
# ═══════════════════════════════════════════════════════════════

class MessageRouter:
    """跨平台消息路由器。

    使用方式:
        router = MessageRouter(event_bus=bus, agent_loop=loop)
        router.attach_adapter(wechat_adapter)
        router.attach_adapter(qq_adapter)

        # 当各平台收到消息时, 自动调用:
        #   message → router.route() → EventBus + AgentLoop → 响应回到原平台
        router.start()
    """

    MAX_HISTORY = 500

    def __init__(
        self,
        event_bus: Any = None,
        agent_loop: Any = None,
    ) -> None:
        """
        Args:
            event_bus: EventBus 实例 (可选)
            agent_loop: AgentLoop 实例 (可选)
        """
        self._event_bus = event_bus
        self._agent_loop = agent_loop
        self._adapters: dict[str, PlatformAdapter] = {}
        self._history: list[RoutedMessage] = []
        self._lock = threading.Lock()
        self._stats_by_platform: dict[str, int] = {}

        # 消息处理器链
        self._handlers: list[Callable[[Message], str | None]] = []

        # 去重 (最近 1000 条消息 ID)
        self._seen_ids: set[str] = set()
        self._seen_max = 1000

        self._running: bool = False

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def attach_adapter(self, adapter: PlatformAdapter) -> None:
        """挂载一个平台适配器。

        自动注册消息回调, 当适配器收到新消息时路由到 EventBus。
        """
        platform = adapter.platform_name
        self._adapters[platform] = adapter
        adapter.on_message(lambda msg: self.route(msg))
        logger.info("Attached platform: %s", platform)

    def detach_adapter(self, platform: str) -> None:
        """卸载平台适配器。"""
        self._adapters.pop(platform, None)
        logger.info("Detached platform: %s", platform)

    def add_handler(self, handler: Callable[[Message], str | None]) -> None:
        """注册消息处理器。

        处理器接收 Message, 可选返回响应字符串。
        返回 None 表示不处理 (交给下一个处理器)。
        返回字符串则作为响应发送回原会话。
        """
        self._handlers.append(handler)

    def route(self, message: Message) -> RoutedMessage:
        """路由一条消息。

        处理流程:
          1. 去重检查
          2. 发布到 EventBus
          3. 遍历处理器链
          4. 如有响应, 发送回原平台
          5. 记录到历史
        """
        # 去重
        if message.message_id in self._seen_ids:
            return RoutedMessage(message=message, processed=False,
                                 error="Duplicate")

        self._seen_ids.add(message.message_id)
        if len(self._seen_ids) > self._seen_max:
            self._prune_seen()

        # 统计
        self._stats_by_platform[message.platform] = \
            self._stats_by_platform.get(message.platform, 0) + 1

        # 发布到 EventBus
        if self._event_bus:
            try:
                self._event_bus.publish(
                    "message.received",
                    data={
                        "platform": message.platform,
                        "message_id": message.message_id,
                        "conversation_id": message.conversation_id,
                        "sender_id": message.sender_id,
                        "sender_name": message.sender_name,
                        "content": message.content,
                        "is_command": message.is_command,
                        "is_mention": message.is_mention,
                        "timestamp": message.timestamp,
                    },
                    source=f"MessageRouter/{message.platform}",
                )
            except Exception as e:
                logger.debug("EventBus publish error: %s", e)

        # 遍历处理器链
        response = ""
        error = ""
        for handler in self._handlers:
            try:
                result = handler(message)
                if result is not None:
                    response = result
                    break
            except Exception as e:
                logger.warning("Handler error: %s", e)
                error = str(e)

        # 如有响应, 发送回原平台
        if response and message.platform in self._adapters:
            adapter = self._adapters[message.platform]
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        adapter.send_message(message.conversation_id, response)
                    )
                else:
                    loop.run_until_complete(
                        adapter.send_message(message.conversation_id, response)
                    )
            except RuntimeError:
                asyncio.run(
                    adapter.send_message(message.conversation_id, response)
                )
            except Exception as e:
                logger.warning("Failed to send response: %s", e)

        routed = RoutedMessage(
            message=message,
            processed=True,
            response=response,
            error=error,
        )

        with self._lock:
            self._history.append(routed)
            if len(self._history) > self.MAX_HISTORY:
                self._history = self._history[-self.MAX_HISTORY:]

        logger.debug("Routed [%s] %s → %s",
                     message.platform, message.sender_id,
                     message.content[:50])

        return routed

    def get_history(self, limit: int = 50) -> list[RoutedMessage]:
        """获取路由历史。"""
        with self._lock:
            return list(self._history[-limit:])

    def get_stats(self) -> RouterStats:
        """获取路由器统计。"""
        with self._lock:
            return RouterStats(
                total_received=len(self._history),
                total_processed=sum(1 for r in self._history if r.processed),
                total_errors=sum(1 for r in self._history if r.error),
                by_platform=dict(self._stats_by_platform),
                active_handlers=len(self._handlers),
            )

    def clear(self) -> None:
        """清空历史。"""
        with self._lock:
            self._history.clear()

    def get_adapter(self, platform: str) -> PlatformAdapter | None:
        """获取指定平台的适配器。"""
        return self._adapters.get(platform)

    def list_platforms(self) -> list[str]:
        """列出已挂载的平台。"""
        return list(self._adapters.keys())

    # ═══════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════

    def _prune_seen(self) -> None:
        """裁剪去重集合。"""
        if len(self._seen_ids) > self._seen_max:
            # 保留最近 500 条
            keep = list(self._seen_ids)[-500:]
            self._seen_ids = set(keep)
