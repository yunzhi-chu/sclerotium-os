"""L5 4.1: AgentFactory — "干细胞生态位"(HSC Niche) Agent工厂.

Biological Metaphor:
  骨髓中的造血干细胞(Hematopoietic Stem Cell, HSC)生态位:
    - 一个HSC可以分化为所有血细胞类型: 红细胞(O2运输)/白细胞(免疫防御)/血小板(修复)
    - 不同类型在需要时被不同生长因子激活: EPO→红细胞, G-CSF→中性粒细胞, TPO→血小板
    - 生态位(Niche): 骨髓微环境精确调控HSC的静止/增殖/分化

  AgentFactory = 骨髓生态位:
    - REGIME_RESEARCH = 记忆T细胞(巡逻检测异常)
    - STRATEGY_MINING = B细胞(产生抗体=策略)
    - INDICATOR_COMPILATION = 红细胞(携带"氧气"=技术指标)
    - TACTICS_RESEARCH = NK细胞(快速反应)
    - RISK_CONTROL = Treg细胞(抑制过度反应)

Reference:
  Schuler et al. (2026), "Energy Allocation System", IJMS 27(3):1345
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from src.utils.logging import CortexLogger


# ── Constants ────────────────────────────────────────────────────────

class AgentSpecialty(str, Enum):
    """Agent specialties — blood cell type analogs."""
    REGIME_RESEARCH = "regime_research"     # 记忆T细胞: 巡逻检测异常
    STRATEGY_MINING = "strategy_mining"      # B细胞: 产生抗体/策略
    INDICATOR_COMPILATION = "indicator_compilation"  # 红细胞: 携带氧气/指标
    TACTICS_RESEARCH = "tactics_research"    # NK细胞: 快速反应
    RISK_CONTROL = "risk_control"            # Treg: 抑制过度反应
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"  # 血小板: 修复/再平衡
    DATA_INGESTION = "data_ingestion"        # 树突状细胞: 抗原采集/数据输入
    BACKTEST_RUNNER = "backtest_runner"      # 中性粒细胞: 批量验证


MAX_AGENTS = 50
MAX_MEMORY_MB = 512.0
MAX_CPU_PERCENT = 30.0
DEFAULT_LIFESPAN = 3600.0  # 1 hour default agent lifespan


# ── Data Structures ──────────────────────────────────────────────────


@dataclass
class ClusterAgent:
    """A cluster agent — like a differentiated blood cell."""

    agent_id: str
    specialty: AgentSpecialty
    status: str = "idle"  # "idle", "active", "dead"
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    threads: int = 1
    open_files: int = 0
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + DEFAULT_LIFESPAN)
    task_count: int = 0
    error_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_alive(self) -> bool:
        return self.status != "dead" and time.time() < self.expires_at

    def utilization(self) -> float:
        return max(self.memory_mb / MAX_MEMORY_MB, self.cpu_percent / MAX_CPU_PERCENT)


# ── Main Class ───────────────────────────────────────────────────────


class AgentFactory:
    """HSC niche — creates and manages differentiated cluster agents.

    Config:
      - max_agents: hard limit on total agents
      - max_memory_mb: per-agent memory limit
      - max_cpu_percent: per-agent CPU limit
      - default_lifespan: default agent TTL
    """

    _SPECIALTY_GROWTH_FACTORS: dict[AgentSpecialty, dict[str, float]] = {
        AgentSpecialty.REGIME_RESEARCH: {"memory": 0.15, "cpu": 0.2, "lifespan": 7200},
        AgentSpecialty.STRATEGY_MINING: {"memory": 0.25, "cpu": 0.3, "lifespan": 5400},
        AgentSpecialty.INDICATOR_COMPILATION: {"memory": 0.1, "cpu": 0.15, "lifespan": 3600},
        AgentSpecialty.TACTICS_RESEARCH: {"memory": 0.08, "cpu": 0.1, "lifespan": 1800},
        AgentSpecialty.RISK_CONTROL: {"memory": 0.05, "cpu": 0.08, "lifespan": 7200},
        AgentSpecialty.PORTFOLIO_OPTIMIZATION: {"memory": 0.2, "cpu": 0.25, "lifespan": 3600},
        AgentSpecialty.DATA_INGESTION: {"memory": 0.12, "cpu": 0.1, "lifespan": 3600},
        AgentSpecialty.BACKTEST_RUNNER: {"memory": 0.3, "cpu": 0.4, "lifespan": 1800},
    }

    def __init__(
        self,
        max_agents: int = MAX_AGENTS,
        max_memory_mb: float = MAX_MEMORY_MB,
        max_cpu_percent: float = MAX_CPU_PERCENT,
    ) -> None:
        self._max_agents = max_agents
        self._max_memory_mb = max_memory_mb
        self._max_cpu_percent = max_cpu_percent

        self._agents: dict[str, ClusterAgent] = {}
        self._logger = CortexLogger("agent_factory")

    # ── Public API ──────────────────────────────────────────────────

    def create_agent(
        self, specialty: AgentSpecialty, agent_id: str | None = None
    ) -> ClusterAgent | None:
        """Differentiate a new agent from the stem cell pool. Returns None if capacity full."""
        if len(self._agents) >= self._max_agents:
            self._logger.warn("max_agents_reached")
            return None

        # Resource check (like CBC: Complete Blood Count)
        current_usage = self._current_resource_usage()
        factors = self._SPECIALTY_GROWTH_FACTORS.get(specialty, {"memory": 0.1, "cpu": 0.1})

        if current_usage["memory"] + factors["memory"] > self._max_memory_mb:
            self._logger.warn("memory_limit", current=current_usage["memory"])
            return None
        if current_usage["cpu"] + factors["cpu"] > self._max_cpu_percent:
            self._logger.warn("cpu_limit", current=current_usage["cpu"])
            return None

        aid = agent_id or self._gen_agent_id(specialty.value)
        agent = ClusterAgent(
            agent_id=aid,
            specialty=specialty,
            memory_mb=factors["memory"],
            cpu_percent=factors["cpu"],
            expires_at=time.time() + factors.get("lifespan", DEFAULT_LIFESPAN),
        )
        self._agents[aid] = agent

        self._logger.info("agent_created", agent_id=aid[:12], specialty=specialty.value)
        return agent

    def get_or_create(
        self, specialty: AgentSpecialty, agent_id: str | None = None
    ) -> ClusterAgent | None:
        """Get an existing idle agent or create a new one."""
        for agent in self._agents.values():
            if agent.specialty == specialty and agent.status == "idle" and agent.is_alive():
                agent.status = "active"
                return agent
        return self.create_agent(specialty, agent_id)

    def apoptose(self, agent_id: str) -> bool:
        """Remove an agent (programmed cell death). Returns True if found."""
        agent = self._agents.pop(agent_id, None)
        if agent:
            agent.status = "dead"
            self._logger.info("agent_apoptosed", agent_id=agent_id[:12], task_count=agent.task_count)
            return True
        return False

    def constrain_resources(self) -> dict[str, Any]:
        """Enforce resource limits — like spleen clearing old erythrocytes.

        Kills agents that exceed resource limits or have expired.
        """
        removed: list[str] = []
        for agent_id, agent in list(self._agents.items()):
            if not agent.is_alive():
                removed.append(agent_id)
                continue
            if agent.memory_mb > self._max_memory_mb or agent.cpu_percent > self._max_cpu_percent:
                removed.append(agent_id)

        for aid in removed:
            self.apoptose(aid)

        return {
            "removed": len(removed),
            "remaining": len(self._agents),
            "utilization": self._current_resource_usage(),
        }

    def report_stats(self, agent_id: str, memory_mb: float, cpu_percent: float,
                     threads: int = 1, open_files: int = 0) -> bool:
        """Update agent resource usage (like a real-time CBC)."""
        agent = self._agents.get(agent_id)
        if agent is None:
            return False
        agent.memory_mb = memory_mb
        agent.cpu_percent = cpu_percent
        agent.threads = threads
        agent.open_files = open_files
        return True

    def get_agent(self, agent_id: str) -> ClusterAgent | None:
        return self._agents.get(agent_id)

    def list_by_specialty(self, specialty: AgentSpecialty) -> list[ClusterAgent]:
        return [a for a in self._agents.values() if a.specialty == specialty and a.is_alive()]

    def count_by_specialty(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for agent in self._agents.values():
            if agent.is_alive():
                counts[agent.specialty.value] = counts.get(agent.specialty.value, 0) + 1
        return counts

    # ── Private Methods ─────────────────────────────────────────────

    def _current_resource_usage(self) -> dict[str, float]:
        alive = [a for a in self._agents.values() if a.is_alive()]
        return {
            "memory": sum(a.memory_mb for a in alive),
            "cpu": sum(a.cpu_percent for a in alive),
            "count": len(alive),
        }

    @staticmethod
    def _gen_agent_id(specialty: str) -> str:
        raw = f"{specialty}|{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        usage = self._current_resource_usage()
        return {
            "total_agents": len(self._agents),
            "alive": usage["count"],
            "memory_usage": round(usage["memory"], 2),
            "cpu_usage": round(usage["cpu"], 2),
            "by_specialty": self.count_by_specialty(),
        }
