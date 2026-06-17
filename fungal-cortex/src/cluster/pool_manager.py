"""L5 4.3: AgentPoolManager — "内分泌能量分配系统"(EAS) Agent池管理器.

Biological Metaphor:
  内分泌能量分配系统(EAS): HPA+HPT+HPG三轴根据线粒体储备协调能量分配
    - 不是"谁喊得响就给谁", 而是根据全局需求智能调配
    - 运动时: 骨骼肌血流从20%→80%, 内脏血流相应减少
    - 安静时: 恢复基线分配

  BCAA代谢反馈(Akh→BCAA分解→谷胱甘肽→负反馈抑制Akh):
    昆虫的脂肪体释放Akh激素→刺激BCAA分解→产生谷胱甘肽
    →谷胱甘肽积累到阈值后负反馈抑制Akh释放
    →自主代谢稳态! 不需要大脑控制!

  三级池:
    active(执行中) = 骨骼肌(高能耗, 高产出)
    idle(等待) = 肝脏(待命, 随时可被激活)
    sleep(低功耗) = 脂肪组织(长期储能, 慢速释能)

Reference:
  Schuler et al. (2026), "Energy Allocation System", IJMS;
  BCAA-Akh feedback loop (2026), Nature Communications
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.cluster.agent_factory import AgentSpecialty, ClusterAgent
from src.cluster.communicator import ClusterCommunicator
from src.utils.logging import CortexLogger


# ── Constants ────────────────────────────────────────────────────────

class PoolState(str, Enum):
    """Pool energy states."""
    ACTIVE = "active"    # 骨骼肌: 高能耗/产出
    IDLE = "idle"        # 肝脏: 待命
    SLEEP = "sleep"      # 脂肪组织: 长期储能


UTILIZATION_HIGH = 0.7   # >70% → expand
UTILIZATION_LOW = 0.3    # <30% → shrink
COOLDOWN_SECONDS = 60.0  # hormone pulse interval
PHEROMONE_HALF_LIFE = 60.0  # task pheromone evaporation
MAX_POOL_SIZE = 100


# ── Data Structures ──────────────────────────────────────────────────


@dataclass
class AgentPool:
    """A pool of agents sharing a specialty — like a tissue/organ."""

    pool_id: str
    specialty: AgentSpecialty
    state: PoolState = PoolState.IDLE
    agents: list[str] = field(default_factory=list)  # agent_ids
    max_size: int = 10
    utilization: float = 0.0
    created_at: float = field(default_factory=time.time)
    last_scaled: float = 0.0
    task_completion_rate: float = 0.0  # tasks completed / tasks assigned
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadBalancer:
    """Load balancer with pheromone-guided routing."""

    task_type_pheromones: dict[str, deque[tuple[str, float]]] = field(
        default_factory=lambda: defaultdict(lambda: deque(maxlen=100))
    )  # {task_type: [(agent_id, quality_score), ...]}

    def deposit(self, task_type: str, agent_id: str, quality: float) -> None:
        self.task_type_pheromones[task_type].append((agent_id, quality))

    def select(self, task_type: str) -> str | None:
        """Select best agent for task type based on pheromone quality scores."""
        candidates = self.task_type_pheromones.get(task_type)
        if not candidates:
            return None

        # Score each agent by recent quality * recency
        scores: dict[str, float] = defaultdict(float)
        total_weight = 0.0
        for i, (aid, quality) in enumerate(candidates):
            recency = (i + 1) / len(candidates)  # newer = higher weight
            scores[aid] += quality * recency
            total_weight += quality * recency

        if not scores:
            return None

        # Probabilistic selection weighted by score
        import random
        r = random.random() * sum(scores.values())
        cumulative = 0.0
        for aid, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            cumulative += score
            if r <= cumulative:
                return aid

        return max(scores, key=scores.get)


# ── Main Class ───────────────────────────────────────────────────────


class AgentPoolManager:
    """Endocrine Energy Allocation System for cluster agent pools.

    Manages three-tier pools (active/idle/sleep), auto-scales based on
    utilization, and uses pheromone-guided load balancing (ACO-inspired).

    Config:
      - utilization_high: threshold for expansion
      - utilization_low: threshold for contraction
      - cooldown: minimum seconds between scaling operations
    """

    def __init__(
        self,
        utilization_high: float = UTILIZATION_HIGH,
        utilization_low: float = UTILIZATION_LOW,
        cooldown: float = COOLDOWN_SECONDS,
        communicator: ClusterCommunicator | None = None,
    ) -> None:
        self._util_high = utilization_high
        self._util_low = utilization_low
        self._cooldown = cooldown

        self._pools: dict[str, AgentPool] = {}  # {specialty.value: pool}
        self._load_balancer = LoadBalancer()
        self._communicator = communicator
        self._logger = CortexLogger("pool_manager")

    # ── Public API ──────────────────────────────────────────────────

    def register_pool(
        self, specialty: AgentSpecialty, max_size: int = 10
    ) -> AgentPool:
        """Register a new agent pool for a specialty."""
        if specialty.value in self._pools:
            return self._pools[specialty.value]

        pool = AgentPool(
            pool_id=self._gen_pool_id(specialty.value),
            specialty=specialty,
            max_size=max_size,
        )
        self._pools[specialty.value] = pool
        return pool

    def add_agent(self, agent: ClusterAgent) -> bool:
        """Add an agent to its specialty pool."""
        pool = self._pools.get(agent.specialty.value)
        if pool is None:
            pool = self.register_pool(agent.specialty)

        if len(pool.agents) >= pool.max_size:
            return False

        pool.agents.append(agent.agent_id)
        self._update_utilization(pool)
        return True

    def remove_agent(self, agent: ClusterAgent) -> bool:
        """Remove an agent from its pool."""
        pool = self._pools.get(agent.specialty.value)
        if pool is None:
            return False
        if agent.agent_id in pool.agents:
            pool.agents.remove(agent.agent_id)
            self._update_utilization(pool)
            return True
        return False

    def assign_task(self, task_type: str, task_id: str) -> str | None:
        """Assign a task to the best agent using pheromone-guided selection.

        Returns agent_id or None.
        """
        # Try pheromone-based routing first
        agent_id = self._load_balancer.select(task_type)

        if agent_id is None:
            # Fallback: find first active pool with capacity
            for pool in self._pools.values():
                if pool.state == PoolState.ACTIVE and pool.agents:
                    agent_id = pool.agents[0]
                    break

        if agent_id and self._communicator:
            # Mark task assignment via communication
            self._communicator.deposit_pheromone("task", f"assigned:{task_id}", 1.0, agent_id)

        return agent_id

    def complete_task(self, task_type: str, agent_id: str, quality: float) -> None:
        """Record task completion with quality score (pheromone deposition)."""
        self._load_balancer.deposit(task_type, agent_id, quality)

        # Update pool completion rate
        for pool in self._pools.values():
            if agent_id in pool.agents:
                alpha = 0.1
                pool.task_completion_rate = (
                    (1 - alpha) * pool.task_completion_rate + alpha * quality
                )
                break

    def auto_scale(self, factory) -> dict[str, Any]:
        """Auto-scale pools based on utilization (endocrine regulation).

        utilization > 70% → expand (activate sleep→idle, idle→active)
        utilization < 30% → shrink (active→idle, idle→sleep)
        """
        actions: dict[str, list[str]] = {"expanded": [], "contracted": [], "unchanged": []}
        now = time.time()

        for pool in self._pools.values():
            if now - pool.last_scaled < self._cooldown:
                actions["unchanged"].append(pool.specialty.value)
                continue

            utilization = len(pool.agents) / max(pool.max_size, 1)

            if utilization > self._util_high and pool.state == PoolState.ACTIVE:
                # Need more agents — activate from idle pool or expand max
                old_max = pool.max_size
                pool.max_size = min(MAX_POOL_SIZE, int(pool.max_size * 1.3))
                pool.last_scaled = now
                actions["expanded"].append(
                    f"{pool.specialty.value}: {old_max}→{pool.max_size}"
                )
                self._logger.info("pool_expanded", pool=pool.specialty.value, size=pool.max_size)

            elif utilization < self._util_low and pool.state == PoolState.ACTIVE:
                # Overcapacity — shrink
                old_max = pool.max_size
                pool.max_size = max(3, int(pool.max_size * 0.7))
                pool.last_scaled = now
                actions["contracted"].append(
                    f"{pool.specialty.value}: {old_max}→{pool.max_size}"
                )
                self._logger.info("pool_contracted", pool=pool.specialty.value, size=pool.max_size)

            else:
                actions["unchanged"].append(pool.specialty.value)

            self._update_utilization(pool)

        return {
            "actions": actions,
            "timestamp": now,
        }

    def get_pool(self, specialty: AgentSpecialty) -> AgentPool | None:
        return self._pools.get(specialty.value)

    def overall_utilization(self) -> float:
        """Total system utilization across all pools."""
        total_agents = sum(len(p.agents) for p in self._pools.values())
        total_capacity = sum(p.max_size for p in self._pools.values())
        return total_agents / max(total_capacity, 1)

    # ── Private Methods ─────────────────────────────────────────────

    def _update_utilization(self, pool: AgentPool) -> None:
        pool.utilization = len(pool.agents) / max(pool.max_size, 1)
        # State transitions
        if pool.utilization > self._util_high:
            pool.state = PoolState.ACTIVE
        elif pool.utilization < self._util_low:
            pool.state = PoolState.IDLE
        else:
            pool.state = PoolState.ACTIVE

    @staticmethod
    def _gen_pool_id(specialty: str) -> str:
        return hashlib.md5(f"pool_{specialty}".encode()).hexdigest()[:16]

    @property
    def pools(self) -> list[AgentPool]:
        return list(self._pools.values())

    @property
    def stats(self) -> dict[str, Any]:
        pool_stats = {}
        for key, pool in self._pools.items():
            pool_stats[key] = {
                "state": pool.state.value,
                "agents": len(pool.agents),
                "max_size": pool.max_size,
                "utilization": round(pool.utilization, 3),
                "completion_rate": round(pool.task_completion_rate, 3),
            }
        return {
            "pools": pool_stats,
            "overall_utilization": round(self.overall_utilization(), 3),
            "load_balancer_entries": sum(len(v) for v in self._load_balancer.task_type_pheromones.values()),
        }
