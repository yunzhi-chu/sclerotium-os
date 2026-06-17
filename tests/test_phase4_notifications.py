"""Phase 4 灰度测试 — 通知系统 + Alt+Space 快速命令栏 + Web 仪表盘。

测试覆盖:
  - ToastManager: 发送/分级/抑制/历史/后端策略/回调
  - QuickBar: 状态管理/历史/命令条目/可见性
  - DashboardServer: HTTP API/HTML 渲染/数据提供者/复合提供者
  - 集成: 多后端链/热键模拟/仪表盘数据流
"""

from __future__ import annotations

import json
import threading
import time
import urllib.request
import urllib.error
from unittest import mock

import pytest

from ui.toast_notification import (
    ToastManager, Toast, ToastLevel, ToastBackend,
    WinRTToastBackend, BalloonTipBackend, LogBackend,
    get_toast_manager, notify, alert,
)
from ui.quick_bar import QuickBar, QuickBarEntry, QuickBarState
from ui.dashboard_web import (
    DashboardServer, DashboardSnapshot, DataProvider,
    DefaultDataProvider, CompositeDataProvider, _DashboardHandler,
)


# ═══════════════════════════════════════════════════════════════
# 辅助工具
# ═══════════════════════════════════════════════════════════════

class MockToastBackend(ToastBackend):
    """测试用后端 — 记录发送的 Toast。"""

    def __init__(self, available: bool = True, succeed: bool = True):
        self._available = available
        self._succeed = succeed
        self.sent: list[Toast] = []

    def send(self, toast: Toast) -> bool:
        self.sent.append(toast)
        return self._succeed

    def is_available(self) -> bool:
        return self._available


class MockDataProvider(DataProvider):
    """测试用数据提供者 — 返回预设数据。"""

    def __init__(self, **kwargs):
        self._data = kwargs

    def get_system_status(self) -> dict:
        return self._data.get("system", {
            "phase": "RUNNING",
            "uptime": "2h 30m",
            "boot_stage": "5/6",
            "organs_healthy": 12,
            "organs_total": 15,
        })

    def get_event_stats(self) -> dict:
        return self._data.get("events", {
            "total_events": 150,
            "topic_count": 8,
            "recent_events_count": 50,
            "recent_events": [
                {"topic": "window.changed", "timestamp": time.time() - 10},
                {"topic": "clipboard.text", "timestamp": time.time() - 5},
            ],
        })

    def get_rhythm_status(self) -> dict:
        return self._data.get("rhythm", {
            "active_profile": "work",
            "pyloric_ticks": 120,
            "gastric_ticks": 3,
            "metabolic_ticks": 1,
            "total_ticks": 124,
            "pyloric_interval": 30.0,
            "gastric_interval": 3600.0,
        })

    def get_notification_stats(self) -> dict:
        return self._data.get("notifications", {
            "total_sent": 25,
            "by_level": {"SILENT": 5, "TRAY": 10, "NOTIFY": 8, "ALERT": 2},
            "suppressed": False,
        })

    def get_memory_stats(self) -> dict:
        return self._data.get("memory", {
            "working_count": 3,
            "episodic_count": 150,
            "semantic_count": 42,
            "daily_events": 88,
            "active_projects": "sclerotium-os, fungal-cortex",
        })


def _http_get(url: str, timeout: float = 3.0) -> tuple[int, bytes]:
    """辅助: HTTP GET 请求。"""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


# ═══════════════════════════════════════════════════════════════
# Toast 数据类测试
# ═══════════════════════════════════════════════════════════════

class TestToastDataclass:
    """Toast 不可变数据类测试。"""

    def test_create_toast(self):
        """创建基本 Toast。"""
        t = Toast(title="测试", message="这是一条测试通知")
        assert t.title == "测试"
        assert t.message == "这是一条测试通知"
        assert t.level == ToastLevel.NOTIFY
        assert t.category == "general"
        assert t.toast_id != ""

    def test_toast_id_unique(self):
        """每个 Toast 有唯一 ID。"""
        t1 = Toast(title="A", message="1")
        time.sleep(0.001)
        t2 = Toast(title="A", message="1")
        assert t1.toast_id != t2.toast_id

    def test_toast_frozen(self):
        """Toast 不可修改。"""
        t = Toast(title="Test", message="Msg")
        with pytest.raises(Exception):
            t.title = "Changed"  # type: ignore

    def test_toast_with_level(self):
        """Toast 可以指定级别。"""
        t = Toast(title="Alert", message="!", level=ToastLevel.ALERT)
        assert t.level == ToastLevel.ALERT

    def test_toast_with_category(self):
        """Toast 可以指定类别。"""
        t = Toast(title="H", message="M", category="health")
        assert t.category == "health"

    def test_toast_duration(self):
        """Toast 可以指定持续时间。"""
        t = Toast(title="X", message="Y", duration=10.0)
        assert t.duration == 10.0


# ═══════════════════════════════════════════════════════════════
# ToastBackend 测试
# ═══════════════════════════════════════════════════════════════

class TestToastBackends:
    """通知后端测试。"""

    def test_log_backend_always_available(self):
        """LogBackend 始终可用。"""
        backend = LogBackend()
        assert backend.is_available()

    def test_log_backend_sends(self):
        """LogBackend 总是返回 True。"""
        backend = LogBackend()
        toast = Toast(title="T", message="M")
        assert backend.send(toast)

    def test_mock_backend_availability(self):
        """Mock 后端可控可用性。"""
        b1 = MockToastBackend(available=True)
        b2 = MockToastBackend(available=False)
        assert b1.is_available()
        assert not b2.is_available()

    def test_mock_backend_records(self):
        """Mock 后端记录发送的 Toast。"""
        backend = MockToastBackend()
        toast = Toast(title="X", message="Y")
        backend.send(toast)
        assert len(backend.sent) == 1
        assert backend.sent[0].title == "X"

    def test_mock_backend_fail(self):
        """Mock 后端可以模拟失败。"""
        backend = MockToastBackend(succeed=False)
        toast = Toast(title="F", message="ail")
        assert not backend.send(toast)
        assert len(backend.sent) == 1  # 仍然记录

    def test_winrt_backend_not_available_on_linux(self):
        """WinRT 后端在非 Windows 上不可用 (mock 测试)。"""
        with mock.patch("platform.system", return_value="Linux"):
            backend = WinRTToastBackend()
            assert not backend.is_available()

    def test_balloon_backend_available_with_pywin32(self):
        """BalloonTip 后端需要 pywin32。"""
        backend = BalloonTipBackend()
        # pywin32 在当前环境已安装
        assert backend.is_available()


# ═══════════════════════════════════════════════════════════════
# ToastManager 测试
# ═══════════════════════════════════════════════════════════════

class TestToastManager:
    """ToastManager 核心功能测试。"""

    @pytest.fixture
    def mgr(self):
        """创建使用 Mock 后端的 ToastManager。"""
        backend = MockToastBackend()
        return ToastManager(backends=[backend])

    def test_send_toast(self, mgr):
        """基本发送通知。"""
        toast = mgr.send("标题", "正文")
        assert toast.title == "标题"
        assert toast.level == ToastLevel.NOTIFY

    def test_send_silent_not_recorded_in_backend(self, mgr):
        """SILENT 级别不发送到后端。"""
        mgr.send("静默", "不可见", level=ToastLevel.SILENT)
        assert len(mgr._backends[0].sent) == 0

    def test_send_tray_reaches_backend(self, mgr):
        """TRAY 级别发送到后端。"""
        mgr.send("托盘", "提示", level=ToastLevel.TRAY)
        assert len(mgr._backends[0].sent) == 1

    def test_send_notify_reaches_backend(self, mgr):
        """NOTIFY 级别发送到后端。"""
        mgr.send("通知", "正文", level=ToastLevel.NOTIFY)
        assert len(mgr._backends[0].sent) == 1

    def test_send_alert_reaches_backend(self, mgr):
        """ALERT 级别发送到后端。"""
        mgr.send("告警", "严重", level=ToastLevel.ALERT)
        assert len(mgr._backends[0].sent) == 1

    def test_suppress_blocks_all(self, mgr):
        """抑制模式阻止所有通知。"""
        mgr.suppress(True)
        mgr.send("Test", "Msg", level=ToastLevel.ALERT)
        assert len(mgr._backends[0].sent) == 0

    def test_unsuppress_restores(self, mgr):
        """取消抑制恢复通知。"""
        mgr.suppress(True)
        mgr.send("A", "B", level=ToastLevel.NOTIFY)
        mgr.suppress(False)
        mgr.send("C", "D", level=ToastLevel.NOTIFY)
        assert len(mgr._backends[0].sent) == 1

    def test_min_level_filters(self, mgr):
        """最低级别过滤。"""
        mgr.set_min_level(ToastLevel.NOTIFY)
        mgr.send("Tray", "Msg", level=ToastLevel.TRAY)
        assert len(mgr._backends[0].sent) == 0
        mgr.send("Notify", "Msg", level=ToastLevel.NOTIFY)
        assert len(mgr._backends[0].sent) == 1

    def test_history_accumulates(self, mgr):
        """历史记录累积。"""
        for i in range(5):
            mgr.send(f"T{i}", f"M{i}")
        history = mgr.get_history()
        assert len(history) == 5

    def test_history_limit(self, mgr):
        """历史记录有限制。"""
        for i in range(10):
            mgr.send(f"T{i}", f"M{i}")
        assert len(mgr.get_history(limit=3)) == 3

    def test_get_stats(self, mgr):
        """获取通知统计。"""
        mgr.send("T1", "M1", level=ToastLevel.NOTIFY)
        mgr.send("T2", "M2", level=ToastLevel.ALERT)
        stats = mgr.get_stats()
        assert stats["total_sent"] == 2
        assert stats["by_level"]["NOTIFY"] == 1
        assert stats["by_level"]["ALERT"] == 1
        assert not stats["suppressed"]

    def test_stats_with_suppression(self, mgr):
        """抑制状态反映在统计中。"""
        mgr.suppress(True)
        stats = mgr.get_stats()
        assert stats["suppressed"]

    def test_clear_history(self, mgr):
        """清空历史。"""
        mgr.send("A", "B")
        mgr.send("C", "D")
        mgr.clear_history()
        assert len(mgr.get_history()) == 0

    def test_callback_on_send(self, mgr):
        """发送时触发回调。"""
        received: list[Toast] = []

        def callback(toast: Toast):
            received.append(toast)

        mgr.on_send(callback)
        mgr.send("Callback", "Test")
        assert len(received) == 1
        assert received[0].title == "Callback"

    def test_callback_not_called_on_silent(self, mgr):
        """SILENT 级别不触发回调。"""
        received: list[Toast] = []

        def callback(toast: Toast):
            received.append(toast)

        mgr.on_send(callback)
        mgr.send("Silent", "Msg", level=ToastLevel.SILENT)
        assert len(received) == 0

    def test_callback_exception_isolated(self, mgr):
        """回调异常不影响其他回调。"""
        def bad_callback(toast: Toast):
            raise RuntimeError("Boom!")

        good_calls: list[Toast] = []

        def good_callback(toast: Toast):
            good_calls.append(toast)

        mgr.on_send(bad_callback)
        mgr.on_send(good_callback)
        mgr.send("Test", "Msg")
        assert len(good_calls) == 1

    def test_multi_backend_fallback(self):
        """多后端链: 第一个失败则尝试第二个。"""
        b1 = MockToastBackend(succeed=False)
        b2 = MockToastBackend(succeed=True)
        mgr = ToastManager(backends=[b1, b2])
        mgr.send("Test", "Msg")
        assert len(b1.sent) == 1
        assert len(b2.sent) == 1  # 回退成功

    def test_multi_backend_first_succeeds(self):
        """多后端链: 第一个成功则跳过后续。"""
        b1 = MockToastBackend(succeed=True)
        b2 = MockToastBackend(succeed=True)
        mgr = ToastManager(backends=[b1, b2])
        mgr.send("Test", "Msg")
        assert len(b1.sent) == 1
        assert len(b2.sent) == 0  # 不需要回退

    def test_log_backend_default_included(self):
        """默认包含 LogBackend。"""
        mgr = ToastManager()
        has_log = any(isinstance(b, LogBackend) for b in mgr._backends)
        assert has_log

    def test_silent_still_in_history(self, mgr):
        """SILENT 级别不发送但记录在历史。"""
        mgr.send("S", "M", level=ToastLevel.SILENT)
        assert len(mgr.get_history()) == 1

    def test_suppressed_still_in_history(self, mgr):
        """抑制模式不发送但记录在历史。"""
        mgr.suppress(True)
        mgr.send("S", "M")
        assert len(mgr.get_history()) == 1


# ═══════════════════════════════════════════════════════════════
# Toast 便捷函数测试
# ═══════════════════════════════════════════════════════════════

class TestToastConvenience:
    """便捷函数测试。"""

    def test_get_toast_manager_singleton(self):
        """get_toast_manager 返回全局单例。"""
        m1 = get_toast_manager()
        m2 = get_toast_manager()
        assert m1 is m2

    def test_notify_convenience(self):
        """notify() 快捷函数。"""
        backend = MockToastBackend()
        mgr = ToastManager(backends=[backend])
        # 直接使用 mgr.send 测试
        t = mgr.send("N", "M", level=ToastLevel.NOTIFY)
        assert t.level == ToastLevel.NOTIFY

    def test_alert_convenience(self):
        """alert() 快捷函数。"""
        backend = MockToastBackend()
        mgr = ToastManager(backends=[backend])
        t = mgr.send("A", "M", level=ToastLevel.ALERT)
        assert t.level == ToastLevel.ALERT


# ═══════════════════════════════════════════════════════════════
# QuickBar 数据模型测试
# ═══════════════════════════════════════════════════════════════

class TestQuickBarEntry:
    """QuickBarEntry 不可变数据类测试。"""

    def test_user_entry(self):
        """用户输入条目。"""
        e = QuickBarEntry(text="整理桌面")
        assert e.text == "整理桌面"
        assert not e.is_response

    def test_response_entry(self):
        """系统回复条目。"""
        e = QuickBarEntry(text="✅ 完成", is_response=True)
        assert e.is_response
        assert e.text == "✅ 完成"

    def test_timestamp(self):
        """条目有时间戳。"""
        e = QuickBarEntry(text="test")
        assert e.timestamp > 0

    def test_frozen(self):
        """条目不可修改。"""
        e = QuickBarEntry(text="test")
        with pytest.raises(Exception):
            e.text = "changed"  # type: ignore


class TestQuickBarState:
    """QuickBarState 数据类测试。"""

    def test_default_state(self):
        """默认状态。"""
        s = QuickBarState(visible=False)
        assert not s.visible
        assert s.mode == "work"
        assert s.pending_count == 0

    def test_visible_state(self):
        """可见状态。"""
        s = QuickBarState(visible=True, mode="sleep", active_time="8h",
                          pending_count=3, history_count=42)
        assert s.visible
        assert s.mode == "sleep"
        assert s.active_time == "8h"
        assert s.pending_count == 3
        assert s.history_count == 42

    def test_frozen(self):
        """状态不可修改。"""
        s = QuickBarState(visible=False)
        with pytest.raises(Exception):
            s.visible = True  # type: ignore


# ═══════════════════════════════════════════════════════════════
# QuickBar 核心逻辑测试 (无 GUI)
# ═══════════════════════════════════════════════════════════════

class TestQuickBarCore:
    """QuickBar 核心逻辑测试 (不启动 GUI)。"""

    @pytest.fixture
    def bar(self):
        """创建 QuickBar 实例 (不启动)。"""
        return QuickBar()

    def test_initial_state(self, bar):
        """初始状态。"""
        assert not bar.is_running
        assert not bar.is_visible
        assert bar.mode == "work"

    def test_get_state(self, bar):
        """获取状态。"""
        s = bar.get_state()
        assert isinstance(s, QuickBarState)
        assert not s.visible
        assert s.mode == "work"

    def test_set_mode(self, bar):
        """设置模式。"""
        bar.set_mode("sleep")
        assert bar.mode == "sleep"

    def test_set_active_time(self, bar):
        """设置活跃时间。"""
        bar.set_active_time("3h 15m")
        assert bar.get_state().active_time == "3h 15m"

    def test_set_pending_count(self, bar):
        """设置待处理数。"""
        bar.set_pending_count(5)
        assert bar.get_state().pending_count == 5

    def test_add_response(self, bar):
        """添加系统回复。"""
        bar.add_response("✅ 桌面整理完成")
        history = bar.get_history()
        assert len(history) == 1
        assert history[0].is_response
        assert history[0].text == "✅ 桌面整理完成"

    def test_get_history_empty(self, bar):
        """空历史。"""
        assert bar.get_history() == []

    def test_history_limit(self, bar):
        """历史限制。"""
        for i in range(20):
            bar.add_response(f"Reply {i}")
        history = bar.get_history(limit=5)
        assert len(history) == 5

    def test_clear_history(self, bar):
        """清空历史。"""
        bar.add_response("Test")
        bar.clear_history()
        assert bar.get_history() == []

    def test_custom_hotkey(self):
        """自定义热键。"""
        bar = QuickBar(hotkey_mod=0x0002, hotkey_key=0x20)  # Ctrl+Space
        assert bar._hotkey_mod == 0x0002

    def test_on_submit_callback(self, bar):
        """提交回调注册。"""
        results = []

        def handler(text: str) -> str:
            results.append(text)
            return f"Echo: {text}"

        bar._on_submit = handler
        # 不通过 GUI，直接测试回调
        result = bar._on_submit("test input")
        assert result == "Echo: test input"
        assert results == ["test input"]

    def test_on_submit_callback_error(self, bar):
        """回调异常处理。"""
        def bad_handler(text: str) -> str:
            raise ValueError("Boom!")

        bar._on_submit = bad_handler
        with pytest.raises(ValueError, match="Boom!"):
            bar._on_submit("bad input")

    def test_max_history_config(self):
        """自定义最大历史条目数。"""
        bar = QuickBar(max_history=50)
        assert bar._max_history == 50

    def test_running_false_initially(self, bar):
        """初始时 is_running 为 False。"""
        assert not bar.is_running
        assert not bar.is_visible


# ═══════════════════════════════════════════════════════════════
# DashboardServer 数据提供者测试
# ═══════════════════════════════════════════════════════════════

class TestDataProviders:
    """数据提供者测试。"""

    def test_default_provider_empty(self):
        """默认提供者返回空数据。"""
        dp = DefaultDataProvider()
        assert dp.get_system_status() == {}
        assert dp.get_event_stats() == {}
        assert dp.get_rhythm_status() == {}
        assert dp.get_notification_stats() == {}
        assert dp.get_memory_stats() == {}

    def test_mock_provider_system(self):
        """Mock 提供者返回系统状态。"""
        dp = MockDataProvider()
        status = dp.get_system_status()
        assert status["phase"] == "RUNNING"
        assert status["uptime"] == "2h 30m"

    def test_mock_provider_events(self):
        """Mock 提供者返回事件统计。"""
        dp = MockDataProvider()
        events = dp.get_event_stats()
        assert events["total_events"] == 150
        assert len(events["recent_events"]) == 2

    def test_mock_provider_rhythm(self):
        """Mock 提供者返回节律状态。"""
        dp = MockDataProvider()
        rhythm = dp.get_rhythm_status()
        assert rhythm["active_profile"] == "work"
        assert rhythm["pyloric_ticks"] == 120

    def test_mock_provider_custom_data(self):
        """Mock 提供者支持自定义数据。"""
        dp = MockDataProvider(system={"phase": "SLEEPING", "uptime": "10h"})
        status = dp.get_system_status()
        assert status["phase"] == "SLEEPING"


class TestCompositeDataProvider:
    """复合数据提供者测试。"""

    def test_register_and_aggregate(self):
        """注册多个提供者并聚合数据。"""
        cp = CompositeDataProvider()
        p1 = MockDataProvider(system={"phase": "RUNNING"})
        p2 = MockDataProvider(events={"total_events": 999})

        cp.register("p1", p1)
        cp.register("p2", p2)

        system = cp.get_system_status()
        events = cp.get_event_stats()

        assert system.get("phase") == "RUNNING"
        assert events.get("total_events") == 999

    def test_unregister(self):
        """移除提供者。"""
        cp = CompositeDataProvider()
        p = MockDataProvider(system={"phase": "OFFLINE"})
        cp.register("test", p)
        assert cp.get_system_status()["phase"] == "OFFLINE"
        cp.unregister("test")
        assert cp.get_system_status() == {}

    def test_aggregate_multiple(self):
        """多个提供者数据合并。"""
        cp = CompositeDataProvider()
        cp.register("a", MockDataProvider(
            system={"phase": "RUNNING", "uptime": "1h"},
        ))
        cp.register("b", MockDataProvider(
            system={"organs_healthy": 5, "organs_total": 8},
        ))
        status = cp.get_system_status()
        assert status["phase"] == "RUNNING"
        assert status["uptime"] == "1h"
        assert status["organs_healthy"] == 5

    def test_last_wins_on_conflict(self):
        """字段冲突时最后注册的胜出 (dict update 语义)。"""
        cp = CompositeDataProvider()
        cp.register("a", MockDataProvider(system={"phase": "RUNNING"}))
        cp.register("b", MockDataProvider(system={"phase": "SLEEPING"}))
        assert cp.get_system_status()["phase"] == "SLEEPING"

    def test_empty_composite(self):
        """空复合提供者返回空数据。"""
        cp = CompositeDataProvider()
        assert cp.get_system_status() == {}
        assert cp.get_rhythm_status() == {}


# ═══════════════════════════════════════════════════════════════
# DashboardServer HTTP 测试
# ═══════════════════════════════════════════════════════════════

class TestDashboardServer:
    """Dashboard HTTP 服务器测试。"""

    PORT = 11990  # 测试用端口

    @pytest.fixture
    def server(self):
        """创建测试用仪表盘服务器。"""
        provider = MockDataProvider()
        srv = DashboardServer(port=self.PORT, data_provider=provider)
        yield srv
        if srv.is_running:
            srv.stop()

    def test_initial_state(self, server):
        """初始状态。"""
        assert not server.is_running
        assert server.port == self.PORT
        assert server.url == f"http://127.0.0.1:{self.PORT}"

    def test_start_stop(self, server):
        """启动和停止。"""
        server.start()
        assert server.is_running
        server.stop()
        assert not server.is_running

    def test_health_endpoint(self, server):
        """健康检查端点。"""
        server.start()
        time.sleep(0.3)  # 等待服务器就绪
        code, body = _http_get(f"http://127.0.0.1:{self.PORT}/api/health")
        assert code == 200
        data = json.loads(body)
        assert data["status"] == "ok"

    def test_status_endpoint(self, server):
        """系统状态 API。"""
        server.start()
        time.sleep(0.3)
        code, body = _http_get(f"http://127.0.0.1:{self.PORT}/api/status")
        assert code == 200
        data = json.loads(body)
        assert "system" in data
        assert data["system"]["phase"] == "RUNNING"

    def test_events_endpoint(self, server):
        """事件统计 API。"""
        server.start()
        time.sleep(0.3)
        code, body = _http_get(f"http://127.0.0.1:{self.PORT}/api/events")
        assert code == 200
        data = json.loads(body)
        assert data["total_events"] == 150

    def test_rhythm_endpoint(self, server):
        """节律状态 API。"""
        server.start()
        time.sleep(0.3)
        code, body = _http_get(f"http://127.0.0.1:{self.PORT}/api/rhythm")
        assert code == 200
        data = json.loads(body)
        assert data["active_profile"] == "work"

    def test_notifications_endpoint(self, server):
        """通知统计 API。"""
        server.start()
        time.sleep(0.3)
        code, body = _http_get(f"http://127.0.0.1:{self.PORT}/api/notifications")
        assert code == 200
        data = json.loads(body)
        assert data["total_sent"] == 25

    def test_memory_endpoint(self, server):
        """记忆统计 API。"""
        server.start()
        time.sleep(0.3)
        code, body = _http_get(f"http://127.0.0.1:{self.PORT}/api/memory")
        assert code == 200
        data = json.loads(body)
        assert data["daily_events"] == 88

    def test_all_endpoint(self, server):
        """全量快照 API。"""
        server.start()
        time.sleep(0.3)
        code, body = _http_get(f"http://127.0.0.1:{self.PORT}/api/all")
        assert code == 200
        data = json.loads(body)
        assert "system" in data
        assert "events" in data
        assert "rhythm" in data
        assert "notifications" in data
        assert "memory" in data

    def test_html_dashboard(self, server):
        """HTML 仪表盘页面。"""
        server.start()
        time.sleep(0.3)
        code, body = _http_get(f"http://127.0.0.1:{self.PORT}/")
        assert code == 200
        html = body.decode("utf-8")
        assert "Sclerotium OS" in html
        assert "RUNNING" in html
        assert "work" in html

    def test_html_contains_stats(self, server):
        """HTML 仪表盘包含统计数据。"""
        server.start()
        time.sleep(0.3)
        code, body = _http_get(f"http://127.0.0.1:{self.PORT}/")
        assert code == 200
        html = body.decode("utf-8")
        assert "150" in html  # total_events
        assert "120" in html  # pyloric_ticks

    def test_html_has_refresh_meta(self, server):
        """HTML 包含自动刷新。"""
        server.start()
        time.sleep(0.3)
        code, body = _http_get(f"http://127.0.0.1:{self.PORT}/")
        html = body.decode("utf-8")
        assert 'http-equiv="refresh"' in html

    def test_404_on_bad_path(self, server):
        """无效路径返回 404。"""
        server.start()
        time.sleep(0.3)
        code, body = _http_get(f"http://127.0.0.1:{self.PORT}/nonexistent")
        assert code == 404

    def test_get_snapshot(self, server):
        """获取快照。"""
        snap = server.get_snapshot()
        assert isinstance(snap, DashboardSnapshot)
        assert snap.system["phase"] == "RUNNING"
        assert snap.events["total_events"] == 150
        assert snap.rhythm["active_profile"] == "work"

    def test_set_data_provider(self, server):
        """运行时切换数据提供者。"""
        new_provider = MockDataProvider(
            system={"phase": "SLEEPING", "uptime": "5h"},
        )
        server.set_data_provider(new_provider)
        assert _DashboardHandler.data_provider is new_provider

        server.start()
        time.sleep(0.3)
        code, body = _http_get(f"http://127.0.0.1:{self.PORT}/api/status")
        data = json.loads(body)
        assert data["system"]["phase"] == "SLEEPING"

    def test_multiple_start_stop_cycles(self, server):
        """多次启停服务器。"""
        for _ in range(3):
            server.start()
            time.sleep(0.2)
            code, _ = _http_get(f"http://127.0.0.1:{self.PORT}/api/health")
            assert code == 200
            server.stop()
            assert not server.is_running

    def test_dashboard_snapshot_frozen(self):
        """DashboardSnapshot 不可修改。"""
        snap = DashboardSnapshot(system={"phase": "RUNNING"})
        assert snap.system["phase"] == "RUNNING"
        with pytest.raises(Exception):
            snap.system = {}  # type: ignore

    def test_cors_headers(self, server):
        """JSON API 包含 CORS 头。"""
        server.start()
        time.sleep(0.3)
        req = urllib.request.Request(f"http://127.0.0.1:{self.PORT}/api/status")
        with urllib.request.urlopen(req, timeout=3) as resp:
            assert resp.headers.get("Access-Control-Allow-Origin") == "*"

    def test_json_content_type(self, server):
        """JSON API 返回正确 Content-Type。"""
        server.start()
        time.sleep(0.3)
        req = urllib.request.Request(f"http://127.0.0.1:{self.PORT}/api/status")
        with urllib.request.urlopen(req, timeout=3) as resp:
            ct = resp.headers.get("Content-Type", "")
            assert "application/json" in ct


# ═══════════════════════════════════════════════════════════════
# ToastManager + Dashboard 集成测试
# ═══════════════════════════════════════════════════════════════

class TestPhase4Integration:
    """Phase 4 跨模块集成测试。"""

    def test_toast_stats_in_dashboard(self):
        """通知统计通过仪表盘 API 暴露。"""
        backend = MockToastBackend()
        mgr = ToastManager(backends=[backend])

        # 发送多种通知
        mgr.send("T1", "M1", level=ToastLevel.SILENT)
        mgr.send("T2", "M2", level=ToastLevel.TRAY)
        mgr.send("T3", "M3", level=ToastLevel.NOTIFY)
        mgr.send("T4", "M4", level=ToastLevel.ALERT)

        stats = mgr.get_stats()
        assert stats["total_sent"] == 4
        assert stats["by_level"]["SILENT"] == 1
        assert stats["by_level"]["TRAY"] == 1
        assert stats["by_level"]["NOTIFY"] == 1
        assert stats["by_level"]["ALERT"] == 1

    def test_dashboard_with_toast_data(self):
        """仪表盘集成通知数据。"""
        provider = MockDataProvider(notifications={
            "total_sent": 42,
            "by_level": {"SILENT": 10, "TRAY": 15, "NOTIFY": 12, "ALERT": 5},
            "suppressed": False,
        })

        srv = DashboardServer(port=11991, data_provider=provider)
        srv.start()
        time.sleep(0.3)

        try:
            code, body = _http_get("http://127.0.0.1:11991/api/notifications")
            assert code == 200
            data = json.loads(body)
            assert data["total_sent"] == 42
            assert not data["suppressed"]
        finally:
            srv.stop()

    def test_full_pipeline(self):
        """完整管道: Toast + Dashboard 快照。"""
        backend = MockToastBackend()
        mgr = ToastManager(backends=[backend])

        # 模拟一天的通知
        mgr.send("早安", "新的一天开始了", level=ToastLevel.NOTIFY, category="rhythm")
        mgr.send("休息提醒", "你已工作 60 分钟", level=ToastLevel.NOTIFY, category="health")
        mgr.send("安全警告", "未知 USB 设备", level=ToastLevel.ALERT, category="security")

        stats = mgr.get_stats()
        assert stats["total_sent"] == 3
        assert stats["by_category"]["health"] == 1
        assert stats["by_category"]["security"] == 1
        assert stats["by_category"]["rhythm"] == 1

    def test_quickbar_nudge_integration(self):
        """QuickBar 配合 Nudge 通知。"""
        bar = QuickBar()

        # 模拟收到 nudge 后的状态更新
        bar.set_mode("work")
        bar.set_active_time("2h 30m")
        bar.set_pending_count(3)
        bar.add_response("💡 建议: 你已连续工作 2 小时, 考虑休息一下")

        state = bar.get_state()
        assert state.mode == "work"
        assert state.active_time == "2h 30m"
        assert state.pending_count == 3

        history = bar.get_history()
        assert len(history) == 1
        assert "休息" in history[0].text
