"""Windows UIA Controller — 章鱼触手运动核心。

通过 Windows Accessibility API (UIA/MSAA) 实现结构化桌面操控:
  - 窗口查找 (标题/类名/进程名)
  - 元素定位 (name/control_type/automation_id/class_name)
  - 点击/双击/右键
  - 文本输入/读取
  - 截图 (指定窗口或全屏)

三通道策略:
  1. pywinauto + uiautomation (首选, 结构化访问)
  2. win32gui + win32api (回退, Win32 API)
  3. ctypes SendInput (终极回退, 原始输入)

参考: UIA-X MCP, ClawdCursor 94-tool, NativeDevTools MCP
"""

from __future__ import annotations

import ctypes
import logging
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("sclerotium.uia")


# ═══════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════

class ClickType(Enum):
    """点击类型。"""
    LEFT = "left"
    RIGHT = "right"
    DOUBLE = "double"
    MIDDLE = "middle"


@dataclass(frozen=True)
class WindowInfo:
    """窗口信息 (不可变)。"""
    title: str = ""
    process_name: str = ""
    process_id: int = 0
    hwnd: int = 0
    class_name: str = ""
    rect: tuple[int, int, int, int] = (0, 0, 0, 0)  # left, top, right, bottom
    is_visible: bool = True
    is_minimized: bool = False
    is_maximized: bool = False

    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]

    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]


@dataclass(frozen=True)
class UIElement:
    """UI 元素 (不可变)。"""
    name: str = ""
    control_type: str = ""
    automation_id: str = ""
    class_name: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    value: str = ""
    is_enabled: bool = True
    is_visible: bool = True
    hwnd: int = 0

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)


@dataclass(frozen=True)
class AutomationResult:
    """自动化操作结果 (不可变)。"""
    success: bool
    action: str = ""
    target: str = ""
    detail: str = ""
    timestamp: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# UIAController
# ═══════════════════════════════════════════════════════════════

class UIAController:
    """Windows UI Automation 控制器。

    三通道策略:
      1. pywinauto/UIA — 结构化元素访问
      2. win32gui — Win32 API 回退
      3. ctypes SendInput — 原始输入回退

    使用方式:
        ctrl = UIAController()
        win = ctrl.find_window(title="记事本")
        if win:
            ctrl.type_text("Hello, World!")
    """

    def __init__(self) -> None:
        self._pywinauto_ok = False
        self._uia_ok = False
        self._win32_ok = False
        self._lock = threading.Lock()

        # 探测可用后端
        try:
            import pywinauto
            self._pywinauto_ok = True
        except ImportError:
            pass

        try:
            import uiautomation
            self._uia_ok = True
        except ImportError:
            pass

        try:
            import win32gui
            import win32api
            self._win32_ok = True
        except ImportError:
            pass

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════

    @property
    def available(self) -> bool:
        """至少有一个后端可用。"""
        return self._pywinauto_ok or self._uia_ok or self._win32_ok

    @property
    def backend(self) -> str:
        """当前使用的后端。"""
        if self._pywinauto_ok:
            return "pywinauto"
        if self._uia_ok:
            return "uiautomation"
        if self._win32_ok:
            return "win32"
        return "none"

    # ═══════════════════════════════════════════════════════
    # 窗口操作
    # ═══════════════════════════════════════════════════════

    def find_window(
        self,
        title: str = "",
        class_name: str = "",
        process_name: str = "",
    ) -> WindowInfo | None:
        """查找匹配的窗口。

        Args:
            title: 窗口标题 (支持部分匹配)
            class_name: 窗口类名
            process_name: 进程名 (如 "notepad.exe")

        Returns:
            WindowInfo 或 None
        """
        if self._win32_ok:
            return self._find_window_win32(title, class_name, process_name)
        return None

    def get_active_window(self) -> WindowInfo | None:
        """获取当前活动窗口。"""
        if self._win32_ok:
            return self._get_active_win32()
        return None

    def get_all_windows(self, visible_only: bool = True) -> list[WindowInfo]:
        """列举所有窗口。"""
        if self._win32_ok:
            return self._enum_windows_win32(visible_only)
        return []

    def set_foreground(self, window: WindowInfo) -> bool:
        """将窗口设为前台。"""
        if self._win32_ok and window.hwnd:
            try:
                import win32gui
                import win32con
                win32gui.SetForegroundWindow(window.hwnd)
                return True
            except Exception:
                pass

        # ctypes 回退
        if window.hwnd:
            try:
                ctypes.windll.user32.SetForegroundWindow(window.hwnd)
                return True
            except Exception:
                pass
        return False

    # ═══════════════════════════════════════════════════════
    # 元素操作
    # ═══════════════════════════════════════════════════════

    def find_element(
        self,
        name: str = "",
        control_type: str = "",
        automation_id: str = "",
    ) -> UIElement | None:
        """在当前活动窗口中查找 UI 元素。

        Args:
            name: 元素名称
            control_type: 控件类型 (Button/Edit/ListItem...)
            automation_id: AutomationId
        """
        if self._uia_ok:
            return self._find_element_uia(name, control_type, automation_id)
        return None

    def click(
        self,
        element: UIElement | None = None,
        x: int = 0,
        y: int = 0,
        click_type: ClickType = ClickType.LEFT,
    ) -> AutomationResult:
        """点击指定位置或元素。

        如果提供 element, 点击元素中心; 否则点击 (x, y)。
        """
        if element:
            cx, cy = element.center
        else:
            cx, cy = x, y

        if cx == 0 and cy == 0:
            return AutomationResult(
                success=False,
                action="click",
                detail="No target coordinates",
            )

        try:
            import pyautogui
            pyautogui.FAILSAFE = False

            if click_type == ClickType.RIGHT:
                pyautogui.rightClick(cx, cy)
            elif click_type == ClickType.DOUBLE:
                pyautogui.doubleClick(cx, cy)
            elif click_type == ClickType.MIDDLE:
                pyautogui.middleClick(cx, cy)
            else:
                pyautogui.click(cx, cy)

            return AutomationResult(
                success=True,
                action=f"click_{click_type.value}",
                target=f"({cx}, {cy})",
                detail=f"{click_type.value} click at ({cx}, {cy})",
            )
        except Exception as e:
            # pyautogui 回退失败, 尝试 ctypes SendInput
            return self._click_ctypes(cx, cy, click_type)

    def type_text(
        self,
        text: str,
        interval: float = 0.02,
    ) -> AutomationResult:
        """输入文本到当前焦点元素。

        Args:
            text: 要输入的文本
            interval: 字符间延迟 (秒)
        """
        if not text:
            return AutomationResult(
                success=False,
                action="type_text",
                detail="Empty text",
            )

        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            pyautogui.typewrite(text, interval=interval)
            return AutomationResult(
                success=True,
                action="type_text",
                target=f"{len(text)} chars",
                detail=text[:50],
            )
        except Exception as e:
            return AutomationResult(
                success=False,
                action="type_text",
                detail=str(e),
            )

    def read_text(self, element: UIElement | None = None) -> str:
        """读取 UI 元素的文本内容。

        Args:
            element: 目标元素 (可选, 默认读取活动窗口焦点元素)

        Returns:
            文本内容 (可能为空)
        """
        if element and element.value:
            return element.value

        # 尝试通过 UIA 读取焦点元素文本
        if self._uia_ok:
            try:
                import uiautomation as uia
                focused = uia.GetFocusedControl()
                if focused:
                    name = getattr(focused, 'Name', '')
                    value = getattr(focused, 'ValueValue', '') or getattr(focused, 'LegacyIAccessibleValue', '')
                    return value or name
            except Exception:
                pass

        return ""

    def take_screenshot(
        self,
        window: WindowInfo | None = None,
        region: tuple[int, int, int, int] | None = None,
    ) -> bytes | None:
        """截取屏幕或指定窗口。

        Args:
            window: 目标窗口 (可选)
            region: 区域 (left, top, right, bottom)

        Returns:
            PNG 格式图片字节, 失败返回 None
        """
        try:
            from PIL import ImageGrab

            if window and window.hwnd:
                try:
                    import win32gui
                    rect = win32gui.GetWindowRect(window.hwnd)
                    img = ImageGrab.grab(bbox=rect)
                except Exception:
                    img = ImageGrab.grab(bbox=region)
            elif region:
                img = ImageGrab.grab(bbox=region)
            else:
                img = ImageGrab.grab()

            import io
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except Exception as e:
            logger.warning("Screenshot failed: %s", e)
            return None

    # ═══════════════════════════════════════════════════════
    # 便捷方法
    # ═══════════════════════════════════════════════════════

    def click_text(self, text: str) -> AutomationResult:
        """在屏幕上查找文本并点击 (OCR 定位 — 需 ScreenAgent 配合)。"""
        # 此方法需要 OCR, 通过 ScreenAgent 实现
        return AutomationResult(
            success=False,
            action="click_text",
            target=text,
            detail="Requires ScreenAgent OCR integration",
        )

    def press_key(self, key: str, modifiers: list[str] | None = None) -> AutomationResult:
        """按下键盘按键 (可带修饰键)。

        Args:
            key: 主键 (如 'c', 'v', 'tab', 'enter')
            modifiers: 修饰键列表 (如 ['ctrl'], ['alt', 'shift'])
        """
        try:
            import pyautogui
            pyautogui.FAILSAFE = False

            if modifiers:
                pyautogui.hotkey(*modifiers, key)
            else:
                pyautogui.press(key)

            return AutomationResult(
                success=True,
                action="press_key",
                target=key,
                detail=f"Pressed {'+'.join(modifiers or [])}+{key}" if modifiers else f"Pressed {key}",
            )
        except Exception as e:
            return AutomationResult(
                success=False,
                action="press_key",
                target=key,
                detail=str(e),
            )

    # ═══════════════════════════════════════════════════════
    # Internal — Win32 窗口操作
    # ═══════════════════════════════════════════════════════

    def _find_window_win32(
        self, title: str, class_name: str, process_name: str
    ) -> WindowInfo | None:
        """通过 win32gui 查找窗口。"""
        import win32gui
        import win32process

        result: list[WindowInfo] = []

        def _enum(hwnd: int, _ctx: Any) -> bool:
            try:
                wt = win32gui.GetWindowText(hwnd)
                wc = win32gui.GetClassName(hwnd)

                # 标题匹配 (部分)
                if title and title.lower() not in wt.lower():
                    return True
                # 类名匹配
                if class_name and class_name.lower() not in wc.lower():
                    return True
                # 进程名匹配
                if process_name:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    try:
                        import psutil
                        pn = psutil.Process(pid).name().lower()
                        if process_name.lower() not in pn:
                            return True
                    except Exception:
                        return True

                rect = win32gui.GetWindowRect(hwnd)
                result.append(WindowInfo(
                    title=wt,
                    class_name=wc,
                    hwnd=hwnd,
                    rect=rect,
                    is_visible=win32gui.IsWindowVisible(hwnd),
                ))
            except Exception:
                pass
            return True

        win32gui.EnumWindows(_enum, None)
        return result[0] if result else None

    def _get_active_win32(self) -> WindowInfo | None:
        """通过 win32gui 获取活动窗口。"""
        try:
            import win32gui
            import win32process
            hwnd = win32gui.GetForegroundWindow()
            wt = win32gui.GetWindowText(hwnd)
            wc = win32gui.GetClassName(hwnd)
            rect = win32gui.GetWindowRect(hwnd)

            # 获取进程名
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            pn = ""
            try:
                import psutil
                pn = psutil.Process(pid).name()
            except Exception:
                pass

            # 窗口状态
            import win32con
            placement = win32gui.GetWindowPlacement(hwnd)
            minimized = placement[1] == win32con.SW_SHOWMINIMIZED
            maximized = placement[1] == win32con.SW_SHOWMAXIMIZED

            return WindowInfo(
                title=wt,
                class_name=wc,
                process_name=pn,
                process_id=pid,
                hwnd=hwnd,
                rect=rect,
                is_visible=win32gui.IsWindowVisible(hwnd),
                is_minimized=minimized,
                is_maximized=maximized,
            )
        except Exception:
            return None

    def _enum_windows_win32(self, visible_only: bool = True) -> list[WindowInfo]:
        """列举所有窗口。"""
        import win32gui
        import win32process

        result: list[WindowInfo] = []

        def _enum(hwnd: int, _ctx: Any) -> bool:
            try:
                if visible_only and not win32gui.IsWindowVisible(hwnd):
                    return True
                wt = win32gui.GetWindowText(hwnd)
                if not wt.strip():
                    return True  # 跳过无标题窗口

                wc = win32gui.GetClassName(hwnd)
                rect = win32gui.GetWindowRect(hwnd)
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                pn = ""
                try:
                    import psutil
                    pn = psutil.Process(pid).name()
                except Exception:
                    pass

                result.append(WindowInfo(
                    title=wt,
                    class_name=wc,
                    process_name=pn,
                    process_id=pid,
                    hwnd=hwnd,
                    rect=rect,
                    is_visible=True,
                ))
            except Exception:
                pass
            return True

        win32gui.EnumWindows(_enum, None)
        return result

    # ═══════════════════════════════════════════════════════
    # Internal — UIA 元素操作
    # ═══════════════════════════════════════════════════════

    def _find_element_uia(
        self, name: str, control_type: str, automation_id: str
    ) -> UIElement | None:
        """通过 uiautomation 查找元素。支持精确匹配 + 模糊匹配 + 深度递归搜索。"""
        try:
            import uiautomation as uia

            conditions = []
            if name:
                conditions.append(uia.Name == name)
            if control_type:
                try:
                    ct = getattr(uia, f"{control_type}Control", None)
                    if ct:
                        conditions.append(uia.ControlType == ct)
                except Exception:
                    pass
            if automation_id:
                conditions.append(uia.AutomationId == automation_id)

            if not conditions:
                return None

            # Strategy 1: Exact match (fast path)
            cond = conditions[0]
            for c in conditions[1:]:
                cond = cond & c
            ctrl = uia.GetRootControl().Control(cond)
            if ctrl:
                return self._elem_to_uielement(ctrl)

            # Strategy 2: Fuzzy match — 深度递归搜索所有后代
            # BUG#2 修复: 原来只搜索2层, 现在完整递归整个 UIA 树
            if name:
                def _search_descendants(ctrl: Any, depth: int = 0, max_depth: int = 10) -> Any:
                    """递归搜索控件树, 用 name/automation_id/control_type 子串匹配。"""
                    if depth > max_depth:
                        return None
                    try:
                        ctrl_name = getattr(ctrl, 'Name', '') or ''
                        ctrl_aid = getattr(ctrl, 'AutomationId', '') or ''
                        ctrl_ct = str(getattr(ctrl, 'ControlTypeName', ''))

                        # 子串匹配 (双向: target in element OR element in target)
                        name_lower = name.lower()
                        if (name_lower in ctrl_name.lower()
                            or (ctrl_name and ctrl_name.lower() in name_lower)
                            or name_lower in ctrl_aid.lower()
                            or (ctrl_aid and ctrl_aid.lower() in name_lower)
                            or name_lower in ctrl_ct.lower()):
                            return ctrl

                        # 也按 control_type 中文映射搜索
                        CN_TYPE_MAP = {
                            "按钮": "Button", "确定": "Button", "取消": "Button",
                            "编辑": "Edit", "输入": "Edit", "文本": "Text",
                            "列表": "List", "菜单": "Menu", "窗口": "Window",
                            "复选框": "CheckBox", "单选框": "RadioButton",
                            "标签": "Text", "选项卡": "TabItem",
                        }
                        mapped_type = CN_TYPE_MAP.get(name, "")
                        if mapped_type and mapped_type.lower() in ctrl_ct.lower():
                            return ctrl
                    except Exception:
                        pass

                    # 递归搜索子控件
                    try:
                        for child in ctrl.GetChildren():
                            result = _search_descendants(child, depth + 1, max_depth)
                            if result is not None:
                                return result
                    except Exception:
                        pass
                    return None

                root = uia.GetRootControl()
                # 从根节点开始完整递归
                result = _search_descendants(root, depth=0, max_depth=12)
                if result is not None:
                    return self._elem_to_uielement(result)

                # Strategy 3: 按 control_type 枚举搜索 (遍历所有特定类型的控件)
                if control_type:
                    try:
                        cond_type = uia.ControlType == getattr(uia, f"{control_type}Control")
                        all_of_type = root.GetChildren()
                        for child in all_of_type:
                            try:
                                matched = child.Control(cond_type)
                                if matched:
                                    return self._elem_to_uielement(matched)
                            except Exception:
                                # 递归遍历子控件匹配 control_type
                                found = _search_descendants(child, depth=0, max_depth=8)
                                if found is not None:
                                    return self._elem_to_uielement(found)
                    except Exception:
                        pass

        except Exception:
            pass
        return None

    @staticmethod
    def _elem_to_uielement(ctrl: Any) -> UIElement:
        """Convert uiautomation control to UIElement."""
        import uiautomation as uia
        try:
            rect = ctrl.BoundingRectangle
            return UIElement(
                name=getattr(ctrl, 'Name', ''),
                control_type=str(getattr(ctrl, 'ControlTypeName', '')),
                automation_id=getattr(ctrl, 'AutomationId', ''),
                class_name=getattr(ctrl, 'ClassName', ''),
                x=rect.left if rect else 0, y=rect.top if rect else 0,
                width=rect.width() if rect else 0, height=rect.height() if rect else 0,
                is_enabled=ctrl.IsEnabled,
                is_visible=not ctrl.IsOffscreen,
            )
        except Exception:
            return UIElement(
                name=getattr(ctrl, 'Name', ''),
                control_type=str(getattr(ctrl, 'ControlTypeName', '')),
            )

    # ═══════════════════════════════════════════════════════
    # Internal — ctypes 原始点击回退
    # ═══════════════════════════════════════════════════════

    def _click_ctypes(self, x: int, y: int, click_type: ClickType) -> AutomationResult:
        """通过 ctypes SendInput 模拟点击。"""
        try:
            # Windows API 常量
            INPUT_MOUSE = 0
            MOUSEEVENTF_LEFTDOWN = 0x0002
            MOUSEEVENTF_LEFTUP = 0x0004
            MOUSEEVENTF_RIGHTDOWN = 0x0008
            MOUSEEVENTF_RIGHTUP = 0x0010
            MOUSEEVENTF_MIDDLEDOWN = 0x0020
            MOUSEEVENTF_MIDDLEUP = 0x0040

            # 移动光标
            ctypes.windll.user32.SetCursorPos(x, y)
            time.sleep(0.01)

            if click_type == ClickType.RIGHT:
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                time.sleep(0.01)
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            elif click_type == ClickType.MIDDLE:
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
                time.sleep(0.01)
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)
            else:
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.01)
                ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

                if click_type == ClickType.DOUBLE:
                    time.sleep(0.05)
                    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    time.sleep(0.01)
                    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

            return AutomationResult(
                success=True,
                action=f"click_{click_type.value}",
                detail=f"ctypes {click_type.value} at ({x}, {y})",
            )
        except Exception as e:
            return AutomationResult(
                success=False,
                action="click",
                detail=f"All backends failed: {e}",
            )
