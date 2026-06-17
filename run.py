"""Sclerotium OS — 一键启动全部界面。

用法:
    python run.py              → 启动守护进程 + Web仪表盘 + Alt+Space浮窗
    python run.py --tui        → 启动终端 TUI
    python run.py --dashboard  → 仅启动 Web 仪表盘
"""

import sys
import time
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("sclerotium")

args = set(sys.argv[1:])


def start_daemon():
    """启动后台守护进程。"""
    from daemon.service import SclerotiumDaemon
    dm = SclerotiumDaemon(headless=True)
    dm.start()
    log.info("Daemon running")
    return dm


def start_dashboard(port=1990):
    """启动 Web 仪表盘。"""
    from kernel.frontend_bridge import FrontendBridge
    from ui.dashboard_web import FullDashboardServer

    bridge = FrontendBridge()
    # 注册核心模块
    from kernel.event_bus import EventBus
    from kernel.constitutional_arbiter import ConstitutionalArbiter
    from evolution.fcpi_tracker import FCPITracker
    from kernel.consciousness_monitor import ConsciousnessMonitor

    bus = EventBus()
    arbiter = ConstitutionalArbiter()
    tracker = FCPITracker()
    monitor = ConsciousnessMonitor()

    bridge.register("event_bus", bus, "core", "sense", "神经系统")
    bridge.register("constitutional_arbiter", arbiter, "L10", "act", "五门宪法审查")
    bridge.register("fcpi_tracker", tracker, "L6", "evolve", "六维适应度追踪")
    bridge.register("consciousness_monitor", monitor, "L10", "think", "意识监控器")

    server = FullDashboardServer(port=port, bridge=bridge)
    server.start()
    log.info("Dashboard: http://127.0.0.1:%d", port)
    return server


def start_quickbar():
    """启动 Alt+Space 浮窗。"""
    try:
        import subprocess, sys
        proc = subprocess.Popen(
            [sys.executable, "hotkey_launcher.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        log.info("Alt+Space launcher started (PID %d)", proc.pid)
        return proc
    except Exception as e:
        log.warning("QuickBar failed: %s", e)
        return None


# ═══════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════

if "--tui" in args:
    from cli.tui.app import run_tui
    run_tui()

elif "--dashboard" in args:
    server = start_dashboard()
    log.info("Dashboard only mode. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()

else:
    # 一键启动全部
    print(r"""
    ╔══════════════════════════════════════════════╗
    ║  🧬 Sclerotium OS v5.0 — 超级电子生命体      ║
    ║  238器官 · 五层交响乐 · L0-L10              ║
    ╠══════════════════════════════════════════════╣
    ║  Web仪表盘:  http://localhost:1990           ║
    ║  Alt+Space:  浮窗命令栏                       ║
    ║  Ctrl+C:     停止                            ║
    ╚══════════════════════════════════════════════╝
    """)

    daemon = start_daemon()
    dashboard = start_dashboard()
    quickbar = start_quickbar()

    log.info("All systems online. Visit http://localhost:1990")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Shutting down...")
        daemon.stop()
        dashboard.stop()
        log.info("Goodbye.")
