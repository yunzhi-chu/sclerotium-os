"""Daily Digest — the organism's nightly reflection.

Triggered by gastric rhythm (end of day), the digest:
  1. Collects today's events from EventBus
  2. Aggregates activity metrics
  3. Generates a structured summary
  4. Stores it in episodic memory
  5. Surfaces notable patterns

This is the organism "thinking about what happened today."
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from kernel.event_bus import EventBus, Event

logger = logging.getLogger("sclerotium.digest")


class DigestSection(Enum):
    """Sections of the daily digest."""
    ACTIVITY = "activity"        # Time spent, apps used
    FILES = "files"              # Files created/modified
    PROJECTS = "projects"        # Projects worked on
    COMMUNICATION = "comm"       # Messages, emails
    PATTERNS = "patterns"        # Detected behavioral patterns
    HEALTH = "health"            # System health


@dataclass(frozen=True)
class ActivityMetrics:
    """Aggregated activity for a time period."""
    total_active_seconds: float = 0.0
    total_idle_seconds: float = 0.0
    sessions_count: int = 0
    top_apps: tuple[tuple[str, float], ...] = ()
    windows_switched: int = 0
    avg_focus_minutes: float = 0.0
    peak_hour: int = 0
    languages_detected: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_active_hours": round(self.total_active_seconds / 3600, 1),
            "total_idle_minutes": round(self.total_idle_seconds / 60, 1),
            "sessions_count": self.sessions_count,
            "top_apps": list(self.top_apps),
            "windows_switched": self.windows_switched,
            "avg_focus_minutes": round(self.avg_focus_minutes, 1),
            "peak_hour": self.peak_hour,
            "languages": list(self.languages_detected),
        }


@dataclass(frozen=True)
class DailyDigestResult:
    """Complete daily digest."""
    date: str                              # "2026-06-15"
    day_of_week: str                       # "Monday"
    activity: ActivityMetrics
    files_created: int = 0
    files_modified: int = 0
    active_projects: tuple[str, ...] = ()
    notable_events: tuple[str, ...] = ()   # Human-readable highlights
    suggestions: tuple[str, ...] = ()      # "You might want to..."
    system_health: dict[str, Any] = field(default_factory=dict)
    generated_at: float = field(default_factory=time.time)

    def to_summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            f"📅 {self.date} ({self.day_of_week})",
            f"",
            f"⏱ Activity: {self.activity.to_dict()['total_active_hours']}h active "
            f"across {self.activity.sessions_count} sessions",
        ]
        if self.activity.top_apps:
            top = ", ".join(f"{app}({pct:.0%})" for app, pct in self.activity.top_apps[:3])
            lines.append(f"🖥 Top apps: {top}")
        if self.active_projects:
            lines.append(f"📂 Projects: {', '.join(self.active_projects[:3])}")
        if self.files_created or self.files_modified:
            lines.append(f"📝 Files: {self.files_created} created, {self.files_modified} modified")
        if self.notable_events:
            lines.append(f"🔔 Notable:")
            for event in self.notable_events[:5]:
                lines.append(f"   • {event}")
        if self.suggestions:
            lines.append(f"💡 Suggestions:")
            for s in self.suggestions[:3]:
                lines.append(f"   • {s}")
        return "\n".join(lines)


class DailyDigest:
    """Collects and generates daily summaries.

    Subscribes to EventBus topics and accumulates data throughout the day.
    At gastric tick time (or on demand), generates a structured digest.

    Usage:
        bus = EventBus()
        digest = DailyDigest(event_bus=bus)
        digest.start()
        # ... day passes ...
        result = digest.generate()  # Or auto-triggered by gastric rhythm
        print(result.to_summary())
    """

    def __init__(
        self,
        event_bus: EventBus,
        max_events: int = 2000,
    ) -> None:
        self._bus = event_bus
        self._max_events = max_events
        self._sub_ids: list[str] = []

        # Accumulators (reset daily)
        self._today_events: list[Event] = []
        self._active_seconds: float = 0.0
        self._idle_seconds: float = 0.0
        self._sessions: int = 0
        self._app_counts: dict[str, int] = {}
        self._windows_switched: int = 0
        self._files_created: int = 0
        self._files_modified: int = 0
        self._projects: dict[str, int] = {}  # project → event count
        self._languages: dict[str, int] = {}
        self._notable: list[str] = []
        self._hourly_activity: dict[int, int] = {}

        self._started: bool = False
        self._last_digest_time: float = time.time()

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def start(self) -> None:
        """Subscribe to EventBus and begin accumulating."""
        if self._started:
            return
        self._started = True
        self._sub_ids = [
            self._bus.subscribe("window.changed", self._on_window_changed),
            self._bus.subscribe("activity.*", self._on_activity),
            self._bus.subscribe("file.created", self._on_file_created),
            self._bus.subscribe("file.modified", self._on_file_modified),
            self._bus.subscribe("clipboard.text", self._on_clipboard),
            self._bus.subscribe("rhythm.gastric", self._on_gastric),
        ]
        logger.info("DailyDigest started — accumulating events")

    def stop(self) -> None:
        """Unsubscribe and stop accumulating."""
        self._started = False
        for sub_id in self._sub_ids:
            self._bus.unsubscribe(sub_id)
        self._sub_ids.clear()
        logger.info("DailyDigest stopped")

    def generate(self) -> DailyDigestResult:
        """Generate today's digest from accumulated data."""
        now = time.time()
        peak = self._compute_peak_hour()

        activity = ActivityMetrics(
            total_active_seconds=self._active_seconds,
            total_idle_seconds=self._idle_seconds,
            sessions_count=max(self._sessions, 1),
            top_apps=tuple(self._compute_top_apps(5)),
            windows_switched=self._windows_switched,
            avg_focus_minutes=(
                (self._active_seconds / max(self._sessions, 1)) / 60
                if self._sessions > 0 else 0
            ),
            peak_hour=peak,
            languages_detected=tuple(sorted(
                self._languages.keys(),
                key=lambda l: self._languages[l],
                reverse=True,
            )),
        )

        # Generate suggestions
        suggestions = self._generate_suggestions(activity)

        result = DailyDigestResult(
            date=time.strftime("%Y-%m-%d", time.localtime()),
            day_of_week=time.strftime("%A", time.localtime()),
            activity=activity,
            files_created=self._files_created,
            files_modified=self._files_modified,
            active_projects=tuple(
                sorted(self._projects.keys(), key=lambda p: self._projects[p], reverse=True)[:5]
            ),
            notable_events=tuple(self._notable[-10:]),
            suggestions=tuple(suggestions),
            system_health={},  # To be filled by HealthChecker later
        )

        # Store as last digest
        self._last_digest_time = now

        logger.info(
            "Daily digest generated — %s: %.1fh active, %d files, %d sessions",
            result.date,
            activity.total_active_seconds / 3600,
            self._files_created + self._files_modified,
            self._sessions,
        )

        return result

    def reset_daily(self) -> None:
        """Reset all daily accumulators (called at midnight)."""
        self._today_events.clear()
        self._active_seconds = 0.0
        self._idle_seconds = 0.0
        self._sessions = 0
        self._app_counts.clear()
        self._windows_switched = 0
        self._files_created = 0
        self._files_modified = 0
        self._projects.clear()
        self._languages.clear()
        self._notable.clear()
        self._hourly_activity.clear()
        logger.info("Daily accumulators reset")

    def inject_event(self, event: Event) -> None:
        """Manually inject an event (for testing)."""
        self._today_events.append(event)
        if len(self._today_events) > self._max_events:
            self._today_events = self._today_events[-self._max_events:]

    # ═══════════════════════════════════════════════════════
    # Properties
    # ═══════════════════════════════════════════════════════

    @property
    def event_count(self) -> int:
        return len(self._today_events)

    @property
    def is_started(self) -> bool:
        return self._started

    # ═══════════════════════════════════════════════════════
    # Event Handlers
    # ═══════════════════════════════════════════════════════

    def _on_window_changed(self, event: Event) -> None:
        current = event.data.get("current", {})
        app = current.get("process_name", "")
        if app:
            self._app_counts[app] = self._app_counts.get(app, 0) + 1
            self._windows_switched += 1

            hour = int(time.strftime("%H", time.localtime()))
            self._hourly_activity[hour] = self._hourly_activity.get(hour, 0) + 1

            # Detect project from window title
            title = current.get("title", "")
            if " — " in title:
                project = title.split(" — ")[-1]
                self._projects[project] = self._projects.get(project, 0) + 1

        self._store_event(event)

    def _on_activity(self, event: Event) -> None:
        topic = event.topic
        if "session" in topic:
            self._sessions += 1
            self._active_seconds += event.data.get("duration", 0)
            self._idle_seconds += event.data.get("idle_count", 0) * 120  # rough estimate
        self._store_event(event)

    def _on_file_created(self, event: Event) -> None:
        self._files_created += 1
        path = event.data.get("path", "")
        if "/" in path:
            project = path.split("/")[0] if not path.startswith("/") else path.split("/")[1]
            self._projects[project] = self._projects.get(project, 0) + 1
        self._store_event(event)

    def _on_file_modified(self, event: Event) -> None:
        self._files_modified += 1
        suffix = event.data.get("suffix", "")
        if suffix:
            lang = _suffix_to_lang(suffix)
            if lang:
                self._languages[lang] = self._languages.get(lang, 0) + 1
        self._store_event(event)

    def _on_clipboard(self, event: Event) -> None:
        category = event.data.get("category", "")
        if category == "code":
            self._notable.append(f"Copied code ({event.data.get('length', 0)} chars)")
        self._store_event(event)

    def _on_gastric(self, event: Event) -> None:
        """Auto-generate digest on gastric tick (end of day)."""
        hour = event.data.get("hour", 0)
        if hour >= 21 or hour <= 2:  # Late evening / early morning
            logger.info("Gastric tick at hour %d — auto-generating digest", hour)
            self.generate()
            self.reset_daily()

    def _store_event(self, event: Event) -> None:
        """Store event in today's buffer."""
        self._today_events.append(event)
        if len(self._today_events) > self._max_events:
            self._today_events = self._today_events[-self._max_events:]

    # ═══════════════════════════════════════════════════════
    # Computation Helpers
    # ═══════════════════════════════════════════════════════

    def _compute_top_apps(self, limit: int = 5) -> list[tuple[str, float]]:
        """Compute top apps by event count."""
        total = sum(self._app_counts.values()) or 1
        sorted_apps = sorted(
            self._app_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [(app, round(count / total, 3)) for app, count in sorted_apps[:limit]]

    def _compute_peak_hour(self) -> int:
        """Find the hour with most activity."""
        if not self._hourly_activity:
            return 0
        return max(self._hourly_activity, key=self._hourly_activity.get)

    def _generate_suggestions(self, activity: ActivityMetrics) -> list[str]:
        """Generate contextual suggestions."""
        suggestions = []

        active_hours = activity.total_active_seconds / 3600
        if active_hours > 8:
            suggestions.append("You worked over 8 hours today — take care of yourself.")
        if active_hours < 2:
            suggestions.append("Light work day — nice break!")

        if activity.sessions_count > 10:
            suggestions.append("You had many short sessions today. Consider batching tasks for deeper focus.")

        if activity.total_idle_seconds > active_hours * 0.3:
            suggestions.append("High idle time detected. Maybe background distractions?")

        return suggestions


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _suffix_to_lang(suffix: str) -> str | None:
    """Map file extension to language."""
    lang_map = {
        ".py": "Python", ".pyi": "Python",
        ".ts": "TypeScript", ".tsx": "TypeScript",
        ".js": "JavaScript", ".jsx": "JavaScript",
        ".rs": "Rust", ".go": "Go",
        ".java": "Java", ".cpp": "C++", ".h": "C++",
        ".sql": "SQL", ".html": "HTML", ".css": "CSS",
        ".json": "JSON", ".yaml": "YAML", ".md": "Markdown",
    }
    return lang_map.get(suffix.lower())
