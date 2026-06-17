"""Mechanism ⑬: Architecture Scanner — 8-dimensional architecture health analysis.

Inspired by osteocyte networks that sense mechanical stress in bone:
- Redundancy: duplicated functionality wasting resources
- Coupling: excessive module interdependence (should be low)
- Latency: response time bottlenecks
- Algorithm Gap: missing optimization opportunities
- Skill Gap: missing capabilities in the skill registry
- Bottleneck: throughput-limiting nodes
- Dead Code: unused skills/functions
- Error Pattern: recurring failure clusters

Each scan dimension produces a list of ArchitectureIssue objects.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.skill_registry import SkillRegistry
from src.utils.logging import CortexLogger


class IssueSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass(slots=True)
class ArchitectureIssue:
    """A single architectural issue detected by a scanner."""

    id: str
    dimension: str  # e.g., "redundancy", "coupling", "latency"
    severity: IssueSeverity
    title: str
    description: str
    location: str = ""  # e.g., "module.quant-strategies", "l6.meta_cognition"
    evidence: dict[str, Any] = field(default_factory=dict)
    auto_fixable: bool = False
    suggested_fix: str = ""
    detected_at: float = field(default_factory=time.time)


class ArchitectureScanner:
    """8-dimensional architecture health scanner.

    Each _scan_* method inspects a specific dimension and returns
    a list of ArchitectureIssue objects. The dimensions parallel
    the L6 SKILL.md _scan_* methods 1:1.
    """

    def __init__(self, skill_registry: SkillRegistry | None = None) -> None:
        self.skill_registry = skill_registry
        self._logger = CortexLogger("architecture_scanner")
        self._scan_history: list[dict[str, Any]] = []
        self._event_counts: dict[str, int] = {}  # for error pattern detection
        self._call_timings: dict[str, list[float]] = {}  # for latency/bottleneck detection

    def full_scan(self) -> list[ArchitectureIssue]:
        """Execute all 8 dimension scans. Returns aggregated issues sorted by severity."""
        issues: list[ArchitectureIssue] = []
        for scanner in [
            self._scan_redundancy,
            self._scan_coupling,
            self._scan_latency,
            self._scan_algorithm_gap,
            self._scan_skill_gap,
            self._scan_bottleneck,
            self._scan_dead_code,
            self._scan_error_pattern,
        ]:
            try:
                issues.extend(scanner())
            except Exception as exc:
                self._logger.error("scan_error", scanner=scanner.__name__, error=str(exc))

        severity_order = {IssueSeverity.CRITICAL: 0, IssueSeverity.HIGH: 1, IssueSeverity.MEDIUM: 2, IssueSeverity.LOW: 3, IssueSeverity.INFO: 4}
        issues.sort(key=lambda i: severity_order[i.severity])

        self._scan_history.append({
            "timestamp": time.time(),
            "total_issues": len(issues),
            "by_severity": {s.value: sum(1 for i in issues if i.severity == s) for s in IssueSeverity},
        })

        return issues

    def _scan_redundancy(self) -> list[ArchitectureIssue]:
        """Detect redundant functionality across modules.

        Two skills with Jaccard similarity > 0.8 on keyword sets → possible redundancy.
        """
        if self.skill_registry is None:
            return []
        issues: list[ArchitectureIssue] = []
        skills = self.skill_registry.list_all()
        for i in range(len(skills)):
            for j in range(i + 1, len(skills)):
                sk_i, sk_j = skills[i], skills[j]
                if not sk_i.keywords or not sk_j.keywords:
                    continue
                si = set(sk_i.keywords)
                sj = set(sk_j.keywords)
                jaccard = len(si & sj) / len(si | sj) if si | sj else 0
                if jaccard > 0.8 and sk_i.module != sk_j.module:
                    issues.append(ArchitectureIssue(
                        id=f"redundancy-{sk_i.name}-{sk_j.name}",
                        dimension="redundancy",
                        severity=IssueSeverity.MEDIUM if jaccard < 0.95 else IssueSeverity.HIGH,
                        title=f"Redundant skills: {sk_i.name} ≈ {sk_j.name}",
                        description=f"Jaccard similarity {jaccard:.2f} on keywords across modules {sk_i.module}/{sk_j.module}",
                        evidence={"skill_a": sk_i.name, "skill_b": sk_j.name, "jaccard": jaccard},
                        auto_fixable=False,
                        suggested_fix=f"Consider merging {sk_i.name} and {sk_j.name} or differentiating their scopes.",
                    ))
        return issues

    def _scan_coupling(self) -> list[ArchitectureIssue]:
        """Detect excessive module coupling via skill dependency graph.

        High indegree (>5 dependents) → strong coupling → fragility risk.
        """
        if self.skill_registry is None:
            return []
        issues: list[ArchitectureIssue] = []
        indegree: dict[str, set[str]] = {}
        for skill in self.skill_registry.list_all():
            for dep in skill.dependencies:
                indegree.setdefault(dep, set()).add(skill.name)
        for skill_name, dependents in indegree.items():
            if len(dependents) >= 5:
                issues.append(ArchitectureIssue(
                    id=f"coupling-{skill_name}",
                    dimension="coupling",
                    severity=IssueSeverity.HIGH if len(dependents) >= 8 else IssueSeverity.MEDIUM,
                    title=f"High coupling: {skill_name} has {len(dependents)} dependents",
                    description=f"Skill acts as bottleneck dependency for {', '.join(sorted(dependents))}",
                    evidence={"skill": skill_name, "dependent_count": len(dependents), "dependents": sorted(dependents)},
                    auto_fixable=False,
                    suggested_fix="Consider splitting into smaller sub-skills or introducing an abstraction layer.",
                ))
        return issues

    def _scan_latency(self) -> list[ArchitectureIssue]:
        """Detect high-latency call paths from timing data."""
        issues: list[ArchitectureIssue] = []
        for path, timings in self._call_timings.items():
            if not timings:
                continue
            avg_ms = sum(timings) / len(timings)
            p99_ms = sorted(timings)[int(len(timings) * 0.99)] if len(timings) >= 100 else max(timings)
            if avg_ms > 2000:  # >2s avg
                severity = IssueSeverity.CRITICAL
            elif avg_ms > 1000:
                severity = IssueSeverity.HIGH
            elif avg_ms > 500:
                severity = IssueSeverity.MEDIUM
            else:
                continue
            issues.append(ArchitectureIssue(
                id=f"latency-{path.replace('.', '-')}",
                dimension="latency",
                severity=severity,
                title=f"High latency: {path} avg={avg_ms:.0f}ms p99={p99_ms:.0f}ms",
                description=f"Response time exceeds threshold. Check I/O, model calls, or database queries.",
                evidence={"path": path, "avg_ms": avg_ms, "p99_ms": p99_ms, "sample_count": len(timings)},
                auto_fixable=False,
                suggested_fix="Add caching, parallelize I/O, or use async pipeline.",
            ))
        return issues

    def _scan_algorithm_gap(self) -> list[ArchitectureIssue]:
        """Detect algorithm gaps: areas where optimization is possible but missing."""
        issues: list[ArchitectureIssue] = []
        patterns = [
            ("sequential_loop", "Parallel processing opportunity — for-loop over independent items"),
            ("eager_compute", "Lazy evaluation opportunity — computing values not immediately needed"),
            ("linear_search", "Hash-based lookup opportunity — O(n) search when O(1) possible"),
            ("sync_io", "Async I/O opportunity — blocking call on event loop"),
        ]
        for pattern_name, description in patterns:
            count = self._event_counts.get(pattern_name, 0)
            if count >= 3:
                issues.append(ArchitectureIssue(
                    id=f"alg_gap-{pattern_name}",
                    dimension="algorithm_gap",
                    severity=IssueSeverity.LOW,
                    title=f"Algorithm gap: {description}",
                    description=f"Detected {count} occurrences of '{pattern_name}' pattern",
                    evidence={"pattern": pattern_name, "occurrences": count},
                    auto_fixable=True,
                    suggested_fix=f"Replace {pattern_name} pattern with optimized alternative.",
                ))
        return issues

    def _scan_skill_gap(self) -> list[ArchitectureIssue]:
        """Detect missing skills: capability gaps in the ecosystem.

        Compares current skill coverage against expected capability matrix.
        """
        if self.skill_registry is None:
            return []
        issues: list[ArchitectureIssue] = []
        expected_domains = {
            "data": ["ingestion", "cleaning", "validation", "storage"],
            "analysis": ["statistical", "fundamental", "technical", "sentiment"],
            "execution": ["backtest", "papertrade", "risk_check", "order_routing"],
            "monitoring": ["alerting", "dashboard", "audit", "drift_detection"],
            "meta": ["self_heal", "auto_scale", "model_selection", "hyperparameter_tuning"],
        }
        skills = self.skill_registry.list_all()
        covered_keywords = set()
        for skill in skills:
            covered_keywords.update(k.lower() for k in skill.keywords)

        for domain, capabilities in expected_domains.items():
            missing = [c for c in capabilities if c.lower() not in covered_keywords]
            if missing:
                issues.append(ArchitectureIssue(
                    id=f"skill_gap-{domain}",
                    dimension="skill_gap",
                    severity=IssueSeverity.MEDIUM if len(missing) <= 2 else IssueSeverity.HIGH,
                    title=f"Skill gap in {domain}: missing {missing}",
                    description=f"Domain '{domain}' lacks capabilities: {', '.join(missing)}",
                    evidence={"domain": domain, "missing_capabilities": missing},
                    auto_fixable=False,
                    suggested_fix=f"Consider creating skills for: {', '.join(missing)}. Trigger M2 AbilityCreationFactory.",
                ))
        return issues

    def _scan_bottleneck(self) -> list[ArchitectureIssue]:
        """Detect throughput bottlenecks from timing and resource data."""
        issues: list[ArchitectureIssue] = []
        for path, timings in self._call_timings.items():
            if len(timings) < 10:
                continue
            throughput = len(timings) / (max(timings) - min(timings) + 0.001)
            if throughput < 0.5:  # <0.5 ops/sec
                issues.append(ArchitectureIssue(
                    id=f"bottleneck-{path.replace('.', '-')}",
                    dimension="bottleneck",
                    severity=IssueSeverity.HIGH,
                    title=f"Throughput bottleneck: {path} ({throughput:.2f} ops/sec)",
                    description=f"Operation throughput critically low. Check resource contention, lock contention, or I/O saturation.",
                    evidence={"path": path, "throughput_ops_per_sec": throughput},
                    auto_fixable=False,
                    suggested_fix="Profile resource usage, add connection pooling, or batch operations.",
                ))
        return issues

    def _scan_dead_code(self) -> list[ArchitectureIssue]:
        """Detect dead code: skills with zero recent invocations."""
        if self.skill_registry is None:
            return []
        issues: list[ArchitectureIssue] = []
        now = time.time()
        for skill in self.skill_registry.list_all():
            if not skill.enabled:
                issues.append(ArchitectureIssue(
                    id=f"dead_code-disabled-{skill.name}",
                    dimension="dead_code",
                    severity=IssueSeverity.LOW,
                    title=f"Disabled skill: {skill.name}",
                    description=f"Skill has been manually disabled. Remove or re-enable.",
                    evidence={"skill": skill.name},
                    auto_fixable=True,
                    suggested_fix=f"Unregister {skill.name} or re-enable with justification.",
                ))
            elif skill.last_called > 0 and (now - skill.last_called) > 30 * 86400:  # 30 days
                issues.append(ArchitectureIssue(
                    id=f"dead_code-stale-{skill.name}",
                    dimension="dead_code",
                    severity=IssueSeverity.MEDIUM,
                    title=f"Stale skill: {skill.name} (last called {int((now - skill.last_called) / 86400)}d ago)",
                    description=f"Skill has no recent invocations. Consider removing or archiving.",
                    evidence={"skill": skill.name, "days_since_last_call": int((now - skill.last_called) / 86400)},
                    auto_fixable=True,
                    suggested_fix=f"Archive or unregister {skill.name} if permanently unused.",
                ))
        return issues

    def _scan_error_pattern(self) -> list[ArchitectureIssue]:
        """Detect recurring error clusters."""
        issues: list[ArchitectureIssue] = []
        error_threshold = 5
        for event_type, count in self._event_counts.items():
            if "error" in event_type.lower() and count >= error_threshold:
                issues.append(ArchitectureIssue(
                    id=f"error_pattern-{event_type.replace('.', '-')}",
                    dimension="error_pattern",
                    severity=IssueSeverity.HIGH if count >= 20 else IssueSeverity.MEDIUM,
                    title=f"Recurring error: {event_type} ({count} occurrences)",
                    description=f"Error pattern '{event_type}' has occurred {count} times. Root cause analysis needed.",
                    evidence={"error_type": event_type, "occurrences": count},
                    auto_fixable=False,
                    suggested_fix="Investigate root cause. Consider adding circuit breaker or input validation.",
                ))
        return issues

    # --- Instrumentation API ---

    def record_timing(self, path: str, latency_ms: float) -> None:
        """Record an operation's latency for latency/bottleneck scanning."""
        self._call_timings.setdefault(path, []).append(latency_ms)
        if len(self._call_timings[path]) > 1000:
            self._call_timings[path] = self._call_timings[path][-1000:]

    def record_event(self, event_type: str) -> None:
        """Record an event occurrence for error pattern / algorithm gap scanning."""
        self._event_counts[event_type] = self._event_counts.get(event_type, 0) + 1

    @property
    def scan_stats(self) -> dict[str, Any]:
        if not self._scan_history:
            return {"scans": 0}
        last = self._scan_history[-1]
        return {
            "total_scans": len(self._scan_history),
            "last_scan": last,
        }
