"""L0/L4b: MemoryFeedbackBridge — "免疫记忆 + 朊病毒构象记忆" (Immune Memory + Prion Conformational Memory).

Biological Metaphor:
  免疫系统的记忆B细胞(memory B cells)——首次感染后,
  保留高亲和力抗体蓝图数十年(如天花疫苗接种一次终身免疫)
  + 朊病毒构象记忆(conformational memory)——蛋白质折叠状态
  本身就是一种可遗传的"记忆"

  三个反馈通道:
    1. 情景→SHARP样本(高盈亏→高优先级训练)
       = 免疫记忆: 致命病原体的抗原被永久保留(最高警戒)
    2. 语义→模板匹配(相似市场→复用最优参数)
       = 交叉免疫: 牛痘感染后对天花的免疫力
    3. 过程→恢复(故障快照→快速回滚)
       = 自体耐受: 免疫系统记住"自身抗原", 不攻击自己

  AIS克隆选择启发:
    免疫记忆细胞: 长期保留高价值情景(年衰减=记忆B细胞半衰期)
    克隆选择: 高频使用情景自我复制(克隆增殖) = LTP强化
    低频淘汰: 不活跃情景凋亡 = LTD弱化 + 突触修剪
    亲和力成熟: 超突变+选择→抗体亲和力逐步提升
      → 策略参数通过"体细胞超突变"逐步优化!

Reference:
  Singh & Arora (2025), "HAIS-IDS", 波兰科学院技术科学通报;
  Maury (2025), "Amyloid world hypothesis", FEBS Letters 599:2693-2705;
  Kolli et al. (2025), "Functional Amyloids", Advanced Science
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


# ── Data Structures ───────────────────────────────────────────────────

@dataclass
class EpisodicMemory:
    """A high-value episodic memory (like an immune memory B cell).

    Stores a specific market scenario + the successful response.
    """

    memory_id: str
    market_context: list[float]  # encoded market features (the "antigen")
    strategy_response: list[float]  # what strategy worked (the "antibody")
    pnl_impact: float  # how profitable the response was
    affinity: float  # 0-1, how well the response matched the context
    activation_count: int = 0  # how many times this memory was recalled
    created_at: float = field(default_factory=time.time)
    last_activated: float = 0.0
    decay_rate: float = 0.01  # annual decay (memory B cell half-life)


@dataclass
class SemanticTemplate:
    """A generalized pattern template (like cross-reactive immunity).

    Abstracts over multiple episodic memories to form a general principle.
    """

    template_id: str
    pattern_type: str  # e.g., "bull_market_breakout", "bear_market_crash"
    centroid: list[float]  # prototypical feature vector
    optimal_params: list[float]  # best-known parameter set
    confidence: float  # how reliable this template is
    source_memories: list[str]  # which episodic memories formed this template
    created_at: float = field(default_factory=time.time)


@dataclass
class RecoverySnapshot:
    """A system snapshot for fast recovery (like immune self-tolerance).

    Records the healthy system state so we can recognize "self" vs "non-self".
    """

    snapshot_id: str
    state_data: dict[str, Any]
    health_score: float
    created_at: float = field(default_factory=time.time)


@dataclass
class MemoryFeedbackReport:
    """Output report from memory feedback bridge."""

    episodic_recall_count: int
    semantic_matches: list[dict[str, Any]]
    recovery_available: bool
    affinities_updated: int
    memories_promoted: int
    memories_retired: int
    timestamp: float = field(default_factory=time.time)


class MemoryFeedbackBridge:
    """Three-channel memory feedback bridge combining immune and prion memory.

    The "immune memory + prion conformational memory" system — retains
    high-value experiences, generalizes patterns, and enables fast recovery.

    Three feedback channels:
      1. Episodic → SHARP samples (high PnL → high priority training)
      2. Semantic → Template matching (similar markets → reuse optimal params)
      3. Process → Recovery (fault snapshot → fast rollback)

    AIS clonal selection dynamics:
      - High-affinity memories → clonal expansion (more activations)
      - Low-affinity memories → apoptosis (retirement)
      - Somatic hypermutation → gradual affinity improvement
    """

    MAX_EPISODIC_MEMORIES = 5000
    MAX_SEMANTIC_TEMPLATES = 200
    MAX_RECOVERY_SNAPSHOTS = 10
    MEMORY_DECAY_RATE = 0.01  # annual decay rate (memory B cell half-life ≈ years)
    AFFINITY_MATURATION_RATE = 0.05  # SHM rate per activation
    PROMOTION_THRESHOLD = 3  # activations needed for clonal expansion
    RETIREMENT_THRESHOLD = 0.01  # minimum affinity before retirement

    def __init__(self) -> None:
        self._logger = CortexLogger("memory_bridge")
        self._call_count = 0

        # Three memory stores
        self._episodic_memories: dict[str, EpisodicMemory] = {}
        self._semantic_templates: dict[str, SemanticTemplate] = {}
        self._recovery_snapshots: list[RecoverySnapshot] = []

        # Statistics
        self._total_recalls: int = 0
        self._total_promotions: int = 0
        self._total_retirements: int = 0

    # ── Channel 1: Episodic Memory (Immune Memory B Cells) ───────────

    def store_episode(
        self,
        market_context: list[float],
        strategy_response: list[float],
        pnl_impact: float,
    ) -> str:
        """Store a new episodic memory.

        Like a memory B cell encoding a specific pathogen's antigen signature.

        Args:
            market_context: Encoded market features (the "antigen")
            strategy_response: Strategy parameters used (the "antibody blueprint")
            pnl_impact: Profit/loss outcome (positive = successful immune response)

        Returns:
            memory_id of the stored episode
        """
        memory_id = f"ep-{self._call_count:06d}-{int(time.time() * 1000) % 10000:04d}"

        # Compute initial affinity based on PnL impact
        # High PnL → high affinity (effective immune response)
        affinity = 1.0 / (1.0 + math.exp(-pnl_impact * 5))  # sigmoid

        memory = EpisodicMemory(
            memory_id=memory_id,
            market_context=list(market_context),
            strategy_response=list(strategy_response),
            pnl_impact=pnl_impact,
            affinity=affinity,
            activation_count=0,
        )
        self._episodic_memories[memory_id] = memory

        # Maintain capacity: retire lowest-affinity memories
        if len(self._episodic_memories) > self.MAX_EPISODIC_MEMORIES:
            sorted_memories = sorted(
                self._episodic_memories.values(),
                key=lambda m: m.affinity * math.exp(-m.decay_rate * max(0, time.time() - m.last_activated) / 31536000),
            )
            to_remove = sorted_memories[:len(self._episodic_memories) - self.MAX_EPISODIC_MEMORIES]
            for m in to_remove:
                del self._episodic_memories[m.memory_id]
                self._total_retirements += 1

        self._logger.debug("episode_stored",
                          memory_id=memory_id,
                          affinity=round(affinity, 3),
                          pnl_impact=round(pnl_impact, 4))
        return memory_id

    def recall_episodic(
        self,
        market_context: list[float],
        top_k: int = 5,
    ) -> list[EpisodicMemory]:
        """Recall the most relevant episodic memories.

        Like memory B cells being reactivated upon re-exposure to an antigen.

        Uses cosine similarity between current context and stored contexts.
        Returns top-k matches with activation count increment.
        """
        self._total_recalls += 1

        if not self._episodic_memories:
            return []

        now = time.time()
        scored: list[tuple[EpisodicMemory, float]] = []

        for memory in self._episodic_memories.values():
            # Cosine similarity
            similarity = self._cosine_similarity(market_context, memory.market_context)

            # Apply time decay (memory B cells slowly lose affinity if not reactivated)
            time_since_activation = max(0, now - memory.last_activated) / 31536000  # years
            decay_factor = math.exp(-memory.decay_rate * time_since_activation)

            # Composite score: similarity × affinity × decay
            score = similarity * memory.affinity * decay_factor

            scored.append((memory, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_k]

        # Increment activation counts (clonal selection)
        promoted = 0
        for memory, score in top:
            memory.activation_count += 1
            memory.last_activated = now

            # Somatic hypermutation: high-usage memories improve affinity
            if memory.activation_count > self.PROMOTION_THRESHOLD:
                memory.affinity = min(1.0, memory.affinity + self.AFFINITY_MATURATION_RATE)
                memory.decay_rate = max(0.001, memory.decay_rate * 0.9)  # slow decay
                promoted += 1

        self._total_promotions += promoted

        return [m for m, _ in top]

    # ── Channel 2: Semantic Memory (Cross-Reactive Immunity) ──────────

    def store_template(
        self,
        pattern_type: str,
        feature_vectors: list[list[float]],
        optimal_params: list[float],
    ) -> str:
        """Create a semantic template from multiple episodic memories.

        Like the immune system developing cross-reactive immunity —
        exposure to cowpox creates immunity to smallpox.

        The template generalizes across similar market patterns.
        """
        if not feature_vectors:
            return ""

        template_id = f"tmpl-{pattern_type}-{self._call_count:06d}"

        # Compute centroid
        n_dims = len(feature_vectors[0])
        centroid = [0.0] * n_dims
        for vec in feature_vectors:
            for i in range(min(len(vec), n_dims)):
                centroid[i] += vec[i]
        centroid = [c / len(feature_vectors) for c in centroid]

        # Confidence based on number of examples
        confidence = min(len(feature_vectors) / 20.0, 1.0)  # 20 examples → max confidence

        template = SemanticTemplate(
            template_id=template_id,
            pattern_type=pattern_type,
            centroid=centroid,
            optimal_params=list(optimal_params),
            confidence=confidence,
            source_memories=[],  # populated as memories are linked
        )
        self._semantic_templates[template_id] = template

        # Maintain capacity
        if len(self._semantic_templates) > self.MAX_SEMANTIC_TEMPLATES:
            oldest = min(self._semantic_templates.values(), key=lambda t: t.created_at)
            del self._semantic_templates[oldest.template_id]

        self._logger.debug("template_stored",
                          template_id=template_id,
                          pattern_type=pattern_type,
                          confidence=round(confidence, 3))
        return template_id

    def match_template(
        self,
        market_context: list[float],
        min_confidence: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Match current market to semantic templates.

        Like the immune system checking if a new pathogen resembles
        any previously encountered ones (cross-reactivity).
        """
        matches: list[dict[str, Any]] = []

        for template in self._semantic_templates.values():
            if template.confidence < min_confidence:
                continue

            similarity = self._cosine_similarity(market_context, template.centroid)

            if similarity > 0.7:  # high match threshold
                matches.append({
                    "template_id": template.template_id,
                    "pattern_type": template.pattern_type,
                    "similarity": round(similarity, 4),
                    "confidence": round(template.confidence, 3),
                    "optimal_params": [round(p, 4) for p in template.optimal_params[:8]],
                })

        matches.sort(key=lambda m: m["similarity"], reverse=True)
        return matches[:5]

    # ── Channel 3: Recovery Snapshot (Self-Tolerance) ─────────────────

    def create_recovery_snapshot(self, state_data: dict[str, Any], health_score: float) -> str:
        """Create a system snapshot for fast recovery.

        Like the immune system recording "self" antigens to establish tolerance —
        prevents autoimmune attacks on healthy system components.
        """
        snapshot_id = f"snap-{int(time.time())}-{self._call_count:06d}"

        snapshot = RecoverySnapshot(
            snapshot_id=snapshot_id,
            state_data=dict(state_data),
            health_score=health_score,
        )
        self._recovery_snapshots.append(snapshot)

        # Keep only the healthiest snapshots
        self._recovery_snapshots.sort(key=lambda s: s.health_score, reverse=True)
        if len(self._recovery_snapshots) > self.MAX_RECOVERY_SNAPSHOTS:
            self._recovery_snapshots = self._recovery_snapshots[:self.MAX_RECOVERY_SNAPSHOTS]

        self._logger.info("recovery_snapshot_created",
                         snapshot_id=snapshot_id,
                         health_score=round(health_score, 3))
        return snapshot_id

    def get_best_recovery(self, min_health: float = 50.0) -> dict[str, Any] | None:
        """Retrieve the healthiest recovery snapshot.

        Like restoring immune tolerance by referencing the recorded "self" signature.
        """
        if not self._recovery_snapshots:
            return None

        best = max(self._recovery_snapshots, key=lambda s: s.health_score)
        if best.health_score >= min_health:
            return {
                "snapshot_id": best.snapshot_id,
                "health_score": best.health_score,
                "state_data": best.state_data,
                "created_at": best.created_at,
            }
        return None

    # ── Maintenance ───────────────────────────────────────────────────

    def decay_memories(self) -> dict[str, int]:
        """Apply time-based decay to all memories.

        Like the natural turnover of memory B cells — unused memories
        gradually lose affinity and may be retired.
        """
        now = time.time()
        retired = 0
        updated = 0

        for memory_id, memory in list(self._episodic_memories.items()):
            time_since_activation = max(0, now - memory.last_activated) / 31536000
            decay_factor = math.exp(-memory.decay_rate * time_since_activation)
            old_affinity = memory.affinity
            memory.affinity = max(0.001, memory.affinity * decay_factor)

            if memory.affinity < self.RETIREMENT_THRESHOLD and memory.activation_count < 2:
                del self._episodic_memories[memory_id]
                retired += 1
            elif abs(memory.affinity - old_affinity) > 0.001:
                updated += 1

        if retired > 0:
            self._logger.debug("memories_decayed", retired=retired, updated=updated)

        return {"retired": retired, "updated": updated}

    # ── Main Bridge Cycle ─────────────────────────────────────────────

    def cycle(
        self,
        market_context: list[float] | None = None,
        state_data: dict[str, Any] | None = None,
        health_score: float = 0.0,
    ) -> MemoryFeedbackReport:
        """Execute one cycle of the memory feedback bridge.

        Args:
            market_context: Current market encoding for recall + template matching
            state_data: Current system state for recovery snapshot
            health_score: Current health score (0-100)

        Returns:
            MemoryFeedbackReport with cycle statistics
        """
        self._call_count += 1

        # Channel 1: Recall episodic memories
        episodic_recalled = 0
        if market_context:
            recalled = self.recall_episodic(market_context, top_k=5)
            episodic_recalled = len(recalled)

        # Channel 2: Match semantic templates
        semantic_matches: list[dict[str, Any]] = []
        if market_context:
            semantic_matches = self.match_template(market_context)

        # Channel 3: Recovery snapshot
        recovery_available = False
        if state_data and health_score > 60:
            self.create_recovery_snapshot(state_data, health_score)
        if self.get_best_recovery():
            recovery_available = True

        # Periodic maintenance
        decay_stats = self.decay_memories()

        report = MemoryFeedbackReport(
            episodic_recall_count=episodic_recalled,
            semantic_matches=semantic_matches,
            recovery_available=recovery_available,
            affinities_updated=decay_stats.get("updated", 0),
            memories_promoted=self._total_promotions,
            memories_retired=self._total_retirements,
        )

        self._logger.debug("memory_bridge_cycle",
                          episodic=episodic_recalled,
                          semantic=len(semantic_matches),
                          recovery=recovery_available)

        return report

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Cosine similarity between two vectors."""
        min_len = min(len(a), len(b))
        if min_len == 0:
            return 0.0
        dot = sum(a[i] * b[i] for i in range(min_len))
        norm_a = math.sqrt(sum(x ** 2 for x in a[:min_len]))
        norm_b = math.sqrt(sum(x ** 2 for x in b[:min_len]))
        if norm_a < 1e-10 or norm_b < 1e-10:
            return 0.0
        return dot / (norm_a * norm_b)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "call_count": self._call_count,
            "episodic_memories": len(self._episodic_memories),
            "semantic_templates": len(self._semantic_templates),
            "recovery_snapshots": len(self._recovery_snapshots),
            "total_recalls": self._total_recalls,
            "total_promotions": self._total_promotions,
            "total_retirements": self._total_retirements,
            "best_recovery_health": (
                max(s.health_score for s in self._recovery_snapshots)
                if self._recovery_snapshots else 0.0
            ),
        }
