"""Quick Bar — Alt+Space 浮动命令栏。

生命体的"嘴"和"耳朵" — 宿主召唤生命体的主要交互界面。

特性:
  - 全局热键 Alt+Space 弹出/隐藏
  - 无边框、置顶浮窗, 不抢焦点
  - Esc 或点击外部关闭
  - 输入回车 → 提交命令 → 显示结果
  - 最近命令历史
  - 状态栏显示当前模式/活跃时间

热键注册使用 Windows RegisterHotKey API (通过 ctypes),
窗口事件循环使用 tkinter (Python 内置)。

使用方式:
    bar = QuickBar(on_submit=handle_command)
    bar.start()  # 启动热键监听
    # ... 用户按 Alt+Space ...
    bar.stop()   # 停止
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import logging
import threading
import time
import tkinter as tk
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("sclerotium.quickbar")


# ═══════════════════════════════════════════════════════════════
# Windows 常量
# ═══════════════════════════════════════════════════════════════

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
VK_SPACE = 0x20

HOTKEY_ID_ALT_SPACE = 1

# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class QuickBarEntry:
    """一条命令历史记录。"""
    text: str
    timestamp: float = field(default_factory=time.time)
    is_response: bool = False  # True = 系统回复, False = 用户输入


@dataclass(frozen=True)
class QuickBarState:
    """浮窗当前状态快照。"""
    visible: bool
    mode: str = "work"
    active_time: str = ""
    pending_count: int = 0
    history_count: int = 0


# ═══════════════════════════════════════════════════════════════
# QuickBar GUI
# ═══════════════════════════════════════════════════════════════

class QuickBar:
    """Alt+Space 浮动命令栏。

    生命周期:
      1. 创建 QuickBar(on_submit=callback)
      2. 调用 start() 注册热键并启动 GUI 线程
      3. 用户在任意窗口按 Alt+Space → 浮窗弹出
      4. 输入命令回车 → on_submit 被调用
      5. 调用 stop() 注销热键并关闭窗口
    """

    # 窗口尺寸
    WIDTH = 520
    HEIGHT = 320
    INPUT_HEIGHT = 42
    STATUS_HEIGHT = 28

    # 颜色主题
    BG_COLOR = "#1a1a2e"
    FG_COLOR = "#e0e0e0"
    ACCENT_COLOR = "#0f3460"
    HIGHLIGHT_COLOR = "#e94560"
    INPUT_BG = "#16213e"
    STATUS_BG = "#0f3460"
    DIM_COLOR = "#888888"
    BORDER_COLOR = "#333355"

    def __init__(
        self,
        on_submit: Callable[[str], Optional[str]] | None = None,
        hotkey_mod: int = MOD_ALT,
        hotkey_key: int = VK_SPACE,
        max_history: int = 100,
    ) -> None:
        """
        Args:
            on_submit: 用户提交命令时的回调, 接收输入文本, 可选返回响应文本
            hotkey_mod: 热键修饰键 (默认 Alt)
            hotkey_key: 热键虚拟键码 (默认 Space)
            max_history: 最大历史条目数
        """
        self._on_submit = on_submit
        self._hotkey_mod = hotkey_mod
        self._hotkey_key = hotkey_key
        self._max_history = max_history

        # 状态
        self._visible: bool = False
        self._running: bool = False
        self._mode: str = "work"
        self._active_time: str = ""
        self._pending_count: int = 0
        self._history: list[QuickBarEntry] = []

        # GUI 对象 (在 GUI 线程中创建)
        self._root: tk.Tk | None = None
        self._main_frame: tk.Frame | None = None
        self._history_text: tk.Text | None = None
        self._input_var: tk.StringVar | None = None
        self._input_entry: tk.Entry | None = None
        self._status_label: tk.Label | None = None
        self._lock = threading.Lock()

        # 线程
        self._gui_thread: threading.Thread | None = None
        self._hotkey_registered: bool = False

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def start(self) -> None:
        """启动热键监听和 GUI 线程。"""
        if self._running:
            return
        self._running = True
        self._gui_thread = threading.Thread(
            target=self._gui_loop,
            name="sclerotium-quickbar",
            daemon=True,
        )
        self._gui_thread.start()
        logger.info("QuickBar started — Alt+Space to toggle")

    def stop(self) -> None:
        """停止热键监听并关闭 GUI。"""
        self._running = False
        if self._root:
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass
        if self._gui_thread and self._gui_thread.is_alive():
            self._gui_thread.join(timeout=3.0)
        self._gui_thread = None
        self._root = None
        logger.info("QuickBar stopped")

    def toggle(self) -> None:
        """切换浮窗可见性 (由热键触发)。"""
        if self._visible:
            self.hide()
        else:
            self.show()

    def show(self) -> None:
        """显示浮窗。"""
        if self._root:
            self._root.after(0, self._do_show)

    def hide(self) -> None:
        """隐藏浮窗。"""
        if self._root:
            self._root.after(0, self._do_hide)

    def add_response(self, text: str) -> None:
        """添加系统回复到历史。"""
        entry = QuickBarEntry(text=text, is_response=True)
        with self._lock:
            self._history.append(entry)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
        if self._root and self._visible:
            self._root.after(0, self._update_history_display)

    def set_mode(self, mode: str) -> None:
        """更新当前模式显示。"""
        self._mode = mode
        if self._root:
            self._root.after(0, self._update_status)

    def set_active_time(self, active_time: str) -> None:
        """更新活跃时间显示。"""
        self._active_time = active_time
        if self._root:
            self._root.after(0, self._update_status)

    def set_pending_count(self, count: int) -> None:
        """更新待处理事项数。"""
        self._pending_count = count
        if self._root:
            self._root.after(0, self._update_status)

    def get_state(self) -> QuickBarState:
        """获取当前状态快照。"""
        return QuickBarState(
            visible=self._visible,
            mode=self._mode,
            active_time=self._active_time,
            pending_count=self._pending_count,
            history_count=len(self._history),
        )

    def get_history(self, limit: int = 20) -> list[QuickBarEntry]:
        """获取命令历史。"""
        with self._lock:
            return list(self._history[-limit:])

    def clear_history(self) -> None:
        """清空命令历史。"""
        with self._lock:
            self._history.clear()
        if self._root and self._visible:
            self._root.after(0, self._update_history_display)

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════════

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_visible(self) -> bool:
        return self._visible

    @property
    def mode(self) -> str:
        return self._mode

    # ═══════════════════════════════════════════════════════
    # GUI Loop (运行在独立线程)
    # ═══════════════════════════════════════════════════════

    def _gui_loop(self) -> None:
        """主 GUI 事件循环。"""
        try:
            self._root = tk.Tk()
            self._root.title("Sclerotium OS")
            self._root.overrideredirect(True)  # 无边框
            self._root.attributes("-topmost", True)
            self._root.withdraw()  # 初始隐藏

            # 配置窗口
            self._root.configure(bg=self.BG_COLOR)

            # 设置窗口位置 (屏幕中央偏上)
            screen_w = self._root.winfo_screenwidth()
            screen_h = self._root.winfo_screenheight()
            x = (screen_w - self.WIDTH) // 2
            y = int(screen_h * 0.15)
            self._root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

            self._build_ui()
            self._register_hotkey()
            self._root.bind("<FocusOut>", lambda e: self.hide())
            self._root.bind("<Escape>", lambda e: self.hide())

            # 启动事件循环 (每秒检查一次运行状态)
            def _check_running() -> None:
                if self._running and self._root:
                    self._root.after(100, _check_running)
                elif not self._running and self._root:
                    try:
                        self._unregister_hotkey()
                        self._root.destroy()
                    except Exception:
                        pass

            self._root.after(100, _check_running)
            self._root.mainloop()
        except Exception as e:
            logger.error("QuickBar GUI error: %s", e)
        finally:
            self._root = None

    def _build_ui(self) -> None:
        """构建 GUI 组件。"""
        assert self._root is not None

        # 主容器
        self._main_frame = tk.Frame(self._root, bg=self.BG_COLOR, bd=1, relief="solid")
        self._main_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # 标题栏
        title_frame = tk.Frame(self._main_frame, bg=self.ACCENT_COLOR, height=28)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame,
            text="🧬 Sclerotium OS",
            bg=self.ACCENT_COLOR,
            fg=self.FG_COLOR,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(side="left", padx=10, pady=2)

        close_btn = tk.Label(
            title_frame,
            text="✕",
            bg=self.ACCENT_COLOR,
            fg=self.FG_COLOR,
            font=("Segoe UI", 12),
            cursor="hand2",
        )
        close_btn.pack(side="right", padx=10)
        close_btn.bind("<Button-1>", lambda e: self.hide())

        # 历史区域
        history_frame = tk.Frame(self._main_frame, bg=self.BG_COLOR)
        history_frame.pack(fill="both", expand=True, padx=8, pady=(4, 0))

        self._history_text = tk.Text(
            history_frame,
            bg=self.BG_COLOR,
            fg=self.FG_COLOR,
            font=("Consolas", 9),
            wrap="word",
            state="disabled",
            bd=0,
            highlightthickness=0,
            cursor="arrow",
        )
        self._history_text.pack(fill="both", expand=True)

        # 输入区域
        input_frame = tk.Frame(self._main_frame, bg=self.INPUT_BG, height=self.INPUT_HEIGHT)
        input_frame.pack(fill="x", padx=8, pady=(4, 0))
        input_frame.pack_propagate(False)

        self._input_var = tk.StringVar()
        self._input_entry = tk.Entry(
            input_frame,
            textvariable=self._input_var,
            bg=self.INPUT_BG,
            fg=self.FG_COLOR,
            insertbackground=self.FG_COLOR,
            font=("Segoe UI", 12),
            bd=0,
            highlightthickness=0,
        )
        self._input_entry.pack(fill="both", expand=True, padx=12, pady=8)
        self._input_entry.insert(0, "")
        self._input_entry.bind("<Return>", self._on_submit_handler)
        self._input_entry.bind("<Up>", self._on_arrow_up)

        # 设置占位符文本
        self._input_entry.insert(0, "说点什么... (Enter 发送, Esc 关闭)")
        self._input_entry.configure(fg=self.DIM_COLOR)
        self._input_entry.bind("<FocusIn>", self._on_focus_in)
        self._input_entry.bind("<FocusOut>", self._on_focus_out)

        # 状态栏
        self._status_label = tk.Label(
            self._main_frame,
            text="",
            bg=self.STATUS_BG,
            fg=self.FG_COLOR,
            font=("Segoe UI", 8),
            anchor="w",
            height=1,
        )
        self._status_label.pack(fill="x", padx=8, pady=(4, 8))

        self._update_status()

    # ═══════════════════════════════════════════════════════
    # 热键注册 (Windows API)
    # ═══════════════════════════════════════════════════════

    def _register_hotkey(self) -> None:
        """向 Windows 注册全局热键。"""
        if self._hotkey_registered:
            return
        try:
            assert self._root is not None
            hwnd = int(self._root.frame(), 16)

            user32 = ctypes.windll.user32
            result = user32.RegisterHotKey(
                ctypes.wintypes.HWND(hwnd),
                HOTKEY_ID_ALT_SPACE,
                self._hotkey_mod,
                self._hotkey_key,
            )
            if result:
                self._hotkey_registered = True
                # 绑定 WM_HOTKEY 消息处理
                self._root.bind("<<Hotkey-Alt-Space>>", self._on_hotkey)
                # 使用 after 轮询 Windows 消息
                self._root.after(50, self._poll_hotkey)
                logger.debug("Hotkey Alt+Space registered")
            else:
                logger.warning("RegisterHotKey failed — hotkey may be in use")
        except Exception as e:
            logger.warning("Hotkey registration failed: %s", e)

    def _unregister_hotkey(self) -> None:
        """注销全局热键。"""
        if not self._hotkey_registered:
            return
        try:
            user32 = ctypes.windll.user32
            user32.UnregisterHotKey(None, HOTKEY_ID_ALT_SPACE)
            self._hotkey_registered = False
            logger.debug("Hotkey Alt+Space unregistered")
        except Exception as e:
            logger.debug("Hotkey unregister error: %s", e)

    def _poll_hotkey(self) -> None:
        """轮询 Windows 热键消息。"""
        try:
            if self._running and self._hotkey_registered and self._root:
                # 使用 PeekMessage 检测 WM_HOTKEY
                user32 = ctypes.windll.user32
                msg = ctypes.wintypes.MSG()
                if user32.PeekMessageW(
                    ctypes.byref(msg),
                    ctypes.wintypes.HWND(int(self._root.frame(), 16)),
                    WM_HOTKEY,
                    WM_HOTKEY,
                    1,  # PM_REMOVE
                ):
                    if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID_ALT_SPACE:
                        self.toggle()
                self._root.after(50, self._poll_hotkey)
        except Exception:
            pass

    def _on_hotkey(self, event: tk.Event | None = None) -> None:
        """热键回调 — 切换浮窗可见性。"""
        self.toggle()

    # ═══════════════════════════════════════════════════════
    # Show / Hide
    # ═══════════════════════════════════════════════════════

    def _do_show(self) -> None:
        """实际显示浮窗 (在 GUI 线程中执行)。"""
        if not self._root:
            return
        self._visible = True
        self._root.deiconify()
        self._root.lift()
        self._root.focus_force()
        if self._input_entry:
            self._input_entry.delete(0, "end")
            self._input_entry.configure(fg=self.FG_COLOR)
            self._input_entry.focus_set()
        self._update_status()
        self._update_history_display()

    def _do_hide(self) -> None:
        """实际隐藏浮窗 (在 GUI 线程中执行)。"""
        if not self._root:
            return
        self._visible = False
        self._root.withdraw()
        # 释放焦点, 不打扰用户
        self._root.after(50, lambda: self._root.focus_lastfor() if self._root else None)

    # ═══════════════════════════════════════════════════════
    # Input Handling
    # ═══════════════════════════════════════════════════════

    def _on_submit_handler(self, event: tk.Event | None = None) -> None:
        """用户按回车提交命令。"""
        if not self._input_var:
            return
        text = self._input_var.get().strip()
        if not text or text == "说点什么... (Enter 发送, Esc 关闭)":
            return

        # 添加用户输入到历史
        user_entry = QuickBarEntry(text=text, is_response=False)
        with self._lock:
            self._history.append(user_entry)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        # 清空输入
        self._input_var.set("")
        self._update_history_display()

        # 调用提交回调
        if self._on_submit:
            try:
                response = self._on_submit(text)
                if response:
                    self.add_response(response)
            except Exception as e:
                logger.error("QuickBar submit callback error: %s", e)
                self.add_response(f"❌ 错误: {e}")

    def _on_arrow_up(self, event: tk.Event | None = None) -> None:
        """上箭头: 调出上一条输入。"""
        with self._lock:
            user_inputs = [e for e in self._history if not e.is_response]
        if user_inputs and self._input_var is not None:
            self._input_var.set(user_inputs[-1].text)
            if self._input_entry:
                self._input_entry.configure(fg=self.FG_COLOR)
                self._input_entry.icursor("end")

    def _on_focus_in(self, event: tk.Event | None = None) -> None:
        """输入框获得焦点 — 清除占位符。"""
        if self._input_entry and self._input_var:
            current = self._input_var.get()
            if current == "说点什么... (Enter 发送, Esc 关闭)":
                self._input_var.set("")
                self._input_entry.configure(fg=self.FG_COLOR)

    def _on_focus_out(self, event: tk.Event | None = None) -> None:
        """输入框失去焦点 — 恢复占位符。"""
        if self._input_entry and self._input_var:
            if not self._input_var.get().strip():
                self._input_var.set("说点什么... (Enter 发送, Esc 关闭)")
                self._input_entry.configure(fg=self.DIM_COLOR)

    # ═══════════════════════════════════════════════════════
    # Display Updates
    # ═══════════════════════════════════════════════════════

    def _update_history_display(self) -> None:
        """刷新历史显示区域。"""
        if not self._history_text:
            return
        self._history_text.configure(state="normal")
        self._history_text.delete("1.0", "end")

        with self._lock:
            entries = list(self._history[-30:])  # 最多显示 30 条

        for entry in entries:
            if entry.is_response:
                tag = "response"
                prefix = "🧬 "
                color = "#88ccff"
            else:
                tag = "user"
                prefix = "👤 "
                color = "#e0e0e0"

            time_str = time.strftime("%H:%M", time.localtime(entry.timestamp))
            self._history_text.insert("end", f"{prefix}[{time_str}] ", ("dim",))
            self._history_text.insert("end", f"{entry.text}\n", (tag,))

        # 配置标签样式
        self._history_text.tag_configure("user", foreground=self.FG_COLOR)
        self._history_text.tag_configure("response", foreground="#88ccff")
        self._history_text.tag_configure("dim", foreground=self.DIM_COLOR)

        self._history_text.configure(state="disabled")
        self._history_text.see("end")

    def _update_status(self) -> None:
        """刷新状态栏。"""
        if not self._status_label:
            return

        mode_icons = {
            "work": "💼",
            "sleep": "😴",
            "game": "🎮",
            "meeting": "🤝",
            "creative": "🎨",
        }
        icon = mode_icons.get(self._mode, "🧬")
        parts = [f"{icon} {self._mode.capitalize()} 模式"]

        if self._active_time:
            parts.append(f"活跃 {self._active_time}")

        if self._pending_count > 0:
            parts.append(f"{self._pending_count} 个待处理")

        parts.append("Alt+Space 切换 | Esc 关闭 | ↑ 历史")

        self._status_label.configure(text="  │  ".join(parts))
