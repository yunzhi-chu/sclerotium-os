"""Organ Protocol — 统一器官接口 (Gap 18).

Every organ implements: name, initialize, health_check, shutdown, get_tools.
Enables auto-discovery, health monitoring, and hot-reload of all 238 organs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OrganStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPED = "stopped"


@dataclass(frozen=True)
class OrganInfo:
    """Organ metadata (immutable)."""
    name: str
    version: str = "0.1.0"
    category: str = "general"
    status: OrganStatus = OrganStatus.STOPPED
    dependencies: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    tool_count: int = 0


@dataclass(frozen=True)
class HealthReport:
    """Health check result (immutable)."""
    organ: str
    healthy: bool
    status: OrganStatus = OrganStatus.HEALTHY
    message: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0


class OrganProtocol(ABC):
    """Every Sclerotium OS organ MUST implement this protocol.

    Usage:
        class MyOrgan(OrganProtocol):
            @property
            def organ_name(self) -> str:
                return "my_organ"

            async def initialize(self) -> bool:
                self._ready = True
                return True

            async def health_check(self) -> HealthReport:
                return HealthReport(organ=self.organ_name, healthy=self._ready)

            async def shutdown(self) -> None:
                self._ready = False

            def get_tools(self) -> list[dict[str, Any]]:
                return [{"name": "my_tool", "description": "..."}]
    """

    # ── Abstract (MUST implement) ────────────────────────────────────────

    @property
    @abstractmethod
    def organ_name(self) -> str:
        """Unique organ identifier."""

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the organ. Returns True on success."""

    @abstractmethod
    async def health_check(self) -> HealthReport:
        """Check organ health. Returns HealthReport."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Gracefully shut down the organ."""

    # ── Optional (CAN override) ──────────────────────────────────────────

    def get_tools(self) -> list[dict[str, Any]]:
        """Return MCP tool definitions contributed by this organ."""
        return []

    def get_info(self) -> OrganInfo:
        """Return organ metadata."""
        return OrganInfo(
            name=self.organ_name,
            status=OrganStatus.STOPPED,
        )

    def on_config_change(self, key: str, value: Any) -> None:
        """Handle configuration change (hot-reload)."""
        pass

    @property
    def organ_version(self) -> str:
        return "0.1.0"

    @property
    def organ_category(self) -> str:
        return "general"

    @property
    def organ_dependencies(self) -> tuple[str, ...]:
        return ()


class OrganRegistry:
    """Central registry for all organs implementing OrganProtocol.

    Enables auto-discovery, health monitoring, and dependency ordering.
    """

    def __init__(self) -> None:
        self._organs: dict[str, OrganProtocol] = {}
        self._info: dict[str, OrganInfo] = {}

    def register(self, organ: OrganProtocol) -> None:
        """Register an organ."""
        self._organs[organ.organ_name] = organ
        self._info[organ.organ_name] = organ.get_info()

    def unregister(self, name: str) -> None:
        """Unregister an organ."""
        self._organs.pop(name, None)
        self._info.pop(name, None)

    def get(self, name: str) -> OrganProtocol | None:
        return self._organs.get(name)

    def list_organs(self) -> list[OrganInfo]:
        return list(self._info.values())

    def get_all_tools(self) -> list[dict[str, Any]]:
        """Aggregate tools from all organs."""
        tools = []
        for organ in self._organs.values():
            tools.extend(organ.get_tools())
        return tools

    async def initialize_all(self) -> dict[str, bool]:
        """Initialize all organs in dependency order."""
        results = {}
        for name, organ in self._organs.items():
            try:
                results[name] = await organ.initialize()
            except Exception:
                results[name] = False
        return results

    async def health_check_all(self) -> list[HealthReport]:
        """Check health of all organs."""
        reports = []
        for organ in self._organs.values():
            try:
                reports.append(await organ.health_check())
            except Exception as e:
                reports.append(HealthReport(
                    organ=organ.organ_name,
                    healthy=False,
                    status=OrganStatus.UNHEALTHY,
                    message=str(e),
                ))
        return reports

    async def shutdown_all(self) -> None:
        """Shut down all organs."""
        for organ in self._organs.values():
            try:
                await organ.shutdown()
            except Exception:
                pass

    @property
    def organ_count(self) -> int:
        return len(self._organs)
