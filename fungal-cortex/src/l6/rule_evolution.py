"""Mechanism ⑰ M6: Dynamic Rule Evolution — epigenetic regulation + Baldwin effect.

Inspired by:
- Epigenetic regulation: environmental signals → epigenetic marks → switch genes on/off
  (without changing DNA). Rules are "epigenetic marks" that modulate strategy expression.
- Baldwin effect: learned behaviors become genetically assimilated over evolutionary time.
- Immune clonal selection: successful B-cell clones proliferate, failed ones apoptose.

5 rule templates:
1. position_limit — max position size per instrument
2. stop_loss — max loss before forced exit
3. volatility_trigger — reduce exposure when volatility spikes
4. correlation_trigger — reduce exposure when cross-asset correlation spikes
5. concentration_limit — max sector/industry exposure

Pipeline: generate → A/B test 48h → evaluate → adopt winner
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# --- Rule Templates ---

RULE_TEMPLATES: dict[str, dict[str, Any]] = {
    "position_limit": {
        "description": "Limit maximum position size per instrument",
        "parameters": ["max_position_pct", "instrument"],
        "default_max_position_pct": 0.10,
    },
    "stop_loss": {
        "description": "Force exit when loss exceeds threshold",
        "parameters": ["stop_loss_pct", "trailing"],
        "default_stop_loss_pct": 0.08,
    },
    "volatility_trigger": {
        "description": "Reduce exposure when volatility spikes above threshold",
        "parameters": ["volatility_threshold", "exposure_reduction_pct"],
        "default_volatility_threshold": 0.30,
    },
    "correlation_trigger": {
        "description": "Reduce exposure when cross-asset correlation spikes",
        "parameters": ["correlation_threshold", "exposure_reduction_pct"],
        "default_correlation_threshold": 0.80,
    },
    "concentration_limit": {
        "description": "Limit maximum sector/industry concentration",
        "parameters": ["max_sector_pct", "max_industry_pct"],
        "default_max_sector_pct": 0.30,
    },
}


# --- Data Classes ---

class RuleStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    TESTING = "testing"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"


@dataclass
class Rule:
    """A single evolvable rule — the "epigenetic mark" on a strategy."""

    rule_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    template_type: str = ""  # One of RULE_TEMPLATES keys
    strategy_id: str = ""  # Strategy this rule applies to
    parameters: dict[str, Any] = field(default_factory=dict)
    status: RuleStatus = RuleStatus.DRAFT
    created_at: float = field(default_factory=time.time)
    activated_at: float | None = None
    generation: int = 0  # Evolution generation counter
    parent_rule_id: str | None = None  # Lineage tracking
    performance: dict[str, float] = field(default_factory=dict)  # sharpe, max_dd, win_rate

    def clone_for_test(self) -> Rule:
        """Create a variant for A/B testing."""
        new_rule = Rule(
            rule_id=str(uuid.uuid4())[:8],
            name=f"{self.name}-variant-{self.generation + 1}",
            template_type=self.template_type,
            strategy_id=self.strategy_id,
            parameters=dict(self.parameters),
            status=RuleStatus.TESTING,
            generation=self.generation + 1,
            parent_rule_id=self.rule_id,
        )
        return new_rule


@dataclass
class ABTest:
    """A/B test comparing two rules."""

    test_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    rule_a_id: str = ""
    rule_b_id: str = ""
    strategy_id: str = ""
    start_time: float = field(default_factory=time.time)
    duration_hours: float = 48.0
    results_a: dict[str, float] = field(default_factory=dict)
    results_b: dict[str, float] = field(default_factory=dict)
    winner_id: str | None = None
    concluded: bool = False


@dataclass
class RuleEvent:
    """Record of a rule lifecycle event (for audit trail)."""

    event_type: str  # created, activated, tested, adopted, rejected, deprecated
    rule_id: str
    timestamp: float = field(default_factory=time.time)
    detail: str = ""


# --- Main Engine ---

class DynamicRuleEvolutionEngine:
    """Dynamic rule evolution using epigenetic + Baldwinian principles.

    Environmental signals (market volatility, correlations) →
    epigenetic marks (rules) modulate gene (strategy) expression →
    Successful rules proliferate (clonal selection).
    """

    def __init__(
        self,
        ab_test_duration_hours: int = 48,
        sharpe_high: float = 2.0,
        sharpe_medium: float = 1.0,
        max_pos_high: float = 0.25,
        max_pos_medium: float = 0.15,
        max_pos_low: float = 0.08,
    ) -> None:
        self._rules: dict[str, Rule] = {}
        self._active_tests: dict[str, ABTest] = {}
        self._completed_tests: list[ABTest] = []
        self._event_log: list[RuleEvent] = []
        self._ab_test_duration_hours = ab_test_duration_hours
        self._sharpe_high = sharpe_high
        self._sharpe_medium = sharpe_medium
        self._max_pos_high = max_pos_high
        self._max_pos_medium = max_pos_medium
        self._max_pos_low = max_pos_low

    # --- Rule Generation ---

    def generate_rules_for_strategy(
        self,
        strategy_id: str,
        strategy_sharpe: float,
        strategy_volatility: float = 0.2,
    ) -> list[Rule]:
        """Generate rules for a strategy based on its performance profile.

        Higher Sharpe → looser limits. Lower Sharpe → tighter limits.
        Rules are epigenetic marks — they control strategy expression without
        modifying the strategy itself.
        """
        rules: list[Rule] = []

        # Position limit based on Sharpe
        if strategy_sharpe >= self._sharpe_high:
            max_pos = self._max_pos_high
        elif strategy_sharpe >= self._sharpe_medium:
            max_pos = self._max_pos_medium
        else:
            max_pos = self._max_pos_low

        # 1. Position limit
        rules.append(Rule(
            name=f"pos-limit-{strategy_id}",
            template_type="position_limit",
            strategy_id=strategy_id,
            parameters={"max_position_pct": max_pos},
            status=RuleStatus.ACTIVE,
        ))

        # 2. Stop loss
        stop_loss = max(0.03, min(0.15, 0.08 + (2.0 - strategy_sharpe) * 0.02))
        rules.append(Rule(
            name=f"stop-loss-{strategy_id}",
            template_type="stop_loss",
            strategy_id=strategy_id,
            parameters={"stop_loss_pct": round(stop_loss, 4), "trailing": True},
            status=RuleStatus.ACTIVE,
        ))

        # 3. Volatility trigger
        vol_threshold = strategy_volatility * 1.5
        rules.append(Rule(
            name=f"vol-trigger-{strategy_id}",
            template_type="volatility_trigger",
            strategy_id=strategy_id,
            parameters={
                "volatility_threshold": round(vol_threshold, 4),
                "exposure_reduction_pct": 0.50,
            },
            status=RuleStatus.ACTIVE,
        ))

        # 4. Correlation trigger
        rules.append(Rule(
            name=f"corr-trigger-{strategy_id}",
            template_type="correlation_trigger",
            strategy_id=strategy_id,
            parameters={
                "correlation_threshold": 0.80,
                "exposure_reduction_pct": 0.30,
            },
            status=RuleStatus.ACTIVE,
        ))

        # 5. Concentration limit
        rules.append(Rule(
            name=f"conc-limit-{strategy_id}",
            template_type="concentration_limit",
            strategy_id=strategy_id,
            parameters={
                "max_sector_pct": 0.30,
                "max_industry_pct": 0.15,
            },
            status=RuleStatus.ACTIVE,
        ))

        for rule in rules:
            self._rules[rule.rule_id] = rule
            self._log_event("created", rule.rule_id, f"Generated for {strategy_id} (sharpe={strategy_sharpe:.2f})")

        return rules

    def create_custom_rule(
        self, name: str, template_type: str, strategy_id: str, parameters: dict[str, Any]
    ) -> tuple[bool, str, Rule | None]:
        """Create a custom rule with user-specified parameters."""
        if template_type not in RULE_TEMPLATES:
            return False, f"Unknown template '{template_type}'. Available: {list(RULE_TEMPLATES)}", None

        template = RULE_TEMPLATES[template_type]
        for param in template["parameters"]:
            if param not in parameters:
                default_key = f"default_{param}"
                if default_key in template:
                    parameters[param] = template[default_key]

        rule = Rule(
            name=name,
            template_type=template_type,
            strategy_id=strategy_id,
            parameters=parameters,
            status=RuleStatus.ACTIVE,
        )
        self._rules[rule.rule_id] = rule
        self._log_event("created", rule.rule_id, f"Custom rule '{name}' ({template_type})")
        return True, f"Rule '{name}' created", rule

    # --- A/B Testing ---

    def ab_test_rules(self, rule_id: str, variant_parameters: dict[str, Any]) -> tuple[bool, str, str | None]:
        """Start A/B test between existing rule and a variant.

        Returns (success, message, test_id).
        """
        existing = self._rules.get(rule_id)
        if existing is None:
            return False, f"Rule '{rule_id}' not found", None
        if existing.status != RuleStatus.ACTIVE:
            return False, f"Rule '{rule_id}' is not active (status: {existing.status.value})", None

        variant = existing.clone_for_test()
        variant.parameters.update(variant_parameters)
        self._rules[variant.rule_id] = variant

        test = ABTest(
            rule_a_id=rule_id,
            rule_b_id=variant.rule_id,
            strategy_id=existing.strategy_id,
            duration_hours=self._ab_test_duration_hours,
        )
        self._active_tests[test.test_id] = test
        existing.status = RuleStatus.TESTING
        self._log_event("tested", rule_id, f"A/B test started: {rule_id} vs {variant.rule_id}")

        return True, f"A/B test started: {rule_id} vs {variant.rule_id}", test.test_id

    def evaluate_and_adopt(self, test_id: str) -> tuple[bool, str, str | None]:
        """Evaluate A/B test results and adopt winning rule.

        Winner is determined by Sharpe ratio comparison.
        Loser is deprecated (Baldwin effect: only successful variants survive).
        """
        test = self._active_tests.get(test_id)
        if test is None:
            return False, f"Test '{test_id}' not found", None

        # Evaluate based on Sharpe ratio
        sharpe_a = test.results_a.get("sharpe", 0.0)
        sharpe_b = test.results_b.get("sharpe", 0.0)

        if sharpe_a >= sharpe_b:
            winner_id, loser_id = test.rule_a_id, test.rule_b_id
            winner_sharpe, loser_sharpe = sharpe_a, sharpe_b
        else:
            winner_id, loser_id = test.rule_b_id, test.rule_a_id
            winner_sharpe, loser_sharpe = sharpe_b, sharpe_a

        # Adopt winner
        winner = self._rules.get(winner_id)
        loser = self._rules.get(loser_id)

        if winner:
            winner.status = RuleStatus.ACTIVE
            winner.performance = test.results_a if winner_id == test.rule_a_id else test.results_b
            winner.activated_at = time.time()
            self._log_event("adopted", winner_id, f"Adopted with sharpe={winner_sharpe:.2f}")

        if loser:
            loser.status = RuleStatus.DEPRECATED
            self._log_event("rejected", loser_id, f"Rejected with sharpe={loser_sharpe:.2f}")

        test.winner_id = winner_id
        test.concluded = True
        self._completed_tests.append(test)
        del self._active_tests[test_id]

        return True, f"Winner: {winner_id} (sharpe={winner_sharpe:.2f} vs {loser_sharpe:.2f})", winner_id

    def set_test_results(
        self, test_id: str, sharpe_a: float, max_dd_a: float, sharpe_b: float, max_dd_b: float
    ) -> bool:
        """Feed performance data into an ongoing A/B test."""
        test = self._active_tests.get(test_id)
        if test is None:
            return False
        test.results_a = {"sharpe": sharpe_a, "max_drawdown": max_dd_a}
        test.results_b = {"sharpe": sharpe_b, "max_drawdown": max_dd_b}
        return True

    # --- Rule Management ---

    def deprecate_rule(self, rule_id: str, reason: str = "") -> tuple[bool, str]:
        """Manually deprecate a rule."""
        rule = self._rules.get(rule_id)
        if rule is None:
            return False, f"Rule '{rule_id}' not found"
        rule.status = RuleStatus.DEPRECATED
        self._log_event("deprecated", rule_id, reason)
        return True, f"Rule '{rule_id}' deprecated"

    def get_rule(self, rule_id: str) -> Rule | None:
        return self._rules.get(rule_id)

    def get_rules_for_strategy(self, strategy_id: str) -> list[Rule]:
        return [r for r in self._rules.values() if r.strategy_id == strategy_id]

    def get_active_rules(self, strategy_id: str | None = None) -> list[Rule]:
        rules = self._rules.values()
        if strategy_id:
            rules = [r for r in rules if r.strategy_id == strategy_id]
        return [r for r in rules if r.status == RuleStatus.ACTIVE]

    def get_rules_by_template(self, template_type: str) -> list[Rule]:
        return [r for r in self._rules.values() if r.template_type == template_type]

    # --- Events & Audit ---

    def _log_event(self, event_type: str, rule_id: str, detail: str) -> None:
        self._event_log.append(RuleEvent(event_type=event_type, rule_id=rule_id, detail=detail))
        if len(self._event_log) > 1000:
            self._event_log = self._event_log[-1000:]

    @property
    def event_log(self) -> list[RuleEvent]:
        return list(self._event_log)

    # --- Reporting ---

    @property
    def stats(self) -> dict[str, Any]:
        rules = list(self._rules.values())
        active = [r for r in rules if r.status == RuleStatus.ACTIVE]
        testing = [r for r in rules if r.status == RuleStatus.TESTING]
        deprecated = [r for r in rules if r.status == RuleStatus.DEPRECATED]

        template_counts: dict[str, int] = {}
        for r in rules:
            template_counts[r.template_type] = template_counts.get(r.template_type, 0) + 1

        return {
            "total_rules": len(rules),
            "active_rules": len(active),
            "testing_rules": len(testing),
            "deprecated_rules": len(deprecated),
            "active_tests": len(self._active_tests),
            "completed_tests": len(self._completed_tests),
            "templates_used": template_counts,
            "adoption_rate": sum(1 for e in self._event_log if e.event_type == "adopted") / max(len(rules), 1),
        }

    def get_evolution_report(self) -> dict[str, Any]:
        """Get a report on rule evolution lineage."""
        lineage: dict[str, list[str]] = {}
        for rule in self._rules.values():
            if rule.parent_rule_id:
                if rule.parent_rule_id not in lineage:
                    lineage[rule.parent_rule_id] = []
                lineage[rule.parent_rule_id].append(rule.rule_id)

        return {
            "total_rules": len(self._rules),
            "rule_lineage": lineage,
            "active_tests": len(self._active_tests),
            "completed_tests": len(self._completed_tests),
            "recent_events": [
                {"type": e.event_type, "rule_id": e.rule_id, "detail": e.detail}
                for e in self._event_log[-20:]
            ],
        }
