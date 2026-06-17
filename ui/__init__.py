"""UI — 界面层，生命体与宿主交互的窗口。

Phase 4: 通知系统 + Alt+Space 快速命令栏 + Web 仪表盘

五层交互界面:
  L1 系统托盘 (daemon/tray_icon.py)       — 一直在
  L2 Alt+Space 浮窗 (quick_bar.py)        — 主要交互
  L3 Toast 通知 (toast_notification.py)   — 主动提醒
  L4 Web 仪表盘 (dashboard_web.py)        — 深度查看
  L5 IM 触手 (platforms/ — Phase 6)       — 远程交互
"""

from ui.toast_notification import ToastManager, ToastLevel
from ui.quick_bar import QuickBar
from ui.dashboard_web import DashboardServer

__all__ = ["ToastManager", "ToastLevel", "QuickBar", "DashboardServer"]
