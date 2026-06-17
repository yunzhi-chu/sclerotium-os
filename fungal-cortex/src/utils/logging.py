"""Structured logging with Prometheus-compatible format."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class StructuredLog:
    """Single structured log entry compatible with OpenTelemetry pipelines."""

    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    level: str = "INFO"
    module: str = "fungal_cortex"
    agent_id: str = ""
    event: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps({
            "timestamp": self.timestamp,
            "level": self.level,
            "module": self.module,
            "agent_id": self.agent_id,
            "event": self.event,
            **self.data,
        }, ensure_ascii=False)


class CortexLogger:
    """Structured logger for fungal cortex. Emits JSON lines to stdout/stderr."""

    def __init__(self, module: str = "fungal_cortex", agent_id: str = "") -> None:
        self.module = module
        self.agent_id = agent_id
        self._python_logger = logging.getLogger(f"cortex.{module}")

    def _log(self, level: str, event: str, **kwargs: Any) -> None:
        entry = StructuredLog(level=level, module=self.module, agent_id=self.agent_id, event=event, data=kwargs)
        self._python_logger.log(getattr(logging, level), entry.to_json())

    def info(self, event: str, **kwargs: Any) -> None:
        self._log("INFO", event, **kwargs)

    def warn(self, event: str, **kwargs: Any) -> None:
        self._log("WARNING", event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._log("ERROR", event, **kwargs)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._log("DEBUG", event, **kwargs)


def setup_root_logger(level: str = "INFO") -> None:
    """Configure root logger for JSON-line output."""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger("cortex")
    root.setLevel(getattr(logging, level.upper()))
    root.handlers.clear()
    root.addHandler(handler)
    root.propagate = False
