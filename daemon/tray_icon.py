"""Sclerotium OS — System Tray Icon.

The organism's visible presence in the Windows taskbar.
Shows real-time status via icon color and provides a right-click menu.

States:
  🟢 Green pulse  — healthy, running
  🟡 Yellow       — has notifications
  🔵 Blue blink   — thinking/processing
  🔴 Red          — error detected
  ⚫ Gray         — sleeping / offline
"""

from __future__ import annotations

import threading
import time
import logging
from pathlib import Path
from typing import Any, Callable

from orchestrator.lifecycle import LifecycleManager, LifecyclePhase

logger = logging.getLogger("sclerotium.tray")

# pystray is optional — tray only works on desktop systems
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


# ═══════════════════════════════════════════════════════════════
# Icon Drawing
# ═══════════════════════════════════════════════════════════════

def _create_icon_image(
    color: tuple[int, int, int] = (0, 200, 100),
    size: int = 64,
) -> Any:
    """Create a circular icon of the given color.

    Returns a PIL Image (RGBA with transparent background).
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 4
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=color,
        outline=(255, 255, 255, 80),
        width=2,
    )
    # Draw a subtle inner glow
    draw.ellipse(
        [size//4, size//4, size*3//4, size*3//4],
        fill=tuple(min(c + 40, 255) for c in color) + (100,),
    )
    return img


# Icon colors for each state
ICON_COLORS = {
    "running": (0, 200, 100),       # Green
    "notification": (240, 200, 0),   # Yellow
    "thinking": (60, 140, 255),      # Blue
    "error": (220, 40, 40),          # Red
    "sleeping": (120, 120, 120),     # Gray
    "offline": (80, 80, 80),         # Dark gray
}


# ═══════════════════════════════════════════════════════════════
# System Tray Controller
# ═══════════════════════════════════════════════════════════════

class TrayController:
    """Manages the system tray icon and menu.

    Can run standalone (just the tray) or be attached to a daemon
    for real-time status updates.
    """

    def __init__(
        self,
        lifecycle: LifecycleManager | None = None,
        on_show_status: Callable[[], str] | None = None,
        on_show_dashboard: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
    ) -> None:
        if not HAS_TRAY:
            raise RuntimeError(
                "pystray and Pillow are required for system tray support. "
                "Install with: pip install pystray Pillow"
            )

        self._lifecycle = lifecycle
        self._on_show_status = on_show_status
        self._on_show_dashboard = on_show_dashboard
        self._on_quit = on_quit

        self._icon: Any = None
        self._current_color: str = "offline"
        self._running: bool = False
        self._blink_thread: threading.Thread | None = None
        self._notification_count: int = 0

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def start(self) -> None:
        """Start the tray icon. Blocks until the icon exits."""
        if self._running:
            return
        self._running = True

        icon_img = _create_icon_image(ICON_COLORS["running"])
        menu = self._build_menu()

        self._icon = pystray.Icon(
            "sclerotium",
            icon_img,
            "Sclerotium OS",
            menu=menu,
        )
        self._icon.run()

    def stop(self) -> None:
        """Stop the tray icon."""
        self._running = False
        if self._icon:
            self._icon.stop()
            self._icon = None

    def update_icon(self, state: str) -> None:
        """Update the tray icon color based on organism state.

        Args:
            state: One of 'running', 'notification', 'thinking', 'error',
                   'sleeping', 'offline'
        """
        if state not in ICON_COLORS:
            return
        self._current_color = state
        if self._icon:
            color = ICON_COLORS[state]
            self._icon.icon = _create_icon_image(color)
            # Update tooltip
            phase = "Unknown"
            if self._lifecycle:
                phase = self._lifecycle.phase.value
            self._icon.title = f"Sclerotium OS — {phase}"

    def notify(self, title: str, message: str) -> None:
        """Show a system notification bubble."""
        if self._icon and hasattr(self._icon, 'notify'):
            self._icon.notify(message, title=title)
        self._notification_count += 1
        if self._current_color != "error":
            self.update_icon("notification")

    def clear_notifications(self) -> None:
        """Clear the notification count and reset icon."""
        self._notification_count = 0
        if self._lifecycle and self._lifecycle.is_running:
            self.update_icon("running")

    def start_blink(self, color_name: str = "thinking", interval: float = 0.5) -> None:
        """Start a blinking animation (e.g., while LLM is thinking)."""
        if self._blink_thread and self._blink_thread.is_alive():
            return
        self._blink_thread = threading.Thread(
            target=self._blink_loop,
            args=(color_name, interval),
            name="sclerotium-tray-blink",
            daemon=True,
        )
        self._blink_thread.start()

    def stop_blink(self) -> None:
        """Stop blinking and restore the normal icon."""
        if self._blink_thread:
            # Will stop on next interval check
            pass
        self._blink_thread = None
        self.update_icon("running")

    # ═══════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════

    def _build_menu(self) -> Any:
        """Build the right-click context menu."""
        menu_items = []

        # Status item
        menu_items.append(
            pystray.MenuItem(
                "📊 Status",
                self._on_status_click,
                default=True,  # Left-click triggers this
            )
        )
        menu_items.append(pystray.Menu.SEPARATOR)

        # Mode submenu
        mode_menu = pystray.Menu(
            pystray.MenuItem("💼 Work", lambda: self._on_mode_change("work")),
            pystray.MenuItem("😴 Sleep", lambda: self._on_mode_change("sleep")),
            pystray.MenuItem("🎮 Game", lambda: self._on_mode_change("game")),
            pystray.MenuItem("📅 Meeting", lambda: self._on_mode_change("meeting")),
            pystray.MenuItem("🎨 Creative", lambda: self._on_mode_change("creative")),
        )
        menu_items.append(pystray.MenuItem("🔄 Mode", mode_menu))
        menu_items.append(pystray.Menu.SEPARATOR)

        # Dashboard
        if self._on_show_dashboard:
            menu_items.append(
                pystray.MenuItem("📈 Dashboard", self._on_show_dashboard)
            )
            menu_items.append(pystray.Menu.SEPARATOR)

        # Quit
        menu_items.append(pystray.MenuItem("❌ Quit", self._on_quit_click))

        return pystray.Menu(*menu_items)

    def _on_status_click(self, icon: Any, item: Any) -> None:
        """Show a quick status popup."""
        if self._on_show_status:
            msg = self._on_show_status()
        elif self._lifecycle:
            state = self._lifecycle.status()
            msg = (
                f"Sclerotium OS v{state.version}\n"
                f"Phase: {state.phase.value}\n"
                f"Uptime: {state.uptime_seconds:.0f}s\n"
                f"Organs: {len(state.organs)} total\n"
                f"Mode: {state.mode}\n"
            )
        else:
            msg = "Sclerotium OS — Alive"
        self.notify("Sclerotium OS", msg)

    def _on_mode_change(self, mode: str) -> None:
        """Handle mode switch from tray menu."""
        logger.info("Tray mode switch → %s", mode)
        self.clear_notifications()

    def _on_quit_click(self, icon: Any, item: Any) -> None:
        """Handle quit from tray menu."""
        logger.info("Quit requested from tray")
        if self._on_quit:
            self._on_quit()
        self.stop()

    def _blink_loop(self, color_name: str, interval: float) -> None:
        """Blink between the given color and transparent/dim."""
        bright_color = ICON_COLORS.get(color_name, ICON_COLORS["thinking"])
        dim_color = tuple(max(c - 100, 0) for c in bright_color)
        toggle = True
        while self._blink_thread and self._running:
            color = bright_color if toggle else dim_color
            if self._icon:
                self._icon.icon = _create_icon_image(color)
            toggle = not toggle
            time.sleep(interval)


# ═══════════════════════════════════════════════════════════════
# Utility: check if tray is available
# ═══════════════════════════════════════════════════════════════

def is_tray_available() -> bool:
    """Check if the system tray can be used."""
    return HAS_TRAY
