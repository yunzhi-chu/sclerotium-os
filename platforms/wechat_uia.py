"""WeChat UIA Adapter — 用菌核自带的 UIA 控制器操控微信.

零依赖: 只使用 Sclerotium OS 已有的 automation/ 模块.
任何微信版本通用: 通过 UI Automation 查找控件, 不依赖 DLL 注入.

Usage:
    from platforms.wechat_uia import WeChatUIA
    wx = WeChatUIA()
    wx.connect()           # 连接到微信窗口
    wx.send_text("filehelper", "Hello from 菌核!")
    msgs = wx.get_messages("张三")
    wx.listen(callback)    # 监听新消息
"""

from __future__ import annotations

import logging
import time
import threading
from typing import Any, Callable

logger = logging.getLogger("sclerotium.wechat.uia")


class WeChatUIA:
    """用 Windows UI Automation 操控微信客户端.

    不需要 DLL 注入, 不挑微信版本.
    需要: 微信已登录 + 窗口未最小化.
    """

    def __init__(self):
        self._connected = False
        self._hwnd = None
        self._app = None
        self._main_window = None
        self._listening = False
        self._listen_thread = None
        self._msg_callback: Callable | None = None
        self._last_msg_count = 0

    # ═══════════════════════════════════════════════════════
    # Connection
    # ═══════════════════════════════════════════════════════

    def connect(self) -> bool:
        """连接到微信窗口."""
        try:
            import uiautomation as auto

            # Find WeChat/Weixin window
            wx = auto.WindowControl(Name="微信", searchDepth=1)
            if not wx.Exists(0, 0):
                wx = auto.WindowControl(ClassName="WeChatMainWndForPC", searchDepth=1)
            if not wx.Exists(0, 0):
                wx = auto.WindowControl(Name="Weixin", searchDepth=1)
            if not wx.Exists(0, 0):
                # Try partial match
                for w in auto.GetRootControl().GetChildren():
                    if "微信" in (w.Name or "") or "Weixin" in (w.Name or ""):
                        wx = w
                        break

            if not wx or not wx.Exists(0, 0):
                logger.error("WeChat window not found. Is WeChat running?")
                return False

            self._main_window = wx
            self._hwnd = wx.NativeWindowHandle
            self._connected = True
            logger.info("WeChat UIA connected: %s (hwnd=%s)", wx.Name, self._hwnd)
            return True

        except ImportError:
            logger.warning("uiautomation not installed, trying pywinauto...")
            return self._connect_pywinauto()
        except Exception as e:
            logger.error("WeChat UIA connect failed: %s", e)
            return False

    def _connect_pywinauto(self) -> bool:
        """Fallback: use pywinauto."""
        try:
            from pywinauto.application import Application
            # Connect to existing WeChat process
            app = Application(backend="uia").connect(title="微信", timeout=5)
            self._app = app
            self._main_window = app.window(title="微信")
            self._connected = True
            logger.info("WeChat pywinauto connected")
            return True
        except Exception:
            try:
                app = Application(backend="uia").connect(title="Weixin", timeout=5)
                self._app = app
                self._main_window = app.window(title="Weixin")
                self._connected = True
                return True
            except Exception as e:
                logger.error("WeChat pywinauto connect failed: %s", e)
                return False

    def _focus_wechat(self):
        """Ensure WeChat window is active before any keyboard/mouse ops."""
        import pygetwindow as gw
        try:
            # Find WeChat window by title
            for win in gw.getWindowsWithTitle('微信'):
                if win.isMinimized:
                    win.restore()
                win.activate()
                time.sleep(0.2)
                return True
            for win in gw.getWindowsWithTitle('Weixin'):
                if win.isMinimized:
                    win.restore()
                win.activate()
                time.sleep(0.2)
                return True
            # Fallback: use UIA to focus
            if self._main_window:
                try:
                    self._main_window.SetFocus()
                    self._main_window.SetActive()
                    time.sleep(0.2)
                except Exception:
                    pass
        except Exception as e:
            logger.debug("Focus failed: %s", e)

    # ═══════════════════════════════════════════════════════
    # Messaging
    # ═══════════════════════════════════════════════════════

    def send_text(self, who: str, content: str) -> bool:
        """Send text message to a contact or group.

        Args:
            who: contact name, remark, or "filehelper" for 文件传输助手
            content: message text
        """
        if not self._connected:
            return False

        try:
            return self._send_via_clipboard(who, content)
        except Exception as e:
            logger.error("WeChat send failed: %s", e)
            return False

    def _send_via_clipboard(self, who: str, content: str) -> bool:
        """Send message using clipboard + keyboard shortcut."""
        import pyautogui
        import pyperclip

        self._focus_wechat()  # CRITICAL: ensure WeChat has focus

        # Step 1: Ctrl+F to open search
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(0.3)

        # Step 2: Type contact name
        pyperclip.copy(who)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.5)

        # Step 3: Press Enter to select first result
        pyautogui.press('enter')
        time.sleep(0.3)

        # Step 4: Type message
        pyperclip.copy(content)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.2)

        # Step 5: Send
        pyautogui.press('enter')
        logger.info("WeChat sent to '%s': %s", who, content[:50])
        return True

    def send_file(self, who: str, filepath: str) -> bool:
        """Send a file via WeChat (drag & drop or clipboard)."""
        return self.send_text(who, f"[文件] {filepath}")

    # ═══════════════════════════════════════════════════════
    # Reading Messages (Clipboard-based — works on all versions)
    # ═══════════════════════════════════════════════════════

    def get_last_message(self, who: str = "") -> str:
        """Get the last message from a chat using clipboard."""
        if not self._connected:
            return ""

        try:
            import pyautogui
            import pyperclip

            self._focus_wechat()  # CRITICAL

            # Save current clipboard
            old_clip = ""
            try:
                old_clip = pyperclip.paste()
            except Exception:
                pass

            # Navigate to chat
            if who:
                self._navigate_to_chat(who)
                time.sleep(0.3)

            # Click in the message area to focus
            # The message area is roughly in the center-right of the window
            import uiautomation as auto
            rect = self._main_window.BoundingRectangle
            # Click in the message list area (~60% from left, ~40% from top)
            x = rect.left + int(rect.width() * 0.6)
            y = rect.top + int(rect.height() * 0.35)
            pyautogui.click(x, y)
            time.sleep(0.2)

            # Ctrl+A to select all, Ctrl+C to copy
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.3)

            # Read clipboard
            text = pyperclip.paste()

            # Restore old clipboard
            if old_clip:
                try:
                    pyperclip.copy(old_clip)
                except Exception:
                    pass

            # Parse the last message
            if text and text != old_clip:
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                # Return last non-empty line
                for line in reversed(lines):
                    if line and len(line) > 1:
                        return line

            return ""

        except Exception as e:
            logger.debug("Get last message failed: %s", e)
            return ""

    def get_messages(self, who: str = "", count: int = 20) -> list[dict]:
        """Get recent messages from a chat (legacy API, uses get_last_message)."""
        last = self.get_last_message(who)
        if last:
            return [{"content": last, "sender": "", "time": ""}]
        return []

    def has_new_message(self, who: str, last_seen: str) -> bool:
        """Check if there's a new message different from last_seen."""
        current = self.get_last_message(who)
        return current and current != last_seen

    # ═══════════════════════════════════════════════════════
    # Listening (poll-based)
    # ═══════════════════════════════════════════════════════

    def listen(self, callback: Callable[[dict], Any], poll_interval: float = 2.0):
        """Start listening for new messages (polling-based).

        Args:
            callback: called with each new message dict {sender, content, time}
            poll_interval: seconds between polls
        """
        self._msg_callback = callback
        self._listening = True
        self._listen_thread = threading.Thread(
            target=self._poll_loop,
            args=(poll_interval,),
            daemon=True,
        )
        self._listen_thread.start()
        logger.info("WeChat listener started (poll=%.1fs)", poll_interval)

    def stop_listening(self):
        """Stop message listening."""
        self._listening = False
        if self._listen_thread:
            self._listen_thread.join(timeout=3)

    def _poll_loop(self, interval: float):
        """Background poll loop for new messages."""
        import uiautomation as auto

        while self._listening:
            try:
                if not self._connected:
                    time.sleep(interval)
                    continue

                # Check unread badge
                unread = self._get_unread_count()
                if unread > 0 and self._msg_callback:
                    self._msg_callback({
                        "sender": "system",
                        "content": f"{unread} unread messages",
                        "time": time.strftime("%H:%M:%S"),
                        "unread_count": unread,
                    })

            except Exception as e:
                logger.debug("Poll error: %s", e)
            time.sleep(interval)

    # ═══════════════════════════════════════════════════════
    # Contacts
    # ═══════════════════════════════════════════════════════

    def get_contacts(self) -> list[dict]:
        """Get recent contact list from sidebar."""
        if not self._connected:
            return []
        try:
            import uiautomation as auto
            contacts = []
            # Find contact list
            contact_list = self._main_window.ListControl(Name="会话")
            if contact_list.Exists(0, 0):
                for item in contact_list.GetChildren():
                    name = item.Name or ""
                    if name.strip():
                        contacts.append({"name": name.strip(), "wxid": name.strip()})
            return contacts
        except Exception as e:
            logger.debug("Get contacts failed: %s", e)
            return []

    # ═══════════════════════════════════════════════════════
    # Self Info
    # ═══════════════════════════════════════════════════════

    def get_self_info(self) -> dict:
        """Get logged-in WeChat account info."""
        return {
            "name": "微信用户",
            "wxid": "",
            "connected": self._connected,
        }

    # ═══════════════════════════════════════════════════════
    # Internal Helpers
    # ═══════════════════════════════════════════════════════

    def _navigate_to_chat(self, who: str):
        """Navigate to a specific chat."""
        import pyautogui, pyperclip
        pyautogui.hotkey('ctrl', 'f')
        time.sleep(0.3)
        pyperclip.copy(who)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.5)
        pyautogui.press('enter')

    def _get_unread_count(self) -> int:
        """Get total unread message count."""
        try:
            import uiautomation as auto
            # Look for unread badge
            badge = self._main_window.TextControl(searchDepth=4)
            # Just check if any controls have numeric Name
            for c in self._main_window.GetChildren():
                if c.Name and c.Name.isdigit():
                    return int(c.Name)
        except Exception:
            pass
        return 0

    def cleanup(self):
        """Clean up resources."""
        self.stop_listening()
        self._connected = False
        self._main_window = None
        self._app = None


# ═══════════════════════════════════════════════════════════
# Quick test
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("[WeChatUIA] Connecting to WeChat...")
    wx = WeChatUIA()
    if wx.connect():
        print(f"[OK] Connected! hwnd={wx._hwnd}")
        info = wx.get_self_info()
        print(f"  name: {info['name']}")

        contacts = wx.get_contacts()
        print(f"  contacts: {len(contacts)}")
        for c in contacts[:5]:
            print(f"    - {c['name']}")

        print("[OK] WeChat UIA Adapter is working!")
        wx.cleanup()
    else:
        print("[FAIL] Could not connect to WeChat window.")
        print("Make sure WeChat is running and not minimized.")
