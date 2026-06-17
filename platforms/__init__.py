"""Sclerotium OS — IM 平台适配器 (章鱼触手)。

每个适配器封装一个消息平台, 实现统一的 PlatformAdapter 接口:
  - 连接/断开管理
  - 消息收发 (文本/文件/表情)
  - 会话列表
  - 消息回调 (EventBus 集成)

已支持平台:
  - Feishu (飞书) — lark-oapi SDK
  - QQ — OneBot v11 WebSocket
  - WeChat (微信) — Gewechat/Wechaty
  - Telegram — Bot API

核心组件:
  - PlatformAdapter: 抽象基类
  - MockPlatformAdapter: 测试用 Mock
  - MessageRouter: 跨平台消息路由
  - PlatformManager: 多平台生命周期管理
"""

from platforms.base import (
    PlatformAdapter, MockPlatformAdapter,
    Message, Conversation, MessageType, ConversationType, SendResult,
)
from platforms.router import MessageRouter, RoutedMessage, RouterStats
from platforms.manager import PlatformManager, PlatformStatus, ManagerState

__all__ = [
    "PlatformAdapter", "MockPlatformAdapter",
    "Message", "Conversation", "MessageType", "ConversationType", "SendResult",
    "MessageRouter", "RoutedMessage", "RouterStats",
    "PlatformManager", "PlatformStatus", "ManagerState",
]
