"""Input Simulator — 键盘鼠标精确控制。

章鱼触手的"肌肉运动" — 键盘输入、鼠标移动、拖拽、快捷键。

三通道策略:
  1. pyautogui (高优先级, 跨平台, 功能全)
  2. ctypes SendInput (Windows 原生, 零依赖)
  3. win32api keybd_event (Win32 API 回退)

参考: ClawdCursor input controller, UIA-X input tools
"""

from __future__ import annotations

import ctypes
import logging
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("sclerotium.input")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class InputAction:
    """一次输入操作 (不可变)。"""
    action_type: str           # click/type/hotkey/move/drag/scroll/press
    params: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class InputResult:
    """输入操作结果 (不可变)。"""
    success: bool
    action: str = ""
    detail: str = ""
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════
# 虚拟键码映射
# ═══════════════════════════════════════════════════════════════

# Windows 虚拟键码常量 (部分)
_VK_CODES: dict[str, int] = {
    "backspace": 0x08, "tab": 0x09, "enter": 0x0D, "shift": 0x10,
    "ctrl": 0x11, "alt": 0x12, "pause": 0x13, "capslock": 0x14,
    "esc": 0x1B, "escape": 0x1B, "space": 0x20, "pageup": 0x21,
    "pagedown": 0x22, "end": 0x23, "home": 0x24,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "printscreen": 0x2C, "insert": 0x2D, "delete": 0x2E,
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
    "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45,
    "f": 0x46, "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A,
    "k": 0x4B, "l": 0x4C, "m": 0x4D, "n": 0x4E, "o": 0x4F,
    "p": 0x50, "q": 0x51, "r": 0x52, "s": 0x53, "t": 0x54,
    "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58, "y": 0x59, "z": 0x5A,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "numlock": 0x90, "scrolllock": 0x91,
    "volume_mute": 0xAD, "volume_down": 0xAE, "volume_up": 0xAF,
    "media_next": 0xB0, "media_prev": 0xB1, "media_stop": 0xB2,
    "media_play": 0xB3,
}


# ═══════════════════════════════════════════════════════════════
# InputSimulator
# ═══════════════════════════════════════════════════════════════

class InputSimulator:
    """键盘和鼠标输入模拟器。

    使用方式:
        sim = InputSimulator()
        sim.click(100, 200)
        sim.type_text("Hello, World!")
        sim.hotkey("ctrl", "c")
    """

    # 鼠标事件常量
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_MIDDLEDOWN = 0x0020
    MOUSEEVENTF_MIDDLEUP = 0x0040
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_WHEEL = 0x0800

    # 键盘事件常量
    KEYEVENTF_KEYDOWN = 0x0000
    KEYEVENTF_KEYUP = 0x0002

    def __init__(self) -> None:
        self._pyautogui_ok = False
        self._ctypes_ok = False
        self._lock = threading.Lock()

        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            self._pyautogui_ok = True
        except ImportError:
            pass

        # ctypes 始终可用 (Windows)
        try:
            ctypes.windll.user32
            self._ctypes_ok = True
        except Exception:
            pass

        self._action_history: list[InputAction] = []

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════

    @property
    def available(self) -> bool:
        return self._pyautogui_ok or self._ctypes_ok

    @property
    def backend(self) -> str:
        if self._pyautogui_ok:
            return "pyautogui"
        if self._ctypes_ok:
            return "ctypes"
        return "none"

    # ═══════════════════════════════════════════════════════
    # 鼠标操作
    # ═══════════════════════════════════════════════════════

    def click(self, x: int, y: int, button: str = "left") -> InputResult:
        """在屏幕坐标 (x, y) 处点击。

        Args:
            x, y: 屏幕坐标
            button: 'left' / 'right' / 'middle'
        """
        start = time.time()

        try:
            import pyautogui
            pyautogui.click(x, y, button=button)
            dur = (time.time() - start) * 1000
            self._record("click", {"x": x, "y": y, "button": button})
            return InputResult(success=True, action="click",
                               detail=f"{button} at ({x},{y})", duration_ms=dur)
        except Exception:
            # ctypes 回退
            return self._click_ctypes(x, y, button)

    def double_click(self, x: int, y: int) -> InputResult:
        """双击。"""
        start = time.time()
        try:
            import pyautogui
            pyautogui.doubleClick(x, y)
            dur = (time.time() - start) * 1000
            self._record("double_click", {"x": x, "y": y})
            return InputResult(success=True, action="double_click",
                               detail=f"({x},{y})", duration_ms=dur)
        except Exception:
            r1 = self._click_ctypes(x, y, "left")
            if r1.success:
                time.sleep(0.05)
                r2 = self._click_ctypes(x, y, "left")
                return r2
            return r1

    def right_click(self, x: int, y: int) -> InputResult:
        """右键点击。"""
        return self.click(x, y, button="right")

    def move(self, x: int, y: int, duration: float = 0.2) -> InputResult:
        """移动鼠标到 (x, y)。"""
        start = time.time()
        try:
            import pyautogui
            pyautogui.moveTo(x, y, duration=duration)
            dur = (time.time() - start) * 1000
            self._record("move", {"x": x, "y": y})
            return InputResult(success=True, action="move",
                               detail=f"({x},{y})", duration_ms=dur)
        except Exception:
            try:
                ctypes.windll.user32.SetCursorPos(x, y)
                dur = (time.time() - start) * 1000
                self._record("move", {"x": x, "y": y})
                return InputResult(success=True, action="move",
                                   detail=f"ctypes ({x},{y})", duration_ms=dur)
            except Exception as e:
                return InputResult(success=False, action="move", detail=str(e))

    def drag(
        self,
        x1: int, y1: int,
        x2: int, y2: int,
        duration: float = 0.5,
    ) -> InputResult:
        """从 (x1, y1) 拖拽到 (x2, y2)。"""
        start = time.time()
        try:
            import pyautogui
            pyautogui.moveTo(x1, y1)
            pyautogui.drag(x2 - x1, y2 - y1, duration=duration)
            dur = (time.time() - start) * 1000
            self._record("drag", {"from": (x1, y1), "to": (x2, y2)})
            return InputResult(success=True, action="drag",
                               detail=f"({x1},{y1}) → ({x2},{y2})", duration_ms=dur)
        except Exception as e:
            return InputResult(success=False, action="drag", detail=str(e))

    def scroll(self, clicks: int, x: int | None = None, y: int | None = None) -> InputResult:
        """滚轮滚动。

        Args:
            clicks: 正数向上, 负数向下
            x, y: 鼠标位置 (可选)
        """
        start = time.time()
        try:
            import pyautogui
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
            pyautogui.scroll(clicks)
            dur = (time.time() - start) * 1000
            self._record("scroll", {"clicks": clicks})
            return InputResult(success=True, action="scroll",
                               detail=f"{clicks} clicks", duration_ms=dur)
        except Exception as e:
            return InputResult(success=False, action="scroll", detail=str(e))

    # ═══════════════════════════════════════════════════════
    # 键盘操作
    # ═══════════════════════════════════════════════════════

    def type_text(self, text: str, interval: float = 0.02) -> InputResult:
        """输入文本 (模拟键盘逐字输入)。

        Args:
            text: 要输入的文本
            interval: 字符间延迟 (秒)
        """
        if not text:
            return InputResult(success=False, action="type_text", detail="Empty text")

        start = time.time()
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=interval)
            dur = (time.time() - start) * 1000
            self._record("type_text", {"text": text[:50], "len": len(text)})
            return InputResult(success=True, action="type_text",
                               detail=f"{len(text)} chars", duration_ms=dur)
        except Exception:
            # ctypes 回退逐字输入
            return self._type_text_ctypes(text, interval)

    def press(self, key: str) -> InputResult:
        """按下并释放一个键。"""
        start = time.time()
        try:
            import pyautogui
            pyautogui.press(key)
            dur = (time.time() - start) * 1000
            self._record("press", {"key": key})
            return InputResult(success=True, action="press",
                               detail=key, duration_ms=dur)
        except Exception:
            return self._press_key_ctypes(key)

    def key_down(self, key: str) -> InputResult:
        """按下键 (不释放)。"""
        start = time.time()
        try:
            import pyautogui
            pyautogui.keyDown(key)
            dur = (time.time() - start) * 1000
            return InputResult(success=True, action="key_down",
                               detail=key, duration_ms=dur)
        except Exception as e:
            return InputResult(success=False, action="key_down", detail=str(e))

    def key_up(self, key: str) -> InputResult:
        """释放键。"""
        start = time.time()
        try:
            import pyautogui
            pyautogui.keyUp(key)
            dur = (time.time() - start) * 1000
            return InputResult(success=True, action="key_up",
                               detail=key, duration_ms=dur)
        except Exception as e:
            return InputResult(success=False, action="key_up", detail=str(e))

    def hotkey(self, *keys: str) -> InputResult:
        """同时按下多个键 (如 ctrl+c, alt+tab)。

        Args:
            *keys: 键序列 (如 "ctrl", "c")
        """
        if not keys:
            return InputResult(success=False, action="hotkey", detail="No keys")

        start = time.time()
        try:
            import pyautogui
            pyautogui.hotkey(*keys)
            dur = (time.time() - start) * 1000
            combo = "+".join(keys)
            self._record("hotkey", {"keys": combo})
            return InputResult(success=True, action="hotkey",
                               detail=combo, duration_ms=dur)
        except Exception:
            return self._hotkey_ctypes(keys)

    # ═══════════════════════════════════════════════════════
    # 便捷组合
    # ═══════════════════════════════════════════════════════

    def copy(self) -> InputResult:
        """Ctrl+C 复制。"""
        return self.hotkey("ctrl", "c")

    def paste(self) -> InputResult:
        """Ctrl+V 粘贴。"""
        return self.hotkey("ctrl", "v")

    def cut(self) -> InputResult:
        """Ctrl+X 剪切。"""
        return self.hotkey("ctrl", "x")

    def select_all(self) -> InputResult:
        """Ctrl+A 全选。"""
        return self.hotkey("ctrl", "a")

    def undo(self) -> InputResult:
        """Ctrl+Z 撤销。"""
        return self.hotkey("ctrl", "z")

    def enter(self) -> InputResult:
        """回车。"""
        return self.press("enter")

    def tab(self) -> InputResult:
        """Tab。"""
        return self.press("tab")

    # ═══════════════════════════════════════════════════════
    # 历史
    # ═══════════════════════════════════════════════════════

    def get_history(self, limit: int = 20) -> list[InputAction]:
        """获取输入操作历史。"""
        return self._action_history[-limit:]

    def clear_history(self) -> None:
        """清空历史。"""
        self._action_history.clear()

    # ═══════════════════════════════════════════════════════
    # Internal — ctypes 回退
    # ═══════════════════════════════════════════════════════

    def _click_ctypes(self, x: int, y: int, button: str) -> InputResult:
        """ctypes SendInput 点击。"""
        start = time.time()
        try:
            ctypes.windll.user32.SetCursorPos(x, y)

            if button == "right":
                ctypes.windll.user32.mouse_event(self.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(self.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            elif button == "middle":
                ctypes.windll.user32.mouse_event(self.MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(self.MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)
            else:
                ctypes.windll.user32.mouse_event(self.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                ctypes.windll.user32.mouse_event(self.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

            dur = (time.time() - start) * 1000
            self._record("click", {"x": x, "y": y, "button": button})
            return InputResult(success=True, action="click",
                               detail=f"ctypes {button} ({x},{y})", duration_ms=dur)
        except Exception as e:
            return InputResult(success=False, action="click", detail=str(e))

    def _type_text_ctypes(self, text: str, interval: float) -> InputResult:
        """ctypes 逐字输入。"""
        start = time.time()
        try:
            for ch in text:
                vk = _char_to_vk(ch)
                if vk is not None:
                    # 处理 shift 修饰
                    if ch.isupper() or ch in "~!@#$%^&*()_+{}|:\"<>?":
                        ctypes.windll.user32.keybd_event(0x10, 0, 0, 0)  # shift down

                    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)  # key down
                    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)  # key up

                    if ch.isupper() or ch in "~!@#$%^&*()_+{}|:\"<>?":
                        ctypes.windll.user32.keybd_event(0x10, 0, 2, 0)  # shift up

                time.sleep(interval)

            dur = (time.time() - start) * 1000
            return InputResult(success=True, action="type_text",
                               detail=f"ctypes {len(text)} chars", duration_ms=dur)
        except Exception as e:
            return InputResult(success=False, action="type_text", detail=str(e))

    def _press_key_ctypes(self, key: str) -> InputResult:
        """ctypes 按键。"""
        start = time.time()
        vk = _VK_CODES.get(key.lower())
        if vk is None:
            vk = _char_to_vk(key)
        if vk is None:
            return InputResult(success=False, action="press",
                               detail=f"Unknown key: {key}")

        try:
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
            dur = (time.time() - start) * 1000
            return InputResult(success=True, action="press",
                               detail=f"ctypes {key}", duration_ms=dur)
        except Exception as e:
            return InputResult(success=False, action="press", detail=str(e))

    def _hotkey_ctypes(self, keys: tuple[str, ...]) -> InputResult:
        """ctypes 组合键。"""
        start = time.time()
        try:
            # 按下所有修饰键
            for key in keys:
                vk = _VK_CODES.get(key.lower())
                if vk:
                    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)

            # 释放 (逆向)
            for key in reversed(keys):
                vk = _VK_CODES.get(key.lower())
                if vk:
                    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)

            dur = (time.time() - start) * 1000
            combo = "+".join(keys)
            return InputResult(success=True, action="hotkey",
                               detail=f"ctypes {combo}", duration_ms=dur)
        except Exception as e:
            return InputResult(success=False, action="hotkey", detail=str(e))

    def _record(self, action_type: str, params: dict[str, Any]) -> None:
        """记录操作历史。"""
        self._action_history.append(InputAction(
            action_type=action_type,
            params=params,
        ))
        if len(self._action_history) > 500:
            self._action_history = self._action_history[-500:]


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def _char_to_vk(ch: str) -> int | None:
    """将字符映射到虚拟键码。"""
    if not ch:
        return None
    # 字母
    if 'a' <= ch.lower() <= 'z':
        return ord(ch.upper())
    # 数字
    if '0' <= ch <= '9':
        return ord(ch)
    # 特殊字符映射
    char_map = {
        ' ': 0x20, '\n': 0x0D, '\t': 0x09, '\b': 0x08,
        '.': 0xBE, ',': 0xBC, '/': 0xBF, '\\': 0xDC,
        ';': 0xBA, '\'': 0xDE, '[': 0xDB, ']': 0xDD,
        '-': 0xBD, '=': 0xBB, '`': 0xC0,
    }
    return char_map.get(ch)
