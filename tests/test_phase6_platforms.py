"""Phase 6 灰度测试 — IM 平台接入 (章鱼触手)。

测试覆盖:
  - Message/Conversation/SendResult 不可变数据类
  - PlatformAdapter 基类 + MockPlatformAdapter
  - MessageRouter: 路由/去重/处理器链/EventBus集成/响应
  - PlatformManager: 注册/并发连接/发送/广播/健康检查/状态
  - Platform Adapters: WeChat/QQ/Feishu/Telegram 连接/发送
  - 集成: 多平台→路由器→消息去重→回调→EventBus 完整链路
"""

from __future__ import annotations

import asyncio
import time
from unittest import mock

import pytest

from platforms.base import (
    PlatformAdapter, MockPlatformAdapter,
    Message, Conversation, MessageType, ConversationType, SendResult,
)
from platforms.router import (
    MessageRouter, RoutedMessage, RouterStats,
)
from platforms.manager import (
    PlatformManager, PlatformStatus, ManagerState,
)


# ═══════════════════════════════════════════════════════════════
# 辅助工具
# ═══════════════════════════════════════════════════════════════

def _async_run(coro):
    """同步运行异步协程。"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return loop.run_until_complete(asyncio.ensure_future(coro))
    except RuntimeError:
        pass
    return asyncio.run(coro)


@pytest.fixture
def mock_adapter():
    """创建 Mock 适配器。"""
    return MockPlatformAdapter(platform="test_im")


# ═══════════════════════════════════════════════════════════════
# 数据类测试
# ═══════════════════════════════════════════════════════════════

class TestMessageData:
    """Message 数据类测试。"""

    def test_create_message(self):
        m = Message(platform="wechat", message_id="m1",
                    conversation_id="c1", sender_id="u1",
                    content="你好")
        assert m.platform == "wechat"
        assert m.content == "你好"
        assert m.message_type == MessageType.TEXT

    def test_is_command(self):
        m1 = Message(platform="test", message_id="1", conversation_id="c",
                     sender_id="u", content="/status")
        m2 = Message(platform="test", message_id="2", conversation_id="c",
                     sender_id="u", content="hello")
        assert m1.is_command
        assert not m2.is_command

    def test_defaults(self):
        m = Message(platform="t", message_id="m", conversation_id="c",
                    sender_id="s")
        assert m.sender_name == ""
        assert not m.is_mention

    def test_frozen(self):
        m = Message(platform="t", message_id="m", conversation_id="c",
                    sender_id="s")
        with pytest.raises(Exception):
            m.content = "changed"  # type: ignore

    def test_with_mention(self):
        m = Message(platform="t", message_id="m", conversation_id="c",
                    sender_id="s", is_mention=True)
        assert m.is_mention

    def test_message_type_enum(self):
        assert MessageType.TEXT.value == "text"
        assert MessageType.IMAGE.value == "image"


class TestConversationData:
    """Conversation 数据类测试。"""

    def test_create(self):
        c = Conversation(conversation_id="c1", platform="wechat", name="测试群")
        assert c.conversation_id == "c1"
        assert c.name == "测试群"
        assert c.conversation_type == ConversationType.PRIVATE

    def test_group_type(self):
        c = Conversation(conversation_id="g1", conversation_type=ConversationType.GROUP)
        assert c.conversation_type == ConversationType.GROUP

    def test_frozen(self):
        c = Conversation(conversation_id="c1")
        with pytest.raises(Exception):
            c.name = "changed"  # type: ignore


class TestSendResultData:
    """SendResult 数据类测试。"""

    def test_success(self):
        r = SendResult(success=True, platform="wechat",
                       message_id="m1", target="u1")
        assert r.success
        assert r.message_id == "m1"

    def test_failure(self):
        r = SendResult(success=False, platform="qq", target="u1",
                       error="Timeout")
        assert not r.success
        assert r.error == "Timeout"

    def test_frozen(self):
        r = SendResult(success=True, platform="t")
        with pytest.raises(Exception):
            r.success = False  # type: ignore


# ═══════════════════════════════════════════════════════════════
# MockPlatformAdapter 测试
# ═══════════════════════════════════════════════════════════════

class TestMockPlatformAdapter:
    """Mock 适配器测试。"""

    @pytest.fixture
    def mock(self):
        return MockPlatformAdapter(platform="test_im")

    def test_platform_name(self, mock):
        assert mock.platform_name == "test_im"

    def test_connect(self, mock):
        result = _async_run(mock.connect())
        assert result
        assert mock.is_connected

    def test_connect_fail(self, mock):
        mock.set_fail_connect(True)
        result = _async_run(mock.connect())
        assert not result

    def test_disconnect(self, mock):
        _async_run(mock.connect())
        _async_run(mock.disconnect())
        assert not mock.is_connected

    def test_send_message(self, mock):
        _async_run(mock.connect())
        result = _async_run(mock.send_message("u1", "Hello"))
        assert result.success
        assert result.platform == "test_im"
        assert result.message_id != ""

    def test_send_fail(self, mock):
        _async_run(mock.connect())
        mock.set_fail_send(True)
        result = _async_run(mock.send_message("u1", "Hello"))
        assert not result.success

    def test_inject_message_triggers_callback(self, mock):
        received: list[Message] = []

        def callback(msg: Message):
            received.append(msg)

        mock.on_message(callback)
        _async_run(mock.connect())

        msg = Message(platform="test_im", message_id="m1",
                      conversation_id="c1", sender_id="u1",
                      content="测试消息")
        mock.inject_message(msg)
        assert len(received) == 1
        assert received[0].content == "测试消息"

    def test_inject_messages_batch(self, mock):
        received: list[Message] = []

        def callback(msg: Message):
            received.append(msg)

        mock.on_message(callback)
        _async_run(mock.connect())

        msgs = [
            Message(platform="test_im", message_id=f"m{i}",
                    conversation_id="c1", sender_id="u1", content=f"Msg {i}")
            for i in range(5)
        ]
        mock.inject_messages(msgs)
        assert len(received) == 5

    def test_multiple_callbacks(self, mock):
        c1, c2 = [], []

        mock.on_message(lambda m: c1.append(m))
        mock.on_message(lambda m: c2.append(m))
        _async_run(mock.connect())

        msg = Message(platform="test_im", message_id="x",
                      conversation_id="c", sender_id="u", content="test")
        mock.inject_message(msg)
        assert len(c1) == 1
        assert len(c2) == 1

    def test_stats(self, mock):
        _async_run(mock.connect())
        _async_run(mock.send_message("u1", "Hello"))

        msg = Message(platform="test_im", message_id="in",
                      conversation_id="c", sender_id="u", content="in")
        mock.inject_message(msg)

        stats = mock.stats
        assert stats["messages_sent"] == 1
        assert stats["messages_received"] == 1
        assert stats["connected"]

    def test_get_recent_messages(self, mock):
        _async_run(mock.connect())
        _async_run(mock.send_message("c1", "Hello"))
        msgs = _async_run(mock.get_recent_messages("c1"))
        assert len(msgs) >= 1

    def test_conversations(self, mock):
        _async_run(mock.connect())
        mock.add_conversation(Conversation(
            conversation_id="c1", platform="test_im", name="Test Group",
            conversation_type=ConversationType.GROUP,
        ))
        convs = _async_run(mock.list_conversations())
        assert len(convs) == 1

    def test_callback_exception_isolated(self, mock):
        def bad(msg): raise RuntimeError("Boom!")
        good_calls = []
        def good(msg): good_calls.append(msg)

        mock.on_message(bad)
        mock.on_message(good)
        _async_run(mock.connect())

        msg = Message(platform="test_im", message_id="x",
                      conversation_id="c", sender_id="u", content="test")
        mock.inject_message(msg)
        assert len(good_calls) == 1  # 好的回调不受影响


# ═══════════════════════════════════════════════════════════════
# MessageRouter 测试
# ═══════════════════════════════════════════════════════════════

class TestRoutedMessage:
    """RoutedMessage 数据类测试。"""

    def test_create(self):
        msg = Message(platform="t", message_id="m", conversation_id="c",
                      sender_id="s")
        rm = RoutedMessage(message=msg, processed=True)
        assert rm.processed

    def test_frozen(self):
        msg = Message(platform="t", message_id="m", conversation_id="c",
                      sender_id="s")
        rm = RoutedMessage(message=msg)
        with pytest.raises(Exception):
            rm.processed = True  # type: ignore


class TestMessageRouter:
    """MessageRouter 核心测试。"""

    @pytest.fixture
    def router(self):
        return MessageRouter()

    @pytest.fixture
    def router_with_adapter(self):
        router = MessageRouter()
        mock_adapter = MockPlatformAdapter(platform="test_im")
        _async_run(mock_adapter.connect())
        router.attach_adapter(mock_adapter)
        return router, mock_adapter

    def test_attach_adapter(self, router):
        mock = MockPlatformAdapter(platform="test1")
        _async_run(mock.connect())
        router.attach_adapter(mock)
        assert "test1" in router.list_platforms()
        assert router.get_adapter("test1") is mock

    def test_detach_adapter(self, router):
        mock = MockPlatformAdapter(platform="test2")
        _async_run(mock.connect())
        router.attach_adapter(mock)
        router.detach_adapter("test2")
        assert "test2" not in router.list_platforms()

    def test_route_message(self, router_with_adapter):
        router, adapter = router_with_adapter
        msg = Message(platform="test_im", message_id="m1",
                      conversation_id="c1", sender_id="u1",
                      content="Hello")
        result = router.route(msg)
        assert result.processed

    def test_dedup(self, router_with_adapter):
        router, adapter = router_with_adapter
        msg = Message(platform="test_im", message_id="dup",
                      conversation_id="c1", sender_id="u1",
                      content="Hello")

        r1 = router.route(msg)
        r2 = router.route(msg)  # 重复
        assert r1.processed
        assert not r2.processed
        assert r2.error == "Duplicate"

    def test_handler_chain(self, router_with_adapter):
        router, adapter = router_with_adapter

        def handler1(msg: Message) -> str | None:
            if "status" in msg.content.lower():
                return "系统状态: 正常运行"
            return None

        def handler2(msg: Message) -> str | None:
            return "默认回复"

        router.add_handler(handler1)
        router.add_handler(handler2)

        msg = Message(platform="test_im", message_id="m_status",
                      conversation_id="c1", sender_id="u1",
                      content="帮我看看 status")
        result = router.route(msg)
        assert result.response == "系统状态: 正常运行"

    def test_publishes_to_event_bus(self):
        """发布消息到 EventBus。"""
        events = []

        class FakeEventBus:
            def publish(self, topic, data=None, source=""):
                events.append({"topic": topic, "data": data, "source": source})

        bus = FakeEventBus()
        router = MessageRouter(event_bus=bus)
        mock = MockPlatformAdapter(platform="test")
        _async_run(mock.connect())
        router.attach_adapter(mock)

        msg = Message(platform="test", message_id="evt1",
                      conversation_id="c1", sender_id="u1",
                      content="ping")
        router.route(msg)
        assert len(events) == 1
        assert events[0]["topic"] == "message.received"
        assert events[0]["data"]["content"] == "ping"

    def test_history(self, router_with_adapter):
        router, adapter = router_with_adapter
        for i in range(5):
            msg = Message(platform="test_im", message_id=f"m{i}",
                          conversation_id="c1", sender_id="u1",
                          content=f"Msg {i}")
            router.route(msg)

        history = router.get_history()
        assert len(history) == 5

    def test_history_limit(self, router_with_adapter):
        router, adapter = router_with_adapter
        for i in range(20):
            msg = Message(platform="test_im", message_id=f"m{i}",
                          conversation_id="c1", sender_id="u1",
                          content=f"Msg {i}")
            router.route(msg)
        assert len(router.get_history(limit=5)) == 5

    def test_stats(self, router_with_adapter):
        router, adapter = router_with_adapter
        for i in range(3):
            msg = Message(platform="test_im", message_id=f"s{i}",
                          conversation_id="c1", sender_id="u1",
                          content=f"Msg {i}")
            router.route(msg)

        stats = router.get_stats()
        assert stats.total_received == 3
        assert stats.total_processed == 3
        assert stats.by_platform["test_im"] == 3

    def test_clear(self, router_with_adapter):
        router, adapter = router_with_adapter
        msg = Message(platform="test_im", message_id="m1",
                      conversation_id="c1", sender_id="u1",
                      content="x")
        router.route(msg)
        router.clear()
        assert router.get_history() == []

    def test_handler_error(self, router_with_adapter):
        router, adapter = router_with_adapter

        def bad_handler(msg):
            raise RuntimeError("Handler failure")

        router.add_handler(bad_handler)

        msg = Message(platform="test_im", message_id="err1",
                      conversation_id="c1", sender_id="u1",
                      content="test")
        result = router.route(msg)
        assert result.processed  # 仍然标记为已处理
        assert "Handler failure" in result.error

    def test_list_platforms(self, router):
        mock1 = MockPlatformAdapter(platform="p1")
        mock2 = MockPlatformAdapter(platform="p2")
        _async_run(mock1.connect())
        _async_run(mock2.connect())
        router.attach_adapter(mock1)
        router.attach_adapter(mock2)

        platforms = router.list_platforms()
        assert sorted(platforms) == ["p1", "p2"]


# ═══════════════════════════════════════════════════════════════
# PlatformManager 测试
# ═══════════════════════════════════════════════════════════════

class TestPlatformStatus:
    """PlatformStatus 数据类测试。"""

    def test_create(self):
        s = PlatformStatus(platform="wechat", connected=True,
                           messages_received=10)
        assert s.platform == "wechat"
        assert s.messages_received == 10

    def test_frozen(self):
        s = PlatformStatus(platform="t", connected=True)
        with pytest.raises(Exception):
            s.connected = False  # type: ignore


class TestManagerState:
    """ManagerState 数据类测试。"""

    def test_create(self):
        s1 = PlatformStatus(platform="a", connected=True)
        s2 = PlatformStatus(platform="b", connected=False)
        ms = ManagerState(
            platforms=(s1, s2), total_platforms=2,
            connected_count=1, total_messages_received=100,
            total_messages_sent=50,
        )
        assert ms.total_platforms == 2
        assert ms.connected_count == 1

    def test_frozen(self):
        ms = ManagerState(platforms=(), total_platforms=0, connected_count=0,
                          total_messages_received=0, total_messages_sent=0)
        with pytest.raises(Exception):
            ms.total_platforms = 1  # type: ignore


class TestPlatformManager:
    """PlatformManager 核心测试。"""

    @pytest.fixture
    def mgr(self):
        return PlatformManager()

    def test_register(self, mgr):
        mock = MockPlatformAdapter(platform="p1")
        mgr.register(mock)
        assert mgr.platform_count == 1
        assert "p1" in mgr.list_platforms()

    def test_unregister(self, mgr):
        mock = MockPlatformAdapter(platform="p1")
        mgr.register(mock)
        assert mgr.unregister("p1")
        assert mgr.platform_count == 0

    def test_unregister_nonexistent(self, mgr):
        assert not mgr.unregister("nonexistent")

    def test_connect_all(self, mgr):
        p1 = MockPlatformAdapter(platform="p1")
        p2 = MockPlatformAdapter(platform="p2")
        mgr.register(p1)
        mgr.register(p2)

        results = _async_run(mgr.connect_all())
        assert results["p1"]
        assert results["p2"]
        assert mgr.is_running

    def test_connect_with_failure(self, mgr):
        p1 = MockPlatformAdapter(platform="good")
        p2 = MockPlatformAdapter(platform="bad")
        p2.set_fail_connect(True)
        mgr.register(p1)
        mgr.register(p2)

        results = _async_run(mgr.connect_all())
        assert results["good"]
        assert not results["bad"]

    def test_disconnect_all(self, mgr):
        p1 = MockPlatformAdapter(platform="p1")
        mgr.register(p1)
        _async_run(mgr.connect_all())

        _async_run(mgr.disconnect_all())
        assert not p1.is_connected
        assert not mgr.is_running

    def test_send(self, mgr):
        p1 = MockPlatformAdapter(platform="p1")
        mgr.register(p1)
        _async_run(mgr.connect_all())

        result = _async_run(mgr.send("p1", "u1", "Hello"))
        assert result.success

    def test_send_unregistered(self, mgr):
        result = _async_run(mgr.send("unknown", "u1", "Hello"))
        assert not result.success
        assert "not registered" in result.error

    def test_send_not_connected(self, mgr):
        p1 = MockPlatformAdapter(platform="p1")
        mgr.register(p1)
        # 不调用 connect_all
        result = _async_run(mgr.send("p1", "u1", "Hello"))
        assert not result.success
        assert "not connected" in result.error

    def test_broadcast(self, mgr):
        p1 = MockPlatformAdapter(platform="p1")
        p2 = MockPlatformAdapter(platform="p2")
        mgr.register(p1)
        mgr.register(p2)
        _async_run(mgr.connect_all())

        results = _async_run(mgr.broadcast("系统通知: 维护中"))
        assert len(results) == 2
        assert results["p1"].success
        assert results["p2"].success

    def test_health_check_all(self, mgr):
        p1 = MockPlatformAdapter(platform="p1")
        mgr.register(p1)
        _async_run(mgr.connect_all())

        results = _async_run(mgr.health_check_all())
        assert results["p1"]

    def test_get_state(self, mgr):
        p1 = MockPlatformAdapter(platform="p1")
        mgr.register(p1)
        _async_run(mgr.connect_all())

        state = mgr.get_state()
        assert state.total_platforms == 1
        assert state.connected_count == 1

    def test_get_adapter(self, mgr):
        p1 = MockPlatformAdapter(platform="p1")
        mgr.register(p1)
        assert mgr.get_adapter("p1") is p1
        assert mgr.get_adapter("unknown") is None


# ═══════════════════════════════════════════════════════════════
# 平台适配器测试 (WeChat/QQ/Feishu/Telegram)
# ═══════════════════════════════════════════════════════════════

class TestWeChatAdapter:
    """WeChat 适配器测试。"""

    def test_connect(self):
        from platforms.wechat import WeChatAdapter
        ad = WeChatAdapter()
        result = _async_run(ad.connect())
        assert result
        assert ad.is_connected

    def test_send_message(self):
        from platforms.wechat import WeChatAdapter
        ad = WeChatAdapter()
        _async_run(ad.connect())
        result = _async_run(ad.send_message("u1", "你好"))
        assert result.success
        assert result.platform == "wechat"

    def test_platform_name(self):
        from platforms.wechat import WeChatAdapter
        ad = WeChatAdapter()
        assert ad.platform_name == "wechat"


class TestQQAdapter:
    """QQ 适配器测试。"""

    def test_connect(self):
        from platforms.qq import QQAdapter
        ad = QQAdapter()
        result = _async_run(ad.connect())
        assert result

    def test_send_message(self):
        from platforms.qq import QQAdapter
        ad = QQAdapter()
        _async_run(ad.connect())
        result = _async_run(ad.send_message("private:u1", "你好"))
        assert result.success
        assert result.platform == "qq"

    def test_platform_name(self):
        from platforms.qq import QQAdapter
        ad = QQAdapter()
        assert ad.platform_name == "qq"


class TestFeishuAdapter:
    """飞书适配器测试。"""

    def test_connect_without_credentials(self):
        from platforms.feishu import FeishuAdapter
        ad = FeishuAdapter()
        result = _async_run(ad.connect())
        assert result  # Mock mode

    def test_send_message_mock(self):
        from platforms.feishu import FeishuAdapter
        ad = FeishuAdapter()
        _async_run(ad.connect())
        result = _async_run(ad.send_message("c1", "Hello"))
        assert result.success

    def test_platform_name(self):
        from platforms.feishu import FeishuAdapter
        ad = FeishuAdapter()
        assert ad.platform_name == "feishu"


class TestTelegramAdapter:
    """Telegram 适配器测试。"""

    def test_connect_without_token(self):
        from platforms.telegram import TelegramAdapter
        ad = TelegramAdapter()
        result = _async_run(ad.connect())
        assert result  # Mock mode

    def test_send_message_mock(self):
        from platforms.telegram import TelegramAdapter
        ad = TelegramAdapter()
        _async_run(ad.connect())
        result = _async_run(ad.send_message("12345", "Hello"))
        assert result.success

    def test_platform_name(self):
        from platforms.telegram import TelegramAdapter
        ad = TelegramAdapter()
        assert ad.platform_name == "telegram"


# ═══════════════════════════════════════════════════════════════
# 集成测试
# ═══════════════════════════════════════════════════════════════

class TestPhase6Integration:
    """Phase 6 跨模块集成测试。"""

    def test_full_message_flow(self):
        """完整消息流: 适配器→路由器→回调→EventBus→历史。"""
        # 1. 创建路由器
        router = MessageRouter()

        # 2. 创建并挂载适配器
        wechat = MockPlatformAdapter(platform="wechat")
        _async_run(wechat.connect())
        router.attach_adapter(wechat)

        # 3. 添加处理器
        def handler(msg: Message) -> str | None:
            if "状态" in msg.content:
                return "系统: 运行中, 活跃2h"
            return None

        router.add_handler(handler)

        # 4. 注入消息
        msg = Message(platform="wechat", message_id="wx001",
                      conversation_id="c_private", sender_id="user_me",
                      content="/status 帮我看看电脑状态")
        result = router.route(msg)

        # 5. 验证
        assert result.processed
        assert "运行中" in result.response

        # 6. 验证历史
        history = router.get_history()
        assert len(history) == 1

    def test_multi_platform_routing(self):
        """多平台消息路由。"""
        router = MessageRouter()

        platforms = ["wechat", "qq", "feishu"]
        for p in platforms:
            ad = MockPlatformAdapter(platform=p)
            _async_run(ad.connect())
            router.attach_adapter(ad)

        for i, p in enumerate(platforms):
            msg = Message(platform=p, message_id=f"{p}_{i}",
                          conversation_id="c1", sender_id="u1",
                          content=f"来自 {p} 的消息")
            router.route(msg)

        stats = router.get_stats()
        assert stats.total_received == 3
        assert stats.by_platform["wechat"] == 1
        assert stats.by_platform["qq"] == 1
        assert stats.by_platform["feishu"] == 1

    def test_manager_router_integration(self):
        """PlatformManager + MessageRouter 集成。"""
        mgr = PlatformManager()
        router = MessageRouter()

        # 注册平台
        p1 = MockPlatformAdapter(platform="wechat")
        mgr.register(p1)
        router.attach_adapter(p1)

        _async_run(mgr.connect_all())

        # 通过管理器发送
        result = _async_run(mgr.send("wechat", "u1", "测试"))
        assert result.success

        # 状态验证
        state = mgr.get_state()
        assert state.connected_count == 1
        assert state.total_messages_sent == 1

    def test_dedup_across_time(self):
        """跨时间段去重。"""
        router = MessageRouter()
        mock = MockPlatformAdapter(platform="test")
        _async_run(mock.connect())
        router.attach_adapter(mock)

        # 第一次
        msg = Message(platform="test", message_id="dup_001",
                      conversation_id="c1", sender_id="u1", content="A")
        r1 = router.route(msg)

        # 稍后重复
        msg2 = Message(platform="test", message_id="dup_001",
                       conversation_id="c1", sender_id="u1", content="A")
        r2 = router.route(msg2)

        assert r1.processed
        assert not r2.processed

    def test_multiple_injections_flow_correctly(self):
        """批量注入消息流正确。"""
        mock = MockPlatformAdapter(platform="test")
        router = MessageRouter()
        _async_run(mock.connect())
        router.attach_adapter(mock)

        received = []

        def handler(msg: Message) -> str | None:
            received.append(msg.content)
            return "ack"

        router.add_handler(handler)

        # 模拟微信收到5条消息
        for i in range(5):
            mock.inject_message(Message(
                platform="test", message_id=f"inj_{i}",
                conversation_id="c1", sender_id="u1",
                content=f"消息 #{i}",
            ))

        assert len(received) == 5
        assert router.get_stats().total_processed == 5
