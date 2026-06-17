"""L4 M5a: VectorRetrievalEngine — "海马体索引+嗅觉记忆"(Olfactory Memory) 向量检索.

Biological Metaphor:
  人类的嗅觉记忆——闻到一个气味→立即(不可控地)联想起10年前的场景。
  嗅觉是唯一不经过丘脑中继的感觉, 直接投射到海马体和杏仁核→检索延迟<120ms。

  语义搜索: query → embedding → ChromaDB → TopK
    查询向量 = 气味分子
    向量数据库 = 嗅球(olfactory bulb)中的气味受体图
    TopK = 被激活的记忆线索
  LRU缓存(500条) = 嗅球僧帽细胞的适应性(高频气味→反应减弱=缓存命中)
"""

from __future__ import annotations

import hashlib
import math
import random
import time
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class DistanceMetric(str, Enum):
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT = "dot"


@dataclass
class SearchResult:
    vec_id: str
    score: float
    label: str
    metadata: dict[str, Any]
    rank: int


class VectorRetrievalEngine:
    """Olfactory-inspired vector search — direct hippocampus+amygdala projection.

    Config:
      - dimension: vector dimension
      - metric: distance metric
      - cache_size: LRU cache for frequently accessed vectors
    """

    def __init__(
        self, dimension: int = 128, metric: DistanceMetric = DistanceMetric.COSINE,
        cache_size: int = 500,
    ) -> None:
        self._dim = dimension
        self._metric = metric
        self._cache = OrderedDict()  # LRU cache
        self._cache_size = cache_size
        self._vectors: dict[str, dict[str, Any]] = {}  # {vec_id: {vector, label, metadata}}
        self._logger = CortexLogger("vector_retrieval")

    def insert(self, vec_id: str, vector: list[float], label: str = "",
               metadata: dict[str, Any] | None = None) -> str:
        """Insert a vector — encode a new odor memory."""
        if len(vector) != self._dim:
            raise ValueError(f"Expected dim {self._dim}, got {len(vector)}")
        self._vectors[vec_id] = {"vector": list(vector), "label": label, "metadata": metadata or {}}
        return vec_id

    def search(self, query: list[float], top_k: int = 10) -> list[SearchResult]:
        """Search for nearest vectors — sniff and recall."""
        if not self._vectors:
            return []
        if len(query) != self._dim:
            raise ValueError(f"Expected query dim {self._dim}")

        scored = []
        for vid, info in self._vectors.items():
            dist = self._compute_distance(query, info["vector"])
            scored.append((dist, vid))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for rank, (score, vid) in enumerate(scored[:top_k]):
            info = self._vectors[vid]
            results.append(SearchResult(
                vec_id=vid, score=score, label=info["label"],
                metadata=info["metadata"], rank=rank + 1,
            ))
            # Update LRU cache
            self._cache[vid] = info
            if len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)

        return results

    def remove(self, vec_id: str) -> bool:
        if vec_id in self._vectors:
            del self._vectors[vec_id]
            self._cache.pop(vec_id, None)
            return True
        return False

    def _compute_distance(self, a: list[float], b: list[float]) -> float:
        if self._metric == DistanceMetric.COSINE:
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            return max(0.0, dot / max(na * nb, 1e-10))
        elif self._metric == DistanceMetric.EUCLIDEAN:
            d = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
            return -d  # negated so higher=better
        else:
            return sum(x * y for x, y in zip(a, b))

    @property
    def stats(self) -> dict[str, Any]:
        return {"vectors": len(self._vectors), "cache_size": len(self._cache)}
