"""Config Watcher — 热重载无需重启 (Gap 20).

Watches configuration files/directories for changes and fires event callbacks.
Enables runtime config updates without restarting Sclerotium OS.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("sclerotium.config")


@dataclass(frozen=True)
class ConfigChange:
    """A detected configuration change (immutable)."""
    path: str
    event_type: str  # "created", "modified", "deleted"
    timestamp: float = field(default_factory=time.time)


class ConfigWatcher:
    """Polling-based config file watcher.

    Usage:
        watcher = ConfigWatcher()
        watcher.watch("config.yaml", lambda change: print(f"Reload: {change.path}"))
        await watcher.start()  # Background polling loop
    """

    def __init__(self, poll_interval: float = 2.0) -> None:
        self._poll_interval = poll_interval
        self._watches: dict[str, tuple[float, Callable[[ConfigChange], None]]] = {}
        self._running = False
        self._task: asyncio.Task | None = None

    def watch(
        self, path: str,
        callback: Callable[[ConfigChange], Any],
    ) -> None:
        """Watch a file/directory for changes.

        Args:
            path: File or directory path to watch
            callback: Called with ConfigChange when change detected
        """
        p = Path(path)
        if p.exists():
            mtime = p.stat().st_mtime
        else:
            mtime = 0
        self._watches[str(p)] = (mtime, callback)
        logger.info("Watching: %s", path)

    def unwatch(self, path: str) -> None:
        self._watches.pop(str(Path(path)), None)

    async def start(self) -> None:
        """Start background polling loop."""
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """Stop background polling."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _poll_loop(self) -> None:
        """Poll watched files for changes."""
        while self._running:
            for path_str, (last_mtime, callback) in list(self._watches.items()):
                p = Path(path_str)
                if not p.exists():
                    if last_mtime > 0:
                        # File was deleted
                        change = ConfigChange(path=path_str, event_type="deleted")
                        try:
                            callback(change)
                        except Exception as e:
                            logger.warning("Config callback error: %s", e)
                        self._watches[path_str] = (0, callback)
                    continue

                current_mtime = p.stat().st_mtime
                if current_mtime > last_mtime:
                    change = ConfigChange(
                        path=path_str,
                        event_type="created" if last_mtime == 0 else "modified",
                    )
                    try:
                        callback(change)
                    except Exception as e:
                        logger.warning("Config callback error: %s", e)
                    self._watches[path_str] = (current_mtime, callback)

            await asyncio.sleep(self._poll_interval)

    def check_now(self) -> list[ConfigChange]:
        """Synchronous one-shot check. Returns list of changes."""
        changes = []
        for path_str, (last_mtime, _) in list(self._watches.items()):
            p = Path(path_str)
            if not p.exists():
                continue
            current_mtime = p.stat().st_mtime
            if current_mtime > last_mtime:
                changes.append(ConfigChange(path=path_str, event_type="modified"))
                self._watches[path_str] = (current_mtime, self._watches[path_str][1])
        return changes
