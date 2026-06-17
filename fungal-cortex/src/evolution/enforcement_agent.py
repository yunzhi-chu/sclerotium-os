"""Enforcement Agent — Evo-Ego solution via second-level public good.

The Evo-Ego problem: when individual agent interests diverge from system goals,
individual-level selection opposes group-level adaptation.

Solution (Watson & Szathmáry): enforcement agent as "second-level public good."
- Detects when agents deviate from system goals (ego-deviation)
- Penalizes deviation proportionally
- Maintains alignment between individual and collective fitness

The enforcement agent doesn't maximize its own fitness —
it maximizes the system's collective fitness function.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DeviationType(str, Enum):
    """Types of ego-deviation from system goals."""

    EXCESSIVE_RISK = "excessive_risk"  # Taking more risk than system allows
    SHORT_TERM_BIAS = "short_term_bias"  # Optimizing for immediate reward
    COORDINATION_FAILURE = "coordination_failure"  # Not cooperating with peers
    RESOURCE_HOARDING = "resource_hoarding"  # Hogging shared resources
    STRATEGY_DRIFT = "strategy_drift"  # Moving away from assigned strategy


@dataclass
class EgoDeviation:
    """A detected deviation from system goals."""

    agent_id: str
    deviation_type: DeviationType
    severity: float  # 0-1, how severe
    details: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class EnforcementAction:
    """Action taken to correct ego-deviation."""

    agent_id: str
    action_type: str  # "penalty", "warning", "restriction", "isolation"
    penalty_amount: float
    reason: str
    timestamp: float = field(default_factory=time.time)


class EnforcementAgent:
    """Evo-Ego enforcement: maintain alignment between individual and system fitness.

    The enforcement agent provides the "second-level public good" that
    solves the Evo-Ego problem. By penalizing deviations from system goals,
    it aligns individual selection with group selection.

    This makes group-level adaptations possible even when they conflict
    with immediate individual interests.
    """

    def __init__(self, penalty_strength: float = 0.3) -> None:
        self._penalty = penalty_strength
        self._deviations: list[EgoDeviation] = []
        self._actions: list[EnforcementAction] = []
        self._agent_penalty_points: dict[str, float] = {}
        self._warning_threshold = 0.3
        self._penalty_threshold = 0.6
        self._isolation_threshold = 0.85

    def monitor(
        self,
        agent_id: str,
        risk_taken: float,
        short_term_reward: float,
        coordination_score: float,
        resource_usage: float,
        strategy_adherence: float,
    ) -> list[EgoDeviation]:
        """Monitor agent behavior for ego-deviations."""
        deviations: list[EgoDeviation] = []

        if risk_taken > 0.7:
            deviations.append(EgoDeviation(
                agent_id=agent_id,
                deviation_type=DeviationType.EXCESSIVE_RISK,
                severity=risk_taken - 0.5,
                details={"risk_taken": risk_taken, "max_allowed": 0.7},
            ))

        if short_term_reward > 0.8 and coordination_score < 0.4:
            deviations.append(EgoDeviation(
                agent_id=agent_id,
                deviation_type=DeviationType.SHORT_TERM_BIAS,
                severity=(short_term_reward - coordination_score) / 2.0,
                details={"short_term": short_term_reward, "coordination": coordination_score},
            ))

        if coordination_score < 0.3:
            deviations.append(EgoDeviation(
                agent_id=agent_id,
                deviation_type=DeviationType.COORDINATION_FAILURE,
                severity=0.3 - coordination_score,
                details={"coordination_score": coordination_score},
            ))

        if resource_usage > 0.8:
            deviations.append(EgoDeviation(
                agent_id=agent_id,
                deviation_type=DeviationType.RESOURCE_HOARDING,
                severity=resource_usage - 0.5,
                details={"resource_usage": resource_usage},
            ))

        if strategy_adherence < 0.4:
            deviations.append(EgoDeviation(
                agent_id=agent_id,
                deviation_type=DeviationType.STRATEGY_DRIFT,
                severity=0.4 - strategy_adherence,
                details={"adherence": strategy_adherence},
            ))

        self._deviations.extend(deviations)
        return deviations

    def enforce(self, deviations: list[EgoDeviation]) -> list[EnforcementAction]:
        """Apply enforcement actions to correct deviations."""
        actions: list[EnforcementAction] = []

        for dev in deviations:
            # Accumulate penalty points
            current = self._agent_penalty_points.get(dev.agent_id, 0.0)
            current += dev.severity * self._penalty
            self._agent_penalty_points[dev.agent_id] = current

            if current >= self._isolation_threshold:
                action = EnforcementAction(
                    agent_id=dev.agent_id,
                    action_type="isolation",
                    penalty_amount=dev.severity,
                    reason=f"Persistent deviation: {dev.deviation_type.value}, points={current:.2f}",
                )
            elif current >= self._penalty_threshold:
                action = EnforcementAction(
                    agent_id=dev.agent_id,
                    action_type="restriction",
                    penalty_amount=dev.severity * 0.5,
                    reason=f"Significant deviation: {dev.deviation_type.value}, points={current:.2f}",
                )
            elif current >= self._warning_threshold:
                action = EnforcementAction(
                    agent_id=dev.agent_id,
                    action_type="warning",
                    penalty_amount=0.0,
                    reason=f"Minor deviation: {dev.deviation_type.value}, points={current:.2f}",
                )
            else:
                action = EnforcementAction(
                    agent_id=dev.agent_id,
                    action_type="penalty",
                    penalty_amount=dev.severity * 0.1,
                    reason=f"Initial deviation: {dev.deviation_type.value}",
                )

            actions.append(action)

        self._actions.extend(actions)
        return actions

    def decay_penalties(self, rate: float = 0.1) -> None:
        """Gradually decay penalty points (forgiveness mechanism)."""
        for agent_id in list(self._agent_penalty_points.keys()):
            self._agent_penalty_points[agent_id] *= (1.0 - rate)
            if self._agent_penalty_points[agent_id] < 0.01:
                del self._agent_penalty_points[agent_id]

    def get_agent_status(self, agent_id: str) -> dict[str, Any]:
        points = self._agent_penalty_points.get(agent_id, 0.0)
        if points >= self._isolation_threshold:
            status = "isolated"
        elif points >= self._penalty_threshold:
            status = "restricted"
        elif points >= self._warning_threshold:
            status = "warned"
        else:
            status = "clean"
        return {"agent_id": agent_id, "penalty_points": points, "status": status}

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_deviations": len(self._deviations),
            "total_actions": len(self._actions),
            "agents_monitored": len(self._agent_penalty_points),
            "isolated_agents": sum(1 for p in self._agent_penalty_points.values() if p >= self._isolation_threshold),
            "penalty_strength": self._penalty,
        }
