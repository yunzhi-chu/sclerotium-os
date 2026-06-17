"""M3: Cluster Self-Organizer — 7-day evaluation + destroy/promote/spawn/reassign.

Inspired by mycelial network self-organization:
- Agent performance evaluated on 4 dimensions (success × efficiency × quality × resource)
- Excellent → promote (expand specialties)
- Underperforming 3 consecutive times → destroy (apoptose)
- Same-specialty ≥3 agents → elect coordinator (reduce N×N communication)
- Spawn new agents in high-gradient (nutrient-rich) regions
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class AgentVerdict(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    ADEQUATE = "adequate"
    UNDERPERFORMING = "underperforming"
    CRITICAL = "critical"


class AgentSpecialty(str, Enum):
    REGIME_RESEARCH = "regime_research"
    STRATEGY_MINING = "strategy_mining"
    INDICATOR_COMPILATION = "indicator_compilation"
    TACTICS_RESEARCH = "tactics_research"
    RISK_CONTROL = "risk_control"


@dataclass
class AgentPerformance:
    agent_id: str
    specialty: AgentSpecialty
    success_rate: float
    efficiency: float
    quality: float
    resource_usage: float
    overall: float
    verdict: AgentVerdict
    eval_timestamp: float = field(default_factory=time.time)


@dataclass
class ClusterTopology:
    """Current topology state: coordinators, clusters, communication edges."""

    coordinators: dict[str, str]  # specialty → coordinator agent_id
    clusters: dict[str, list[str]]  # specialty → [agent_ids]
    communication_edges: list[tuple[str, str]]  # (agent_a, agent_b)
    last_reorganized: float = field(default_factory=time.time)


class ClusterSelfOrganizer:
    """M3: Self-organizing agent clusters through evaluation and restructuring.

    Core algorithm:
    1. evaluate_all_agents() — multi-dimensional performance scoring
    2. reorganize() — destroy/promote/spawn/reassign based on verdicts
    3. optimize_topology() — elect coordinators, prune edges

    Config:
    - eval_cycle_days: 7-day evaluation cycle
    - success=0.35, efficiency=0.25, quality=0.25, resource=0.15
    - excellent ≥ 0.85 → promote
    - underperforming < 0.40, 3 consecutive → destroy
    """

    def __init__(
        self,
        success_weight: float = 0.35,
        efficiency_weight: float = 0.25,
        quality_weight: float = 0.25,
        resource_weight: float = 0.15,
        excellent_threshold: float = 0.85,
        underperforming_threshold: float = 0.40,
        underperforming_strikes: int = 3,
        coordinator_min_same: int = 3,
    ) -> None:
        self._success_w = success_weight
        self._efficiency_w = efficiency_weight
        self._quality_w = quality_weight
        self._resource_w = resource_weight
        self._excellent_t = excellent_threshold
        self._underperforming_t = underperforming_threshold
        self._underperforming_strikes = underperforming_strikes
        self._coordinator_min_same = coordinator_min_same

        self._logger = CortexLogger("cluster_organizer")
        self._agents: dict[str, dict[str, Any]] = {}  # agent_id → metadata
        self._performance_history: dict[str, list[AgentPerformance]] = {}
        self._strike_counts: dict[str, int] = {}
        self._topology = ClusterTopology(coordinators={}, clusters={}, communication_edges=[])
        self._generation = 0

    def register_agent(self, agent_id: str, specialty: AgentSpecialty, metadata: dict[str, Any] | None = None) -> None:
        self._agents[agent_id] = {
            "specialty": specialty,
            "registered_at": time.time(),
            "status": "active",
            "metadata": metadata or {},
        }
        self._strike_counts[agent_id] = 0
        self._performance_history[agent_id] = []

    def evaluate_all_agents(
        self,
        success_rates: dict[str, float],
        efficiency_scores: dict[str, float],
        quality_scores: dict[str, float],
        resource_usages: dict[str, float],
    ) -> list[AgentPerformance]:
        """Score every active agent on 4 dimensions and assign verdicts."""
        results: list[AgentPerformance] = []

        for agent_id, agent in self._agents.items():
            if agent["status"] != "active":
                continue

            success = success_rates.get(agent_id, 0.0)
            efficiency = efficiency_scores.get(agent_id, 0.0)
            quality = quality_scores.get(agent_id, 0.0)
            resource = resource_usages.get(agent_id, 0.0)
            overall = self._calculate_performance(success, efficiency, quality, resource)
            verdict = self._verdict(overall)

            perf = AgentPerformance(
                agent_id=agent_id,
                specialty=agent["specialty"],
                success_rate=success,
                efficiency=efficiency,
                quality=quality,
                resource_usage=resource,
                overall=overall,
                verdict=verdict,
            )

            self._performance_history[agent_id].append(perf)
            if len(self._performance_history[agent_id]) > 50:
                self._performance_history[agent_id] = self._performance_history[agent_id][-50:]

            # Track consecutive underperforming
            if verdict in (AgentVerdict.UNDERPERFORMING, AgentVerdict.CRITICAL):
                self._strike_counts[agent_id] = self._strike_counts.get(agent_id, 0) + 1
            else:
                self._strike_counts[agent_id] = 0

            results.append(perf)

        self._logger.info("evaluation_complete", agents_evaluated=len(results))
        return results

    def _calculate_performance(self, success: float, efficiency: float, quality: float, resource: float) -> float:
        return (
            self._success_w * success
            + self._efficiency_w * efficiency
            + self._quality_w * quality
            + self._resource_w * (1.0 - resource)  # Lower resource = better
        )

    def _verdict(self, overall: float) -> AgentVerdict:
        if overall >= self._excellent_t:
            return AgentVerdict.EXCELLENT
        if overall >= 0.70:
            return AgentVerdict.GOOD
        if overall >= self._underperforming_t:
            return AgentVerdict.ADEQUATE
        if overall >= 0.20:
            return AgentVerdict.UNDERPERFORMING
        return AgentVerdict.CRITICAL

    def reorganize(self, evaluations: list[AgentPerformance]) -> dict[str, Any]:
        """Apply verdict decisions: destroy/promote/spawn/reassign."""
        actions = {"destroyed": [], "promoted": [], "spawned": [], "reassigned": []}
        self._generation += 1

        for perf in evaluations:
            agent = self._agents.get(perf.agent_id)
            if not agent or agent["status"] != "active":
                continue

            if perf.verdict in (AgentVerdict.UNDERPERFORMING, AgentVerdict.CRITICAL):
                strikes = self._strike_counts.get(perf.agent_id, 0)
                if strikes >= self._underperforming_strikes:
                    self._destroy_agent(perf.agent_id)
                    actions["destroyed"].append(perf.agent_id)
                    self._spawn_replacement(perf.specialty, actions)

            elif perf.verdict == AgentVerdict.EXCELLENT:
                self._promote_agent(perf.agent_id, perf.specialty)
                actions["promoted"].append(perf.agent_id)

        self._logger.info(
            "reorganization_complete",
            generation=self._generation,
            destroyed=len(actions["destroyed"]),
            promoted=len(actions["promoted"]),
        )
        return actions

    def _destroy_agent(self, agent_id: str) -> None:
        if agent_id in self._agents:
            self._agents[agent_id]["status"] = "apoptosed"
        self._strike_counts[agent_id] = 0

    def _spawn_replacement(self, specialty: AgentSpecialty, actions: dict[str, Any]) -> None:
        """Spawn a new agent in the same specialty (nutrient-rich = high-gradient area)."""
        new_id = f"agent-{specialty.value}-gen{self._generation}-{len(actions['spawned'])}"
        self.register_agent(new_id, specialty, {"spawned_generation": self._generation})
        actions["spawned"].append(new_id)

    def _promote_agent(self, agent_id: str, current_specialty: AgentSpecialty) -> None:
        """Promote: agent can expand to 2 related specialties."""
        agent = self._agents[agent_id]
        expanded = agent.get("expanded_specialties", [])
        related = self._related_specialties(current_specialty)
        for rel in related:
            if rel.value not in expanded and len(expanded) < 2:
                expanded.append(rel.value)
        agent["expanded_specialties"] = expanded

    @staticmethod
    def _related_specialties(specialty: AgentSpecialty) -> list[AgentSpecialty]:
        mapping = {
            AgentSpecialty.REGIME_RESEARCH: [AgentSpecialty.STRATEGY_MINING, AgentSpecialty.TACTICS_RESEARCH],
            AgentSpecialty.STRATEGY_MINING: [AgentSpecialty.INDICATOR_COMPILATION, AgentSpecialty.RISK_CONTROL],
            AgentSpecialty.INDICATOR_COMPILATION: [AgentSpecialty.STRATEGY_MINING, AgentSpecialty.TACTICS_RESEARCH],
            AgentSpecialty.TACTICS_RESEARCH: [AgentSpecialty.REGIME_RESEARCH, AgentSpecialty.RISK_CONTROL],
            AgentSpecialty.RISK_CONTROL: [AgentSpecialty.STRATEGY_MINING, AgentSpecialty.INDICATOR_COMPILATION],
        }
        return mapping.get(specialty, [])

    def optimize_topology(self) -> ClusterTopology:
        """Elect coordinators and prune communication edges.

        Same-specialty ≥ coordinator_min_same → elect coordinator.
        Coordinator reduces N×N communication to N×1 (hub-spoke).
        """
        specialty_groups: dict[str, list[str]] = {}
        for agent_id, agent in self._agents.items():
            if agent["status"] != "active":
                continue
            spec = agent["specialty"].value
            specialty_groups.setdefault(spec, []).append(agent_id)

        coordinators: dict[str, str] = {}
        edges: list[tuple[str, str]] = []

        for spec, agents in specialty_groups.items():
            specialty_groups[spec] = agents
            if len(agents) >= self._coordinator_min_same:
                coordinator = self._elect_coordinator(agents)
                coordinators[spec] = coordinator
                for agent_id in agents:
                    if agent_id != coordinator:
                        edges.append((coordinator, agent_id))
            else:
                for i, a1 in enumerate(agents):
                    for a2 in agents[i + 1 :]:
                        edges.append((a1, a2))

        self._topology = ClusterTopology(
            coordinators=coordinators,
            clusters=specialty_groups,
            communication_edges=edges,
        )

        self._logger.info("topology_optimized", coordinators=len(coordinators), edges=len(edges))
        return self._topology

    def _elect_coordinator(self, agent_ids: list[str]) -> str:
        """Elect the agent with highest average performance as coordinator."""
        best_id = agent_ids[0]
        best_score = -1.0
        for agent_id in agent_ids:
            history = self._performance_history.get(agent_id, [])
            if history:
                avg = sum(p.overall for p in history[-3:]) / min(len(history), 3)
            else:
                avg = 0.0
            if avg > best_score:
                best_score = avg
                best_id = agent_id
        return best_id

    def get_agent_history(self, agent_id: str) -> list[AgentPerformance]:
        return list(self._performance_history.get(agent_id, []))

    def get_active_agents(self) -> list[str]:
        return [aid for aid, a in self._agents.items() if a["status"] == "active"]

    @property
    def topology(self) -> ClusterTopology:
        return self._topology

    @property
    def stats(self) -> dict[str, Any]:
        active = self.get_active_agents()
        specialty_counts: dict[str, int] = {}
        for aid in active:
            spec = self._agents[aid]["specialty"].value
            specialty_counts[spec] = specialty_counts.get(spec, 0) + 1

        return {
            "total_agents": len(self._agents),
            "active_agents": len(active),
            "apoptosed_agents": len(self._agents) - len(active),
            "generation": self._generation,
            "specialty_distribution": specialty_counts,
            "coordinators": len(self._topology.coordinators),
            "clusters": len(self._topology.clusters),
            "communication_edges": len(self._topology.communication_edges),
            "average_strikes": sum(self._strike_counts.values()) / max(len(self._strike_counts), 1),
        }
