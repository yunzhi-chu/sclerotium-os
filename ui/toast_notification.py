"""Toast Notification — Windows 原生通知系统。

使用三层策略:
  1. WinRT Toast (Windows 10+ 原生通知)
  2. PowerShell 脚本回退
  3. 纯日志回退 (无图形界面环境)

通知分级 (与 NudgeEngine.NudgeLevel 对齐):
  - SILENT  → 不显示
  - TRAY    → 仅托盘提示
  - NOTIFY  → 桌面 Toast 通知
  - ALERT   → 高优先级 (持续显示直到用户关闭)
"""

from __future__ import annotations

import subprocess
import threading
import time
import logging
import platform
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("sclerotium.toast")


class ToastLevel(int, Enum):
    """通知级别 (对齐 NudgeLevel)。"""
    SILENT = 0
    TRAY = 1
    NOTIFY = 2
    ALERT = 3


@dataclass(frozen=True)
class Toast:
    """不可变 Toast 通知记录。"""
    title: str
    message: str
    level: ToastLevel = ToastLevel.NOTIFY
    duration: float = 5.0       # 显示秒数 (ALERT 级别忽略)
    category: str = "general"   # health/security/insight/info
    timestamp: float = field(default_factory=time.time)
    toast_id: str = ""          # 唯一 ID, 生成时自动填充

    def __post_init__(self) -> None:
        if not self.toast_id:
            object.__setattr__(
                self, "toast_id",
                f"toast_{int(self.timestamp * 1000)}_{hash(self.title) & 0xFFFF:04x}",
            )


# ═══════════════════════════════════════════════════════════════
# Toast 策略接口
# ═══════════════════════════════════════════════════════════════

class ToastBackend:
    """通知后端的抽象基类。"""

    def send(self, toast: Toast) -> bool:
        """发送通知, 返回是否成功。"""
        raise NotImplementedError

    def is_available(self) -> bool:
        """此后端是否可用。"""
        raise NotImplementedError


class WinRTToastBackend(ToastBackend):
    """Windows 10/11 WinRT 原生 Toast 通知。

    使用 PowerShell 调用 WinRT API, 无需额外依赖。
    """

    APP_ID = "SclerotiumOS.Toast"

    _TEMPLATE = r'''
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
    [Windows.UI.Notifications.ToastTemplateType]::ToastText02
)
$texts = $template.GetElementsByTagName("text")
$texts[0].AppendChild($template.CreateTextNode("{title}")) > $null
$texts[1].AppendChild($template.CreateTextNode("{message}")) > $null
$toast = [Windows.UI.Notifications.ToastNotification]::new($template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{app_id}").Show($toast)
'''

    def send(self, toast: Toast) -> bool:
        try:
            script = self._TEMPLATE.format(
                title=self._escape(toast.title),
                message=self._escape(toast.message),
                app_id=self.APP_ID,
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.debug("WinRT toast sent: %s", toast.title)
                return True
            else:
                logger.warning("WinRT toast failed: %s", result.stderr.strip())
                return False
        except Exception as e:
            logger.warning("WinRT toast exception: %s", e)
            return False

    def is_available(self) -> bool:
        return platform.system() == "Windows"

    @staticmethod
    def _escape(text: str) -> str:
        """转义 PowerShell 字符串中的特殊字符。"""
        return text.replace("'", "''").replace('"', '\\"')


class BalloonTipBackend(ToastBackend):
    """pywin32 气球提示 — 当 WinRT 不可用时的回退。

    通过 Shell_NotifyIcon 显示托盘气球提示。
    """

    def send(self, toast: Toast) -> bool:
        try:
            import win32api
            import win32gui
            import win32con

            # 查找或创建临时通知窗口
            flags = {
                ToastLevel.NOTIFY: win32con.NIIF_INFO,
                ToastLevel.ALERT: win32con.NIIF_WARNING,
            }.get(toast.level, win32con.NIIF_INFO)

            # 简单版本: 使用 MessageBox 作为终极回退
            if toast.level == ToastLevel.ALERT:
                win32api.MessageBox(
                    0,
                    toast.message,
                    toast.title,
                    win32con.MB_ICONWARNING | win32con.MB_SYSTEMMODAL,
                )
                return True
            return False
        except Exception as e:
            logger.warning("Balloon tip failed: %s", e)
            return False

    def is_available(self) -> bool:
        try:
            import win32api
            return True
        except ImportError:
            return False


class LogBackend(ToastBackend):
    """纯日志回退 — 无图形界面时将通知写入日志。"""

    def send(self, toast: Toast) -> bool:
        prefix = {
            ToastLevel.SILENT: "🔇",
            ToastLevel.TRAY: "🔔",
            ToastLevel.NOTIFY: "📢",
            ToastLevel.ALERT: "🚨",
        }.get(toast.level, "📢")
        logger.info("%s [%s] %s: %s", prefix, toast.level.name, toast.title, toast.message)
        return True

    def is_available(self) -> bool:
        return True


# ═══════════════════════════════════════════════════════════════
# Toast 管理器
# ═══════════════════════════════════════════════════════════════

class ToastManager:
    """统一的通知管理器。

    自动选择最佳后端:
      1. WinRT (Windows 10+ 原生)
      2. BalloonTip (pywin32 回退)
      3. Log (纯日志回退)

    使用方式:
        mgr = ToastManager()
        mgr.send("休息一下", "你已连续工作 60 分钟", level=ToastLevel.NOTIFY)
        mgr.send("安全警告", "未知程序请求管理员权限", level=ToastLevel.ALERT)

        # 与 NudgeEngine 集成:
        decision = nudge_engine.decide(...)
        if decision.level >= NudgeLevel.NOTIFY:
            mgr.send(decision.title, decision.message, ToastLevel(decision.level))
    """

    MAX_HISTORY = 200

    def __init__(
        self,
        app_name: str = "Sclerotium OS",
        backends: list[ToastBackend] | None = None,
    ) -> None:
        self._app_name = app_name
        self._backends = backends or self._default_backends()
        self._history: list[Toast] = []
        self._lock = threading.Lock()
        self._on_send_callbacks: list[Callable[[Toast], None]] = []
        self._suppressed: bool = False
        self._min_level: ToastLevel = ToastLevel.TRAY

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def send(
        self,
        title: str,
        message: str,
        level: ToastLevel = ToastLevel.NOTIFY,
        duration: float = 5.0,
        category: str = "general",
    ) -> Toast:
        """发送一条通知。

        Args:
            title: 通知标题
            message: 通知正文
            level: 通知级别 (SILENT/TRAY/NOTIFY/ALERT)
            duration: 显示秒数
            category: 类别标签

        Returns:
            Toast 记录 (可用于追踪)
        """
        toast = Toast(
            title=title,
            message=message,
            level=level,
            duration=duration,
            category=category,
        )

        # 静默级别不发送
        if level == ToastLevel.SILENT:
            self._record(toast)
            return toast

        # 全局抑制检查
        if self._suppressed:
            logger.debug("Toast suppressed: %s", title)
            self._record(toast)
            return toast

        # 最低级别过滤
        if level < self._min_level:
            logger.debug("Toast below min_level %s: %s", self._min_level.name, title)
            self._record(toast)
            return toast

        # 尝试后端发送
        sent = False
        for backend in self._backends:
            if backend.is_available():
                try:
                    sent = backend.send(toast)
                    if sent:
                        break
                except Exception as e:
                    logger.debug("Backend %s failed: %s", type(backend).__name__, e)

        if not sent:
            logger.warning("All toast backends failed for: %s", title)

        self._record(toast)
        self._notify_callbacks(toast)
        return toast

    def suppress(self, suppressed: bool = True) -> None:
        """全局抑制/恢复通知。"""
        self._suppressed = suppressed
        logger.debug("Toast suppression: %s", "ON" if suppressed else "OFF")

    def set_min_level(self, level: ToastLevel) -> None:
        """设置最低通知级别，低于此级别的通知被过滤。"""
        self._min_level = level

    def get_history(self, limit: int = 50) -> list[Toast]:
        """获取最近的通知历史。"""
        with self._lock:
            return list(self._history[-limit:])

    def get_stats(self) -> dict[str, Any]:
        """获取通知统计。"""
        with self._lock:
            recent = self._history[-100:]
            return {
                "total_sent": len(self._history),
                "recent_count": len(recent),
                "by_level": {
                    level.name: sum(1 for t in recent if t.level == level)
                    for level in ToastLevel
                },
                "by_category": {
                    cat: sum(1 for t in recent if t.category == cat)
                    for cat in sorted(set(t.category for t in recent))
                },
                "suppressed": self._suppressed,
                "min_level": self._min_level.name,
                "backends_available": [type(b).__name__ for b in self._backends if b.is_available()],
            }

    def on_send(self, callback: Callable[[Toast], None]) -> None:
        """注册通知发送回调 (用于 EventBus 集成)。"""
        self._on_send_callbacks.append(callback)

    def clear_history(self) -> None:
        """清空通知历史。"""
        with self._lock:
            self._history.clear()

    # ═══════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _default_backends() -> list[ToastBackend]:
        """创建默认后端链。"""
        backends: list[ToastBackend] = []
        winrt = WinRTToastBackend()
        if winrt.is_available():
            backends.append(winrt)
        balloon = BalloonTipBackend()
        if balloon.is_available():
            backends.append(balloon)
        backends.append(LogBackend())
        return backends

    def _record(self, toast: Toast) -> None:
        """记录通知到历史。"""
        with self._lock:
            self._history.append(toast)
            if len(self._history) > self.MAX_HISTORY:
                self._history = self._history[-self.MAX_HISTORY:]

    def _notify_callbacks(self, toast: Toast) -> None:
        """通知所有回调。"""
        for cb in self._on_send_callbacks:
            try:
                cb(toast)
            except Exception as e:
                logger.debug("Toast callback error: %s", e)


# ═══════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════

# 全局单例
_default_manager: ToastManager | None = None


def get_toast_manager() -> ToastManager:
    """获取全局 ToastManager 单例。"""
    global _default_manager
    if _default_manager is None:
        _default_manager = ToastManager()
    return _default_manager


def notify(title: str, message: str, level: ToastLevel = ToastLevel.NOTIFY) -> Toast:
    """快捷发送通知。"""
    return get_toast_manager().send(title, message, level)


def alert(title: str, message: str) -> Toast:
    """快捷发送高优先级告警。"""
    return get_toast_manager().send(title, message, ToastLevel.ALERT)
