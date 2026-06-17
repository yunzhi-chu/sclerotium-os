"""L4 M1c: ConflictDetector — "小脑运动协调"(Cerebellum) 冲突检测器.

Biological Metaphor:
  小脑(Cerebellum)不发起运动, 但协调运动——检测并纠正"这个动作会摔倒"→在摔倒前调整。

  检测三种冲突:
    - 互斥检测: 同skill不可并行2次(同一条肌肉不能同时收缩和舒张)
    - 资源限制: max_parallel=8, max_time=600s(能量预算约束)
    - 循环依赖检测: nx.find_cycle(运动中的死锁检测)
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class ConflictType(str, Enum):
    MUTUAL_EXCLUSION = "mutual_exclusion"  # same skill parallel
    RESOURCE_EXCEEDED = "resource_exceeded"  # over capacity
    CYCLE_DETECTED = "cycle_detected"  # deadlock
    DEPENDENCY_VIOLATION = "dependency_violation"


@dataclass
class Conflict:
    """A detected conflict — like cerebellum detecting an unstable movement."""

    conflict_id: str
    conflict_type: ConflictType
    description: str
    entities: list[str]
    severity: str = "high"  # "low", "medium", "high"
    resolved: bool = False
    detected_at: float = field(default_factory=time.time)


class ConflictDetector:
    """Cerebellar movement coordinator — detects and prevents conflicts."""

    def __init__(self, max_parallel: int = 8, max_time: int = 600) -> None:
        self._max_parallel = max_parallel
        self._max_time = max_time
        self._active_skills: dict[str, int] = defaultdict(int)  # {skill_name: active_count}
        self._conflicts: list[Conflict] = []
        self._logger = CortexLogger("conflict_detector")

    def check_dag(self, dag) -> list[Conflict]:
        """Check a DAG for all types of conflicts."""
        conflicts: list[Conflict] = []

        # 1. Mutual exclusion: same skill cannot run twice in parallel
        skill_counts: dict[str, list[str]] = defaultdict(list)
        for nid, node in dag.nodes.items():
            skill_counts[node.skill_name].append(nid)
        for skill, ids in skill_counts.items():
            if len(ids) > 1:
                conflicts.append(Conflict(
                    conflict_id=self._gen_id("mutex", skill),
                    conflict_type=ConflictType.MUTUAL_EXCLUSION,
                    description=f"Skill '{skill}' assigned to {len(ids)} parallel tasks",
                    entities=ids,
                ))

        # 2. Resource limits
        if len(dag.nodes) > self._max_parallel * 3:
            conflicts.append(Conflict(
                conflict_id=self._gen_id("resource", dag.dag_id),
                conflict_type=ConflictType.RESOURCE_EXCEEDED,
                description=f"DAG has {len(dag.nodes)} tasks, limit is {self._max_parallel * 3}",
                entities=[dag.dag_id],
                severity="medium",
            ))

        if dag.total_estimated_time > self._max_time:
            conflicts.append(Conflict(
                conflict_id=self._gen_id("timeout", dag.dag_id),
                conflict_type=ConflictType.RESOURCE_EXCEEDED,
                description=f"Estimated time {dag.total_estimated_time:.0f}s exceeds limit {self._max_time}s",
                entities=[dag.dag_id],
                severity="medium",
            ))

        # 3. Cycle detection
        if self._has_cycle(dag.nodes, dag.edges):
            conflicts.append(Conflict(
                conflict_id=self._gen_id("cycle", dag.dag_id),
                conflict_type=ConflictType.CYCLE_DETECTED,
                description="Cycle detected in DAG",
                entities=[dag.dag_id],
                severity="high",
            ))

        # 4. Dependency violation
        for nid, node in dag.nodes.items():
            for dep in node.dependencies:
                if dep not in dag.nodes:
                    conflicts.append(Conflict(
                        conflict_id=self._gen_id("dep", nid),
                        conflict_type=ConflictType.DEPENDENCY_VIOLATION,
                        description=f"Task {nid} depends on missing task {dep}",
                        entities=[nid, dep],
                    ))

        self._conflicts.extend(conflicts)
        return conflicts

    def _has_cycle(self, nodes: dict, edges: list) -> bool:
        WHITE, GRAY, BLACK = 0, 1, 2
        colors: dict[str, int] = {nid: WHITE for nid in nodes}
        adj: dict[str, list[str]] = defaultdict(list)
        for f, t in edges:
            adj[f].append(t)

        def dfs(n: str) -> bool:
            colors[n] = GRAY
            for nb in adj.get(n, []):
                if colors.get(nb) == GRAY:
                    return True
                if colors.get(nb) == WHITE:
                    if dfs(nb):
                        return True
            colors[n] = BLACK
            return False

        for nid in nodes:
            if colors.get(nid) == WHITE:
                if dfs(nid):
                    return True
        return False

    @staticmethod
    def _gen_id(prefix: str, suffix: str) -> str:
        return hashlib.md5(f"{prefix}|{suffix}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, int]:
        return {"active_conflicts": len([c for c in self._conflicts if not c.resolved])}
