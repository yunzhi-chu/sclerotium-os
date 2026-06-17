"""L4 M3b: CausalTracer — "海马体记忆回溯"(Hippocampal Replay) 因果追踪器.

Biological Metaphor:
  海马体的模式完成(Pattern Completion)和反向重放(reverse replay):
    给定部分线索→自动激活完整记忆表征
    大鼠到达目标后, 海马体场所细胞以反向顺序重放走过的路径

  输出: 结论←维度←信号←数据源 全依赖树
    每个节点含: module(脑区) + confidence(突触权重) + timestamp(发放时间)

Reference: Hippocampal replay & pattern completion literature
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class CausalLink:
    """A single causal link — one step in the reverse replay chain."""

    link_id: str
    source: str  # cause
    target: str  # effect
    module: str  # brain region
    confidence: float  # synaptic weight
    timestamp: float = field(default_factory=time.time)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalChain:
    """Complete causal chain — full reverse replay path."""

    chain_id: str
    conclusion: str  # final observed effect
    links: list[CausalLink]  # ordered from conclusion back to root cause
    total_confidence: float = 0.0
    length: int = 0
    created_at: float = field(default_factory=time.time)

    def summary(self) -> str:
        arrow = " ← "
        path = arrow.join(link.source for link in self.links)
        return f"[{self.total_confidence:.3f}] {self.conclusion} ← {path}"


class CausalTracer:
    """Hippocampal reverse replay — traces effects back to root causes."""

    def __init__(self, max_links: int = 5000) -> None:
        self._max_links = max_links
        self._links: dict[str, CausalLink] = {}
        self._chains: dict[str, CausalChain] = {}
        self._forward: dict[str, list[CausalLink]] = {}  # source→links
        self._reverse: dict[str, list[CausalLink]] = {}  # target→links
        self._logger = CortexLogger("causal_tracer")

    def add_link(
        self, source: str, target: str, module: str = "unknown",
        confidence: float = 0.5, evidence: dict[str, Any] | None = None,
    ) -> CausalLink:
        """Add a causal link — record one synapse in the replay."""
        link = CausalLink(
            link_id=self._gen_id("link", source, target),
            source=source,
            target=target,
            module=module,
            confidence=confidence,
            evidence=evidence or {},
        )
        self._links[link.link_id] = link

        if source not in self._forward:
            self._forward[source] = []
        self._forward[source].append(link)

        if target not in self._reverse:
            self._reverse[target] = []
        self._reverse[target].append(link)

        if len(self._links) > self._max_links:
            oldest = min(self._links.keys(), key=lambda k: self._links[k].timestamp)
            self._links.pop(oldest, None)

        return link

    def trace_back(self, conclusion: str, max_depth: int = 5) -> CausalChain:
        """Trace back from conclusion to root cause — reverse replay."""
        chain_id = self._gen_id("chain", conclusion)
        links: list[CausalLink] = []
        visited: set[str] = set()

        current = conclusion
        for _ in range(max_depth):
            incoming = self._reverse.get(current, [])
            if not incoming:
                break
            # Select strongest incoming link
            best = max(incoming, key=lambda l: l.confidence)
            if best.source in visited:
                break
            visited.add(best.source)
            links.append(best)
            current = best.source

        total_conf = 1.0
        for link in links:
            total_conf *= link.confidence

        chain = CausalChain(
            chain_id=chain_id,
            conclusion=conclusion,
            links=links,
            total_confidence=total_conf,
            length=len(links),
        )
        self._chains[chain_id] = chain
        return chain

    def export_dependency_tree(self, conclusion: str) -> dict[str, Any]:
        """Export full dependency tree: conclusion←dimension←signal←source."""
        chain = self.trace_back(conclusion)
        tree: dict[str, Any] = {"conclusion": conclusion, "nodes": []}
        for link in chain.links:
            tree["nodes"].append({
                "module": link.module,
                "from": link.source,
                "to": link.target,
                "confidence": link.confidence,
            })
        return tree

    def get_link(self, link_id: str) -> CausalLink | None:
        return self._links.get(link_id)

    @staticmethod
    def _gen_id(prefix: str, *args: str) -> str:
        return hashlib.md5(f"{prefix}|{'|'.join(args)}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, int]:
        return {"links": len(self._links), "chains": len(self._chains)}
