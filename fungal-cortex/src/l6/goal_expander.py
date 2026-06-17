"""Mechanism ⑮ M4: Global Goal Expander — curiosity-driven exploration.

Inspired by:
- Raccoon studies (UBC 2026): raccoons solve puzzle boxes beyond food reward —
  pure "information foraging" behavior. Low difficulty → broad exploration;
  high difficulty → conservative verification.
- Learning Progress Hypothesis (LPH): Curiosity = w1(information_gain) + w2(learning_progress).
  Dopamine neurons encode "information prediction error" — information as intrinsic reward.
- Information foraging theory: organisms optimize information gain per unit cost.

Goal expansion: discover_new_directions → assess_feasibility (5-dim) → deploy_goal → decompose.
7 known domains + 12 exploration domains + cross-domain intersections.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# --- Domain Space ---

KNOWN_DOMAINS: list[str] = [
    "china_equity_valuation",
    "china_macro_analysis",
    "quantitative_strategy",
    "risk_management",
    "portfolio_optimization",
    "market_microstructure",
    "alternative_data",
]

EXPLORATION_DOMAINS: list[str] = [
    "global_macro_linkages",
    "crypto_asset_pricing",
    "climate_risk_modeling",
    "supply_chain_analytics",
    "geopolitical_risk",
    "behavioral_finance_models",
    "high_frequency_patterns",
    "cross_asset_arbitrage",
    "derivatives_pricing",
    "private_market_valuation",
    "real_estate_finance",
    "insurance_risk_modeling",
]


class GoalStatus(Enum):
    PROPOSED = "proposed"
    FEASIBLE = "feasible"
    DEPLOYED = "deployed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FROZEN = "frozen"


@dataclass
class Goal:
    """A single exploration goal — candidate for L5 LONG_TERM_TARGETS."""

    goal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    domain: str = ""
    description: str = ""
    status: GoalStatus = GoalStatus.PROPOSED
    feasibility_score: float = 0.0  # Composite 0-1
    dimension_scores: dict[str, float] = field(default_factory=dict)
    sub_tasks: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    deployed_at: float | None = None
    completed_at: float | None = None


@dataclass
class ExplorationState:
    """Tracks exploration state for learning progress calculation."""

    domain: str
    visits: int = 0
    successes: int = 0
    last_visited: float = 0.0
    knowledge_gained: float = 0.0  # Cumulative information gain
    learning_rate: float = 0.0  # Recent progress rate


class GlobalGoalExpander:
    """Global goal expander — curiosity engine for the fungal cortex.

    Instead of "which direction is most profitable?", asks
    "which direction maximizes learning progress?"

    Like the raccoon: solve puzzles for information, not just food.
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        known_domains: list[str] | None = None,
        exploration_domains: list[str] | None = None,
        decomposition_count: int = 5,
    ) -> None:
        self._goals: dict[str, Goal] = {}
        self._exploration: dict[str, ExplorationState] = {}
        self._weights = weights or {
            "data": 0.25,
            "compute": 0.20,
            "contribution": 0.25,
            "risk": 0.15,
            "novelty": 0.15,
        }
        self._known_domains = known_domains or list(KNOWN_DOMAINS)
        self._exploration_domains = exploration_domains or list(EXPLORATION_DOMAINS)
        self._decomposition_count = decomposition_count

        # Initialize exploration state for all domains
        for domain in self._known_domains + self._exploration_domains:
            self._exploration[domain] = ExplorationState(domain=domain)

    # --- Discovery ---

    def discover_new_directions(self, limit: int = 10) -> list[dict[str, Any]]:
        """Discover new exploration directions.

        Combines:
        1. Unexplored domains (low visit count)
        2. Cross-domain intersections (n×(n-1)/2 combinations)
        3. Knowledge network driven (domains with high info gain)
        """
        directions: list[dict[str, Any]] = []

        # 1. Pure exploration domains (lowest visit count first)
        unexplored = sorted(self._exploration.values(), key=lambda e: e.visits)
        for state in unexplored:
            if len(directions) >= limit:
                break
            directions.append({
                "type": "pure_exploration",
                "domain": state.domain,
                "visits": state.visits,
                "knowledge_gained": state.knowledge_gained,
                "learning_rate": state.learning_rate,
                "priority": "high" if state.visits == 0 else "medium",
            })

        # 2. Cross-domain intersections
        all_domains = self._known_domains + self._exploration_domains
        for i, d1 in enumerate(all_domains):
            for d2 in all_domains[i + 1 :]:
                if len(directions) >= limit:
                    break
                cross_name = f"{d1} × {d2}"
                if cross_name not in self._exploration:
                    directions.append({
                        "type": "cross_domain",
                        "domain": cross_name,
                        "source_domains": [d1, d2],
                        "priority": "medium",
                        "potential_synergy": "high" if d1.split("_")[0] != d2.split("_")[0] else "medium",
                    })

        # 3. High-learning-progress domains
        progressing = sorted(self._exploration.values(), key=lambda e: e.learning_rate, reverse=True)
        for state in progressing:
            if state.learning_rate > 0.1 and len(directions) < limit:
                directions.append({
                    "type": "learning_driven",
                    "domain": state.domain,
                    "learning_rate": state.learning_rate,
                    "knowledge_gained": state.knowledge_gained,
                    "priority": "high",
                })

        return directions[:limit]

    # --- Feasibility Assessment ---

    def assess_feasibility(self, domain: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """5-dimension feasibility scoring.

        Dimensions:
        - data (0.25): data availability and quality
        - compute (0.20): computational requirements
        - contribution (0.25): expected contribution to system
        - risk (0.15): implementation and market risk
        - novelty (0.15): how novel is this direction

        Returns composite score and detailed breakdown.
        """
        ctx = context or {}

        scores: dict[str, float] = {
            "data": self._score_data_availability(domain, ctx),
            "compute": self._score_compute_feasibility(domain, ctx),
            "contribution": self._score_contribution(domain, ctx),
            "risk": self._score_risk(domain, ctx),
            "novelty": self._score_novelty(domain, ctx),
        }

        composite = sum(scores[k] * self._weights[k] for k in self._weights)

        # Update exploration state
        if domain in self._exploration:
            state = self._exploration[domain]
            prev_knowledge = state.knowledge_gained
            state.visits += 1
            state.last_visited = time.time()
            info_gain = scores["novelty"] * 0.1  # Novelty proxies information gain
            state.knowledge_gained += info_gain
            state.learning_rate = state.knowledge_gained - prev_knowledge
            if state.learning_rate > 0:
                state.successes += 1

        return {
            "domain": domain,
            "composite_score": round(composite, 4),
            "feasible": composite >= 0.5,
            "dimensions": scores,
            "weights": dict(self._weights),
        }

    def _score_data_availability(self, domain: str, ctx: dict[str, Any]) -> float:
        known_keywords = {"china", "equity", "market", "stock", "bond", "index", "forex", "commodity"}
        domain_words = set(domain.lower().replace("_", " ").split())
        overlap = len(domain_words & known_keywords)
        base = 0.5 + overlap * 0.1
        return min(1.0, base if ctx.get("data_sources") is None else base + 0.2)

    def _score_compute_feasibility(self, domain: str, ctx: dict[str, Any]) -> float:
        heavy_keywords = {"climate", "high_frequency", "supply_chain", "deep_learning", "simulation"}
        domain_words = set(domain.lower().replace("_", " ").split())
        if domain_words & heavy_keywords:
            return 0.4  # Heavy compute required
        return 0.8 if ctx.get("compute_budget") is None else min(1.0, ctx["compute_budget"])

    def _score_contribution(self, domain: str, ctx: dict[str, Any]) -> float:
        contribution = 0.5  # Base
        known_words = set(" ".join(self._known_domains).lower().split("_"))
        domain_words = set(domain.lower().replace("_", " ").split())
        if domain_words & known_words:
            contribution += 0.2  # Builds on existing knowledge
        if domain in self._exploration_domains:
            contribution += 0.1  # Expands frontier
        return min(1.0, contribution + ctx.get("contribution_bonus", 0.0))

    def _score_risk(self, domain: str, ctx: dict[str, Any]) -> float:
        risk = 0.5  # Medium risk base
        low_risk_words = {"equity", "valuation", "analysis", "portfolio"}
        high_risk_words = {"crypto", "derivative", "geopolitical", "leverage"}
        domain_words = set(domain.lower().replace("_", " ").split())
        if domain_words & low_risk_words:
            risk -= 0.2
        if domain_words & high_risk_words:
            risk += 0.2
        return max(0.0, min(1.0, 1.0 - risk))  # Invert: higher score = lower risk

    def _score_novelty(self, domain: str, ctx: dict[str, Any]) -> float:
        if domain in self._known_domains:
            return 0.2
        if domain in self._exploration_domains:
            return 0.7
        # Cross-domain or entirely new
        return 0.9 if "×" in domain else 0.5

    # --- Goal Deployment ---

    def deploy_goal(self, name: str, domain: str, description: str = "") -> tuple[bool, str, str | None]:
        """Deploy a goal for execution (sends to L5 LONG_TERM_TARGETS).

        Assesses feasibility first, then decomposes into sub-tasks.
        """
        # Feasibility check
        assessment = self.assess_feasibility(domain)
        if not assessment["feasible"]:
            return False, f"Domain '{domain}' not feasible (composite={assessment['composite_score']:.2f})", None

        goal = Goal(
            name=name,
            domain=domain,
            description=description,
            status=GoalStatus.FEASIBLE,
            feasibility_score=assessment["composite_score"],
            dimension_scores=assessment["dimensions"],
        )

        # Decompose into sub-tasks
        goal.sub_tasks = self._decompose_goal(goal)

        goal.status = GoalStatus.DEPLOYED
        goal.deployed_at = time.time()
        self._goals[goal.goal_id] = goal

        return True, f"Goal '{name}' deployed with {len(goal.sub_tasks)} sub-tasks", goal.goal_id

    def _decompose_goal(self, goal: Goal) -> list[dict[str, Any]]:
        """Break down a goal into sub-tasks for L5 execution."""
        tasks: list[dict[str, Any]] = []
        prefixes = ["Research", "Data collection for", "Prototype for", "Validate", "Integrate"]

        for i, prefix in enumerate(prefixes[: self._decomposition_count]):
            task = {
                "task_id": f"{goal.goal_id}-t{i + 1}",
                "title": f"{prefix} {goal.name}",
                "domain": goal.domain,
                "status": "pending",
                "priority": "high" if i < 2 else "medium",
                "estimated_effort_hours": 4 + i * 2,
            }
            tasks.append(task)

        return tasks

    # --- Goal Management ---

    def mark_completed(self, goal_id: str) -> tuple[bool, str]:
        goal = self._goals.get(goal_id)
        if goal is None:
            return False, f"Goal '{goal_id}' not found"
        goal.status = GoalStatus.COMPLETED
        goal.completed_at = time.time()
        if goal.domain in self._exploration:
            self._exploration[goal.domain].successes += 1
            self._exploration[goal.domain].knowledge_gained += 0.1
            self._exploration[goal.domain].learning_rate = 0.1
        return True, f"Goal '{goal.name}' completed"

    def freeze_goal(self, goal_id: str, reason: str = "") -> tuple[bool, str]:
        goal = self._goals.get(goal_id)
        if goal is None:
            return False, f"Goal '{goal_id}' not found"
        goal.status = GoalStatus.FROZEN
        return True, f"Goal '{goal.name}' frozen: {reason}"

    def get_goal(self, goal_id: str) -> Goal | None:
        return self._goals.get(goal_id)

    def get_goals_by_status(self, status: GoalStatus) -> list[Goal]:
        return [g for g in self._goals.values() if g.status == status]

    # --- Coverage ---

    def get_current_coverage(self) -> dict[str, Any]:
        """Return current exploration coverage of the domain space."""
        all_domains = set(self._known_domains + self._exploration_domains)
        covered = {d for d, s in self._exploration.items() if s.visits > 0}

        return {
            "total_domains": len(all_domains),
            "covered_domains": len(covered),
            "coverage_pct": len(covered) / max(len(all_domains), 1),
            "unexplored": sorted(all_domains - covered),
            "most_progressing": sorted(
                [(d, s.learning_rate) for d, s in self._exploration.items() if s.learning_rate > 0],
                key=lambda x: x[1],
                reverse=True,
            )[:5],
        }

    # --- Reporting ---

    @property
    def stats(self) -> dict[str, Any]:
        goals = list(self._goals.values())
        deployed = [g for g in goals if g.status == GoalStatus.DEPLOYED]
        completed = [g for g in goals if g.status == GoalStatus.COMPLETED]
        avg_feasibility = sum(g.feasibility_score for g in goals) / max(len(goals), 1)

        return {
            "total_goals": len(goals),
            "deployed_goals": len(deployed),
            "completed_goals": len(completed),
            "avg_feasibility_score": round(avg_feasibility, 4),
            "domains_exploring": sum(1 for s in self._exploration.values() if s.visits > 0),
            "total_domains_known": len(self._known_domains) + len(self._exploration_domains),
            "curiosity_index": sum(s.knowledge_gained for s in self._exploration.values()),
        }
