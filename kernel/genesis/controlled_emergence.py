"""Controlled Emergence Governance (DARPA DICE grade).

Harnesses scalability of self-organizing systems while ensuring
collective behavior remains predictable and aligned.

Architecture:
  - Local rules produce global order (slime mold principle)
  - Invariant constraints prevent harmful emergence
  - Human commander's intent encoded as boundary conditions
  - Real-time emergence monitoring with automatic guardrail activation

Reference: DARPA DICE program (2026), Physarum Lagrangian (arXiv 2511.08531),
Mycel Network 70-day trial, "Drop the Hierarchy and Roles" (25K-task experiment).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EmergencePhase(Enum):
    STABLE = "stable"
    DIVERGING = "diverging"
    CRITICAL = "critical"
    COLLAPSING = "collapsing"


@dataclass
class Guardrail:
    name: str; condition: str; action: str  # "alert", "constrain", "halt"
    threshold: float; current_value: float = 0.0
    triggered: bool = False


class ControlledEmergence:
    """DARPA DICE: controlled emergence via invariant guardrails.

    Allows agents to self-organize freely within bounded space.
    Guardrails detect divergence and automatically constrain/halt.
    Human commander's intent = boundary conditions.
    """

    def __init__(self) -> None:
        self._guardrails: list[Guardrail] = [
            Guardrail("agent_count", "count > max", "alert", 256),
            Guardrail("trust_collapse", "avg_trust < 0.2", "constrain", 0.2),
            Guardrail("role_explosion", "unique_roles > 500", "alert", 500),
            Guardrail("task_starvation", "completion_rate < 0.1", "halt", 0.1),
            Guardrail("credit_inequality", "gini > 0.8", "constrain", 0.8),
            Guardrail("pheromone_flood", "active_pheromones > 10000", "constrain", 10000),
            Guardrail("energy_collapse", "agents_below_energy > 5", "halt", 5),
            Guardrail("runaway_evolution", "fitness_gain_per_gen > 0.5", "constrain", 0.5),
        ]
        self._phase: EmergencePhase = EmergencePhase.STABLE
        self._interventions: list[dict] = []

    # ── Monitoring ───────────────────────────────────────────────

    def assess(self, system_state: dict[str, Any]) -> dict[str, Any]:
        """Assess system state and determine emergence phase."""
        triggered = []
        for g in self._guardrails:
            g.current_value = self._measure(g.name, system_state)
            g.triggered = g.current_value > g.threshold if ">" in g.condition else g.current_value < g.threshold
            if g.triggered:
                triggered.append(g)

        # Phase determination
        triggered_count = len(triggered)
        if triggered_count == 0:
            self._phase = EmergencePhase.STABLE
        elif triggered_count <= 2:
            self._phase = EmergencePhase.DIVERGING
        elif triggered_count <= 4:
            self._phase = EmergencePhase.CRITICAL
        else:
            self._phase = EmergencePhase.COLLAPSING

        return {
            "phase": self._phase.value,
            "triggered_guardrails": [g.name for g in triggered],
            "total_guardrails": len(self._guardrails),
        }

    def _measure(self, name: str, state: dict) -> float:
        measures = {
            "agent_count": state.get("total_agents", 0),
            "trust_collapse": 1.0 - state.get("avg_trust", 0.5),
            "role_explosion": state.get("emergent_roles", 0),
            "task_starvation": 1.0 - state.get("completion_rate", 1.0),
            "credit_inequality": state.get("gini", 0.0),
            "pheromone_flood": state.get("active_pheromones", 0),
            "energy_collapse": state.get("active_agents", 100) - state.get("agents_above_energy", 0),
            "runaway_evolution": abs(state.get("fitness_gain_per_gen", 0.0)),
        }
        return float(measures.get(name, 0))

    # ── Intervention ─────────────────────────────────────────────

    def intervene(self, assessment: dict) -> list[dict]:
        """Apply guardrail actions based on emergence phase."""
        actions = []
        phase = assessment.get("phase", "stable")

        if phase == "collapsing":
            actions.append({"action": "halt_all_agents", "reason": "System collapse detected"})
            actions.append({"action": "notify_human_commander", "priority": "CRITICAL"})

        elif phase == "critical":
            for g_name in assessment.get("triggered_guardrails", []):
                g = next((g for g in self._guardrails if g.name == g_name), None)
                if g and g.action == "halt":
                    actions.append({"action": f"halt_{g.name}", "reason": f"Guardrail: {g.name} exceeded"})
                elif g and g.action == "constrain":
                    actions.append({"action": f"constrain_{g.name}", "reason": f"Limit imposed on {g.name}"})

        elif phase == "diverging":
            actions.append({"action": "log_divergence", "phase": phase})

        self._interventions.extend(actions)
        return actions

    # ── Commander's intent ───────────────────────────────────────

    def set_commander_intent(self, constraints: dict[str, Any]) -> None:
        """Encode human commander's intent as boundary conditions."""
        for key, value in constraints.items():
            if key == "max_agents":
                self._update_guardrail("agent_count", float(value))
            elif key == "min_completion_rate":
                self._update_guardrail("task_starvation", 1.0 - float(value))
            elif key == "max_role_explosion":
                self._update_guardrail("role_explosion", float(value))

    def _update_guardrail(self, name: str, new_threshold: float) -> None:
        for g in self._guardrails:
            if g.name == name:
                g.threshold = new_threshold

    def get_status(self) -> dict:
        return {
            "phase": self._phase.value,
            "guardrails_active": sum(1 for g in self._guardrails if g.triggered),
            "total_interventions": len(self._interventions),
            "last_interventions": self._interventions[-3:] if self._interventions else [],
        }
