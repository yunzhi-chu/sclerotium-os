"""Structured JSON Logger — pino-style (Gap 22).

All logs are JSON objects with standard fields: level, time, module, msg, data, err.
Supports both human-readable console output and JSON file output.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LogEntry:
    """A single structured log entry (immutable)."""
    level: str
    msg: str
    module: str = ""
    time: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))
    data: dict[str, Any] = field(default_factory=dict)
    err: str = ""


class StructuredLogger:
    """JSON-structured logger — pino-style output.

    Usage:
        slog = StructuredLogger("sclerotium.agent")
        slog.info("Agent started", tools=191, model="deepseek-v4-flash")
        slog.warn("Retry", attempt=2, provider="deepseek")
        slog.error("LLM failed", err=str(e), provider="openai")
    """

    LEVELS = {"debug": 10, "info": 20, "warn": 30, "error": 40, "fatal": 50}

    def __init__(
        self, module: str,
        json_file: str | None = None,
        min_level: str = "info",
    ) -> None:
        self.module = module
        self.min_level = self.LEVELS.get(min_level, 20)
        self._file = open(json_file, "a", encoding="utf-8") if json_file else None

    def _log(self, level: str, msg: str, **kwargs: Any) -> None:
        if self.LEVELS.get(level, 0) < self.min_level:
            return

        entry = LogEntry(
            level=level,
            msg=msg,
            module=self.module,
            data={k: v for k, v in kwargs.items() if k != "err"} if kwargs else {},
            err=str(kwargs.get("err", "")),
        )

        # JSON line
        line = json.dumps({
            "level": entry.level,
            "time": entry.time,
            "module": entry.module,
            "msg": entry.msg,
            **({"data": entry.data} if entry.data else {}),
            **({"err": entry.err} if entry.err else {}),
        }, ensure_ascii=False, default=str)

        # Console: human-readable
        prefix = {"debug": "·", "info": "→", "warn": "⚠", "error": "✗", "fatal": "‼"}.get(level, "?")
        extras = ""
        if entry.data:
            extras = " " + " ".join(f"{k}={v}" for k, v in list(entry.data.items())[:3])
        if entry.err:
            extras += f" err={entry.err[:80]}"
        print(f"  {prefix} {msg}{extras}", file=sys.stderr, flush=True)

        # File: JSON line
        if self._file:
            self._file.write(line + "\n")
            self._file.flush()

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._log("debug", msg, **kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        self._log("info", msg, **kwargs)

    def warn(self, msg: str, **kwargs: Any) -> None:
        self._log("warn", msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        self._log("error", msg, **kwargs)

    def fatal(self, msg: str, **kwargs: Any) -> None:
        self._log("fatal", msg, **kwargs)

    def close(self) -> None:
        if self._file:
            self._file.close()


# Global convenience
_loggers: dict[str, StructuredLogger] = {}

def get_logger(module: str) -> StructuredLogger:
    if module not in _loggers:
        _loggers[module] = StructuredLogger(module)
    return _loggers[module]
