"""L4 M5b: FinancialKnowledgeGraph — "语义记忆网络+菌根共生"(Mycorrhizal Network) 金融知识图谱.

Biological Metaphor:
  森林地下的菌根网络(Mycorrhizal Network) — "Wood-Wide Web":
  树木不是孤立存在的——通过真菌菌丝交换碳、氮、磷、水和信息。
  Mother Tree = 知识图谱的Hub节点(如"MACD"概念连接数百个策略)。

  节点类型映射:
    Indicator=树木, Strategy=灌木, Regime=气候带, Pattern=林窗,
    Stock=土壤斑块, Sector=森林类型, MasterTrader=关键物种

  边类型映射:
    APPLIES_TO=植物-土壤反馈, DERIVED_FROM=营养来源,
    CORRELATED_WITH=共生关系, OPTIMAL_IN=生态位优化

  2跳内关联知识 = 一棵树通过菌根网络连接到的所有其他树
  scenario_match: 当前体制→自动关联最优策略

Reference:
  Chen et al. (2025), Frontiers in Plant Science;
  Tagirdzhanova et al. (2025), Current Biology
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class RelationType(str, Enum):
    APPLIES_TO = "applies_to"
    DERIVED_FROM = "derived_from"
    CORRELATED_WITH = "correlated_with"
    OPTIMAL_IN = "optimal_in"
    SIMILAR_TO = "similar_to"
    CONTRADICTS = "contradicts"


@dataclass
class EntityNode:
    """A knowledge graph node — like a tree in the forest."""

    entity_id: str
    entity_type: str  # indicator, strategy, regime, pattern, stock, sector, master_trader
    name: str
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class FinancialKnowledgeGraph:
    """Mycorrhizal knowledge network — connects strategies, indicators, regimes.

    Config:
      - max_entities: node limit
      - max_edges: edge limit
    """

    def __init__(self, max_entities: int = 5000, max_edges: int = 20000) -> None:
        self._max_entities = max_entities
        self._max_edges = max_edges
        self._entities: dict[str, EntityNode] = {}
        self._edges: dict[str, list[tuple[str, str, float]]] = defaultdict(list)  # {from: [(to, type, weight)]}
        self._reverse: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
        self._logger = CortexLogger("financial_kg")

    def add_entity(self, entity_id: str, entity_type: str, name: str,
                   properties: dict[str, Any] | None = None) -> EntityNode | None:
        if len(self._entities) >= self._max_entities:
            return None
        node = EntityNode(entity_id=entity_id, entity_type=entity_type, name=name, properties=properties or {})
        self._entities[entity_id] = node
        return node

    def add_relation(self, from_id: str, to_id: str, rel_type: RelationType,
                     weight: float = 0.5) -> bool:
        if from_id not in self._entities or to_id not in self._entities:
            return False
        self._edges[from_id].append((to_id, rel_type.value, weight))
        self._reverse[to_id].append((from_id, rel_type.value, weight))
        return True

    def query_relations(self, entity_id: str, max_hops: int = 2) -> dict[str, Any]:
        """Query within max_hops — tree connecting through mycorrhizal network."""
        if entity_id not in self._entities:
            return {"nodes": [], "edges": []}

        visited_nodes: set[str] = {entity_id}
        visited_edges: list[dict[str, Any]] = []
        frontier = {entity_id}

        for hop in range(max_hops):
            next_frontier: set[str] = set()
            for node_id in frontier:
                for to_id, rel_type, weight in self._edges.get(node_id, []):
                    if to_id not in visited_nodes:
                        visited_nodes.add(to_id)
                        next_frontier.add(to_id)
                    visited_edges.append({"from": node_id, "to": to_id, "type": rel_type, "weight": weight})
                for from_id, rel_type, weight in self._reverse.get(node_id, []):
                    if from_id not in visited_nodes:
                        visited_nodes.add(from_id)
                        next_frontier.add(from_id)
                    visited_edges.append({"from": from_id, "to": node_id, "type": rel_type, "weight": weight})
            frontier = next_frontier

        return {
            "nodes": [{"id": nid, "name": self._entities[nid].name, "type": self._entities[nid].entity_type}
                      for nid in visited_nodes],
            "edges": visited_edges,
        }

    def scenario_match(self, current_regime: str) -> list[dict[str, Any]]:
        """Match current regime to optimal strategies — niche optimization."""
        matches = []
        for entity in self._entities.values():
            if entity.entity_type == "strategy":
                for to_id, rel_type, weight in self._edges.get(entity.entity_id, []):
                    if rel_type == "optimal_in" and self._entities.get(to_id, EntityNode("", "", "")).entity_type == "regime":
                        if self._entities[to_id].name == current_regime:
                            matches.append({"strategy": entity.name, "weight": weight, "node_id": entity.entity_id})
        return sorted(matches, key=lambda m: m["weight"], reverse=True)

    def get_entity(self, entity_id: str) -> EntityNode | None:
        return self._entities.get(entity_id)

    @property
    def stats(self) -> dict[str, int]:
        return {"entities": len(self._entities), "edges": sum(len(v) for v in self._edges.values())}
