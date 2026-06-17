"""Nudge Engine — decides WHEN and HOW to interrupt the user.

The organism must know when to speak and when to stay silent.
Three levels of interruption:
  - SILENT: record the observation, don't notify
  - TRAY: update tray icon / tooltip
  - NOTIFY: show desktop notification
  - ALERT: high-priority popup (safety/security only)

Decision factors:
  1. Current mode (work/sleep/game/meeting/creative)
  2. Time since last notification (anti-spam)
  3. Importance of the message
  4. User's notification preference (from UserModel)
  5. Whether user is in fullscreen / game
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("sclerotium.nudge")


class NudgeLevel(int, Enum):
    """How aggressively to interrupt. Uses int for comparison support."""
    SILENT = 0     # Record only, no notification
    TRAY = 1       # Update tray icon/tooltip
    NOTIFY = 2     # Desktop notification
    ALERT = 3      # High-priority popup


class NudgeCategory(Enum):
    """What kind of nudge this is."""
    HEALTH = "health"             # "You've been working for 2 hours"
    SECURITY = "security"          # "This .exe wants admin"
    INSIGHT = "insight"            # "I noticed you're debugging auth again"
    MAINTENANCE = "maintenance"    # "C drive has 15GB left"
    RHYTHM = "rhythm"             # "Friday 3pm — time for weekly report?"
    INFO = "info"                  # General information


@dataclass(frozen=True)
class NudgeDecision:
    """Immutable decision about whether/how to interrupt."""
    level: NudgeLevel
    category: NudgeCategory
    title: str
    message: str
    importance: float          # 0.0–1.0
    reason: str = ""           # Why this decision was made
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class NudgePolicy:
    """Configuration for how nudges work in a given mode."""
    min_importance_for_tray: float = 0.3
    min_importance_for_notify: float = 0.5
    min_importance_for_alert: float = 0.9
    cooldown_seconds: float = 300.0   # 5 min between notifications
    max_notifications_per_hour: int = 6


# Preset policies per mode
MODE_POLICIES: dict[str, NudgePolicy] = {
    "work": NudgePolicy(
        min_importance_for_tray=0.3,
        min_importance_for_notify=0.5,
        min_importance_for_alert=0.9,
        cooldown_seconds=300,
        max_notifications_per_hour=8,
    ),
    "sleep": NudgePolicy(
        min_importance_for_tray=0.7,
        min_importance_for_notify=0.9,
        min_importance_for_alert=0.95,
        cooldown_seconds=3600,
        max_notifications_per_hour=1,
    ),
    "game": NudgePolicy(
        min_importance_for_tray=0.6,
        min_importance_for_notify=0.85,
        min_importance_for_alert=0.95,
        cooldown_seconds=900,
        max_notifications_per_hour=2,
    ),
    "meeting": NudgePolicy(
        min_importance_for_tray=0.7,
        min_importance_for_notify=0.9,
        min_importance_for_alert=0.95,
        cooldown_seconds=1800,
        max_notifications_per_hour=2,
    ),
    "creative": NudgePolicy(
        min_importance_for_tray=0.3,
        min_importance_for_notify=0.6,
        min_importance_for_alert=0.9,
        cooldown_seconds=600,
        max_notifications_per_hour=5,
    ),
}


class NudgeEngine:
    """Decides when the organism should interrupt its human host.

    Usage:
        engine = NudgeEngine(mode="work")
        decision = engine.decide(
            category=NudgeCategory.HEALTH,
            title="Time for a break",
            message="You've been working for 2 hours.",
            importance=0.7,
        )
        if decision.level != NudgeLevel.SILENT:
            show_notification(decision)
    """

    def __init__(
        self,
        mode: str = "work",
        custom_policy: NudgePolicy | None = None,
    ) -> None:
        self._mode = mode
        self._policy = custom_policy or MODE_POLICIES.get(mode, MODE_POLICIES["work"])
        self._last_notification_time: float = 0.0
        self._notifications_this_hour: int = 0
        self._hour_start: float = time.time()
        self._decision_history: list[NudgeDecision] = []
        self._is_fullscreen: bool = False

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def decide(
        self,
        category: NudgeCategory,
        title: str,
        message: str,
        importance: float,
        force: bool = False,
    ) -> NudgeDecision:
        """Decide whether and how to nudge the user.

        Args:
            category: What kind of nudge
            title: Short title
            message: Body text
            importance: 0.0–1.0 how important this is
            force: If True, bypass all checks (for security alerts)

        Returns:
            NudgeDecision with the chosen level and reasoning.
        """
        # Reset hourly counter
        self._maybe_reset_hourly()

        # Security overrides everything
        if force or category == NudgeCategory.SECURITY:
            decision = NudgeDecision(
                level=NudgeLevel.ALERT,
                category=category,
                title=title,
                message=message,
                importance=importance,
                reason="Security override — bypassing mode checks",
            )
            self._record(decision)
            return decision

        # Cooldown check
        if self._in_cooldown():
            decision = NudgeDecision(
                level=NudgeLevel.SILENT,
                category=category,
                title=title,
                message=message,
                importance=importance,
                reason=f"Cooldown active — {self._cooldown_remaining():.0f}s remaining",
            )
            self._record(decision)
            return decision

        # Hourly cap check
        if self._notifications_this_hour >= self._policy.max_notifications_per_hour:
            decision = NudgeDecision(
                level=NudgeLevel.SILENT,
                category=category,
                title=title,
                message=message,
                importance=importance,
                reason=f"Hourly cap reached ({self._policy.max_notifications_per_hour})",
            )
            self._record(decision)
            return decision

        # Fullscreen override — only ALERT level gets through
        if self._is_fullscreen and importance < 0.9:
            decision = NudgeDecision(
                level=NudgeLevel.SILENT,
                category=category,
                title=title,
                message=message,
                importance=importance,
                reason="User in fullscreen — suppressing non-critical notification",
            )
            self._record(decision)
            return decision

        # Determine level based on importance thresholds
        level = self._determine_level(importance)
        reason = (
            f"importance={importance:.2f} >= threshold={self._threshold_for_level(level):.2f}"
            f" (mode={self._mode})"
        )

        decision = NudgeDecision(
            level=level,
            category=category,
            title=title,
            message=message,
            importance=importance,
            reason=reason,
        )
        self._record(decision)
        return decision

    def set_mode(self, mode: str) -> None:
        """Switch to a different mode's nudge policy."""
        self._mode = mode
        self._policy = MODE_POLICIES.get(mode, MODE_POLICIES["work"])
        logger.debug("Nudge policy switched to mode=%s", mode)

    def set_fullscreen(self, is_fullscreen: bool) -> None:
        """Notify the engine that the user is in fullscreen."""
        self._is_fullscreen = is_fullscreen

    def get_history(self, limit: int = 20) -> list[NudgeDecision]:
        """Get recent nudge decisions."""
        return self._decision_history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get nudge statistics."""
        recent = self._decision_history[-100:]
        return {
            "mode": self._mode,
            "total_decisions": len(self._decision_history),
            "notifications_this_hour": self._notifications_this_hour,
            "notifications_allowed": sum(
                1 for d in recent if d.level != NudgeLevel.SILENT
            ),
            "notifications_silent": sum(
                1 for d in recent if d.level == NudgeLevel.SILENT
            ),
            "cooldown_active": self._in_cooldown(),
            "cooldown_remaining_s": self._cooldown_remaining(),
        }

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def policy(self) -> NudgePolicy:
        return self._policy

    # ═══════════════════════════════════════════════════════
    # Internal
    # ═══════════════════════════════════════════════════════

    def _determine_level(self, importance: float) -> NudgeLevel:
        """Map importance → nudge level based on current policy."""
        if importance >= self._policy.min_importance_for_alert:
            return NudgeLevel.ALERT
        if importance >= self._policy.min_importance_for_notify:
            return NudgeLevel.NOTIFY
        if importance >= self._policy.min_importance_for_tray:
            return NudgeLevel.TRAY
        return NudgeLevel.SILENT

    def _threshold_for_level(self, level: NudgeLevel) -> float:
        """Get the importance threshold for a given level."""
        if level == NudgeLevel.ALERT:
            return self._policy.min_importance_for_alert
        if level == NudgeLevel.NOTIFY:
            return self._policy.min_importance_for_notify
        if level == NudgeLevel.TRAY:
            return self._policy.min_importance_for_tray
        return 0.0

    def _in_cooldown(self) -> bool:
        """Check if we're still in notification cooldown."""
        if self._last_notification_time == 0.0:
            return False
        return (time.time() - self._last_notification_time) < self._policy.cooldown_seconds

    def _cooldown_remaining(self) -> float:
        """Seconds remaining in cooldown."""
        if self._last_notification_time == 0.0:
            return 0.0
        remaining = self._policy.cooldown_seconds - (time.time() - self._last_notification_time)
        return max(0.0, remaining)

    def _maybe_reset_hourly(self) -> None:
        """Reset hourly counter if an hour has passed."""
        if time.time() - self._hour_start > 3600:
            self._notifications_this_hour = 0
            self._hour_start = time.time()

    def _record(self, decision: NudgeDecision) -> None:
        """Record a decision and update state."""
        self._decision_history.append(decision)
        if len(self._decision_history) > 500:
            self._decision_history = self._decision_history[-500:]

        if decision.level >= NudgeLevel.NOTIFY:
            self._last_notification_time = time.time()
            self._notifications_this_hour += 1

        logger.debug(
            "Nudge: %s | level=%s importance=%.2f | %s",
            decision.category.value,
            decision.level.name,
            decision.importance,
            decision.reason,
        )
