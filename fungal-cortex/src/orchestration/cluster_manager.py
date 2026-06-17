"""Cluster Manager — 5 specialties × N instances cluster management.

The cluster manager handles:
1. Specialty registration and agent allocation
2. Cross-specialty communication routing
3. Agent lifecycle within clusters (spawn, idle, activate, decommission)
4. Load balancing across instances within a specialty
5. Cluster health monitoring

5 Specialties (from AGENT.md / L6 SKILL.md):
- REGIME: 体制研究 — Market regime detection and classification
- STRATEGY: 策略挖掘 — Strategy generation and optimization
- INDICATOR: 指标编译 — Technical indicator compilation
- TACTICAL: 本土战法 — Local trading tactics
- RISK: 风控压力 — Risk control and stress testing
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.event_bus import EventBus
from src.utils.logging import CortexLogger


class Specialty(Enum):
    REGIME = "regime"
    STRATEGY = "strategy"
    INDICATOR = "indicator"
    TACTICAL = "tactical"
    RISK = "risk"


class AgentStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    OFFLINE = "offline"


@dataclass
class AgentHandle:
    """A handle to a managed agent instance."""

    agent_id: str
    specialty: Specialty
    status: AgentStatus = AgentStatus.IDLE
    load: float = 0.0  # 0-1, current utilization
    task_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    last_heartbeat: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SpecialtyCluster:
    """A cluster of agents sharing the same specialty."""

    specialty: Specialty
    agents: dict[str, AgentHandle] = field(default_factory=dict)
    max_instances: int = 20
    min_instances: int = 1
    coordinator_id: str = ""  # Elected coordinator for N×N → coordinator routing
    total_tasks_processed: int = 0
    total_errors: int = 0

    @property
    def active_count(self) -> int:
        return sum(1 for a in self.agents.values() if a.status != AgentStatus.OFFLINE)

    @property
    def average_load(self) -> float:
        active = [a for a in self.agents.values() if a.status != AgentStatus.OFFLINE]
        if not active:
            return 0.0
        return sum(a.load for a in active) / len(active)


class ClusterManager:
    """Manages 5 specialty clusters with N agent instances each.

    Key operations:
    - register_agent(): Add agent to a specialty cluster
    - route_task(): Route a task to the best available agent
    - elect_coordinator(): Elect coordinator for clusters with ≥3 same-specialty agents
    - scale_cluster(): Auto-scale based on load (add/remove instances)
    - heartbeat(): Health check all agents
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._clusters: dict[Specialty, SpecialtyCluster] = {
            s: SpecialtyCluster(specialty=s) for s in Specialty
        }
        self._event_bus = event_bus
        self._logger = CortexLogger("cluster_manager")
        self._total_tasks = 0

    def register_agent(self, specialty: Specialty, agent_id: str | None = None, metadata: dict[str, Any] | None = None) -> AgentHandle:
        """Register a new agent in its specialty cluster."""
        cluster = self._clusters[specialty]
        if cluster.active_count >= cluster.max_instances:
            raise ValueError(f"Cluster {specialty.value} at max capacity ({cluster.max_instances})")

        handle = AgentHandle(
            agent_id=agent_id or f"agent-{specialty.value}-{uuid.uuid4().hex[:8]}",
            specialty=specialty,
            metadata=metadata or {},
        )
        cluster.agents[handle.agent_id] = handle

        # Elect coordinator if ≥3 agents in same specialty
        if cluster.active_count >= 3 and not cluster.coordinator_id:
            self.elect_coordinator(specialty)

        self._logger.info("agent_registered", agent_id=handle.agent_id, specialty=specialty.value, cluster_size=cluster.active_count)
        return handle

    def deregister_agent(self, agent_id: str) -> bool:
        """Remove an agent from its cluster."""
        for cluster in self._clusters.values():
            if agent_id in cluster.agents:
                del cluster.agents[agent_id]
                if agent_id == cluster.coordinator_id:
                    cluster.coordinator_id = ""
                    if cluster.active_count >= 3:
                        self.elect_coordinator(cluster.specialty)
                return True
        return False

    def route_task(self, specialty: Specialty, task: dict[str, Any]) -> AgentHandle | None:
        """Route a task to the best available agent in the cluster.

        If a coordinator exists, route through coordinator (star topology).
        Otherwise, direct routing to least-loaded agent.
        """
        cluster = self._clusters[specialty]
        self._total_tasks += 1

        # Coordinator routing (star topology reduces N×N communication)
        if cluster.coordinator_id and cluster.coordinator_id in cluster.agents:
            coordinator = cluster.agents[cluster.coordinator_id]
            if coordinator.status != AgentStatus.OFFLINE:
                coordinator.task_count += 1
                coordinator.load = min(1.0, coordinator.task_count / 50.0)
                cluster.total_tasks_processed += 1
                return coordinator

        # Direct routing to least-loaded agent
        available = [
            a for a in cluster.agents.values()
            if a.status in (AgentStatus.IDLE, AgentStatus.BUSY)
        ]
        if not available:
            return None

        best = min(available, key=lambda a: a.load)
        best.task_count += 1
        best.load = min(1.0, best.task_count / 50.0)
        best.status = AgentStatus.BUSY if best.load > 0.7 else AgentStatus.IDLE
        cluster.total_tasks_processed += 1
        return best

    def elect_coordinator(self, specialty: Specialty) -> str | None:
        """Elect a coordinator for a specialty cluster.

        Coordinator is the agent with the highest (task_count - error_count) score.
        """
        cluster = self._clusters[specialty]
        best_agent: AgentHandle | None = None
        best_score = -1

        for agent in cluster.agents.values():
            if agent.status == AgentStatus.OFFLINE:
                continue
            score = agent.task_count - agent.error_count * 2
            if score > best_score:
                best_score = score
                best_agent = agent

        if best_agent:
            cluster.coordinator_id = best_agent.agent_id
            self._logger.info("coordinator_elected", specialty=specialty.value, coordinator=best_agent.agent_id)
            return best_agent.agent_id
        return None

    def scale_cluster(self, specialty: Specialty) -> str:
        """Auto-scale: ADD agents if load > 0.8, REMOVE if load < 0.2 and > min."""
        cluster = self._clusters[specialty]
        avg_load = cluster.average_load
        action = "hold"

        if avg_load > 0.8 and cluster.active_count < cluster.max_instances:
            # Scale up: add 1-2 agents
            count = min(2, cluster.max_instances - cluster.active_count)
            for _ in range(count):
                self.register_agent(specialty)
            action = f"scale_up_{count}"
        elif avg_load < 0.2 and cluster.active_count > cluster.min_instances:
            # Scale down: remove idle agents
            idle = [aid for aid, a in cluster.agents.items() if a.status == AgentStatus.IDLE and a.task_count == 0]
            for aid in idle[:1]:
                self.deregister_agent(aid)
            action = f"scale_down_{min(1, len(idle))}"

        if action != "hold":
            self._logger.info("cluster_scaled", specialty=specialty.value, action=action, avg_load=round(avg_load, 2))
        return action

    def heartbeat(self, agent_id: str) -> bool:
        """Record a heartbeat from an agent. Returns False if agent not found."""
        for cluster in self._clusters.values():
            if agent_id in cluster.agents:
                cluster.agents[agent_id].last_heartbeat = time.time()
                return True
        return False

    def check_offline_agents(self, timeout_seconds: float = 30.0) -> list[str]:
        """Mark agents as offline if heartbeat timeout exceeded. Returns list of offline IDs."""
        now = time.time()
        offline: list[str] = []
        for cluster in self._clusters.values():
            for agent_id, agent in cluster.agents.items():
                if now - agent.last_heartbeat > timeout_seconds and agent.status != AgentStatus.OFFLINE:
                    agent.status = AgentStatus.OFFLINE
                    offline.append(agent_id)
        return offline

    def get_cluster(self, specialty: Specialty) -> SpecialtyCluster:
        return self._clusters[specialty]

    @property
    def total_agents(self) -> int:
        return sum(c.active_count for c in self._clusters.values())

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_agents": self.total_agents,
            "total_tasks": self._total_tasks,
            "clusters": {
                s.value: {
                    "active_count": c.active_count,
                    "coordinator": c.coordinator_id,
                    "avg_load": round(c.average_load, 3),
                    "total_processed": c.total_tasks_processed,
                    "total_errors": c.total_errors,
                }
                for s, c in self._clusters.items()
            },
        }
