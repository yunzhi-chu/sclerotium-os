"""L4 M6a: PolicyEngine — "内环境稳态"(Homeostasis) 策略引擎.

Biological Metaphor:
  内环境稳态(Homeostasis)——人体维持37°C体温/pH 7.4/血糖5mM的精妙调控。
  所有参数都有限制范围, 超出范围触发纠偏机制。

  甲状腺作为"双调控器"(Dual Governor):
    1. 全系统代谢节拍(类比: 系统执行速率)
    2. 压力-语言一致性(类比: 全局参数约束如何解释为执行规则)

  约束维度:
    evolution: max_param_change/day=3%(24h变动上限)
    execution: max_parallel=8, max_duration=30min
    risk: max_position=15%, stop_loss_daily=3%
    sandbox: trial_days=30, min_sharpe=0.5
    memory: max_episodic=100000, audit_retention=365d

Reference: Schuler et al. (2026), IJMS; Thyroid as Dual Governor (Zenodo 2026)
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class RulePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PolicyRule:
    """A single homeostasis rule — like a physiological setpoint."""

    rule_id: str
    name: str
    category: str  # evolution, execution, risk, sandbox, memory
    constraint: str  # e.g., "max_param_change", "max_parallel"
    limit: float
    unit: str = ""
    priority: RulePriority = RulePriority.MEDIUM
    enabled: bool = True
    created_at: float = field(default_factory=time.time)


class PolicyEngine:
    """Homeostatic regulator — enforces limits across all system dimensions.

    Default constraints mirror physiological limits:
      - evolution: 3% param change per day
      - execution: 8 parallel, 30min duration
      - risk: 15% position, 3% daily stop
      - sandbox: 30-day trial, 0.5 min sharpe
      - memory: 100k episodic, 365d audit
    """

    def __init__(self) -> None:
        self._rules: dict[str, PolicyRule] = {}
        self._initialize_defaults()
        self._logger = CortexLogger("policy_engine")

    def _initialize_defaults(self) -> None:
        defaults = [
            ("evo_max_param_change", "evolution", "max_param_change_per_day", 0.03, "fraction", RulePriority.HIGH),
            ("exec_max_parallel", "execution", "max_parallel", 8, "tasks", RulePriority.HIGH),
            ("exec_max_duration", "execution", "max_duration", 30, "minutes", RulePriority.MEDIUM),
            ("risk_max_position", "risk", "max_position_pct", 0.15, "fraction", RulePriority.CRITICAL),
            ("risk_stop_loss", "risk", "stop_loss_daily", 0.03, "fraction", RulePriority.CRITICAL),
            ("sandbox_trial_days", "sandbox", "trial_days", 30, "days", RulePriority.MEDIUM),
            ("sandbox_min_sharpe", "sandbox", "min_sharpe", 0.5, "ratio", RulePriority.HIGH),
            ("mem_max_episodic", "memory", "max_episodic", 100000, "records", RulePriority.LOW),
            ("mem_audit_retention", "memory", "audit_retention", 365, "days", RulePriority.MEDIUM),
        ]
        for rule_id, cat, constraint, limit, unit, pri in defaults:
            self._rules[rule_id] = PolicyRule(
                rule_id=rule_id, name=rule_id, category=cat,
                constraint=constraint, limit=limit, unit=unit, priority=pri,
            )

    def check(self, category: str, constraint: str, proposed_value: float) -> tuple[bool, str]:
        """Check if a proposed value violates a constraint. Returns (allowed, reason)."""
        for rule in self._rules.values():
            if rule.category == category and rule.constraint == constraint and rule.enabled:
                if proposed_value > rule.limit:
                    return False, f"{constraint}={proposed_value} exceeds limit {rule.limit}{rule.unit}"
                return True, "ok"
        return True, "no_constraint"

    def check_all(self, values: dict[str, dict[str, float]]) -> dict[str, list[str]]:
        """Check multiple categories. Returns {category: [violations]}."""
        violations: dict[str, list[str]] = defaultdict(list)
        for category, checks in values.items():
            for constraint, value in checks.items():
                ok, reason = self.check(category, constraint, value)
                if not ok:
                    violations[category].append(reason)
        return dict(violations)

    def add_rule(self, name: str, category: str, constraint: str,
                 limit: float, unit: str = "", priority: RulePriority = RulePriority.MEDIUM) -> PolicyRule:
        rule = PolicyRule(
            rule_id=self._gen_id(name), name=name, category=category,
            constraint=constraint, limit=limit, unit=unit, priority=priority,
        )
        self._rules[rule.rule_id] = rule
        return rule

    def get_rules(self, category: str | None = None) -> list[PolicyRule]:
        rules = list(self._rules.values())
        if category:
            rules = [r for r in rules if r.category == category]
        return sorted(rules, key=lambda r: ["critical", "high", "medium", "low"].index(r.priority.value))

    @staticmethod
    def _gen_id(name: str) -> str:
        return hashlib.md5(f"{name}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        cats = defaultdict(int)
        for r in self._rules.values():
            cats[r.category] += 1
        return {"total_rules": len(self._rules), "by_category": dict(cats)}
