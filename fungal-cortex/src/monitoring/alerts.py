"""Alert Manager — severity-based alerting with notification routing.

Alert severity levels:
- CRITICAL: System failure, data loss, trading halt — immediate paging
- HIGH: Performance degradation, risk breach — notification within 5min
- MEDIUM: Anomaly detected, approaching limit — notification within 30min
- LOW: Informational, potential optimization — daily digest

Alert sources:
- L6 health scan issues (CRITICAL/HIGH severity)
- Risk gate BLOCK events
- Pipeline bottleneck detection
- Immune system anomaly detection
- Phase transition events (DEGENERATE state)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class AlertSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def response_time_minutes(self) -> int:
        return {
            AlertSeverity.CRITICAL: 1,
            AlertSeverity.HIGH: 5,
            AlertSeverity.MEDIUM: 30,
            AlertSeverity.LOW: 1440,  # 24 hours (daily digest)
        }[self]


class AlertStatus(Enum):
    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """A rule that triggers an alert when a condition is met."""

    name: str
    description: str
    severity: AlertSeverity
    metric_name: str  # Metric to monitor
    condition: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    cooldown_seconds: float = 300.0  # Minimum time between repeated alerts
    enabled: bool = True


@dataclass
class Alert:
    """A triggered alert instance."""

    alert_id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.FIRING
    message: str = ""
    metric_value: float = 0.0
    threshold: float = 0.0
    source: str = ""
    fired_at: float = field(default_factory=time.time)
    acknowledged_at: float = 0.0
    resolved_at: float = 0.0

    @property
    def duration_seconds(self) -> float:
        end = self.resolved_at or time.time()
        return end - self.fired_at


class AlertManager:
    """Manages alert rules, firing, acknowledgement, and resolution.

    Features:
    - Rule-based alert triggering with cooldown
    - Severity-based notification routing
    - Alert lifecycle: firing → acknowledged → resolved
    - Alert suppression for known maintenance windows
    - Alert history with max retention
    """

    # Default alert rules covering the main system concerns
    DEFAULT_RULES = [
        AlertRule("health_score_low", "System health score below critical threshold", AlertSeverity.CRITICAL, "l6_health_score", "lt", 50.0),
        AlertRule("risk_gate_block", "Risk gate blocked a trade", AlertSeverity.HIGH, "risk_gate_blocks", "gt", 5.0, cooldown_seconds=600.0),
        AlertRule("pipeline_bottleneck", "Pipeline bottleneck detected", AlertSeverity.MEDIUM, "pipeline_bottleneck", "gt", 0.0),
        AlertRule("emergence_rate_high", "Unusually high emergence rate", AlertSeverity.MEDIUM, "emergence_rate", "gt", 10.0),
        AlertRule("immune_detection", "Immune system anomaly detected", AlertSeverity.HIGH, "immune_anomalies", "gt", 0.0),
        AlertRule("phase_degenerate", "Autocatalytic system degenerated", AlertSeverity.CRITICAL, "phase_state", "eq", 3.0),
        AlertRule("memory_high", "Memory usage above warning threshold", AlertSeverity.MEDIUM, "memory_mb", "gt", 4096.0),
        AlertRule("dropped_events", "Event bus dropping events", AlertSeverity.HIGH, "events_dropped", "gt", 100.0),
    ]

    def __init__(self, max_history: int = 1000, check_interval: int = 60) -> None:
        self._rules: dict[str, AlertRule] = {r.name: r for r in self.DEFAULT_RULES}
        self._alerts: dict[str, Alert] = {}
        self._alert_history: list[Alert] = []
        self._max_history = max_history
        self._check_interval = check_interval
        self._last_fire_times: dict[str, float] = {}  # rule_name → last fire time
        self._logger = CortexLogger("alert_manager")
        self._suppressed_rules: set[str] = set()

    def add_rule(self, rule: AlertRule) -> None:
        """Add a custom alert rule."""
        self._rules[rule.name] = rule
        self._logger.info("alert_rule_added", name=rule.name, severity=rule.severity.value)

    def remove_rule(self, name: str) -> bool:
        """Remove an alert rule."""
        if name in self._rules:
            del self._rules[name]
            return True
        return False

    def evaluate_metric(self, metric_name: str, value: float) -> list[Alert]:
        """Evaluate all rules against a metric value. Returns triggered alerts."""
        triggered: list[Alert] = []

        for rule in self._rules.values():
            if not rule.enabled or rule.metric_name != metric_name:
                continue
            if rule.name in self._suppressed_rules:
                continue

            if self._check_condition(value, rule.condition, rule.threshold):
                # Check cooldown
                now = time.time()
                last_fire = self._last_fire_times.get(rule.name, 0.0)
                if now - last_fire < rule.cooldown_seconds:
                    continue

                alert = self._fire_alert(rule, value)
                triggered.append(alert)
                self._last_fire_times[rule.name] = now

        return triggered

    def _fire_alert(self, rule: AlertRule, value: float) -> Alert:
        """Create and register a new alert."""
        alert = Alert(
            alert_id=f"alert-{uuid.uuid4().hex[:8]}",
            rule_name=rule.name,
            severity=rule.severity,
            message=f"{rule.description}: {rule.metric_name} = {value:.3f} (threshold: {rule.condition} {rule.threshold})",
            metric_value=value,
            threshold=rule.threshold,
            source=rule.metric_name,
        )
        self._alerts[alert.alert_id] = alert
        self._alert_history.append(alert)

        # Trim history
        if len(self._alert_history) > self._max_history:
            self._alert_history = self._alert_history[-self._max_history // 2:]

        self._logger.info("alert_fired", alert_id=alert.alert_id, rule=rule.name, severity=rule.severity.value, value=value)
        return alert

    def acknowledge(self, alert_id: str) -> bool:
        """Acknowledge an alert (human operator response)."""
        alert = self._alerts.get(alert_id)
        if alert is None or alert.status != AlertStatus.FIRING:
            return False
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = time.time()
        self._logger.info("alert_acknowledged", alert_id=alert_id)
        return True

    def resolve(self, alert_id: str) -> bool:
        """Resolve an alert (issue fixed)."""
        alert = self._alerts.get(alert_id)
        if alert is None:
            return False
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = time.time()
        self._logger.info("alert_resolved", alert_id=alert_id, duration_s=round(alert.duration_seconds, 1))
        return True

    def suppress_rule(self, rule_name: str) -> None:
        """Suppress a rule (e.g., during maintenance)."""
        self._suppressed_rules.add(rule_name)

    def unsuppress_rule(self, rule_name: str) -> None:
        """Remove suppression from a rule."""
        self._suppressed_rules.discard(rule_name)

    @staticmethod
    def _check_condition(value: float, condition: str, threshold: float) -> bool:
        """Evaluate a metric value against a condition."""
        if condition == "gt":
            return value > threshold
        if condition == "lt":
            return value < threshold
        if condition == "gte":
            return value >= threshold
        if condition == "lte":
            return value <= threshold
        if condition == "eq":
            return value == threshold
        return False

    def get_firing_alerts(self) -> list[Alert]:
        """Get all currently firing alerts, ordered by severity."""
        firing = [a for a in self._alerts.values() if a.status == AlertStatus.FIRING]
        severity_order = {AlertSeverity.CRITICAL: 0, AlertSeverity.HIGH: 1, AlertSeverity.MEDIUM: 2, AlertSeverity.LOW: 3}
        return sorted(firing, key=lambda a: severity_order[a.severity])

    def get_active_alerts(self) -> list[Alert]:
        """Get all non-resolved alerts."""
        return [a for a in self._alerts.values() if a.status != AlertStatus.RESOLVED]

    @property
    def stats(self) -> dict[str, Any]:
        firing = self.get_firing_alerts()
        return {
            "total_rules": len(self._rules),
            "suppressed_rules": len(self._suppressed_rules),
            "firing_alerts": len(firing),
            "active_alerts": len(self.get_active_alerts()),
            "total_alerts_history": len(self._alert_history),
            "by_severity": {
                s.value: len([a for a in firing if a.severity == s])
                for s in AlertSeverity
            },
        }
