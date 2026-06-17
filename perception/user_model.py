"""User Model — the organism's understanding of its human host.

Builds and continuously updates a mental model of the user based on
observed behavior patterns. This is the foundation of "越用越懂你".

The model is stored as immutable snapshots — each update produces a
new UserModel instance. The updater subscribes to EventBus topics and
applies incremental updates.
"""

from __future__ import annotations

import time
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kernel.event_bus import EventBus, Event

logger = logging.getLogger("sclerotium.perception.user_model")


# ═══════════════════════════════════════════════════════════════
# User Model — Immutable Snapshot
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class UserModel:
    """Immutable snapshot of what the organism knows about its user.

    All fields are optional with sensible defaults — the model starts
    empty and fills in as observations accumulate.
    """

    # ── Work Rhythm ──
    work_start_hour: float = 9.0       # Typical work start (hour of day)
    work_end_hour: float = 18.0        # Typical work end
    peak_focus_hours: tuple[tuple[float, float], ...] = ()  # [(10,12), (15,17)]
    break_pattern: tuple[float, ...] = ()  # Typical break durations in minutes
    lunch_window: tuple[float, float] = (11.5, 13.5)  # Typical lunch window

    # ── Tool Usage ──
    top_apps: tuple[tuple[str, float], ...] = ()  # [("vscode", 0.6), ("chrome", 0.3)]
    primary_editor: str = ""            # "vscode" / "pycharm" / "neovim" etc.
    primary_terminal: str = ""          # "windows-terminal" / "alacritty" etc.
    primary_browser: str = ""

    # ── Technical Profile ──
    primary_language: str = ""          # "python" / "typescript" / ...
    languages: tuple[str, ...] = ()     # All detected languages
    code_style_preferences: dict[str, str] = field(default_factory=dict)
    uses_docker: bool = False
    uses_git: bool = False
    uses_tests: bool = False

    # ── Cognitive Patterns ──
    context_switch_frequency: float = 0.0  # Switches per hour
    avg_focus_duration_minutes: float = 0.0
    interrupted_count_today: int = 0
    deep_work_sessions_today: int = 0

    # ── Communication ──
    interrupt_ok_hours: tuple[tuple[float, float], ...] = ((10.0, 12.0), (14.0, 17.0))
    notification_preference: str = "moderate"  # minimal / moderate / all
    preferred_channels: tuple[str, ...] = ()   # ["desktop", "wechat", ...]

    # ── Meta ──
    confidence: float = 0.1             # Overall model confidence [0, 1]
    total_observations: int = 0         # Number of data points collected
    last_updated: float = field(default_factory=time.time)
    model_version: int = 1

    # ── Active Projects ──
    active_projects: tuple[str, ...] = ()      # Recently active project paths
    learning_directions: tuple[str, ...] = ()   # Detected learning interests

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        d = {
            "work_start_hour": self.work_start_hour,
            "work_end_hour": self.work_end_hour,
            "peak_focus_hours": list(self.peak_focus_hours),
            "top_apps": list(self.top_apps),
            "primary_editor": self.primary_editor,
            "primary_language": self.primary_language,
            "languages": list(self.languages),
            "context_switch_frequency": self.context_switch_frequency,
            "avg_focus_duration_minutes": self.avg_focus_duration_minutes,
            "notification_preference": self.notification_preference,
            "confidence": self.confidence,
            "total_observations": self.total_observations,
            "last_updated": self.last_updated,
            "active_projects": list(self.active_projects),
            "learning_directions": list(self.learning_directions),
        }
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> UserModel:
        """Deserialize from a dict."""
        return cls(
            work_start_hour=d.get("work_start_hour", 9.0),
            work_end_hour=d.get("work_end_hour", 18.0),
            peak_focus_hours=tuple(
                tuple(p) for p in d.get("peak_focus_hours", [])
            ),
            top_apps=tuple(
                tuple(a) for a in d.get("top_apps", [])
            ),
            primary_editor=d.get("primary_editor", ""),
            primary_language=d.get("primary_language", ""),
            languages=tuple(d.get("languages", [])),
            context_switch_frequency=d.get("context_switch_frequency", 0.0),
            avg_focus_duration_minutes=d.get("avg_focus_duration_minutes", 0.0),
            notification_preference=d.get("notification_preference", "moderate"),
            confidence=d.get("confidence", 0.1),
            total_observations=d.get("total_observations", 0),
            last_updated=d.get("last_updated", time.time()),
            active_projects=tuple(d.get("active_projects", [])),
            learning_directions=tuple(d.get("learning_directions", [])),
        )


# ═══════════════════════════════════════════════════════════════
# User Model Updater
# ═══════════════════════════════════════════════════════════════

class UserModelUpdater:
    """Subscribes to EventBus and incrementally updates the UserModel.

    Each update produces a new immutable UserModel snapshot — never
    mutates the existing one.

    Usage:
        bus = EventBus()
        updater = UserModelUpdater(event_bus=bus)
        updater.start()
        # ... events flow in ...
        model = updater.get_model()  # Latest snapshot
        updater.save_to_disk(Path("~/.sclerotium/user_model.json"))
    """

    # How much each observation shifts the model (EMA smoothing factor)
    DEFAULT_LEARNING_RATE = 0.05

    def __init__(
        self,
        event_bus: EventBus,
        learning_rate: float = DEFAULT_LEARNING_RATE,
    ) -> None:
        self._bus = event_bus
        self._lr = learning_rate
        self._model = UserModel()
        self._sub_ids: list[str] = []

        # Internal accumulators (not part of the immutable model)
        self._app_durations: dict[str, float] = {}   # app → total seconds
        self._hourly_activity: dict[int, int] = {}    # hour (0-23) → activity count
        self._project_paths: dict[str, float] = {}    # path → last seen timestamp
        self._language_detections: dict[str, int] = {}  # language → detection count

    # ═══════════════════════════════════════════════════════
    # Public API
    # ═══════════════════════════════════════════════════════

    def start(self) -> None:
        """Subscribe to relevant EventBus topics."""
        self._sub_ids = [
            self._bus.subscribe("window.changed", self._on_window_changed),
            self._bus.subscribe("clipboard.text", self._on_clipboard_text),
            self._bus.subscribe("file.modified", self._on_file_modified),
            self._bus.subscribe("activity.session", self._on_activity_session),
            self._bus.subscribe("activity.idle", self._on_activity_idle),
            self._bus.subscribe("activity.active", self._on_activity_active),
        ]
        logger.info("UserModelUpdater started — listening on %d topics", len(self._sub_ids))

    def stop(self) -> None:
        """Unsubscribe from all topics."""
        for sub_id in self._sub_ids:
            self._bus.unsubscribe(sub_id)
        self._sub_ids.clear()
        logger.info("UserModelUpdater stopped")

    def get_model(self) -> UserModel:
        """Get the current immutable user model snapshot."""
        return self._model

    def reset(self) -> None:
        """Reset the model to factory defaults."""
        self._model = UserModel()
        self._app_durations.clear()
        self._hourly_activity.clear()
        self._project_paths.clear()
        self._language_detections.clear()

    def save_to_disk(self, path: Path) -> None:
        """Persist the current model to disk as JSON."""
        path = Path(path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._model.to_dict()
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("User model saved to %s", path)

    def load_from_disk(self, path: Path) -> bool:
        """Load a previously saved model from disk."""
        path = Path(path).expanduser().resolve()
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._model = UserModel.from_dict(data)
            logger.info("User model loaded from %s", path)
            return True
        except Exception as e:
            logger.warning("Failed to load user model: %s", e)
            return False

    # ═══════════════════════════════════════════════════════
    # Event Handlers
    # ═══════════════════════════════════════════════════════

    def _on_window_changed(self, event: Event) -> None:
        """Update app usage and context switch stats from window changes."""
        current = event.data.get("current", {})
        app_name = current.get("process_name", "")
        if not app_name:
            return

        # Track app durations
        self._app_durations[app_name] = self._app_durations.get(app_name, 0) + 1

        # Track hourly activity
        hour = int(time.strftime("%H", time.localtime()))
        self._hourly_activity[hour] = self._hourly_activity.get(hour, 0) + 1

        # Update model: context switch frequency
        new_csf = self._ema_update(
            self._model.context_switch_frequency,
            self._hourly_switch_rate(),
        )

        # Update top apps
        top = self._compute_top_apps()

        # Detect primary tools
        editor = self._detect_editor(app_name)
        primary_editor = editor or self._model.primary_editor

        browser = self._detect_browser(app_name)
        primary_browser = browser or self._model.primary_browser

        # Detect project paths from window titles
        self._detect_project_from_title(current.get("title", ""))

        # Produce new immutable model
        self._model = UserModel(
            **{**self._model.__dict__,
               "context_switch_frequency": round(new_csf, 3),
               "top_apps": tuple(top),
               "primary_editor": primary_editor,
               "primary_browser": primary_browser,
               "active_projects": tuple(self._project_paths.keys())[-5:],
               "total_observations": self._model.total_observations + 1,
               "last_updated": time.time(),
               "confidence": min(self._model.confidence + 0.001, 1.0),
            }
        )

    def _on_clipboard_text(self, event: Event) -> None:
        """Detect programming languages from clipboard content."""
        text = event.data.get("text", "")
        category = event.data.get("category", "")
        if category != "code" or len(text) < 50:
            return

        detected = self._detect_language(text)
        if detected and detected not in self._language_detections:
            self._language_detections[detected] = 0
        if detected:
            self._language_detections[detected] += 1

        # Update language profile
        languages = self._compute_languages()
        primary = languages[0] if languages else self._model.primary_language

        self._model = UserModel(
            **{**self._model.__dict__,
               "languages": languages,
               "primary_language": primary,
               "total_observations": self._model.total_observations + 1,
               "last_updated": time.time(),
            }
        )

    def _on_file_modified(self, event: Event) -> None:
        """Detect project activity and languages from file modifications."""
        path = event.data.get("path", "")
        suffix = event.data.get("suffix", "")

        # Track project directories
        try:
            p = Path(path)
            self._project_paths[p.parent] = time.time()
        except Exception:
            pass

        # Detect language from file extension
        lang = _suffix_to_language(suffix)
        if lang:
            self._language_detections[lang] = self._language_detections.get(lang, 0) + 1
            languages = self._compute_languages()
            primary = languages[0] if languages else self._model.primary_language
            self._model = UserModel(
                **{**self._model.__dict__,
                   "languages": languages,
                   "primary_language": primary,
                   "total_observations": self._model.total_observations + 1,
                   "last_updated": time.time(),
                }
            )

    def _on_activity_session(self, event: Event) -> None:
        """Update work rhythm from session data."""
        duration = event.data.get("duration", 0)
        windows = event.data.get("windows_switched", 0)

        # Estimate focus duration
        if duration > 300:  # Sessions > 5 min
            new_avg = self._ema_update(
                self._model.avg_focus_duration_minutes,
                duration / 60.0,
            )
            deep = self._model.deep_work_sessions_today + (
                1 if duration > 1800 else 0  # >30 min = deep work
            )
            self._model = UserModel(
                **{**self._model.__dict__,
                   "avg_focus_duration_minutes": round(new_avg, 1),
                   "deep_work_sessions_today": deep,
                   "total_observations": self._model.total_observations + 1,
                   "last_updated": time.time(),
                }
            )

    def _on_activity_idle(self, event: Event) -> None:
        """Track break patterns."""
        idle_s = event.data.get("idle_seconds", 0)
        if 120 < idle_s < 7200:  # 2 min to 2 hours → probably a break
            breaks = list(self._model.break_pattern)
            breaks.append(idle_s / 60.0)  # Convert to minutes
            # Keep last 20 breaks
            breaks = breaks[-20:]
            self._model = UserModel(
                **{**self._model.__dict__,
                   "break_pattern": tuple(breaks),
                   "total_observations": self._model.total_observations + 1,
                   "last_updated": time.time(),
                }
            )

    def _on_activity_active(self, event: Event) -> None:
        """User returned from idle — update work hours."""
        hour = time.localtime().tm_hour + time.localtime().tm_min / 60.0

        # EMA update work start/end
        new_start = self._ema_update(self._model.work_start_hour, hour, rate=0.01)
        new_end = self._ema_update(self._model.work_end_hour, hour, rate=0.01)

        # Detect peak focus hours
        self._hourly_activity[time.localtime().tm_hour] = (
            self._hourly_activity.get(time.localtime().tm_hour, 0) + 2
        )
        peaks = self._compute_peak_hours()

        self._model = UserModel(
            **{**self._model.__dict__,
               "work_start_hour": round(new_start, 1),
               "work_end_hour": round(new_end, 1),
               "peak_focus_hours": peaks,
               "total_observations": self._model.total_observations + 1,
               "last_updated": time.time(),
            }
        )

    # ═══════════════════════════════════════════════════════
    # Computation Helpers
    # ═══════════════════════════════════════════════════════

    def _ema_update(self, old: float, new: float, rate: float | None = None) -> float:
        """Exponential moving average update."""
        r = rate if rate is not None else self._lr
        return old + r * (new - old)

    def _hourly_switch_rate(self) -> float:
        """Compute context switches per hour based on recent activity."""
        total = sum(self._hourly_activity.values())
        if total == 0:
            return 0.0
        hours = max(len(self._hourly_activity), 1)
        return total / hours

    def _compute_top_apps(self, limit: int = 8) -> list[tuple[str, float]]:
        """Compute top-used applications."""
        total = sum(self._app_durations.values()) or 1
        sorted_apps = sorted(
            self._app_durations.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return [(app, round(count / total, 3)) for app, count in sorted_apps[:limit]]

    def _compute_languages(self) -> tuple[str, ...]:
        """Compute detected programming languages sorted by frequency."""
        sorted_langs = sorted(
            self._language_detections.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return tuple(lang for lang, _ in sorted_langs)

    def _compute_peak_hours(self) -> tuple[tuple[float, float], ...]:
        """Detect peak focus hours from hourly activity distribution."""
        if not self._hourly_activity:
            return ()
        total = sum(self._hourly_activity.values()) or 1
        threshold = total / len(self._hourly_activity) * 1.2

        peaks = []
        in_peak = False
        start = 0.0
        for hour in sorted(self._hourly_activity.keys()):
            count = self._hourly_activity[hour]
            if count >= threshold and not in_peak:
                start = float(hour)
                in_peak = True
            elif count < threshold and in_peak:
                peaks.append((start, float(hour)))
                in_peak = False
        if in_peak:
            peaks.append((start, float(sorted(self._hourly_activity.keys())[-1]) + 1))

        return tuple(peaks)

    def _detect_editor(self, app_name: str) -> str | None:
        """Detect primary editor from process name."""
        editors = {
            "code": "vscode", "code-insiders": "vscode",
            "pycharm": "pycharm", "idea": "intellij",
            "nvim": "neovim", "vim": "vim",
            "notepad++": "notepad++", "sublime_text": "sublime",
            "cursor": "cursor", "windsurf": "windsurf",
        }
        app_lower = app_name.lower().replace(".exe", "")
        for key, editor_name in editors.items():
            if key in app_lower:
                return editor_name
        return None

    def _detect_browser(self, app_name: str) -> str | None:
        """Detect primary browser from process name."""
        browsers = ["chrome", "firefox", "msedge", "brave", "opera", "arc"]
        app_lower = app_name.lower()
        for b in browsers:
            if b in app_lower:
                return b
        return None

    def _detect_project_from_title(self, title: str) -> None:
        """Extract project path hints from window titles."""
        # VS Code format: "file.py — ProjectName"
        if " — " in title:
            parts = title.split(" — ")
            if len(parts) >= 2:
                project = parts[-1]
                self._project_paths[project] = time.time()

    def _detect_language(self, text: str) -> str | None:
        """Detect programming language from code text."""
        # Heuristic keyword matching
        lang_markers = {
            "python": ["def ", "import ", "from ", "class ", "self.", "__init__"],
            "typescript": ["interface ", "type ", "const ", "async ", "export "],
            "javascript": ["function ", "const ", "let ", "var ", "require("],
            "rust": ["fn ", "let mut ", "impl ", "struct ", "crate"],
            "go": ["func ", "package ", "defer ", "goroutine"],
            "java": ["public class", "private ", "void ", "String "],
            "cpp": ["#include", "std::", "template<"],
            "sql": ["SELECT ", "FROM ", "INSERT ", "CREATE TABLE"],
        }
        text_lower = text.lower()
        for lang, markers in lang_markers.items():
            hits = sum(1 for m in markers if m.lower() in text_lower)
            if hits >= 2:
                return lang
        return None


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _suffix_to_language(suffix: str) -> str | None:
    """Map file extension to language name."""
    lang_map = {
        ".py": "python", ".pyi": "python",
        ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript", ".jsx": "javascript",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".h": "cpp", ".hpp": "cpp",
        ".sql": "sql",
        ".html": "html", ".css": "css",
        ".json": "json", ".yaml": "yaml", ".yml": "yaml",
        ".md": "markdown",
        ".toml": "toml",
    }
    return lang_map.get(suffix.lower())
