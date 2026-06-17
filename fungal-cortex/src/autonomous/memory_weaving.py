"""L4 M5c: MemoryWeaving — "REM睡眠记忆巩固+淀粉样蛋白模板"(REM Sleep + Amyloid) 记忆编织.

Biological Metaphor:
  REM睡眠中的记忆巩固——大脑重放白天的经历, 提取共同特征,
  形成"概念"和"模式" + 淀粉样蛋白(Amyloid)的自催化模板聚合

  weave(90天窗口→跨案例聚类→提炼通用模式):
    如同REM睡眠中, 海马体与新皮层对话:
    海马体:"今天遇到了这三件事"
    新皮层:"它们有什么共同点?"
    海马体:"都发生在熊市环境下, 且RSI都<30"
    新皮层:"那我创建一个新概念: bear_range_bounce"

  最小样本数=10(统计学显著性要求)
  输出: pattern + avg_return + win_rate + n_samples

Reference:
  Maury (2025), FEBS Letters; Kolli et al. (2025), Advanced Science
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class WorkingMemory:
    """Temporary buffer — prefrontal working memory."""

    item_id: str
    content: dict[str, Any]
    importance: float = 0.5
    timestamp: float = field(default_factory=time.time)

    def decay(self, current_time: float | None = None) -> float:
        elapsed = (current_time or time.time()) - self.timestamp
        return self.importance * math.exp(-elapsed / 1800)  # 30min half-life


@dataclass
class EpisodicMemory:
    """Concrete event — hippocampal episodic trace."""

    epis_id: str
    episode_type: str
    context: dict[str, Any]
    outcome: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class SemanticPattern:
    """Abstracted pattern — neocortical semantic memory."""

    pattern_id: str
    pattern_name: str
    description: str
    avg_return: float
    win_rate: float
    n_samples: int
    source_episodes: list[str] = field(default_factory=list)
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)


@dataclass
class MemoryConsolidation:
    """Result of a consolidation cycle (sleep episode)."""

    cycle_id: str
    wm_items_processed: int
    new_patterns_discovered: int
    patterns_reinforced: int
    timestamp: float = field(default_factory=time.time)


class MemoryWeaving:
    """REM sleep consolidation — weaves episodic memories into semantic patterns.

    Config:
      - window_days: lookback window for pattern extraction
      - min_samples: minimum episodes to form a pattern
      - wm_capacity: working memory item limit
    """

    def __init__(self, window_days: int = 90, min_samples: int = 10, wm_capacity: int = 9) -> None:
        self._window = window_days
        self._min_samples = min_samples
        self._wm_capacity = wm_capacity
        self._wm: dict[str, WorkingMemory] = {}
        self._em: list[EpisodicMemory] = []
        self._sm: dict[str, SemanticPattern] = {}
        self._consolidations: list[MemoryConsolidation] = []
        self._logger = CortexLogger("memory_weaving")

    def attend(self, content: dict[str, Any], importance: float = 0.5) -> str | None:
        """Add to working memory — sensory input enters consciousness."""
        if len(self._wm) >= self._wm_capacity:
            self._evict_wm()
        item_id = self._gen_id("wm")
        self._wm[item_id] = WorkingMemory(item_id=item_id, content=content, importance=importance)
        return item_id

    def store_episode(self, episode_type: str, context: dict[str, Any],
                      outcome: dict[str, Any]) -> EpisodicMemory:
        """Store an episodic memory — what happened, in what context."""
        ep = EpisodicMemory(
            epis_id=self._gen_id("em"),
            episode_type=episode_type,
            context=context,
            outcome=outcome,
        )
        self._em.append(ep)
        if len(self._em) > 5000:
            self._em = self._em[-5000:]
        return ep

    def weave(self) -> MemoryConsolidation:
        """Consolidation cycle — REM sleep pattern extraction.

        90-day window → cross-case clustering → extract general patterns.
        """
        cutoff = time.time() - self._window * 86400
        recent = [ep for ep in self._em if ep.timestamp > cutoff]

        # Group by episode_type
        groups: dict[str, list[EpisodicMemory]] = defaultdict(list)
        for ep in recent:
            groups[ep.episode_type].append(ep)

        new_patterns = 0
        reinforced = 0

        for etype, episodes in groups.items():
            if len(episodes) < self._min_samples:
                continue

            # Compute aggregate stats
            returns = [ep.outcome.get("return", 0) for ep in episodes]
            wins = sum(1 for r in returns if r > 0)
            avg_ret = sum(returns) / len(returns)
            win_rate = wins / len(returns) if returns else 0

            pattern_name = f"pattern_{etype}"
            existing = self._sm.get(pattern_name)
            if existing:
                # Reinforce existing
                alpha = 0.3
                existing.avg_return = (1 - alpha) * existing.avg_return + alpha * avg_ret
                existing.win_rate = (1 - alpha) * existing.win_rate + alpha * win_rate
                existing.n_samples += len(episodes)
                existing.confidence = min(1.0, existing.confidence + 0.1)
                reinforced += 1
            else:
                self._sm[pattern_name] = SemanticPattern(
                    pattern_id=self._gen_id("sm"),
                    pattern_name=pattern_name,
                    description=f"Extracted from {len(episodes)} episodes of {etype}",
                    avg_return=avg_ret,
                    win_rate=win_rate,
                    n_samples=len(episodes),
                    source_episodes=[ep.epis_id for ep in episodes[:20]],
                    confidence=min(0.5 + 0.05 * len(episodes), 0.9),
                )
                new_patterns += 1

        cycle = MemoryConsolidation(
            cycle_id=self._gen_id("consolidation"),
            wm_items_processed=len(self._wm),
            new_patterns_discovered=new_patterns,
            patterns_reinforced=reinforced,
        )
        self._consolidations.append(cycle)
        return cycle

    def recall_patterns(self, min_confidence: float = 0.5) -> list[SemanticPattern]:
        """Recall semantic patterns — neocortical memory retrieval."""
        return [p for p in self._sm.values() if p.confidence >= min_confidence]

    def _evict_wm(self) -> None:
        if not self._wm:
            return
        worst = min(self._wm, key=lambda k: self._wm[k].decay())
        del self._wm[worst]

    @staticmethod
    def _gen_id(prefix: str) -> str:
        return hashlib.md5(f"{prefix}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "working_memory": len(self._wm),
            "episodic_memory": len(self._em),
            "semantic_patterns": len(self._sm),
            "consolidation_cycles": len(self._consolidations),
        }
