"""L2: Agent Evolution — success→proliferate, failure→apoptose.

Operates at the daily timescale. Agents are evaluated on cumulative performance.
Successful agents replicate (with mutation) and expand capabilities.
Failing agents are removed (apoptose) and their resources reallocated.

Inspired by clonal selection in the immune system and natural selection
in evolutionary biology. This is the "middle tier" of the 3-level evolution.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentFitness:
    """Multi-dimensional fitness assessment for one agent."""

    agent_id: str
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    consistency: float  # How stable is performance over time
    composite_fitness: float  # Weighted overall
    generation: int


@dataclass
class AgentGenome:
    """Agent's evolvable characteristics."""

    agent_id: str
    specialty: str
    strategy_dna: dict[str, float]  # Core strategy parameters
    skill_set: list[str]  # Active skills
    risk_profile: str  # "aggressive", "neutral", "conservative"
    mutation_history: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    parent_id: str | None = None


class AgentEvolver:
    """L2: Agent-level evolution through proliferation and apoptosis.

    Timescale: daily evaluation cycle.

    Success threshold: composite_fitness ≥ threshold → replicate (with mutation)
    Failure threshold: composite_fitness < apoptose_threshold → remove
    Between thresholds: maintain, no change

    Mutation types:
    - Parameter tweak: small adjustment to strategy DNA
    - Skill expansion: add a new skill from available pool
    - Risk profile shift: move toward more/less aggressive
    """

    def __init__(
        self,
        success_threshold: float = 0.6,
        apoptose_threshold: float = 0.2,
        mutation_rate: float = 0.1,
        seed: int | None = None,
    ) -> None:
        self._success_t = success_threshold
        self._apoptose_t = apoptose_threshold
        self._mutation_rate = mutation_rate
        self._agents: dict[str, AgentGenome] = {}
        self._fitness_history: dict[str, list[AgentFitness]] = {}
        self._generation = 0
        self._available_skills: list[str] = []
        if seed is not None:
            random.seed(seed)

    def register_agent(
        self,
        agent_id: str,
        specialty: str,
        strategy_dna: dict[str, float],
        skills: list[str],
        risk_profile: str = "neutral",
    ) -> AgentGenome:
        genome = AgentGenome(
            agent_id=agent_id,
            specialty=specialty,
            strategy_dna=dict(strategy_dna),
            skill_set=list(skills),
            risk_profile=risk_profile,
        )
        self._agents[agent_id] = genome
        self._fitness_history[agent_id] = []
        return genome

    def set_available_skills(self, skills: list[str]) -> None:
        self._available_skills = list(skills)

    def evaluate(
        self,
        agent_id: str,
        sharpe: float,
        win_rate: float,
        profit_factor: float,
        max_drawdown: float,
        consistency: float = 0.5,
    ) -> AgentFitness:
        """Evaluate one agent's multi-dimensional fitness."""
        composite = (
            0.35 * min(sharpe / 3.0, 1.0)
            + 0.25 * win_rate
            + 0.20 * min(profit_factor / 3.0, 1.0)
            + 0.10 * (1.0 - min(max_drawdown, 1.0))
            + 0.10 * consistency
        )

        fitness = AgentFitness(
            agent_id=agent_id,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            consistency=consistency,
            composite_fitness=composite,
            generation=self._generation,
        )

        self._fitness_history.setdefault(agent_id, []).append(fitness)
        return fitness

    def evolve(self, fitness_scores: list[AgentFitness]) -> dict[str, Any]:
        """Apply evolution: proliferate successes, apoptose failures."""
        self._generation += 1
        actions: dict[str, list[str]] = {"proliferated": [], "apoptosed": [], "mutated": []}

        for fitness in fitness_scores:
            agent = self._agents.get(fitness.agent_id)
            if agent is None:
                continue

            if fitness.composite_fitness >= self._success_t:
                # Proliferate: create mutated copy
                child_id = self._proliferate(agent, fitness)
                if child_id:
                    actions["proliferated"].append(child_id)

            elif fitness.composite_fitness < self._apoptose_t:
                # Apoptose: remove agent
                self._apoptose(fitness.agent_id)
                actions["apoptosed"].append(fitness.agent_id)

            else:
                # Maintain with possible mutation
                if random.random() < self._mutation_rate:
                    self._mutate(agent)
                    actions["mutated"].append(fitness.agent_id)

        return actions

    def _proliferate(self, parent: AgentGenome, fitness: AgentFitness) -> str | None:
        """Create a mutated child from a successful parent."""
        child_id = f"{parent.agent_id}-gen{self._generation}"
        child_dna = dict(parent.strategy_dna)

        # Mutate DNA
        for key in child_dna:
            if random.random() < self._mutation_rate:
                child_dna[key] += random.gauss(0.0, abs(child_dna[key]) * 0.05 + 0.001)

        # Possibly expand skills
        child_skills = list(parent.skill_set)
        if self._available_skills and random.random() < 0.3:
            new_skills = [s for s in self._available_skills if s not in child_skills]
            if new_skills:
                child_skills.append(random.choice(new_skills))

        child = AgentGenome(
            agent_id=child_id,
            specialty=parent.specialty,
            strategy_dna=child_dna,
            skill_set=child_skills,
            risk_profile=parent.risk_profile,
            parent_id=parent.agent_id,
        )
        self._agents[child_id] = child
        self._fitness_history[child_id] = []
        return child_id

    def _apoptose(self, agent_id: str) -> None:
        if agent_id in self._agents:
            del self._agents[agent_id]

    def _mutate(self, agent: AgentGenome) -> None:
        """Apply random mutation to an agent."""
        # Parameter tweak
        for key in agent.strategy_dna:
            if random.random() < self._mutation_rate * 0.5:
                agent.strategy_dna[key] += random.gauss(0.0, abs(agent.strategy_dna[key]) * 0.02 + 0.001)

        # Risk profile shift
        profiles = ["aggressive", "neutral", "conservative"]
        if random.random() < self._mutation_rate * 0.3:
            current_idx = profiles.index(agent.risk_profile) if agent.risk_profile in profiles else 1
            shift = random.choice([-1, 1])
            new_idx = max(0, min(len(profiles) - 1, current_idx + shift))
            agent.risk_profile = profiles[new_idx]

        agent.mutation_history.append(f"mutated-gen{self._generation}")

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "agent_count": len(self._agents),
            "generation": self._generation,
            "success_threshold": self._success_t,
            "apoptose_threshold": self._apoptose_t,
            "specialties": list(set(a.specialty for a in self._agents.values())),
        }
