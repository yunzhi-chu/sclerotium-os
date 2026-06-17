"""L6 M1: MetaCognition Engine — 8-dimension health scan + auto-refactoring orchestration.

The central orchestrator of the L6 cognitive platform.
Runs periodic full system scans, triggers refactoring, integrates with
FINAL Bench validation, and emits health reports.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from src.core.event_bus import EventBus
from src.core.skill_registry import SkillRegistry
from src.l6.architecture_scanner import ArchitectureIssue, ArchitectureScanner, IssueSeverity
from src.l6.auto_refactor import AutoRefactorEngine, RefactorStatus
from src.utils.logging import CortexLogger


@dataclass
class HealthReport:
    """Complete system health assessment from a full M1 scan."""

    health_score: int  # 0-100
    total_issues: int
    open_critical: int
    open_high: int
    open_medium: int
    open_low: int
    total_fixed: int
    pending_approvals: int
    recommendations: list[str]
    timestamp: float = field(default_factory=time.time)


class MetaCognitionEngine:
    """M1: The brain's self-awareness module.

    Full scan cycle:
    1. ArchitectureScanner.full_scan() → 8-dimension issues
    2. AutoRefactorEngine.process_issues() → apply/queue
    3. Generate HealthReport
    4. Publish events to event bus
    5. (Phase 2) Bridge to FINALBenchValidator for MA-ER scoring

    Config:
    - scan_interval_seconds: how often to run full scan (default 3600)
    - auto_refactor_enabled: auto-apply fixable issues
    - require_human_approval: gate non-trivial changes
    """

    def __init__(
        self,
        skill_registry: SkillRegistry,
        event_bus: EventBus | None = None,
        scan_interval: float = 3600.0,
        auto_refactor_enabled: bool = True,
        require_human_approval: bool = True,
    ) -> None:
        self._registry = skill_registry
        self._event_bus = event_bus
        self.scan_interval = scan_interval
        self.scanner = ArchitectureScanner(skill_registry)
        self.refactor_engine = AutoRefactorEngine(
            auto_refactor_enabled=auto_refactor_enabled,
            require_human_approval=require_human_approval,
        )
        self._logger = CortexLogger("meta_cognition")

        # State
        self._last_scan_time: float = 0.0
        self._scan_count = 0
        self._health_history: list[HealthReport] = []
        self._running = False
        self._scan_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the periodic scan loop."""
        self._running = True
        self._scan_task = asyncio.create_task(self._scan_loop())
        self._logger.info("meta_cognition_started", scan_interval_s=self.scan_interval)

    async def stop(self) -> None:
        """Stop the periodic scan loop."""
        self._running = False
        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass
        self._logger.info("meta_cognition_stopped", total_scans=self._scan_count)

    async def _scan_loop(self) -> None:
        """Periodic full scan loop."""
        while self._running:
            try:
                await asyncio.sleep(self.scan_interval)
                await self.full_scan()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._logger.error("scan_loop_error", error=str(exc))

    async def full_scan(self) -> HealthReport:
        """Execute a complete M1 full scan cycle.

        Returns a HealthReport summarizing system state.
        """
        t0 = time.perf_counter()
        self._scan_count += 1

        # 1. Scan all 8 dimensions
        issues = self.scanner.full_scan()
        self._logger.info("scan_complete", issues=len(issues), scan_number=self._scan_count)

        # 2. Process through refactor engine
        refactor_result = self.refactor_engine.process_issues(issues)

        # 3. Build health report
        report = self._build_report(issues)

        # 4. Store history
        self._health_history.append(report)
        if len(self._health_history) > 100:
            self._health_history = self._health_history[-100:]

        self._last_scan_time = time.time()

        # 5. Emit events
        if self._event_bus:
            await self._event_bus.publish_nowait("l6.scan.complete", {
                "report": self._report_to_dict(report),
                "refactor_result": refactor_result,
                "latency_ms": (time.perf_counter() - t0) * 1000,
            })

        self._logger.info("health_report", health_score=report.health_score, critical=report.open_critical)
        return report

    def _build_report(self, issues: list[ArchitectureIssue]) -> HealthReport:
        """Compute health score and aggregate issue counts."""
        # Severity weights for health score
        weights = {IssueSeverity.CRITICAL: 25, IssueSeverity.HIGH: 10, IssueSeverity.MEDIUM: 5, IssueSeverity.LOW: 2, IssueSeverity.INFO: 0}

        penalty = sum(weights.get(i.severity, 0) for i in issues)
        locked = sum(weights[s] * c for s, c in {IssueSeverity.CRITICAL: 1, IssueSeverity.HIGH: 2, IssueSeverity.MEDIUM: 3, IssueSeverity.LOW: 4, IssueSeverity.INFO: 0}.items())

        # Health starts at 100 and degrades with issue severity
        health_score = max(0, int(100 - penalty * 0.5))

        recommendations: list[str] = []
        criticals = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        if criticals:
            recommendations.append(f"Address {len(criticals)} CRITICAL issues immediately")
        if health_score < 70:
            recommendations.append("Schedule system-wide architecture review")
        if health_score < 50:
            recommendations.append("Consider pausing auto-refactor and entering maintenance mode")
        if self.refactor_engine._pending_count >= 8:
            recommendations.append(f"Review {self.refactor_engine._pending_count} pending approvals")

        refactor_stats = self.refactor_engine.stats

        return HealthReport(
            health_score=health_score,
            total_issues=len(issues),
            open_critical=sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL),
            open_high=sum(1 for i in issues if i.severity == IssueSeverity.HIGH),
            open_medium=sum(1 for i in issues if i.severity == IssueSeverity.MEDIUM),
            open_low=sum(1 for i in issues if i.severity == IssueSeverity.LOW),
            total_fixed=refactor_stats["applied"],
            pending_approvals=refactor_stats["pending"],
            recommendations=recommendations,
        )

    def get_health_report(self) -> HealthReport:
        """Get the most recent health report, or run a scan if none exists."""
        if not self._health_history:
            # Run a synchronous scan (for simple cases where async isn't available)
            issues = self.scanner.full_scan()
            self.refactor_engine.process_issues(issues)
            report = self._build_report(issues)
            self._health_history.append(report)
            return report
        return self._health_history[-1]

    async def auto_refactor(self, issue_ids: list[str]) -> dict[str, Any]:
        """Attempt to auto-refactor specific issues by ID."""
        results = {}
        all_issues = self.scanner.full_scan()
        targeted = [i for i in all_issues if i.id in issue_ids]
        for issue in targeted:
            success = self.refactor_engine._apply_refactor(
                self.refactor_engine._process_single(issue)
            )
            results[issue.id] = "applied" if success else "failed"
        return results

    def approve_refactor(self, action_id: str) -> bool:
        """Approve a pending refactoring action."""
        return self.refactor_engine.approve(action_id)

    def reject_refactor(self, action_id: str) -> bool:
        """Reject a pending refactoring action."""
        return self.refactor_engine.reject(action_id)

    def rollback_refactor(self, action_id: str) -> bool:
        """Roll back a previously applied refactoring."""
        return self.refactor_engine.rollback(action_id)

    def _report_to_dict(self, report: HealthReport) -> dict[str, Any]:
        return {
            "health_score": report.health_score,
            "total_issues": report.total_issues,
            "open_critical": report.open_critical,
            "open_high": report.open_high,
            "open_medium": report.open_medium,
            "open_low": report.open_low,
            "total_fixed": report.total_fixed,
            "pending_approvals": report.pending_approvals,
            "recommendations": report.recommendations,
            "timestamp": report.timestamp,
        }

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "scan_count": self._scan_count,
            "last_scan_time": self._last_scan_time,
            "scanner": self.scanner.scan_stats,
            "refactor": self.refactor_engine.stats,
        }
