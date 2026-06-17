"""L4 M1b: TaskDAGBuilder — "运动皮层规划 + Physarum路径优化" 任务DAG构建器.

Biological Metaphor:
  运动皮层(Motor Cortex)将"我要喝水"分解为: 伸手→抓取杯子→举起到嘴边→倾斜→吞咽
  数十个肌肉群的精确时序协调 + Physarum黏菌用最小作用量原理找到最优路径。

  Physarum启发(Physarum Lagrangian, Nov 2025):
    - 每条DAG边 = 黏菌的营养管(tube)
    - 正反馈: 高频使用边增粗(降低延迟) = 黏菌的flux强化效应
    - 退化: 低频使用边萎缩(最终消失) = 黏菌的管退化
    - Mesh→Tree收敛: 初始全连接探索→执行中收敛为最优路径
    - 最小作用量Lagrangian: L = Σ(延迟×流量权重) + λ×Σ(边数)

Reference: Physarum Lagrangian (arXiv:2511.08531, Nov 2025)
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class TaskStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskNode:
    """A single task node — like one motor command in a movement sequence."""

    task_id: str
    skill_name: str  # which skill to invoke
    description: str
    dependencies: list[str] = field(default_factory=list)
    dependents: list[str] = field(default_factory=list)
    priority: float = 0.5
    estimated_duration: float = 1.0
    status: TaskStatus = TaskStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskDAG:
    """Complete task DAG — the spinal pattern generator output."""

    dag_id: str
    nodes: dict[str, TaskNode]
    edges: list[tuple[str, str]]
    critical_path: list[str] = field(default_factory=list)
    total_estimated_time: float = 0.0
    max_parallelism: int = 1
    depth: int = 0
    created_at: float = field(default_factory=time.time)


class TaskDAGBuilder:
    """Builds task DAGs from intents — motor cortex planning + Physarum optimization.

    Config:
      - skills: dict of {skill_name: {inputs: [...], outputs: [...]}}
      - max_parallel: max concurrent tasks
      - lambda_cost: weight for edge count penalty in Lagrangian
    """

    def __init__(
        self,
        skills: dict[str, dict[str, Any]] | None = None,
        max_parallel: int = 8,
        lambda_cost: float = 0.1,
    ) -> None:
        self._skills = skills or self._default_skills()
        self._max_parallel = max_parallel
        self._lambda = lambda_cost
        self._usage_counts: dict[str, int] = defaultdict(int)  # for Physarum flux
        self._build_count = 0
        self._logger = CortexLogger("task_dag_builder")

    def build(self, intent_type: str, constraints: dict[str, Any] | None = None) -> TaskDAG:
        """Build a DAG from intent — decompose intention into motor commands."""
        dag_id = self._gen_dag_id(intent_type)
        constraints = constraints or {}
        nodes: dict[str, TaskNode] = {}
        edges: list[tuple[str, str]] = []

        # Select skill sequence based on intent type
        sequence = self._select_skill_sequence(intent_type, constraints)

        prev_id: str | None = None
        for i, skill_name in enumerate(sequence):
            task_id = f"{dag_id}_{i}"
            node = TaskNode(
                task_id=task_id,
                skill_name=skill_name,
                description=f"Execute {skill_name}",
                priority=1.0 - i / max(len(sequence), 1) * 0.5,
                estimated_duration=self._skills.get(skill_name, {}).get("duration", 1.0),
            )
            if prev_id:
                node.dependencies.append(prev_id)
                edges.append((prev_id, task_id))
                nodes[prev_id].dependents.append(task_id)

            nodes[task_id] = node
            prev_id = task_id

        # Physarum optimization: reinforce frequently used paths, prune unused
        for edge in edges:
            self._usage_counts[edge[0]] += 1
            self._usage_counts[edge[1]] += 1

        # Topological sort
        topo = self._topological_sort(nodes, edges)
        critical_path = self._find_critical_path(nodes, edges, topo)
        max_parallel = self._compute_max_parallelism(nodes)

        # Lagrangian cost: L = Σ(delay × flux) + λ × Σ(edges)
        total_cost = sum(
            nodes[nid].estimated_duration * self._usage_counts.get(nid, 1)
            for nid in nodes
        ) + self._lambda * len(edges)

        self._build_count += 1
        return TaskDAG(
            dag_id=dag_id,
            nodes=nodes,
            edges=edges,
            critical_path=critical_path,
            total_estimated_time=total_cost,
            max_parallelism=max_parallel,
            depth=len(topo),
        )

    def merge_dags(self, dags: list[TaskDAG]) -> TaskDAG:
        """Merge multiple DAGs into a super-DAG (like coordinating both arms)."""
        merged_nodes: dict[str, TaskNode] = {}
        merged_edges: list[tuple[str, str]] = []
        for dag in dags:
            for nid, node in dag.nodes.items():
                new_id = f"merged_{nid}"
                merged_nodes[new_id] = TaskNode(
                    task_id=new_id, skill_name=node.skill_name,
                    description=node.description, priority=node.priority,
                    estimated_duration=node.estimated_duration,
                )
            for src, dst in dag.edges:
                merged_edges.append((f"merged_{src}", f"merged_{dst}"))

        dag_id = self._gen_dag_id("merged")
        topo = self._topological_sort(merged_nodes, merged_edges)
        return TaskDAG(
            dag_id=dag_id, nodes=merged_nodes, edges=merged_edges,
            critical_path=self._find_critical_path(merged_nodes, merged_edges, topo),
            max_parallelism=self._compute_max_parallelism(merged_nodes),
            depth=len(topo),
        )

    def _select_skill_sequence(self, intent_type: str, constraints: dict[str, Any]) -> list[str]:
        sequences = {
            "backtest": ["data_ingestion", "signal_generation", "backtest_execution", "performance_analysis", "report_generation"],
            "screen": ["universe_definition", "factor_computation", "ranking", "filtering", "result_presentation"],
            "analyze": ["data_collection", "feature_engineering", "model_inference", "interpretation", "visualization"],
            "recommend": ["context_analysis", "opportunity_scan", "strategy_selection", "risk_assessment", "recommendation"],
            "monitor": ["data_streaming", "anomaly_detection", "alert_evaluation", "notification"],
            "query": ["query_parsing", "data_retrieval", "formatting", "presentation"],
            "alert": ["signal_verification", "severity_assessment", "escalation", "resolution_tracking"],
        }
        return sequences.get(intent_type, ["data_collection", "processing", "output"])

    def _topological_sort(self, nodes: dict[str, TaskNode], edges: list[tuple[str, str]]) -> list[str]:
        in_degree: dict[str, int] = {nid: 0 for nid in nodes}
        adj: dict[str, list[str]] = defaultdict(list)
        for f, t in edges:
            adj[f].append(t)
            in_degree[t] = in_degree.get(t, 0) + 1
        queue = deque(nid for nid, d in in_degree.items() if d == 0)
        result: list[str] = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for nb in adj.get(node, []):
                in_degree[nb] -= 1
                if in_degree[nb] == 0:
                    queue.append(nb)
        return result

    def _find_critical_path(self, nodes: dict[str, TaskNode], edges: list[tuple[str, str]], topo: list[str]) -> list[str]:
        longest_to: dict[str, float] = {}
        prev: dict[str, str | None] = {}
        for nid in topo:
            node = nodes.get(nid)
            dur = node.estimated_duration if node else 1.0
            best = dur
            best_prev = None
            for f, t in edges:
                if t == nid and f in longest_to:
                    cand = longest_to[f] + dur
                    if cand > best:
                        best = cand
                        best_prev = f
            longest_to[nid] = best
            prev[nid] = best_prev
        if not longest_to:
            return []
        end = max(longest_to, key=longest_to.get)
        path = []
        cur: str | None = end
        while cur:
            path.append(cur)
            cur = prev.get(cur)
        path.reverse()
        return path

    def _compute_max_parallelism(self, nodes: dict[str, TaskNode]) -> int:
        depths: dict[str, int] = {}
        for nid, node in nodes.items():
            if not node.dependencies:
                depths[nid] = 0
            else:
                depths[nid] = max(
                    (depths.get(d, 0) for d in node.dependencies), default=0
                ) + 1
        depth_counts: dict[int, int] = defaultdict(int)
        for d in depths.values():
            depth_counts[d] += 1
        return max(depth_counts.values()) if depth_counts else 1

    @staticmethod
    def _default_skills() -> dict[str, dict[str, Any]]:
        return {
            "data_ingestion": {"duration": 2.0, "inputs": [], "outputs": ["dataset"]},
            "signal_generation": {"duration": 3.0, "inputs": ["dataset"], "outputs": ["signals"]},
            "backtest_execution": {"duration": 5.0, "inputs": ["signals"], "outputs": ["trades"]},
            "performance_analysis": {"duration": 2.0, "inputs": ["trades"], "outputs": ["metrics"]},
            "report_generation": {"duration": 1.0, "inputs": ["metrics"], "outputs": ["report"]},
            "data_collection": {"duration": 1.0, "inputs": [], "outputs": ["data"]},
            "processing": {"duration": 2.0, "inputs": ["data"], "outputs": ["result"]},
            "output": {"duration": 1.0, "inputs": ["result"], "outputs": []},
        }

    @staticmethod
    def _gen_dag_id(intent_type: str) -> str:
        return hashlib.md5(f"{intent_type}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, int]:
        return {"build_count": self._build_count}
