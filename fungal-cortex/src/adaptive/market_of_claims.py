"""L3/2.1: MarketOfClaims — "MHC抗原呈递 + T/B细胞激活" (Adaptive Immune Response).

Biological Metaphor:
  完整的适应性免疫应答过程:

  1. decompose_to_claims(): 12维信号→50-200个原子Claim
     = 抗原呈递细胞(APC)将病原体蛋白分解为肽段(pHLA),
       每个肽段被MHC-I/MHC-II分子呈递到细胞表面

  2. open_market(): 多方/空方竞价, 净价格判定
     = T细胞识别MHC-肽段复合物→激活→克隆增殖
     多方=BULL=Th1辅助T细胞(促进细胞免疫/买方)
     空方=BEAR=Th2辅助T细胞(促进体液免疫/卖方)
     净价格>0→VERIFIED = 正向选择(抗原被确认为病原体)
     净价格<0→REFUTED = 负向选择(抗原被确认为自身抗原→耐受)

  3. cross_examine(): Claim间逻辑冲突检测
     = 免疫检查点(CTLA-4/PD-1):
     "这个免疫反应会不会过度? 会不会攻击自身组织?"
     因果链断裂检测 = 检查"抗原A的清除是否依赖于抗原B的识别?"
     事实矛盾检测 = 检查"是否同时存在互相矛盾的免疫信号?"

  4. synthesize_decision(): 加权合成最终决策
     = 效应阶段: 激活的T/B细胞执行免疫效应
     BUY=炎症反应(扩大血管, 招募更多免疫细胞)
     SELL=细胞毒性(CD8+ T细胞直接杀死靶细胞)
     HOLD=免疫耐受(不反应)

  AIS集成:
    每个Claim = 抗原(antigen)
    验证通过 = 抗体(antibody)
    被驳倒 = 被清除的病原体(免疫清除)
    高置信度Claim = 高亲和力抗体 → 抗体成熟 → 长期免疫记忆

Reference:
  MoCA-Agent (arXiv 2606.11537, 2026);
  Kolli et al. (2025), Advanced Science——功能淀粉样蛋白的免疫学意义
"""

from __future__ import annotations

import hashlib
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


# ── Deterministic Hash ───────────────────────────────────────────────────

def _det_hash(*args: str) -> int:
    """Deterministic hash for reproducible noise generation.

    Uses MD5 which is stable across Python processes (unlike built-in hash()
    which is randomized via PYTHONHASHSEED). Not used for security — only
    for reproducible pseudo-randomness in market simulations.
    """
    payload = "|".join(args).encode("utf-8")
    return int(hashlib.md5(payload).hexdigest()[:8], 16)


# ── Data Classes ────────────────────────────────────────────────────────

@dataclass
class Claim:
    """A single atomic claim — an "antigen peptide" presented on MHC.

    Each claim represents a falsifiable hypothesis about market state,
    decomposed from the 12-dim raw signal vector.
    """

    claim_id: str
    claim_type: str  # "bullish", "bearish", "neutral"
    description: str  # human-readable statement
    confidence: float  # 0-1, initial confidence from source signal
    source_signals: list[int]  # indices into the 12-dim signal vector
    dependencies: list[str]  # claim_ids this claim logically depends on
    contradicting: list[str]  # claim_ids this claim contradicts

    # MHC presentation metadata
    mhc_class: str  # "I" (endogenous/cellular) or "II" (exogenous/humoral)
    peptide_sequence: list[float]  # the encoded "amino acid" feature vector

    # Market of Claims state
    bull_bids: float = 0.0  # total bullish bidding weight
    bear_asks: float = 0.0  # total bearish asking weight
    net_price: float = 0.0  # bull_bids - bear_asks
    status: str = "pending"  # pending/verified/refuted/dead
    round_id: int = 0  # which market round this claim belongs to

    timestamp: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)


@dataclass
class MarketState:
    """Current state of the claim marketplace."""

    total_claims: int
    active_claims: int
    verified_claims: int
    refuted_claims: int
    dead_claims: int
    net_market_price: float  # aggregate net price across all claims
    market_temperature: float  # 0-1, how heated the debate is
    consensus_level: float  # 0-1, how much agreement exists


@dataclass
class ImmuneDecision:
    """Final synthesized decision from the immune debate."""

    action: str  # "BUY", "SELL", "HOLD"
    confidence: float  # 0-1
    supporting_claims: list[str]  # claim_ids that support this decision
    opposing_claims: list[str]  # claim_ids that oppose this decision
    neutral_claims: list[str]  # claim_ids that were neutral
    risk_assessment: str  # "low", "medium", "high", "critical"
    immune_memory_candidates: list[str]  # claims worth remembering
    market_state: MarketState | None = None
    timestamp: float = field(default_factory=time.time)


# ── Claim Type Templates ─────────────────────────────────────────────────

CLAIM_TEMPLATES = {
    "trend": [
        ("bullish", "价格处于上升趋势(连续高点和低点上移)", [0, 1, 4]),
        ("bearish", "价格处于下降趋势(连续高点和低点下移)", [0, 2, 4]),
        ("neutral", "价格处于横盘整理(无明显方向)", [0, 3, 4]),
    ],
    "momentum": [
        ("bullish", "动量指标显示加速上行", [5, 6]),
        ("bearish", "动量指标显示加速下行", [5, 6]),
        ("neutral", "动量指标处于中性区域", [5]),
    ],
    "volatility": [
        ("bullish", "波动率收敛预示着突破上行", [3, 7]),
        ("bearish", "波动率扩张伴随着下跌", [3, 7]),
        ("neutral", "波动率处于历史正常范围", [3]),
    ],
    "volume": [
        ("bullish", "放量上涨确认买方力量", [5, 6]),
        ("bearish", "放量下跌确认卖方力量", [5, 6]),
        ("neutral", "成交量萎缩市场观望", [5]),
    ],
    "sentiment": [
        ("bullish", "市场情绪转向乐观", [8, 9]),
        ("bearish", "市场情绪转向悲观", [8, 9]),
        ("neutral", "市场情绪中性偏谨慎", [8]),
    ],
    "liquidity": [
        ("bullish", "流动性改善利于做多", [10, 11]),
        ("bearish", "流动性收紧不利做多", [10, 11]),
        ("neutral", "流动性状况正常", [10]),
    ],
}


class MarketOfClaims:
    """Claim marketplace — the adaptive immune system's antigen processing center.

    The "lymph node" of the adaptive engine — where antigens (market signals)
    are presented, debated by T cells (bull/bear bidders), checked for
    autoimmunity risk (cross-examination), and synthesized into effector
    decisions (BUY/SELL/HOLD).

    Architecture:
      1. Antigen Processing: 12-dim signal → 50-200 atomic Claims (MHC presentation)
      2. T Cell Activation: Bull/Bear bidding → net price → verification (clonal selection)
      3. Immune Checkpoint: Cross-examination for logical conflicts (CTLA-4/PD-1)
      4. Effector Phase: Weighted synthesis into final decision
    """

    SIGNAL_DIM = 12
    MIN_CLAIMS = 50
    MAX_CLAIMS = 200

    # Claim type weights for diversity
    CLAIM_TYPE_WEIGHTS = {
        "trend": 0.25,
        "momentum": 0.20,
        "volatility": 0.15,
        "volume": 0.15,
        "sentiment": 0.15,
        "liquidity": 0.10,
    }

    # Market thresholds
    VERIFICATION_THRESHOLD = 0.15  # net_price > this → verified
    REFUTATION_THRESHOLD = -0.10  # net_price < this → refuted
    DEATH_THRESHOLD = -0.30  # net_price < this → dead (apoptosis)
    MARKET_TEMPERATURE_BASE = 0.3

    def __init__(self) -> None:
        self._logger = CortexLogger("market_of_claims")

        # Claim registry — keyed by claim_id, scoped by round
        self._claims: dict[str, Claim] = {}
        self._claim_history: list[dict[str, Any]] = []
        self._current_round_id: int = 0

        # Market statistics
        self._market_rounds: int = 0
        self._total_bull_volume: float = 0.0
        self._total_bear_volume: float = 0.0

        # Immune memory: high-affinity verified claims
        self._immune_memory: list[Claim] = []

        # Cross-examination log
        self._conflict_log: list[dict[str, Any]] = []

        self._last_decision: ImmuneDecision | None = None
        self._last_market_state: MarketState | None = None

        # Maximum claims to retain (per-round cleanup)
        self._MAX_CLAIMS_RETAIN = 5000
        self._MAX_ROUND_HISTORY = 50

    # ── Phase 1: Antigen Processing (Decomposition) ─────────────────────

    def decompose_to_claims(
        self,
        signal_vector: list[float],
        regime_distribution: list[float] | None = None,
        max_claims: int | None = None,
    ) -> list[Claim]:
        """Decompose 12-dim signal vector into atomic claims (antigen peptides).

        Like APCs (dendritic cells/macrophages) processing a pathogen —
        breaking it down into peptide fragments, each presented on MHC molecules.

        Args:
            signal_vector: 12-dim OHLCV + derived features
            regime_distribution: optional 6-dim regime context
            max_claims: override max claims (default from regime context)

        Returns:
            List of Claim objects (50-200, each an "antigen-MHC complex")
        """
        s = list(signal_vector[:self.SIGNAL_DIM])
        while len(s) < self.SIGNAL_DIM:
            s.append(0.0)

        claims: list[Claim] = []

        # Determine claim budget based on signal strength
        signal_strength = sum(abs(v) for v in s) / self.SIGNAL_DIM
        base_claims = int(self.MIN_CLAIMS + signal_strength * (self.MAX_CLAIMS - self.MIN_CLAIMS))
        claim_budget = max_claims or min(base_claims, self.MAX_CLAIMS)

        # Generate claims from each template category
        for claim_type, weight in self.CLAIM_TYPE_WEIGHTS.items():
            n_claims = max(1, int(claim_budget * weight))
            templates = CLAIM_TEMPLATES.get(claim_type, [])

            for i in range(n_claims):
                template_idx = i % len(templates) if templates else 0
                if templates:
                    direction, desc_template, signal_indices = templates[template_idx]
                else:
                    direction, desc_template, signal_indices = ("neutral", "unknown", [0])

                # Compute confidence from source signals
                raw_conf = sum(abs(s[idx]) for idx in signal_indices) / max(len(signal_indices), 1)
                confidence = 1.0 / (1.0 + math.exp(-3.0 * (raw_conf - 0.5)))  # sigmoid normalize

                # Build peptide sequence from relevant signal dimensions
                peptide = [s[idx] if idx < len(s) else 0.0 for idx in signal_indices]
                while len(peptide) < 4:
                    peptide.append(0.0)

                # MHC class assignment
                mhc_class = "I" if claim_type in ("trend", "momentum") else "II"

                # Generate unique claim ID
                claim_id = f"claim_{self._market_rounds:04d}_{claim_type}_{i:03d}"

                claim = Claim(
                    claim_id=claim_id,
                    claim_type=direction,
                    description=f"[{claim_type}] {desc_template}",
                    confidence=round(confidence, 4),
                    source_signals=list(signal_indices),
                    dependencies=[],
                    contradicting=[],
                    mhc_class=mhc_class,
                    peptide_sequence=peptide,
                )
                claims.append(claim)

        # Register all claims with round tracking
        for claim in claims:
            claim.round_id = self._market_rounds
            self._claims[claim.claim_id] = claim

        # Populate claim_history snapshot for audit/rollback
        self._claim_history.append({
            "round": self._market_rounds,
            "claim_ids": [c.claim_id for c in claims],
            "count": len(claims),
            "signal_strength": round(signal_strength, 3),
            "timestamp": time.time(),
        })
        if len(self._claim_history) > self._MAX_ROUND_HISTORY * 2:
            self._claim_history = self._claim_history[-self._MAX_ROUND_HISTORY:]

        self._logger.info("claims_decomposed",
                         total=len(claims),
                         budget=claim_budget,
                         signal_strength=round(signal_strength, 3))

        return claims

    # ── Phase 2: T Cell Activation (Open Market) ────────────────────────

    def open_market(
        self,
        claims: list[Claim] | None = None,
        bull_sentiment: float = 0.5,
        bear_sentiment: float = 0.5,
        regime_context: list[float] | None = None,
    ) -> MarketState:
        """Open the claim marketplace — T cells bid on antigen-MHC complexes.

        Bull bidders = Th1 helper T cells (promoting cellular immunity/buying)
        Bear bidders = Th2 helper T cells (promoting humoral immunity/selling)

        Each claim gets bull_bids and bear_asks. The net_price determines
        whether the claim is verified (confirmed as pathogen/opportunity),
        refuted (tolerated as self-antigen), or dead (apoptosis).

        Args:
            claims: claims to debate (uses all registered if None)
            bull_sentiment: 0-1, baseline bullish bias
            bear_sentiment: 0-1, baseline bearish bias
            regime_context: optional 6-dim regime for context-aware bidding

        Returns:
            MarketState with aggregate market statistics
        """
        self._market_rounds += 1
        active = claims or list(self._claims.values())
        if not active:
            return MarketState(
                total_claims=0, active_claims=0, verified_claims=0,
                refuted_claims=0, dead_claims=0, net_market_price=0.0,
                market_temperature=0.0, consensus_level=0.0,
            )

        # Regime-aware sentiment modulation
        if regime_context and len(regime_context) >= 6:
            r = regime_context[:6]
            # trending_up → bull bias, trending_down → bear bias
            bull_bias = bull_sentiment * (0.7 + 0.6 * r[0])  # boosted by trending_up
            bear_bias = bear_sentiment * (0.7 + 0.6 * r[1])  # boosted by trending_down
            # high_volatility → increased skepticism (both sides more cautious)
            skepticism = 1.0 - 0.3 * r[2]
            bull_bias *= skepticism
            bear_bias *= skepticism
        else:
            bull_bias = bull_sentiment
            bear_bias = bear_sentiment

        verified = 0
        refuted = 0
        dead = 0
        total_net = 0.0

        for claim in active:
            # Compute bidding interest based on claim properties
            base_interest = claim.confidence

            # Bull bidding: attracted to bullish claims, deterred by bearish ones
            if claim.claim_type == "bullish":
                bull_prob = base_interest * bull_bias * 1.3
            elif claim.claim_type == "bearish":
                bull_prob = base_interest * bull_bias * 0.4
            else:
                bull_prob = base_interest * bull_bias * 0.7

            # Bear bidding: attracted to bearish claims, deterred by bullish ones
            if claim.claim_type == "bearish":
                bear_prob = base_interest * bear_bias * 1.3
            elif claim.claim_type == "bullish":
                bear_prob = base_interest * bear_bias * 0.4
            else:
                bear_prob = base_interest * bear_bias * 0.7

            # Add noise (stochastic T cell repertoire sampling) — deterministic hash
            bull_noise = (_det_hash(claim.claim_id, "bull", str(self._market_rounds)) % 100) / 100 * 0.2
            bear_noise = (_det_hash(claim.claim_id, "bear", str(self._market_rounds)) % 100) / 100 * 0.2

            claim.bull_bids = round(max(0.0, bull_prob + bull_noise - 0.1), 4)
            claim.bear_asks = round(max(0.0, bear_prob + bear_noise - 0.1), 4)
            claim.net_price = round(claim.bull_bids - claim.bear_asks, 4)

            # Determine claim fate (positive/negative selection)
            if claim.net_price >= self.VERIFICATION_THRESHOLD:
                claim.status = "verified"
                verified += 1
            elif claim.net_price <= self.DEATH_THRESHOLD:
                claim.status = "dead"
                dead += 1
            elif claim.net_price <= self.REFUTATION_THRESHOLD:
                claim.status = "refuted"
                refuted += 1
            else:
                claim.status = "pending"

            total_net += claim.net_price

        n = len(active)
        avg_net = total_net / n if n > 0 else 0.0

        # Market temperature: how heated is the debate?
        # High when verified+refuted ratio is high (strong opinions)
        decided = verified + refuted + dead
        temperature = self.MARKET_TEMPERATURE_BASE + 0.5 * (decided / n) if n > 0 else 0.0

        # Consensus level: how much agreement exists?
        # High when one side dominates
        if n > 0:
            bull_dominance = sum(1 for c in active if c.net_price > 0) / n
            consensus = max(bull_dominance, 1 - bull_dominance)
        else:
            consensus = 0.0

        # Immune memory consolidation
        for claim in active:
            if claim.status == "verified" and claim.confidence > 0.6:
                self._store_immune_memory(claim)

        state = MarketState(
            total_claims=len(self._claims),
            active_claims=n,
            verified_claims=verified,
            refuted_claims=refuted,
            dead_claims=dead,
            net_market_price=round(avg_net, 4),
            market_temperature=round(temperature, 3),
            consensus_level=round(consensus, 3),
        )
        self._last_market_state = state

        # Track volume
        self._total_bull_volume += sum(c.bull_bids for c in active)
        self._total_bear_volume += sum(c.bear_asks for c in active)

        self._logger.info("market_opened",
                         round=self._market_rounds,
                         verified=verified,
                         refuted=refuted,
                         dead=dead,
                         net_price=round(avg_net, 4),
                         temperature=round(temperature, 3))

        return state

    # ── Phase 3: Immune Checkpoint (Cross-Examination) ──────────────────

    def cross_examine(
        self,
        claims: list[Claim] | None = None,
        strictness: float = 0.5,
    ) -> dict[str, Any]:
        """Cross-examine claims for logical conflicts — immune checkpoint.

        Like CTLA-4 and PD-1 checkpoint receptors that prevent autoimmune attacks:
        - Causal chain break detection: "Does clearing antigen A depend on recognizing antigen B?"
        - Factual contradiction detection: "Are there mutually contradictory immune signals?"
        - Dependency cycle detection: circular logic in claim dependencies

        Args:
            claims: claims to cross-examine (uses all verified+refuted if None)
            strictness: 0-1, how aggressively to detect conflicts

        Returns:
            Dict with conflict analysis results
        """
        active = claims or [
            c for c in self._claims.values()
            if c.status in ("verified", "refuted", "pending")
            and c.round_id >= self._market_rounds - 1  # only current + last round
        ]
        if len(active) < 2:
            return {"conflicts_found": 0, "conflicts": [], "safe": True}

        conflicts: list[dict[str, Any]] = []
        conflict_pairs: set[tuple[str, str]] = set()

        # 1. Direct contradiction: same claim_type, opposite direction
        for i, c1 in enumerate(active):
            for c2 in active[i + 1:]:
                pair_key = tuple(sorted([c1.claim_id, c2.claim_id]))
                if pair_key in conflict_pairs:
                    continue

                conflict_severity = 0.0
                conflict_type = ""

                # Check direct opposition
                if (c1.claim_type == "bullish" and c2.claim_type == "bearish"
                        and self._signal_overlap(c1, c2) > 0.5):
                    conflict_type = "direct_opposition"
                    conflict_severity = 0.7 + 0.3 * strictness

                # Check source signal contradiction
                elif (c1.claim_type == c2.claim_type
                      and self._signal_divergence(c1, c2) > 0.6):
                    conflict_type = "signal_divergence"
                    conflict_severity = 0.5 + 0.3 * strictness

                # Same MHC class competing for same T cell attention
                elif c1.mhc_class == c2.mhc_class and c1.claim_type != c2.claim_type:
                    conflict_type = "t_cell_competition"
                    conflict_severity = 0.3 + 0.3 * strictness

                if conflict_type:
                    conflict_pairs.add(pair_key)
                    # Update contradicting references
                    if c2.claim_id not in c1.contradicting:
                        c1.contradicting.append(c2.claim_id)
                    if c1.claim_id not in c2.contradicting:
                        c2.contradicting.append(c1.claim_id)

                    conflicts.append({
                        "claim_a": c1.claim_id,
                        "claim_b": c2.claim_id,
                        "type": conflict_type,
                        "severity": round(conflict_severity, 3),
                        "resolution": self._resolve_conflict(c1, c2, conflict_type),
                    })

        # 2. Causal chain integrity check
        for claim in active:
            if claim.dependencies:
                for dep_id in claim.dependencies:
                    dep_claim = self._claims.get(dep_id)
                    if dep_claim and dep_claim.status == "dead":
                        conflicts.append({
                            "claim_a": claim.claim_id,
                            "claim_b": dep_id,
                            "type": "causal_chain_broken",
                            "severity": 0.8,
                            "resolution": f"Claim {claim.claim_id} depends on dead claim {dep_id}",
                        })

        # 3. Autoimmunity risk: verified claims that share signal patterns
        # with refuted claims (potential self-attack)
        verified_claims = [c for c in active if c.status == "verified"]
        refuted_claims = [c for c in active if c.status == "refuted"]
        for vc in verified_claims:
            for rc in refuted_claims:
                overlap = self._signal_overlap(vc, rc)
                if overlap > 0.7 and vc.claim_type == rc.claim_type:
                    conflicts.append({
                        "claim_a": vc.claim_id,
                        "claim_b": rc.claim_id,
                        "type": "autoimmunity_risk",
                        "severity": round(0.6 * overlap, 3),
                        "resolution": f"Claim {vc.claim_id} similar to refuted {rc.claim_id} — potential self-attack",
                    })

        self._conflict_log.extend(conflicts)

        is_safe = len(conflicts) == 0 or all(
            c["severity"] < 0.6 for c in conflicts
        )

        self._logger.info("cross_examination_complete",
                         conflicts=len(conflicts),
                         safe=is_safe,
                         strictness=round(strictness, 3))

        return {
            "conflicts_found": len(conflicts),
            "conflicts": conflicts,
            "safe": is_safe,
            "autoimmunity_risk": any(
                c["type"] == "autoimmunity_risk" for c in conflicts
            ),
        }

    # ── Phase 4: Effector Phase (Synthesize Decision) ───────────────────

    def synthesize_decision(
        self,
        market_state: MarketState | None = None,
        risk_tolerance: float = 0.5,
    ) -> ImmuneDecision:
        """Synthesize final trading decision from claim marketplace.

        Like the effector phase of adaptive immunity:
        BUY = Inflammatory response (vasodilation, recruit more immune cells)
        SELL = Cytotoxicity (CD8+ T cells directly kill target cells)
        HOLD = Immune tolerance (no response)

        Args:
            market_state: optional pre-computed market state
            risk_tolerance: 0-1, higher = more willing to act

        Returns:
            ImmuneDecision with action, confidence, and supporting/opposing claims
        """
        state = market_state or self._last_market_state
        if state is None:
            return ImmuneDecision(
                action="HOLD", confidence=0.0,
                supporting_claims=[], opposing_claims=[], neutral_claims=[],
                risk_assessment="low", immune_memory_candidates=[],
            )

        # Collect verified and refuted claims — current round only
        current_round = self._market_rounds
        all_claims = [
            c for c in self._claims.values()
            if c.round_id >= current_round - 1  # current + last round
        ]
        verified = [c for c in all_claims if c.status == "verified"]
        refuted = [c for c in all_claims if c.status == "refuted"]
        dead = [c for c in all_claims if c.status == "dead"]
        pending = [c for c in all_claims if c.status == "pending"]

        # Weighted scoring
        bullish_score = 0.0
        bearish_score = 0.0

        for claim in verified:
            weight = claim.confidence * (1.0 + abs(claim.net_price))
            if claim.claim_type == "bullish":
                bullish_score += weight
            elif claim.claim_type == "bearish":
                bearish_score += weight
            # neutral claims don't contribute to directional score

        # Penalize from refuted claims (negative selection)
        for claim in refuted:
            weight = claim.confidence * 0.5
            if claim.claim_type == "bullish":
                bearish_score += weight  # refuting bull = bearish signal
            elif claim.claim_type == "bearish":
                bullish_score += weight  # refuting bear = bullish signal

        # Normalize
        total_score = bullish_score + bearish_score
        if total_score > 0:
            bullish_pct = bullish_score / total_score
            bearish_pct = bearish_score / total_score
        else:
            bullish_pct = bearish_pct = 0.5

        # Decision threshold (modulated by risk tolerance)
        decision_threshold = 0.55 - risk_tolerance * 0.15  # 0.40-0.55

        if bullish_pct > decision_threshold:
            action = "BUY"
            confidence = bullish_pct
            supporting = [c.claim_id for c in verified if c.claim_type == "bullish"]
            opposing = [c.claim_id for c in verified if c.claim_type == "bearish"]
        elif bearish_pct > decision_threshold:
            action = "SELL"
            confidence = bearish_pct
            supporting = [c.claim_id for c in verified if c.claim_type == "bearish"]
            opposing = [c.claim_id for c in verified if c.claim_type == "bullish"]
        else:
            action = "HOLD"
            confidence = max(bullish_pct, bearish_pct)
            supporting = []
            opposing = []

        neutral = [c.claim_id for c in pending]

        # Risk assessment
        risk = self._assess_risk(state, len(dead), len(verified), len(refuted))

        # Immune memory candidates: high-confidence verified claims
        memory_candidates = [
            c.claim_id for c in verified
            if c.confidence > 0.65 and abs(c.net_price) > 0.2
        ]

        decision = ImmuneDecision(
            action=action,
            confidence=round(confidence, 4),
            supporting_claims=supporting,
            opposing_claims=opposing,
            neutral_claims=neutral,
            risk_assessment=risk,
            immune_memory_candidates=memory_candidates,
            market_state=state,
        )
        self._last_decision = decision

        self._logger.info("decision_synthesized",
                         action=action,
                         confidence=round(confidence, 3),
                         risk=risk,
                         bull_score=round(bullish_score, 3),
                         bear_score=round(bearish_score, 3))

        return decision

    # ── Full Immune Response Pipeline ────────────────────────────────────

    def immune_response(
        self,
        signal_vector: list[float],
        regime_distribution: list[float] | None = None,
        bull_sentiment: float = 0.5,
        bear_sentiment: float = 0.5,
        strictness: float = 0.5,
        risk_tolerance: float = 0.5,
    ) -> ImmuneDecision:
        """Execute the complete adaptive immune response pipeline.

        APC processing → T cell activation → immune checkpoint → effector decision

        This is the main entry point for the Market of Claims engine.
        """
        # Phase 1: Antigen processing
        claims = self.decompose_to_claims(signal_vector, regime_distribution)

        # Phase 2: T cell activation (open market)
        market_state = self.open_market(claims, bull_sentiment, bear_sentiment, regime_distribution)

        # Phase 3: Immune checkpoint (cross-examination)
        exam_result = self.cross_examine(strictness=strictness)

        # Phase 4: Effector decision
        decision = self.synthesize_decision(market_state, risk_tolerance)

        # If cross-examination found severe issues, downgrade confidence
        if not exam_result["safe"]:
            decision = ImmuneDecision(
                action=decision.action,
                confidence=round(decision.confidence * 0.5, 4),
                supporting_claims=decision.supporting_claims,
                opposing_claims=decision.opposing_claims,
                neutral_claims=decision.neutral_claims,
                risk_assessment="high",
                immune_memory_candidates=[],
                market_state=decision.market_state,
            )

        self._cleanup_old_rounds()

        self._logger.info("immune_response_complete",
                         action=decision.action,
                         confidence=round(decision.confidence, 3),
                         safe=exam_result["safe"])

        return decision

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _signal_overlap(c1: Claim, c2: Claim) -> float:
        """Compute Jaccard similarity of source signal indices."""
        s1 = set(c1.source_signals)
        s2 = set(c2.source_signals)
        if not s1 or not s2:
            return 0.0
        return len(s1 & s2) / len(s1 | s2)

    @staticmethod
    def _signal_divergence(c1: Claim, c2: Claim) -> float:
        """Compute how much two claims' peptide sequences diverge."""
        if not c1.peptide_sequence or not c2.peptide_sequence:
            return 0.0
        min_len = min(len(c1.peptide_sequence), len(c2.peptide_sequence))
        if min_len == 0:
            return 0.0
        diff = sum(
            abs(c1.peptide_sequence[i] - c2.peptide_sequence[i])
            for i in range(min_len)
        ) / min_len
        return min(diff, 1.0)

    def _resolve_conflict(
        self, c1: Claim, c2: Claim, conflict_type: str
    ) -> str:
        """Determine how to resolve a conflict between two claims.

        Like Treg cells deciding which immune response to suppress.
        """
        if conflict_type == "direct_opposition":
            # Higher confidence claim wins; both are downgraded
            if c1.confidence > c2.confidence:
                return f"Favor {c1.claim_id} (confidence {c1.confidence:.3f} > {c2.confidence:.3f})"
            return f"Favor {c2.claim_id} (confidence {c2.confidence:.3f} > {c1.confidence:.3f})"

        if conflict_type == "signal_divergence":
            # Both claims are suspect — flag for re-examination
            return f"Both claims flagged for re-examination — signal divergence {self._signal_divergence(c1, c2):.3f}"

        if conflict_type == "t_cell_competition":
            # MHC class determines priority
            if c1.mhc_class == "I" and c2.mhc_class == "II":
                return f"Prioritize {c1.claim_id} (MHC-I endogenous pathway)"
            elif c2.mhc_class == "I" and c1.mhc_class == "II":
                return f"Prioritize {c2.claim_id} (MHC-I endogenous pathway)"
            return "Equal priority — both claims retained"

        return "unresolved"

    def _assess_risk(
        self,
        state: MarketState,
        dead_count: int,
        verified_count: int,
        refuted_count: int,
    ) -> str:
        """Assess overall risk level from market state.

        Like evaluating whether the immune response is appropriate or excessive.
        """
        risk_score = 0.0

        # High temperature = heated debate = higher risk
        risk_score += state.market_temperature * 0.3

        # High dead claim ratio = immune exhaustion
        total_decided = verified_count + refuted_count + dead_count
        if total_decided > 0:
            death_ratio = dead_count / total_decided
            risk_score += death_ratio * 0.3

        # Low consensus = uncertainty = higher risk
        risk_score += (1.0 - state.consensus_level) * 0.2

        # Too many refuted = possible autoimmunity
        if total_decided > 0:
            refuted_ratio = refuted_count / total_decided
            risk_score += refuted_ratio * 0.2

        if risk_score > 0.7:
            return "critical"
        elif risk_score > 0.5:
            return "high"
        elif risk_score > 0.3:
            return "medium"
        return "low"

    def _store_immune_memory(self, claim: Claim) -> None:
        """Store a verified claim in immune memory.

        Like memory B cells retaining high-affinity antibody blueprints.
        """
        # Check if similar claim already in memory
        for existing in self._immune_memory:
            if (existing.claim_type == claim.claim_type
                    and self._signal_overlap(existing, claim) > 0.7):
                # Update existing memory (affinity maturation)
                existing.confidence = max(existing.confidence, claim.confidence)
                existing.last_updated = time.time()
                return

        self._immune_memory.append(claim)
        # Cap memory size
        if len(self._immune_memory) > 1000:
            # Remove lowest confidence
            self._immune_memory.sort(key=lambda c: c.confidence)
            self._immune_memory = self._immune_memory[-1000:]

    def get_immune_memory(self) -> list[dict[str, Any]]:
        """Retrieve immune memory for inspection."""
        return [
            {
                "claim_id": c.claim_id,
                "claim_type": c.claim_type,
                "confidence": c.confidence,
                "mhc_class": c.mhc_class,
                "status": c.status,
            }
            for c in self._immune_memory[-20:]  # last 20
        ]

    def _cleanup_old_rounds(self) -> None:
        """Remove claims from rounds older than MAX_ROUND_HISTORY.

        Like the immune system clearing old apoptotic cells through
        efferocytosis — prevents accumulation of cellular debris.
        """
        cutoff_round = max(0, self._market_rounds - self._MAX_ROUND_HISTORY)
        stale_ids = [
            cid for cid, c in self._claims.items()
            if c.round_id < cutoff_round
        ]
        for cid in stale_ids:
            del self._claims[cid]

        # Also cap total claims
        if len(self._claims) > self._MAX_CLAIMS_RETAIN:
            # Keep most recent
            sorted_ids = sorted(
                self._claims.keys(),
                key=lambda cid: self._claims[cid].round_id,
                reverse=True,
            )
            for cid in sorted_ids[self._MAX_CLAIMS_RETAIN:]:
                del self._claims[cid]

        if stale_ids:
            self._logger.debug("claims_cleaned",
                             removed=len(stale_ids),
                             remaining=len(self._claims))

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_claims": len(self._claims),
            "immune_memory_size": len(self._immune_memory),
            "market_rounds": self._market_rounds,
            "total_bull_volume": round(self._total_bull_volume, 2),
            "total_bear_volume": round(self._total_bear_volume, 2),
            "conflict_log_size": len(self._conflict_log),
            "last_action": self._last_decision.action if self._last_decision else "none",
            "last_market": {
                "verified": self._last_market_state.verified_claims,
                "refuted": self._last_market_state.refuted_claims,
                "temperature": self._last_market_state.market_temperature,
            } if self._last_market_state else None,
        }
