"""L5 Root Agent — cluster lifecycle management + cross-agent coordination.

The Root Agent is the "Mother Tree" of the Fungal Cortex — it doesn't trade
or analyze, but manages the lifecycle of all worker agents (spawn, monitor,
promote, terminate) and coordinates cross-cluster communication.

Biological Metaphor:
  Mother Tree (母树): 森林中最古老/最大的树, 通过菌根网络连接整个森林,
  向幼树输送碳/氮/水, 感知森林的整体胁迫状态。

RootAgent roles per the plan:
- boundary_setter: Define the operational boundaries of the system
- axis_definer: Define the coordinate axes (risk, return, time, etc.)
- constraint_enforcer: Enforce global constraints (capital, risk, compliance)
- resource_allocator: Allocate compute budget across specialties
- lifecycle_manager: Spawn/promote/apoptose agents based on performance

v4.0 additions (Phase 4 L5):
  - submit_batch_task(): DAG → cluster distribution (Mother Tree sensing)
  - aggregate_results(): 4 aggregation modes (consensus/weighted/best/cross_validate)
  - Cluster state WebSocket push (hive broadcast)
  - Endogenous target engine integration (forest succession)
  - Global carrying capacity enforcement (carrying capacity)
"""

from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.event_bus import EventBus
from src.utils.logging import CortexLogger


class RootAgentRole(Enum):
    BOUNDARY_SETTER = "boundary_setter"
    AXIS_DEFINER = "axis_definer"
    CONSTRAINT_ENFORCER = "constraint_enforcer"
    RESOURCE_ALLOCATOR = "resource_allocator"
    LIFECYCLE_MANAGER = "lifecycle_manager"


class AgentLifecycle(Enum):
    SPAWNING = "spawning"
    ACTIVE = "active"
    IDLE = "idle"
    PROMOTING = "promoting"
    APOPTOSING = "apoptosing"
    DEAD = "dead"


@dataclass
class RootAgentState:
    """The root agent's internal state."""

    root_id: str
    role: RootAgentRole
    lifecycle: AgentLifecycle = AgentLifecycle.ACTIVE
    managed_agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    boundaries: dict[str, tuple[float, float]] = field(default_factory=dict)
    axes: dict[str, tuple[float, float]] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    resource_budget: float = 1.0  # Normalized total compute budget
    uptime_seconds: float = 0.0
    total_actions: int = 0


class RootAgent:
    """L5 Root Agent — manages the agent colony.

    The Root Agent implements:
    1. Boundary setting: Define the safe operating envelope
    2. Axis definition: Set coordinate axes for agent specialization
    3. Constraint enforcement: Global rules (capital limits, risk limits)
    4. Resource allocation: Budget distribution across specialties
    5. Lifecycle management: Spawn/grow/apoptose agents
    """

    SPECIALTIES = ["regime", "strategy", "indicator", "tactical", "risk"]

    def __init__(self, root_id: str | None = None, event_bus: EventBus | None = None) -> None:
        self.state = RootAgentState(
            root_id=root_id or f"root-{uuid.uuid4().hex[:8]}",
            role=RootAgentRole.LIFECYCLE_MANAGER,
        )
        self._event_bus = event_bus
        self._logger = CortexLogger("root_agent", self.state.root_id[:8])
        self._start_time = time.time()

    def set_boundaries(self, risk_range: tuple[float, float], capital_range: tuple[float, float]) -> None:
        """Define operational boundaries (boundary_setter role)."""
        self.state.boundaries["risk"] = risk_range
        self.state.boundaries["capital"] = capital_range
        self.state.role = RootAgentRole.BOUNDARY_SETTER
        self._logger.info("boundaries_set", risk=risk_range, capital=capital_range)

    def define_axis(self, name: str, min_val: float, max_val: float) -> None:
        """Define a coordinate axis for agents to specialize along."""
        self.state.axes[name] = (min_val, max_val)
        self.state.role = RootAgentRole.AXIS_DEFINER
        self._logger.info("axis_defined", name=name, range=(min_val, max_val))

    def set_constraint(self, name: str, value: Any) -> None:
        """Set a global constraint that all agents must obey."""
        self.state.constraints[name] = value
        self.state.role = RootAgentRole.CONSTRAINT_ENFORCER
        self._logger.info("constraint_set", name=name, value=value)

    def check_constraint(self, name: str, proposed_value: Any) -> tuple[bool, str]:
        """Check if a proposed value violates a constraint."""
        if name not in self.state.constraints:
            return True, "no_constraint"
        limit = self.state.constraints[name]
        if isinstance(limit, (int, float)) and isinstance(proposed_value, (int, float)):
            if proposed_value > limit:
                return False, f"Value {proposed_value} exceeds limit {limit}"
        return True, "ok"

    def allocate_resources(self, allocations: dict[str, float]) -> dict[str, float]:
        """Allocate compute budget across specialties.

        Args:
            allocations: Dict of specialty → desired fraction
        Returns:
            Dict of specialty → allocated fraction (normalized to budget)
        """
        total_desired = sum(allocations.values())
        if total_desired > self.state.resource_budget:
            scale = self.state.resource_budget / total_desired
            allocations = {k: v * scale for k, v in allocations.items()}
        self.state.role = RootAgentRole.RESOURCE_ALLOCATOR
        self._logger.info("resources_allocated", allocations=allocations)
        return allocations

    def spawn_agent(self, specialty: str, metadata: dict[str, Any] | None = None) -> str:
        """Spawn a new agent in a specialty."""
        agent_id = f"agent-{specialty}-{uuid.uuid4().hex[:8]}"
        self.state.managed_agents[agent_id] = {
            "specialty": specialty,
            "lifecycle": AgentLifecycle.SPAWNING.value,
            "spawned_at": time.time(),
            "metadata": metadata or {},
            "performance": 0.5,
            "strikes": 0,
        }
        self.state.total_actions += 1
        self._logger.info("agent_spawned", agent_id=agent_id, specialty=specialty)
        return agent_id

    def promote_agent(self, agent_id: str) -> bool:
        """Promote an agent (upgrade role, expand scope)."""
        info = self.state.managed_agents.get(agent_id)
        if info is None:
            return False
        info["lifecycle"] = AgentLifecycle.PROMOTING.value
        info["performance"] = min(1.0, info.get("performance", 0.5) + 0.1)
        self.state.total_actions += 1
        self._logger.info("agent_promoted", agent_id=agent_id)
        return True

    def apoptose_agent(self, agent_id: str) -> bool:
        """Terminate an underperforming agent."""
        info = self.state.managed_agents.get(agent_id)
        if info is None:
            return False
        info["lifecycle"] = AgentLifecycle.DEAD.value
        self.state.total_actions += 1
        self._logger.info("agent_apoptosed", agent_id=agent_id)
        return True

    def evaluate_agents(self) -> dict[str, list[dict[str, Any]]]:
        """Evaluate all managed agents, return categorized results."""
        result: dict[str, list[dict[str, Any]]] = {
            "excellent": [], "good": [], "adequate": [],
            "underperforming": [], "critical": [],
        }

        for agent_id, info in self.state.managed_agents.items():
            perf = info.get("performance", 0.5)
            entry = {"agent_id": agent_id, **info}
            if perf >= 0.85:
                result["excellent"].append(entry)
            elif perf >= 0.70:
                result["good"].append(entry)
            elif perf >= 0.40:
                result["adequate"].append(entry)
            elif perf >= 0.20:
                result["underperforming"].append(entry)
            else:
                result["critical"].append(entry)

        return result

    async def tick(self) -> None:
        """Periodic tick: update state, evaluate agents, publish events."""
        self.state.uptime_seconds = time.time() - self._start_time

        # Evaluate and take actions
        evals = self.evaluate_agents()
        for agent in evals["critical"]:
            self.apoptose_agent(agent["agent_id"])
        for agent in evals["excellent"]:
            self.promote_agent(agent["agent_id"])

        if self._event_bus:
            await self._event_bus.publish_nowait(
                "root.tick",
                {"managed_count": len(self.state.managed_agents), "ratings": {k: len(v) for k, v in evals.items()}},
                source=self.state.root_id,
            )

    # ── Phase 4 v4.0: Mother Tree Capabilities ──────────────────────

    def submit_batch_task(self, tasks: list[dict[str, Any]],
                          dag_id: str = "") -> dict[str, Any]:
        """Batch task DAG decomposition — Mother Tree sensing forest stress.

        Decompose a batch of tasks and distribute to the optimal agent pool.
        Like a mother tree routing nutrients to saplings through the mycorrhizal network.

        Args:
            tasks: List of {specialty, payload, priority} dicts
            dag_id: Optional parent DAG identifier
        Returns:
            {assigned_count, assignments: {task_id: agent_id}, unassigned: [...]}
        """
        assignments: dict[str, str] = {}
        unassigned: list[dict[str, Any]] = []

        for i, task in enumerate(tasks):
            task_id = task.get("task_id", f"task-{dag_id}-{i}")
            specialty = task.get("specialty", "general")

            # Find best agent for this task
            best_agent = self._find_best_agent(specialty, task.get("priority", 5))
            if best_agent:
                assignments[task_id] = best_agent
                if best_agent in self.state.managed_agents:
                    self.state.managed_agents[best_agent]["task_count"] = (
                        self.state.managed_agents[best_agent].get("task_count", 0) + 1
                    )
            else:
                unassigned.append(task)

        self.state.total_actions += len(tasks)
        self._logger.info(
            "batch_task_submitted",
            total=len(tasks),
            assigned=len(assignments),
            unassigned=len(unassigned),
        )
        return {
            "total": len(tasks),
            "assigned": len(assignments),
            "assignments": assignments,
            "unassigned": unassigned,
        }

    def aggregate_results(self, results: list[dict[str, Any]],
                          method: str = "weighted") -> dict[str, Any]:
        """Aggregate results from multiple agents using 4 strategies.

        Biological metaphors:
          consensus = bee quorum sensing (majority voting)
          weighted = endocrine hormone concentration weighting
          best = immune clonal selection (highest affinity)
          cross_validate = mycorrhizal carbon source-sink verification

        Args:
            results: List of {agent_id, value, confidence, specialty} dicts
            method: "consensus", "weighted", "best", "cross_validate"
        Returns:
            Aggregated result dict
        """
        if not results:
            return {"method": method, "result": None, "confidence": 0.0, "count": 0}

        n = len(results)

        if method == "consensus":
            # Majority vote (bee quorum)
            value_counts: dict[str, int] = defaultdict(int)
            for r in results:
                val = str(r.get("value", ""))
                value_counts[val] += 1
            winner = max(value_counts, key=value_counts.get)
            confidence = value_counts[winner] / n if n > 0 else 0
            return {
                "method": "consensus",
                "result": winner,
                "confidence": confidence,
                "quorum_reached": confidence >= 0.6,
                "count": n,
            }

        elif method == "weighted":
            # Confidence-weighted average (hormone concentration)
            total_weight = 0.0
            weighted_sum = 0.0
            for r in results:
                w = r.get("confidence", 0.5)
                v = r.get("value", 0)
                if isinstance(v, (int, float)):
                    weighted_sum += float(v) * w
                    total_weight += w
            avg = weighted_sum / max(total_weight, 0.001)
            return {
                "method": "weighted",
                "result": avg,
                "confidence": min(1.0, total_weight / n),
                "count": n,
            }

        elif method == "best":
            # Select highest-confidence (clonal selection)
            best = max(results, key=lambda r: r.get("confidence", 0))
            return {
                "method": "best",
                "result": best.get("value"),
                "confidence": best.get("confidence", 0),
                "agent": best.get("agent_id", ""),
                "count": n,
            }

        elif method == "cross_validate":
            # Cross-validation: check consistency across results
            values = [r.get("value", 0) for r in results if isinstance(r.get("value"), (int, float))]
            if len(values) < 2:
                return {"method": "cross_validate", "result": values[0] if values else None, "confidence": 0.3, "count": n}

            mean_val = sum(values) / len(values)
            variance = sum((v - mean_val) ** 2 for v in values) / len(values)
            cv = math.sqrt(variance) / max(abs(mean_val), 0.001) if mean_val != 0 else 1.0

            return {
                "method": "cross_validate",
                "result": mean_val,
                "confidence": max(0.1, 1.0 - cv),
                "variance": variance,
                "coefficient_of_variation": cv,
                "count": n,
            }

        else:
            return {"method": method, "result": None, "confidence": 0.0, "count": n}

    def configure_endogenous_engine(self, engine_config: dict[str, Any]) -> None:
        """Configure the endogenous target engine integration.

        Like forest succession: pioneer species → intermediate → climax community.
        In idle periods, the system self-optimizes and accumulates knowledge.
        """
        self.state.constraints["endogenous_enabled"] = engine_config.get("enabled", True)
        self.state.constraints["endogenous_idle_threshold"] = engine_config.get("idle_threshold", 0.5)
        self.state.constraints["endogenous_interval"] = engine_config.get("interval_seconds", 3600.0)
        self._logger.info("endogenous_engine_configured", config=engine_config)

    def enforce_carrying_capacity(self) -> dict[str, Any]:
        """Enforce global carrying capacity — like forest ecosystem limits.

        Any timepoint's total agent count is limited by CPU/memory/budget.
        Any timepoint's total biomass is limited by soil nutrients/water/sunlight.
        """
        limits = {
            "max_agents": self.state.constraints.get("max_agents", 500),
            "max_cpu_percent": self.state.constraints.get("max_cpu_percent", 80.0),
            "max_memory_mb": self.state.constraints.get("max_memory_mb", 8192.0),
            "max_capital": self.state.constraints.get("max_capital", 1e7),
        }

        current = {
            "agents": len(self.state.managed_agents),
            "cpu_estimate": len(self.state.managed_agents) * 2.0,  # rough estimate
            "memory_estimate": len(self.state.managed_agents) * 100.0,  # MB estimate
        }

        violations: list[str] = []
        if current["agents"] > limits["max_agents"]:
            violations.append(f"Agent count {current['agents']} > {limits['max_agents']}")
        if current["cpu_estimate"] > limits["max_cpu_percent"]:
            violations.append(f"CPU {current['cpu_estimate']:.0f}% > {limits['max_cpu_percent']}%")
        if current["memory_estimate"] > limits["max_memory_mb"]:
            violations.append(f"Memory {current['memory_estimate']:.0f}MB > {limits['max_memory_mb']}MB")

        # Auto-cull if violations found
        culled = 0
        if violations:
            evals = self.evaluate_agents()
            for agent in evals["critical"]:
                self.apoptose_agent(agent["agent_id"])
                culled += 1
            for agent in evals["underperforming"]:
                if culled < len(violations) * 3:
                    self.apoptose_agent(agent["agent_id"])
                    culled += 1

        return {
            "violations": violations,
            "culled": culled,
            "current": current,
            "limits": limits,
            "within_capacity": len(violations) == 0,
        }

    def get_cluster_state_for_broadcast(self) -> dict[str, Any]:
        """Get cluster state for WebSocket broadcast — hive status update.

        Like scout bees returning to hive: not just food location,
        but also urgency encoded in wing vibration frequency.
        """
        evals = self.evaluate_agents()
        return {
            "root_id": self.state.root_id,
            "managed_count": len(self.state.managed_agents),
            "agent_distribution": {
                specialty: sum(
                    1 for info in self.state.managed_agents.values()
                    if info.get("specialty") == specialty
                )
                for specialty in self.SPECIALTIES
            },
            "performance_summary": {k: len(v) for k, v in evals.items()},
            "constraints_active": len(self.state.constraints),
            "boundaries": dict(self.state.boundaries),
            "timestamp": time.time(),
        }

    # ── Private Helpers ─────────────────────────────────────────────

    def _find_best_agent(self, specialty: str, priority: int = 5) -> str | None:
        """Find the best available agent for a task."""
        candidates: list[tuple[float, str]] = []
        for agent_id, info in self.state.managed_agents.items():
            if info.get("lifecycle") not in (AgentLifecycle.ACTIVE.value, AgentLifecycle.IDLE.value):
                continue
            if info.get("specialty") != specialty:
                continue

            perf = info.get("performance", 0.5)
            load = info.get("task_count", 0)
            # Score: higher performance, lower load
            score = perf * 0.7 + (1.0 / max(load + 1, 1)) * 0.3
            if priority > 5:
                score *= 1.2  # urgent tasks get wider search
            candidates.append((score, agent_id))

        if not candidates:
            # Fallback: any idle agent
            for agent_id, info in self.state.managed_agents.items():
                if info.get("lifecycle") == AgentLifecycle.IDLE.value:
                    candidates.append((0.3, agent_id))

        if not candidates:
            # Try to spawn new agent
            return self.spawn_agent(specialty)

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    @property
    def stats(self) -> dict[str, Any]:
        evals = self.evaluate_agents()
        return {
            "root_id": self.state.root_id,
            "role": self.state.role.value,
            "managed_agents": len(self.state.managed_agents),
            "boundaries": dict(self.state.boundaries),
            "axes": list(self.state.axes.keys()),
            "constraints": len(self.state.constraints),
            "agent_evaluations": {k: len(v) for k, v in evals.items()},
            "uptime_seconds": time.time() - self._start_time,
        }
