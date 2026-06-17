"""L5 4.6: GlobalKnowledgeNetwork — "菌根母树网络 + 地衣全息体" 知识网络.

Biological Metaphor:
  森林地下的菌根共生网络(Mycorrhizal Network) — "Wood-Wide Web":
    - Mother Tree(母树): 森林中最古老/最大的树, 通过菌丝连接数百棵幼树
    - 双向碳氮转移: 幼树向母树输送光合产物(C), 母树向幼树提供N/P/H₂O
    - 胁迫传播: Ectomycorrhizal网络会传播碳亏缺和干旱胁迫!
    - 检疫隔离: 如同森林病理学中需要隔离带防止病害传播

  地衣全息体(Lichen Holobiont):
    - 至少3个界(真菌+藻类+细菌)的稳定共生体
    - 功能冗余: 多个物种有重叠代谢功能→任何单一物种失效不影响系统
    - 水平基因转移(HGT): 细菌抗逆基因→真菌→藻类

  记忆新陈代谢(Memory Metabolism):
    评分 = PnL影响×0.4 + 使用频率×0.3 + 新鲜度(年衰减)×0.3

Reference:
  Qarachal & Alizadeh (2025), "Mother trees as hub nodes", PMPP;
  Tagirdzhanova et al. (2025), "Xanthoria parietina", Current Biology;
  Mawarda et al. (2026), "Functional redundancy in lichen holobionts", Env Microbiome
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


# ── Constants ────────────────────────────────────────────────────────

class MemoryType(str, Enum):
    EPISODIC = "episodic"      # 情景: 具体事件
    SEMANTIC = "semantic"      # 语义: 抽象知识
    PROCEDURAL = "procedural"  # 过程: 执行模式


MAX_NODES = 10000
MAX_EDGES = 50000
KNOWLEDGE_DECAY = 0.3  # annual decay factor
QUARANTINE_THRESHOLD = -0.3  # negative score triggers quarantine


# ── Data Structures ──────────────────────────────────────────────────


@dataclass
class KnowledgeNode:
    """A knowledge node — like a tree in the forest network."""

    node_id: str
    node_type: str  # "agent", "strategy", "indicator", "pattern", "regime", "stock"
    content: dict[str, Any]  # the stored knowledge
    memory_type: MemoryType = MemoryType.SEMANTIC
    score: float = 0.5  # 0-1, overall quality/value
    pnl_impact: float = 0.0
    use_count: int = 0
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    quarantined: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def freshness(self, current_time: float | None = None) -> float:
        t = current_time or time.time()
        years = (t - self.created_at) / 31536000
        return math.exp(-KNOWLEDGE_DECAY * years)


@dataclass
class MemoryMetabolism:
    """Metabolic scoring for knowledge — decides what to keep."""

    @staticmethod
    def score(node: KnowledgeNode) -> float:
        return (
            0.4 * abs(node.pnl_impact)
            + 0.3 * min(1.0, node.use_count / 100)
            + 0.3 * node.freshness()
        )


# ── Main Class ───────────────────────────────────────────────────────


class GlobalKnowledgeNetwork:
    """Wood-Wide Web for cluster knowledge — mycorrhizal network + lichen holobiont.

    Stores, routes, and metabolizes knowledge across the entire cluster.
    Implements quarantine for "pathogenic" (bad) knowledge.

    Config:
      - max_nodes: max knowledge nodes
      - quarantine_threshold: score below which knowledge is quarantined
    """

    def __init__(
        self,
        max_nodes: int = MAX_NODES,
        quarantine_threshold: float = QUARANTINE_THRESHOLD,
    ) -> None:
        self._max_nodes = max_nodes
        self._quarantine_threshold = quarantine_threshold

        self._nodes: dict[str, KnowledgeNode] = {}  # all knowledge
        self._edges: dict[str, list[tuple[str, float]]] = defaultdict(list)  # {from_id: [(to_id, weight), ...]}
        self._mother_trees: dict[str, KnowledgeNode] = {}  # hub nodes (oldest/most connected)
        self._logger = CortexLogger("knowledge_network")

    # ── Public API ──────────────────────────────────────────────────

    def sync_from_agent(
        self, agent_id: str, data: dict[str, Any], memory_type: MemoryType = MemoryType.EPISODIC,
        pnl_impact: float = 0.0,
    ) -> KnowledgeNode | None:
        """Sync knowledge from an agent — like a sapling sharing photosynthate with the network."""
        if len(self._nodes) >= self._max_nodes:
            self._metabolize()

        node_id = self._gen_node_id(agent_id, str(data.get("key", time.time())))
        node = KnowledgeNode(
            node_id=node_id,
            node_type="agent_knowledge",
            content=data,
            memory_type=memory_type,
            pnl_impact=pnl_impact,
            score=MemoryMetabolism.score(
                KnowledgeNode(node_id=node_id, node_type="", content=data, pnl_impact=pnl_impact)
            ),
        )
        self._nodes[node_id] = node

        # Connect to agent's existing nodes
        for existing_id, existing_node in self._nodes.items():
            if existing_node.node_type == "agent_knowledge" and existing_id != node_id:
                similarity = self._content_similarity(data, existing_node.content)
                if similarity > 0.5:
                    self._edges[node_id].append((existing_id, similarity))
                    self._edges[existing_id].append((node_id, similarity))

        # Check if this node should become a mother tree hub
        if node.score > 0.8 and len(self._edges.get(node_id, [])) > 5:
            self._mother_trees[node_id] = node
            self._logger.info("mother_tree_emerged", node_id=node_id[:12])

        # Quarantine check
        if node.score < self._quarantine_threshold:
            node.quarantined = True
            self._logger.warn("knowledge_quarantined", node_id=node_id[:12], score=round(node.score, 3))

        return node

    def query(
        self, query_data: dict[str, Any], top_k: int = 10,
        exclude_quarantined: bool = True,
    ) -> list[KnowledgeNode]:
        """Query the knowledge network for relevant information.

        Like a tree requesting nutrients through the mycorrhizal network.
        """
        candidates: list[tuple[float, KnowledgeNode]] = []

        for node in self._nodes.values():
            if exclude_quarantined and node.quarantined:
                continue
            sim = self._content_similarity(query_data, node.content)
            score = sim * node.score * node.freshness()
            if score > 0.1:
                candidates.append((score, node))

        candidates.sort(key=lambda x: x[0], reverse=True)

        # Update access stats
        for _, node in candidates[:top_k]:
            node.use_count += 1
            node.last_accessed = time.time()

        return [c[1] for c in candidates[:top_k]]

    def get_network_stats(self, center_id: str | None = None) -> dict[str, Any]:
        """Get network topology stats — like measuring the forest's health."""
        total_edges = sum(len(v) for v in self._edges.values())
        return {
            "total_nodes": len(self._nodes),
            "total_edges": total_edges,
            "mother_trees": len(self._mother_trees),
            "quarantined": sum(1 for n in self._nodes.values() if n.quarantined),
            "avg_degree": total_edges / max(len(self._nodes), 1),
            "center_degree": len(self._edges.get(center_id or "", [])) if center_id else 0,
        }

    def get_hub_nodes(self, top_k: int = 5) -> list[KnowledgeNode]:
        """Get the most connected nodes (mother trees)."""
        sorted_mothers = sorted(
            self._mother_trees.values(),
            key=lambda n: len(self._edges.get(n.node_id, [])),
            reverse=True,
        )
        return sorted_mothers[:top_k]

    def transfer_knowledge(
        self, from_node_id: str, to_node_id: str, bidirectional: bool = True
    ) -> None:
        """Create a knowledge transfer edge (like carbon/nitrogen exchange)."""
        if from_node_id in self._nodes and to_node_id in self._nodes:
            self._edges[from_node_id].append((to_node_id, 0.5))
            if bidirectional:
                self._edges[to_node_id].append((from_node_id, 0.5))

    # ── Private Methods ─────────────────────────────────────────────

    def _metabolize(self) -> int:
        """Remove low-score knowledge (like autophagy of weak synapses)."""
        if not self._nodes:
            return 0

        scores: list[tuple[str, float]] = []
        for nid, node in self._nodes.items():
            scores.append((nid, MemoryMetabolism.score(node)))

        scores.sort(key=lambda x: x[1])
        to_remove = scores[:max(1, len(scores) // 10)]  # remove bottom 10%

        for nid, _ in to_remove:
            del self._nodes[nid]
            self._edges.pop(nid, None)
            self._mother_trees.pop(nid, None)

        return len(to_remove)

    @staticmethod
    def _content_similarity(a: dict[str, Any], b: dict[str, Any]) -> float:
        """Simple key overlap similarity."""
        if not a or not b:
            return 0.0
        keys_a = set(a.keys())
        keys_b = set(b.keys())
        if not keys_a or not keys_b:
            return 0.0
        overlap = keys_a & keys_b
        return len(overlap) / max(len(keys_a), len(keys_b))

    @staticmethod
    def _gen_node_id(*args: str) -> str:
        raw = "|".join(args)
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_nodes": len(self._nodes),
            "mother_trees": len(self._mother_trees),
            "quarantined": sum(1 for n in self._nodes.values() if n.quarantined),
            "by_type": {
                mt.value: sum(1 for n in self._nodes.values() if n.memory_type == mt)
                for mt in MemoryType
            },
        }
