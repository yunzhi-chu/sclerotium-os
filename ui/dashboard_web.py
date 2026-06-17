"""Dashboard Web Server — 生命体的"内脏"可视化仪表盘。

轻量级 HTTP 服务器, 运行在 localhost:1990, 展示:
  - 系统生命周期状态
  - 事件总线统计
  - 节律引擎状态
  - 通知历史
  - 今日摘要
  - 六维 FCPI 进化指标 (Phase 8 连线后启用)

使用 Python 内置 http.server, 零额外依赖。
HTML 仪表盘内联 CSS, 单文件自包含。

使用方式:
    bus = EventBus()
    lifecycle = LifecycleManager(...)
    rhythm = RhythmEngine(event_bus=bus)

    dashboard = DashboardServer(
        event_bus=bus,
        lifecycle=lifecycle,
        rhythm=rhythm,
    )
    dashboard.start()  # 启动在 localhost:1990
    # ... 浏览器打开 http://localhost:1990 ...
    dashboard.stop()
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Callable

logger = logging.getLogger("sclerotium.dashboard")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class DashboardSnapshot:
    """仪表盘状态快照。"""
    timestamp: float = field(default_factory=time.time)
    system: dict[str, Any] = field(default_factory=dict)
    events: dict[str, Any] = field(default_factory=dict)
    rhythm: dict[str, Any] = field(default_factory=dict)
    notifications: dict[str, Any] = field(default_factory=dict)
    memory: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# Dashboard HTML 模板
# ═══════════════════════════════════════════════════════════════

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="10">
<title>Sclerotium OS — 生命仪表盘</title>
<style>
  :root {
    --bg: #0a0a1a;
    --card-bg: #12122a;
    --accent: #0f3460;
    --highlight: #e94560;
    --text: #e0e0e0;
    --dim: #888;
    --green: #00cc66;
    --yellow: #ffcc00;
    --blue: #3399ff;
    --red: #ff4444;
    --border: #222244;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    padding: 20px;
    min-height: 100vh;
  }
  h1 {
    font-size: 24px;
    margin-bottom: 4px;
    background: linear-gradient(135deg, var(--green), var(--blue));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .subtitle {
    color: var(--dim);
    font-size: 13px;
    margin-bottom: 24px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px;
  }
  .card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 18px;
  }
  .card h2 {
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--blue);
    margin-bottom: 12px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
  }
  .stat-row {
    display: flex;
    justify-content: space-between;
    padding: 5px 0;
    font-size: 13px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
  }
  .stat-label { color: var(--dim); }
  .stat-value { font-weight: 600; }
  .stat-value.green { color: var(--green); }
  .stat-value.yellow { color: var(--yellow); }
  .stat-value.blue { color: var(--blue); }
  .stat-value.red { color: var(--red); }

  .phase-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 700;
  }
  .phase-RUNNING { background: rgba(0,204,102,0.2); color: var(--green); }
  .phase-SLEEPING { background: rgba(136,136,136,0.2); color: var(--dim); }
  .phase-BOOTING { background: rgba(255,204,0,0.2); color: var(--yellow); }
  .phase-OFFLINE { background: rgba(255,68,68,0.2); color: var(--red); }

  .mode-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 600;
    margin-right: 4px;
  }
  .mode-work { background: rgba(51,153,255,0.2); color: var(--blue); }
  .mode-sleep { background: rgba(136,136,136,0.2); color: var(--dim); }

  .bar-container { margin: 6px 0; }
  .bar-label { font-size: 11px; color: var(--dim); margin-bottom: 2px; }
  .bar-track { background: var(--bg); border-radius: 4px; overflow: hidden; height: 8px; }
  .bar-fill { height: 100%; border-radius: 4px; transition: width 0.5s; }

  .event-list { max-height: 200px; overflow-y: auto; font-size: 11px; font-family: "Consolas", monospace; }
  .event-item { padding: 3px 0; border-bottom: 1px solid rgba(255,255,255,0.02); }
  .event-topic { color: var(--blue); }
  .event-time { color: var(--dim); font-size: 10px; }

  .footer {
    margin-top: 24px;
    text-align: center;
    color: var(--dim);
    font-size: 11px;
  }
  .pulse {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--green);
    animation: pulse 2s infinite;
    margin-right: 6px;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }
</style>
</head>
<body>
<h1>🧬 Sclerotium OS</h1>
<p class="subtitle">{{subtitle}}</p>

<div class="grid">
  <!-- 系统状态 -->
  <div class="card">
    <h2>⚙ 系统状态</h2>
    <div class="stat-row"><span class="stat-label">生命周期</span>
      <span class="phase-badge phase-{{phase}}">{{phase}}</span></div>
    <div class="stat-row"><span class="stat-label">运行时长</span>
      <span class="stat-value green">{{uptime}}</span></div>
    <div class="stat-row"><span class="stat-label">启动阶段</span>
      <span class="stat-value">{{boot_stage}}</span></div>
    <div class="stat-row"><span class="stat-label">器官状态</span>
      <span class="stat-value blue">{{organs_healthy}}/{{organs_total}} 健康</span></div>
    <div class="stat-row"><span class="stat-label">当前模式</span>
      <span class="mode-badge mode-{{mode}}">{{mode}}</span></div>
  </div>

  <!-- 事件总线 -->
  <div class="card">
    <h2>📡 事件总线</h2>
    <div class="stat-row"><span class="stat-label">总事件数</span>
      <span class="stat-value blue">{{total_events}}</span></div>
    <div class="stat-row"><span class="stat-label">活跃主题</span>
      <span class="stat-value">{{active_topics}}</span></div>
    <div class="stat-row"><span class="stat-label">最近事件</span>
      <span class="stat-value">{{recent_count}}</span></div>
    <div class="bar-container">
      <div class="bar-label">事件流速 (最近 50)</div>
      <div class="bar-track"><div class="bar-fill" style="width:{{event_flow_pct}}%;background:var(--blue);"></div></div>
    </div>
    <div class="event-list">{{{event_list}}}</div>
  </div>

  <!-- 节律系统 -->
  <div class="card">
    <h2>🫀 STG 节律</h2>
    <div class="stat-row"><span class="stat-label">幽门节律 (高频)</span>
      <span class="stat-value">{{pyloric_ticks}} 次</span></div>
    <div class="stat-row"><span class="stat-label">胃磨节律 (低频)</span>
      <span class="stat-value">{{gastric_ticks}} 次</span></div>
    <div class="stat-row"><span class="stat-label">代谢节律</span>
      <span class="stat-value">{{metabolic_ticks}} 次</span></div>
    <div class="stat-row"><span class="stat-label">总脉冲</span>
      <span class="stat-value blue">{{total_ticks}}</span></div>
    <div class="stat-row"><span class="stat-label">幽门间隔</span>
      <span class="stat-value">{{pyloric_interval}}s</span></div>
    <div class="stat-row"><span class="stat-label">胃磨间隔</span>
      <span class="stat-value">{{gastric_interval}}s</span></div>
  </div>

  <!-- 通知统计 -->
  <div class="card">
    <h2>🔔 通知系统</h2>
    <div class="stat-row"><span class="stat-label">总通知数</span>
      <span class="stat-value">{{notifications_total}}</span></div>
    <div class="stat-row"><span class="stat-label">SILENT</span>
      <span class="stat-value dim">{{notif_SILENT}}</span></div>
    <div class="stat-row"><span class="stat-label">TRAY</span>
      <span class="stat-value">{{notif_TRAY}}</span></div>
    <div class="stat-row"><span class="stat-label">NOTIFY</span>
      <span class="stat-value blue">{{notif_NOTIFY}}</span></div>
    <div class="stat-row"><span class="stat-label">ALERT</span>
      <span class="stat-value red">{{notif_ALERT}}</span></div>
    <div class="stat-row"><span class="stat-label">状态</span>
      <span class="stat-value {{notif_status_color}}">{{notif_status}}</span></div>
  </div>

  <!-- 记忆系统 -->
  <div class="card">
    <h2>🧠 记忆系统</h2>
    <div class="stat-row"><span class="stat-label">工作记忆</span>
      <span class="stat-value">{{mem_working}}</span></div>
    <div class="stat-row"><span class="stat-label">情景记忆</span>
      <span class="stat-value">{{mem_episodic}}</span></div>
    <div class="stat-row"><span class="stat-label">语义记忆</span>
      <span class="stat-value">{{mem_semantic}}</span></div>
    <div class="stat-row"><span class="stat-label">今日事件</span>
      <span class="stat-value blue">{{daily_events}}</span></div>
    <div class="stat-row"><span class="stat-label">活跃项目</span>
      <span class="stat-value">{{active_projects}}</span></div>
  </div>
</div>

<p class="footer">
  <span class="pulse"></span>
  Sclerotium OS v4.0 — 电子章鱼·黏菌·龙虾·地衣·马 融合生命体
  &nbsp;|&nbsp;
  刷新: {{refresh_time}}
</p>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# API 数据提供者接口
# ═══════════════════════════════════════════════════════════════

class DataProvider:
    """仪表盘数据提供者抽象基类。

    DashboardServer 通过 DataProvider 获取各子系统状态，
    无需直接依赖具体模块。各 Phase 可以注册自己的数据提供者。
    """

    def get_system_status(self) -> dict[str, Any]:
        """获取系统生命周期状态。"""
        return {}

    def get_event_stats(self) -> dict[str, Any]:
        """获取事件总线统计。"""
        return {}

    def get_rhythm_status(self) -> dict[str, Any]:
        """获取节律引擎状态。"""
        return {}

    def get_notification_stats(self) -> dict[str, Any]:
        """获取通知系统统计。"""
        return {}

    def get_memory_stats(self) -> dict[str, Any]:
        """获取记忆系统统计。"""
        return {}

    def get_daily_summary(self) -> dict[str, Any]:
        """获取今日摘要。"""
        return {}


class DefaultDataProvider(DataProvider):
    """默认数据提供者 — 返回空数据, 各 Phase 逐步填充。"""

    pass


# ═══════════════════════════════════════════════════════════════
# HTTP 请求处理器
# ═══════════════════════════════════════════════════════════════

class _DashboardHandler(BaseHTTPRequestHandler):
    """仪表盘 HTTP 请求处理器 (内部类)。

    路由:
      GET /           → HTML 仪表盘页面
      GET /api/status → JSON 系统状态
      GET /api/events → JSON 事件统计
      GET /api/rhythm → JSON 节律状态
      GET /api/health → JSON 健康检查
    """

    # 类变量, 由 DashboardServer 设置
    data_provider: DataProvider = DefaultDataProvider()

    def log_message(self, format: str, *args: Any) -> None:
        """重定向日志到 logger。"""
        logger.debug("Dashboard HTTP: %s", format % args)

    def do_GET(self) -> None:
        """处理 GET 请求。"""
        path = self.path.split("?")[0]

        if path == "/":
            self._serve_html()
        elif path == "/api/status":
            self._serve_json(self._build_status_response())
        elif path == "/api/events":
            self._serve_json(self.data_provider.get_event_stats())
        elif path == "/api/rhythm":
            self._serve_json(self.data_provider.get_rhythm_status())
        elif path == "/api/health":
            self._serve_json({"status": "ok", "timestamp": time.time()})
        elif path == "/api/notifications":
            self._serve_json(self.data_provider.get_notification_stats())
        elif path == "/api/memory":
            self._serve_json(self.data_provider.get_memory_stats())
        elif path == "/api/all":
            self._serve_json(self._build_full_snapshot())
        else:
            self.send_error(404, "Not Found")

    def _serve_html(self) -> None:
        """渲染并返回 HTML 仪表盘。"""
        sys = self.data_provider.get_system_status()
        evt = self.data_provider.get_event_stats()
        rhy = self.data_provider.get_rhythm_status()
        notif = self.data_provider.get_notification_stats()
        mem = self.data_provider.get_memory_stats()

        # 构建事件列表 HTML
        recent = evt.get("recent_events", [])
        event_items = ""
        for e in recent[:15]:
            topic = e.get("topic", "?")
            ts = e.get("timestamp", 0)
            time_str = time.strftime("%H:%M:%S", time.localtime(ts)) if ts else "--:--:--"
            event_items += (
                f'<div class="event-item">'
                f'<span class="event-time">{time_str}</span> '
                f'<span class="event-topic">{topic}</span>'
                f'</div>\n'
            )

        # 安全获取嵌套值
        def _get(d: dict, key: str, default: Any = "—") -> Any:
            return d.get(key, default) if d else default

        # 事件流速百分比
        total_events = _get(evt, "total_events", 0)
        flow_pct = min(100, (total_events % 51) * 2)  # 近似的可视化

        html = DASHBOARD_HTML
        replacements = {
            "{{subtitle}}": f"电子生命体 · 运行中 · {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "{{phase}}": str(_get(sys, "phase", "UNKNOWN")),
            "{{uptime}}": str(_get(sys, "uptime", "—")),
            "{{boot_stage}}": str(_get(sys, "boot_stage", "—")),
            "{{organs_healthy}}": str(_get(sys, "organs_healthy", 0)),
            "{{organs_total}}": str(_get(sys, "organs_total", 0)),
            "{{mode}}": str(_get(rhy, "active_profile", "work")),
            "{{total_events}}": str(total_events),
            "{{active_topics}}": str(_get(evt, "topic_count", 0)),
            "{{recent_count}}": str(_get(evt, "recent_events_count", 0)),
            "{{event_flow_pct}}": str(flow_pct),
            "{{event_list}}": event_items if event_items else '<div style="color:var(--dim);padding:8px;">暂无事件</div>',
            "{{pyloric_ticks}}": str(_get(rhy, "pyloric_ticks", 0)),
            "{{gastric_ticks}}": str(_get(rhy, "gastric_ticks", 0)),
            "{{metabolic_ticks}}": str(_get(rhy, "metabolic_ticks", 0)),
            "{{total_ticks}}": str(_get(rhy, "total_ticks", 0)),
            "{{pyloric_interval}}": str(_get(rhy, "pyloric_interval", "—")),
            "{{gastric_interval}}": str(_get(rhy, "gastric_interval", "—")),
            "{{notifications_total}}": str(_get(notif, "total_sent", 0)),
            "{{notif_SILENT}}": str(_get(notif, "by_level", {}).get("SILENT", 0)),
            "{{notif_TRAY}}": str(_get(notif, "by_level", {}).get("TRAY", 0)),
            "{{notif_NOTIFY}}": str(_get(notif, "by_level", {}).get("NOTIFY", 0)),
            "{{notif_ALERT}}": str(_get(notif, "by_level", {}).get("ALERT", 0)),
            "{{notif_status}}": "抑制中" if _get(notif, "suppressed", False) else "活跃",
            "{{notif_status_color}}": "red" if _get(notif, "suppressed", False) else "green",
            "{{mem_working}}": str(_get(mem, "working_count", 0)),
            "{{mem_episodic}}": str(_get(mem, "episodic_count", 0)),
            "{{mem_semantic}}": str(_get(mem, "semantic_count", 0)),
            "{{daily_events}}": str(_get(mem, "daily_events", 0)),
            "{{active_projects}}": str(_get(mem, "active_projects", "—")),
            "{{refresh_time}}": time.strftime("%H:%M:%S"),
        }

        for key, value in replacements.items():
            html = html.replace(key, value)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _serve_json(self, data: dict[str, Any]) -> None:
        """返回 JSON 响应。"""
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _build_status_response(self) -> dict[str, Any]:
        """构建完整状态响应。"""
        return {
            "system": self.data_provider.get_system_status(),
            "events": self.data_provider.get_event_stats(),
            "rhythm": self.data_provider.get_rhythm_status(),
            "notifications": self.data_provider.get_notification_stats(),
            "memory": self.data_provider.get_memory_stats(),
            "timestamp": time.time(),
        }

    def _build_full_snapshot(self) -> dict[str, Any]:
        """构建完整快照。"""
        return {
            "system": self.data_provider.get_system_status(),
            "events": self.data_provider.get_event_stats(),
            "rhythm": self.data_provider.get_rhythm_status(),
            "notifications": self.data_provider.get_notification_stats(),
            "memory": self.data_provider.get_memory_stats(),
            "daily": self.data_provider.get_daily_summary(),
            "timestamp": time.time(),
        }


# ═══════════════════════════════════════════════════════════════
# Dashboard 服务器
# ═══════════════════════════════════════════════════════════════

class DashboardServer:
    """轻量级 HTTP 仪表盘服务器。

    使用方式:
        server = DashboardServer(port=1990)
        server.set_data_provider(provider)
        server.start()
        # ... 浏览器 http://localhost:1990 ...
        server.stop()
    """

    DEFAULT_PORT = 1990

    def __init__(
        self,
        port: int = DEFAULT_PORT,
        host: str = "127.0.0.1",
        data_provider: DataProvider | None = None,
    ) -> None:
        self._port = port
        self._host = host
        self._data_provider = data_provider or DefaultDataProvider()
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._running: bool = False

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def set_data_provider(self, provider: DataProvider) -> None:
        """设置/替换数据提供者。"""
        self._data_provider = provider
        _DashboardHandler.data_provider = provider

    def start(self) -> None:
        """启动 HTTP 服务器 (后台线程)。"""
        if self._running:
            return

        # 注入数据提供者到处理器
        _DashboardHandler.data_provider = self._data_provider

        self._httpd = HTTPServer((self._host, self._port), _DashboardHandler)
        self._running = True

        self._thread = threading.Thread(
            target=self._serve_forever,
            name="sclerotium-dashboard",
            daemon=True,
        )
        self._thread.start()
        logger.info("Dashboard started at http://%s:%d", self._host, self._port)

    def stop(self) -> None:
        """停止 HTTP 服务器。"""
        self._running = False
        if self._httpd:
            try:
                self._httpd.shutdown()
            except Exception:
                pass
            self._httpd = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        logger.info("Dashboard stopped")

    def get_snapshot(self) -> DashboardSnapshot:
        """获取当前仪表盘状态快照。"""
        return DashboardSnapshot(
            system=self._data_provider.get_system_status(),
            events=self._data_provider.get_event_stats(),
            rhythm=self._data_provider.get_rhythm_status(),
            notifications=self._data_provider.get_notification_stats(),
            memory=self._data_provider.get_memory_stats(),
        )

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def port(self) -> int:
        return self._port

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}"

    # ═══════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════

    def _serve_forever(self) -> None:
        """后台线程 — 阻塞式 serve_forever。"""
        try:
            if self._httpd:
                self._httpd.serve_forever(poll_interval=0.5)
        except Exception as e:
            if self._running:
                logger.error("Dashboard server error: %s", e)


# ═══════════════════════════════════════════════════════════════
# 内置数据提供者工厂
# ═══════════════════════════════════════════════════════════════

class CompositeDataProvider(DataProvider):
    """复合数据提供者 — 聚合多个子提供者。

    允许各 Phase 独立注册自己的数据源, 互不耦合。

    使用:
        provider = CompositeDataProvider()
        provider.register("system", lifecycle_data_provider)
        provider.register("events", event_data_provider)
    """

    def __init__(self) -> None:
        self._providers: dict[str, DataProvider] = {}

    def register(self, name: str, provider: DataProvider) -> None:
        """注册一个数据提供者。"""
        self._providers[name] = provider

    def unregister(self, name: str) -> None:
        """移除一个数据提供者。"""
        self._providers.pop(name, None)

    def get_system_status(self) -> dict[str, Any]:
        result = {}
        for p in self._providers.values():
            result.update(p.get_system_status())
        return result

    def get_event_stats(self) -> dict[str, Any]:
        result = {}
        for p in self._providers.values():
            result.update(p.get_event_stats())
        return result

    def get_rhythm_status(self) -> dict[str, Any]:
        result = {}
        for p in self._providers.values():
            result.update(p.get_rhythm_status())
        return result

    def get_notification_stats(self) -> dict[str, Any]:
        result = {}
        for p in self._providers.values():
            result.update(p.get_notification_stats())
        return result

    def get_memory_stats(self) -> dict[str, Any]:
        result = {}
        for p in self._providers.values():
            result.update(p.get_memory_stats())
        return result

    def get_daily_summary(self) -> dict[str, Any]:
        result = {}
        for p in self._providers.values():
            result.update(p.get_daily_summary())
        return result


# ═══════════════════════════════════════════════════════════════
# Dashboard v2.0 — 全器官Web仪表盘
# ═══════════════════════════════════════════════════════════════

FULL_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta http-equiv="refresh" content="5">
<title>Sclerotium OS v5.0 — 超级生命仪表盘</title>
<style>
:root{--bg:#06060f;--card:#0c0c1d;--accent:#16213e;--hl:#e94560;--text:#e0e0e0;
--dim:#777;--g:#00cc66;--y:#ffcc00;--b:#3399ff;--r:#ff4444;--p:#aa66ff;--border:#1a1a3a}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:"Segoe UI","Microsoft YaHei",sans-serif;padding:12px;min-height:100vh}
h1{font-size:22px;background:linear-gradient(135deg,var(--g),var(--b),var(--p));-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:2px}
.sub{color:var(--dim);font-size:12px;margin-bottom:12px}
.symphony{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:8px;margin-bottom:8px}
.layer{border:1px solid var(--border);border-radius:10px;padding:10px}
.layer h3{font-size:12px;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid rgba(255,255,255,.05)}
.layer.sense h3{color:var(--g)}.layer.think h3{color:var(--b)}.layer.act h3{color:var(--hl)}
.layer.evolve h3{color:var(--p)}.layer.metabolize h3{color:var(--y)}
.organ{display:flex;justify-content:space-between;align-items:center;padding:4px 0;font-size:11px;border-bottom:1px solid rgba(255,255,255,.02)}
.organ-name{flex:1}.organ-layer{color:var(--dim);font-size:10px;margin:0 8px}
.status-dot{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:4px}
.status-dot.healthy{background:var(--g)}.status-dot.degraded{background:var(--y)}
.status-dot.failing{background:var(--r)}.status-dot.offline{background:var(--dim)}
.metrics-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-bottom:8px}
.metric{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:10px;text-align:center}
.metric .val{font-size:28px;font-weight:700}.metric .lbl{font-size:10px;color:var(--dim);text-transform:uppercase}
.val.g{color:var(--g)}.val.b{color:var(--b)}.val.r{color:var(--r)}.val.p{color:var(--p)}.val.y{color:var(--y)}
.footer{text-align:center;color:var(--dim);font-size:10px;margin-top:8px}
.pulse{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--g);animation:pulse 2s infinite;margin-right:4px}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.organs-summary{display:flex;gap:12px;margin-bottom:8px;flex-wrap:wrap}
.organs-summary span{font-size:12px}.organs-summary .g{color:var(--g)}.organs-summary .y{color:var(--y)}.organs-summary .r{color:var(--r)}
</style></head>
<body>
<h1>🧬 Sclerotium OS v5.0</h1>
<p class="sub">{{subtitle}}</p>

<div class="organs-summary">
  <span>🫀 器官: <b class="g">{{healthy}}</b> 健康 / <b class="y">{{degraded}}</b> 退化 / <b class="r">{{failing}}</b> 故障 / <b>{{total}}</b> 总计</span>
  <span>⏱ 运行: <b>{{uptime}}</b></span>
</div>

<div class="metrics-grid">
  <div class="metric"><div class="val b">{{fcpi}}</div><div class="lbl">FCPI 总分</div></div>
  <div class="metric"><div class="val p">{{phi}}</div><div class="lbl">Φ 意识值</div></div>
  <div class="metric"><div class="val g">{{safety}}</div><div class="lbl">安全状态</div></div>
  <div class="metric"><div class="val">{{memory}}</div><div class="lbl">记忆总数</div></div>
  <div class="metric"><div class="val y">Gen {{gen}}</div><div class="lbl">进化代数</div></div>
  <div class="metric"><div class="val">{{nudge}}%</div><div class="lbl">通知接受率</div></div>
  <div class="metric"><div class="val">{{skills}}</div><div class="lbl">可用技能</div></div>
  <div class="metric"><div class="val">{{mcp}}</div><div class="lbl">MCP服务</div></div>
  <div class="metric"><div class="val">{{hotspots}}</div><div class="lbl">信息素热点</div></div>
  <div class="metric"><div class="val">{{twin}}%</div><div class="lbl">孪生健康度</div></div>
</div>

<div class="symphony">{{{layers}}}</div>

<p class="footer"><span class="pulse"></span>Sclerotium OS v5.0 — 238器官超级生命体 | 刷新: {{refresh}}</p>
</body></html>"""


class FullDashboardHandler(BaseHTTPRequestHandler):
    """全器官仪表盘 HTTP 处理器。"""

    frontend_bridge: Any = None

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self._serve_full_html()
        elif path == "/api/full":
            self._serve_full_json()
        elif path == "/api/health":
            self._json({"status": "ok", "timestamp": time.time()})
        else:
            self.send_error(404)

    def _serve_full_html(self):
        bridge = self.__class__.frontend_bridge
        if bridge is None:
            self._json({"error": "No frontend bridge registered"})
            return

        snap = bridge.snapshot()

        # 构建层 HTML
        layers_html = ""
        for layer_class, color, label, organs in [
            ("sense", "g", "SENSE 感知层",
             snap.sense_organs),
            ("think", "b", "THINK 思考层",
             snap.think_organs),
            ("act", "hl", "ACT 行动层",
             snap.act_organs),
            ("evolve", "p", "EVOLVE 进化层",
             snap.evolve_organs),
            ("metabolize", "y", "METABOLIZE 代谢层",
             snap.metabolize_organs),
        ]:
            if not organs:
                continue
            rows = ""
            for o in organs:
                dot = o.status if o.status in ("healthy", "degraded", "failing") else "offline"
                rows += (
                    f'<div class="organ">'
                    f'<span class="organ-name"><span class="status-dot {dot}"></span>{o.name}</span>'
                    f'<span class="organ-layer">{o.layer}</span>'
                    f'</div>'
                )
            layers_html += (
                f'<div class="layer {layer_class}">'
                f'<h3>{label} ({len(organs)} 器官)</h3>'
                f'{rows}</div>'
            )

        html = FULL_DASHBOARD_HTML
        html = html.replace("{{subtitle}}",
            f"238 器官超级生命体 · {time.strftime('%Y-%m-%d %H:%M:%S')}")
        html = html.replace("{{healthy}}", str(snap.healthy_organs))
        html = html.replace("{{degraded}}", str(snap.degraded_organs))
        html = html.replace("{{failing}}", str(snap.failing_organs))
        html = html.replace("{{total}}", str(snap.total_organs))
        html = html.replace("{{uptime}}", f"{snap.uptime_seconds:.0f}s")
        html = html.replace("{{fcpi}}", f"{snap.fcpi_score:.3f}")
        html = html.replace("{{phi}}", f"{snap.phi_value:.3f}")
        html = html.replace("{{safety}}", snap.safety_status)
        html = html.replace("{{memory}}", str(snap.memory_total))
        html = html.replace("{{gen}}", str(snap.evolution_generation))
        html = html.replace("{{nudge}}", f"{snap.nudge_acceptance*100:.0f}")
        html = html.replace("{{skills}}", str(snap.market_skills))
        html = html.replace("{{mcp}}", str(snap.market_mcp))
        html = html.replace("{{hotspots}}", str(snap.field_hotspots))
        html = html.replace("{{twin}}", f"{snap.digital_twin_health*100:.0f}")
        html = html.replace("{{layers}}", layers_html)
        html = html.replace("{{refresh}}", time.strftime("%H:%M:%S"))

        self._html(html)

    def _serve_full_json(self):
        bridge = self.__class__.frontend_bridge
        if bridge is None:
            self._json({"error": "No frontend bridge"})
            return
        self._json(json.loads(bridge.to_json()))

    def _html(self, content):
        body = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


class FullDashboardServer:
    """全器官仪表盘 HTTP 服务器 v2.0。

    使用方式:
        bridge = FrontendBridge()
        bridge.register("arbiter", arbiter, "L10", "act")
        # ... register all modules ...

        dashboard = FullDashboardServer(port=1990, bridge=bridge)
        dashboard.start()
        # → http://localhost:1990
    """

    def __init__(self, port: int = 1990, bridge: Any = None):
        self._port = port
        self._bridge = bridge
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def set_bridge(self, bridge):
        self._bridge = bridge
        FullDashboardHandler.frontend_bridge = bridge

    def start(self):
        if self._running:
            return
        FullDashboardHandler.frontend_bridge = self._bridge
        self._httpd = HTTPServer(("127.0.0.1", self._port), FullDashboardHandler)
        self._running = True
        self._thread = threading.Thread(target=self._httpd.serve_forever,
                                        name="dashboard-v2", daemon=True)
        self._thread.start()
        logger.info("Full Dashboard at http://127.0.0.1:%d", self._port)

    def stop(self):
        self._running = False
        if self._httpd:
            try:
                self._httpd.shutdown()
            except Exception:
                pass
        self._httpd = None
