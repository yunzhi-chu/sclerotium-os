"""L4↔L5 Bridge: DAGClusterBridge — "神经肌肉接头(Neuromuscular Junction)" DAG集群桥.

Biological Metaphor:
  神经肌肉接头——运动神经元轴突末梢与骨骼肌纤维的突触连接:
    神经冲动(动作电位) → 乙酰胆碱(ACh)释放 → 肌肉收缩
    这是"思想→行动"的唯一桥梁

  我们映射:
    运动神经元 = L4 TaskDAG(任务规划/编排)
    突触间隙 = DAGClusterBridge(本模块, 信号转换)
    骨骼肌纤维 = L5 Cluster Agents(执行单元)
    乙酰胆碱 = ClusterTask(标准化任务格式)
    运动单位 = 同相位并行任务组(多条肌纤维同时收缩)
    双重神经支配 = 关键路径×2冗余(防瘫痪)

  核心机制:
    DAG子任务 → ClusterTask自动映射
    同相位并行任务 → 多Agent并行执行(多条肌肉纤维同时收缩)
    关键路径 → 冗余副本(×2)(如同关键肌肉的双重神经支配, 防瘫痪)

Reference:
  Sanes & Lichtman (2001), "Neuromuscular junction", Nature Reviews Neuroscience;
  S-MADRL (AROB 2026) — stigmergic task coordination
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class TaskPhase(str, Enum):
    """Task execution phase — like muscle contraction phases."""
    LATENT = "latent"        # ACh not yet released (waiting)
    CONTRACTING = "contracting"  # Active execution
    RELAXING = "relaxing"    # Completion / cooldown


class RedundancyLevel(str, Enum):
    """Redundancy strategy for task execution."""
    NONE = "none"        # Single execution
    DUPLICATE = "duplicate"  # ×2 redundancy (dual innervation)
    TRIPLICATE = "triplicate"  # ×3 for critical tasks


@dataclass
class ClusterTask:
    """A task converted from DAG node → cluster-executable format.

    Analogous to a vesicle of acetylcholine ready to be released.
    """

    task_id: str
    dag_node_id: str        # Source DAG node
    specialty: str           # Required agent specialty
    payload: dict[str, Any]  # Task parameters
    priority: int = 5        # 1(highest)-10(lowest)
    phase: TaskPhase = TaskPhase.LATENT
    redundancy: RedundancyLevel = RedundancyLevel.NONE
    dependencies: list[str] = field(default_factory=list)  # task_ids that must complete first
    assigned_agents: list[str] = field(default_factory=list)

    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0


@dataclass
class DAGDecomposition:
    """Result of decomposing a TaskDAG into cluster-executable tasks."""

    decomposition_id: str
    dag_id: str
    total_nodes: int
    cluster_tasks: list[ClusterTask]
    parallel_groups: list[list[str]]  # Groups of task_ids that can run in parallel
    critical_path: list[str]          # task_ids on the critical path
    redundant_tasks: list[str]        # task_ids that received redundancy copies
    estimated_duration: float = 0.0   # Sum of critical path delays

    created_at: float = field(default_factory=time.time)


class DAGClusterBridge:
    """Neuromuscular Junction: L4 TaskDAG → L5 Cluster execution.

    Config:
      - critical_path_redundancy: multiplier for critical path tasks (>1 = redundant copies)
      - max_parallel_group: maximum tasks in a single parallel group
      - specialty_map: mapping from DAG intent types → cluster agent specialties
      - priority_inheritance: whether child tasks inherit parent priority
    """

    # Default mapping: DAG node skill → cluster agent specialty
    _DEFAULT_SPECIALTY_MAP: dict[str, str] = {
        "regime_detect": "regime",
        "signal_generate": "strategy",
        "indicator_compute": "indicator",
        "risk_assess": "risk",
        "backtest": "tactical",
        "order_execute": "tactical",
        "portfolio_rebalance": "strategy",
        "data_fetch": "indicator",
        "strategy_evolve": "strategy",
        "audit": "risk",
        "report": "general",
    }

    def __init__(
        self,
        critical_path_redundancy: int = 2,
        max_parallel_group: int = 8,
        specialty_map: dict[str, str] | None = None,
        priority_inheritance: bool = True,
    ) -> None:
        self._cp_redundancy = critical_path_redundancy
        self._max_parallel = max_parallel_group
        self._specialty_map = specialty_map or dict(self._DEFAULT_SPECIALTY_MAP)
        self._priority_inheritance = priority_inheritance

        self._decompositions: dict[str, DAGDecomposition] = {}
        self._task_index: dict[str, ClusterTask] = {}
        self._logger = CortexLogger("dag_cluster_bridge")

    # ── Core Bridge: DAG → Cluster Tasks ──────────────────────────────

    def decompose_dag(self, dag: dict[str, Any], dag_id: str = "") -> DAGDecomposition:
        """Decompose a TaskDAG into cluster-executable tasks.

        Like a motor neuron converting an action potential into ACh release:
          1. Each DAG node → ClusterTask (ACh vesicle)
          2. Parallel groups identified (motor units)
          3. Critical path marked for redundancy (dual innervation)
        """
        nodes = dag.get("nodes", [])
        edges = dag.get("edges", [])
        if not nodes:
            return DAGDecomposition(
                decomposition_id=self._gen_id("decomp"),
                dag_id=dag_id,
                total_nodes=0,
                cluster_tasks=[],
                parallel_groups=[],
                critical_path=[],
                redundant_tasks=[],
            )

        dag_id = dag_id or dag.get("dag_id", self._gen_id("dag"))

        # Step 1: Convert each DAG node to a ClusterTask
        tasks: dict[str, ClusterTask] = {}
        for node in nodes:
            task = self._node_to_task(node, dag_id)
            tasks[task.task_id] = task
            self._task_index[task.task_id] = task

        # Step 2: Build dependency graph
        in_degree: dict[str, int] = defaultdict(int)
        children: dict[str, list[str]] = defaultdict(list)
        for edge in edges:
            from_node_id = edge.get("from", edge.get("source", ""))
            to_node_id = edge.get("to", edge.get("target", ""))
            # Map DAG node IDs to task IDs
            from_tid = self._find_task_by_node(tasks, from_node_id)
            to_tid = self._find_task_by_node(tasks, to_node_id)
            if from_tid and to_tid:
                to_task = tasks[to_tid]
                to_task.dependencies.append(from_tid)
                in_degree[to_tid] += 1
                children[from_tid].append(to_tid)

        # Step 3: Identify parallel groups (topological levels)
        parallel_groups = self._compute_parallel_groups(tasks, in_degree, children)

        # Step 4: Find critical path (longest path through DAG)
        critical_path = self._find_critical_path(tasks, children)

        # Step 5: Apply redundancy to critical path tasks
        redundant_tasks: list[str] = []
        for task_id in critical_path:
            task = tasks.get(task_id)
            if task and task.redundancy == RedundancyLevel.NONE:
                task.redundancy = RedundancyLevel.DUPLICATE
                redundant_tasks.append(task_id)

        decomposition = DAGDecomposition(
            decomposition_id=self._gen_id("decomp"),
            dag_id=dag_id,
            total_nodes=len(nodes),
            cluster_tasks=list(tasks.values()),
            parallel_groups=parallel_groups,
            critical_path=critical_path,
            redundant_tasks=redundant_tasks,
            estimated_duration=self._estimate_duration(tasks, critical_path),
        )
        self._decompositions[decomposition.decomposition_id] = decomposition

        self._logger.info(
            "dag_decomposed",
            dag_id=dag_id[:16],
            nodes=len(nodes),
            tasks=len(tasks),
            parallel_groups=len(parallel_groups),
            critical_path_len=len(critical_path),
            redundant=len(redundant_tasks),
        )
        return decomposition

    def to_batch_input(
        self, decomposition: DAGDecomposition,
    ) -> list[dict[str, Any]]:
        """Convert a decomposition into RootAgent.submit_batch_task() input format.

        This is the 'acetylcholine release' step — converting neural signal
        into the format that muscles can act upon.
        """
        batch: list[dict[str, Any]] = []

        for task in decomposition.cluster_tasks:
            entry = {
                "task_id": task.task_id,
                "specialty": task.specialty,
                "payload": task.payload,
                "priority": task.priority,
                "dag_node_id": task.dag_node_id,
                "redundancy": task.redundancy.value,
            }
            batch.append(entry)

            # Create redundant copies for critical path tasks
            if task.redundancy != RedundancyLevel.NONE:
                copies = 1 if task.redundancy == RedundancyLevel.DUPLICATE else 2
                for i in range(copies):
                    redundant_entry = dict(entry)
                    redundant_entry["task_id"] = f"{task.task_id}-r{i}"
                    redundant_entry["payload"] = {**task.payload, "redundant_copy": True, "original_task": task.task_id}
                    batch.append(redundant_entry)

        return batch

    # ── Task Lifecycle Tracking ───────────────────────────────────────

    def mark_started(self, task_id: str) -> bool:
        """Mark a cluster task as started (ACh released into synaptic cleft)."""
        task = self._task_index.get(task_id)
        if task is None:
            return False
        task.phase = TaskPhase.CONTRACTING
        task.started_at = time.time()
        return True

    def mark_completed(self, task_id: str, result: dict[str, Any] | None = None) -> bool:
        """Mark a cluster task as completed (muscle contraction finished)."""
        task = self._task_index.get(task_id)
        if task is None:
            return False
        task.phase = TaskPhase.RELAXING
        task.completed_at = time.time()
        if result:
            task.payload["_result"] = result
        return True

    def get_phase_stats(self) -> dict[str, int]:
        """Get task counts by phase — like measuring muscle activation state."""
        counts: dict[str, int] = defaultdict(int)
        for task in self._task_index.values():
            counts[task.phase.value] += 1
        return dict(counts)

    # ── Query Interface ───────────────────────────────────────────────

    def get_task(self, task_id: str) -> ClusterTask | None:
        return self._task_index.get(task_id)

    def get_decomposition(self, decomp_id: str) -> DAGDecomposition | None:
        return self._decompositions.get(decomp_id)

    def get_tasks_by_phase(self, phase: TaskPhase) -> list[ClusterTask]:
        return [t for t in self._task_index.values() if t.phase == phase]

    def get_critical_path_tasks(
        self, decomp_id: str,
    ) -> list[ClusterTask]:
        """Get all tasks on the critical path for a decomposition."""
        decomp = self._decompositions.get(decomp_id)
        if decomp is None:
            return []
        return [self._task_index[tid] for tid in decomp.critical_path if tid in self._task_index]

    # ── Internal Helpers ──────────────────────────────────────────────

    def _node_to_task(self, node: dict[str, Any], dag_id: str) -> ClusterTask:
        """Convert a single DAG node to a ClusterTask (ACh vesicle packaging)."""
        node_id = node.get("node_id", node.get("id", self._gen_id("node")))
        skill = node.get("skill", node.get("type", "general")).lower()

        # Map skill to cluster agent specialty
        specialty = "general"
        for key, spec in self._specialty_map.items():
            if key in skill:
                specialty = spec
                break

        # Determine priority from node criticality
        priority = 5  # default
        if node.get("critical", False):
            priority = 1
        elif node.get("important", False):
            priority = 3
        elif node.get("optional", False):
            priority = 8

        # Determine redundancy level
        redundancy = RedundancyLevel.NONE
        if node.get("critical", False):
            redundancy = RedundancyLevel.DUPLICATE

        return ClusterTask(
            task_id=f"task-{dag_id}-{node_id}",
            dag_node_id=node_id,
            specialty=specialty,
            payload={
                "skill": skill,
                "params": node.get("params", node.get("data", {})),
                "dag_id": dag_id,
                "node_id": node_id,
            },
            priority=priority,
            redundancy=redundancy,
            dependencies=[],
        )

    @staticmethod
    def _find_task_by_node(tasks: dict[str, ClusterTask], node_id: str) -> str | None:
        """Find a task_id by its source DAG node_id."""
        for tid, task in tasks.items():
            if task.dag_node_id == node_id:
                return tid
        return None

    def _compute_parallel_groups(
        self,
        tasks: dict[str, ClusterTask],
        in_degree: dict[str, int],
        children: dict[str, list[str]],
    ) -> list[list[str]]:
        """Compute topological levels for parallel execution groups.

        Like identifying which muscle fibers can contract simultaneously.
        """
        groups: list[list[str]] = []
        remaining = set(tasks.keys())

        # Start with tasks that have no dependencies
        ready = [tid for tid in remaining if in_degree.get(tid, 0) == 0]

        while ready:
            if len(ready) > self._max_parallel:
                # Split large groups
                groups.append(ready[:self._max_parallel])
                ready = ready[self._max_parallel:]
            else:
                groups.append(list(ready))
                remaining -= set(ready)
                # Find next wave
                next_ready = []
                for tid in ready:
                    for child in children.get(tid, []):
                        in_degree[child] -= 1
                        if in_degree[child] == 0 and child in remaining:
                            next_ready.append(child)
                ready = next_ready

        return [[tid for tid in g if tid in tasks] for g in groups]

    def _find_critical_path(
        self,
        tasks: dict[str, ClusterTask],
        children: dict[str, list[str]],
    ) -> list[str]:
        """Find the critical path through the task DAG.

        The critical path is the longest chain of dependent tasks.
        Like the minimum time needed for a complete muscle contraction cycle.
        """
        # Longest path using DP (DAG topological order)
        longest: dict[str, int] = {}
        predecessor: dict[str, str | None] = {}

        def dfs(task_id: str) -> int:
            if task_id in longest:
                return longest[task_id]
            max_len = 1
            predecessor[task_id] = None
            for child in children.get(task_id, []):
                child_len = dfs(child) + 1
                if child_len > max_len:
                    max_len = child_len
                    predecessor[task_id] = child
            longest[task_id] = max_len
            return max_len

        # Compute longest path for all nodes
        for tid in tasks:
            dfs(tid)

        # Find the start of the longest path
        if not longest:
            return []
        start = max(longest, key=lambda k: longest[k])

        # Reconstruct path
        path = []
        current = start
        while current is not None:
            path.append(current)
            current = predecessor.get(current)
        return path

    def _estimate_duration(
        self,
        tasks: dict[str, ClusterTask],
        critical_path: list[str],
    ) -> float:
        """Estimate total execution duration from critical path."""
        # Assume 1.0 time unit per task on critical path
        base = len(critical_path)
        # Add overhead for redundant copies
        redundant = sum(1 for tid in critical_path if tasks.get(tid) and tasks[tid].redundancy != RedundancyLevel.NONE)
        return base * 1.0 + redundant * 0.3  # redundant copies add 30% overhead each

    @staticmethod
    def _gen_id(prefix: str) -> str:
        return hashlib.md5(f"{prefix}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        phase_counts = self.get_phase_stats()
        return {
            "total_tasks": len(self._task_index),
            "decompositions": len(self._decompositions),
            "phases": phase_counts,
            "redundant_tasks": sum(
                1 for t in self._task_index.values()
                if t.redundancy != RedundancyLevel.NONE
            ),
        }
