"""L3/2.2: AISImmuneValidator — "克隆选择 + 负选择 + 危险理论" (AIS Three-Layer Defense).

Biological Metaphor:
  免疫系统的三层防御架构:

  第一层: 负选择(Negative Selection)——识别"非我"(non-self)
    正常交易模式 = self(自体)——不应触发免疫反应
    异常信号 = non-self(非自体)——触发免疫警报
    = 胸腺中的T细胞教育: 能识别自身抗原的T细胞被清除(凋亡)
      只有不攻击自身的T细胞才能存活→外周
    → 防止"自体免疫"(autoimmunity): 系统错误地攻击自己的健康组织(优秀策略)

  第二层: 克隆选择(Clonal Selection)——验证"抗体"
    高置信度Claim→高亲和力抗体→克隆增殖(Clonal Expansion)
    低置信度Claim→低亲和力→超突变(Somatic Hypermutation)优化
    → 如同B细胞在生发中心(Germinal Center)经历:
      1. 体细胞超突变(SHM): 随机改变抗体可变区基因
      2. 亲和力选择: 高亲和力B细胞被滤泡树突状细胞(FDC)选择存活
      3. 类别转换(Class Switching): IgG/IgA/IgE(不同策略类型)
    超突变率 ∝ (1 - affinity):
      低亲和力→高突变率(需要更多变异才能找到更好的)
      高亲和力→低突变率(已经很好, 微调即可)
    99.83%准确率(HAIS-IDS)——这是我们追求的目标

  第三层: 危险理论(Danger Theory)
    检测"危险信号"(DAMPs: Damage-Associated Molecular Patterns):
    - PnL异常 = 组织损伤
    - 回撤超标 = 器官功能衰竭
    - 信号矛盾 = 细胞因子风暴(免疫系统过度激活)
    危险区域: 触发局部免疫增强(如同炎症部位招募更多免疫细胞)

Reference:
  Singh & Arora (2025), "HAIS-IDS", 波兰科学院技术科学通报;
  Grimm (AAAI 2025)——AIS用于GNN防御;
  Matzinger (2002), "Danger Model"
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


# ── Deterministic Hash ───────────────────────────────────────────────────

def _det_hash(*args: str) -> int:
    """Deterministic hash for reproducible noise generation."""
    payload = "|".join(args).encode("utf-8")
    return int(hashlib.md5(payload).hexdigest()[:8], 16)


# ── Data Classes ────────────────────────────────────────────────────────

@dataclass
class SelfProfile:
    """A "self" profile — normal/healthy market behavior pattern.

    Like the thymic medullary epithelial cells (mTECs) that express
    tissue-specific self-antigens for T cell education.
    """

    profile_id: str
    feature_centroid: list[float]  # mean of normal behavior features
    feature_variance: list[float]  # acceptable variance range
    sample_count: int  # number of observations forming this profile
    last_updated: float
    regime_label: str  # which regime this self-profile belongs to


@dataclass
class Antibody:
    """A validated "antibody" — high-affinity strategy/trade signal.

    Like an IgG antibody secreted by plasma cells after clonal selection.
    """

    antibody_id: str
    claim_id: str  # source claim (antigen)
    specificity: list[float]  # what this antibody recognizes (feature pattern)
    affinity: float  # 0-1, how strongly it binds to target
    antibody_class: str  # "IgG" (trend), "IgM" (momentum), "IgA" (volatility)
    mutation_count: int  # number of somatic hypermutations applied
    clone_size: int  # how many copies exist (proliferation level)
    validated: bool  # passed negative selection
    timestamp: float = field(default_factory=time.time)


@dataclass
class DangerSignal:
    """A DAMP (Damage-Associated Molecular Pattern) detection.

    Like HMGB1, ATP, uric acid released by damaged cells —
    these trigger sterile inflammation and recruit immune cells.
    """

    signal_type: str  # "pnl_abnormal", "drawdown", "signal_contradiction", etc.
    severity: float  # 0-1
    source: str  # where the damage is detected
    description: str
    triggered_protection: bool  # whether protective measures were activated
    timestamp: float = field(default_factory=time.time)


@dataclass
class ImmuneValidationReport:
    """Complete report from one immune validation cycle."""

    negative_selection_passed: bool
    self_similarity_score: float  # 0-1, 1=perfectly normal/self
    antibodies_generated: int
    antibodies_validated: int
    clonal_expansion_count: int
    somatic_hypermutation_applied: int
    danger_signals: list[str]  # list of triggered danger signal types
    danger_level: float  # 0-1, aggregate danger
    immune_response: str  # "active", "tolerant", "suppressed"
    timestamp: float = field(default_factory=time.time)


class AISImmuneValidator:
    """Three-layer Artificial Immune System validator.

    The "thymus + bone marrow + lymph node" of the adaptive engine —
    educates T cells (negative selection), matures B cells (clonal selection),
    and detects tissue damage (danger theory).

    Architecture:
      Layer 1 — Negative Selection: Match against self-profiles, purge auto-reactive
      Layer 2 — Clonal Selection: Affinity maturation via SHM + proliferation
      Layer 3 — Danger Theory: DAMP detection → protective response modulation
    """

    FEATURE_DIM = 32
    SELF_PROFILE_EMA = 0.05  # slow adaptation to new "normal"
    NEGATIVE_SELECTION_THRESHOLD = 0.85  # similarity > this → self (safe)
    DANGER_THRESHOLD = 0.3  # danger level > this → protective response

    # Clonal selection parameters
    BASE_MUTATION_RATE = 0.30  # max mutation rate for lowest-affinity antibodies
    MIN_MUTATION_RATE = 0.02  # min mutation rate for highest-affinity antibodies
    CLONE_BASE_SIZE = 1
    CLONE_MAX_SIZE = 100
    AFFINITY_TARGET = 0.9983  # HAIS-IDS target accuracy

    # Danger signal types
    DANGER_TYPES = [
        "pnl_abnormal",
        "drawdown_exceeded",
        "signal_contradiction",
        "volatility_spike",
        "liquidity_dry_up",
        "correlation_breakdown",
        "regime_flip",
        "execution_failure",
    ]

    def __init__(self) -> None:
        self._logger = CortexLogger("immune_validator")

        # Self-profile library
        self._self_profiles: dict[str, SelfProfile] = {}

        # Antibody repertoire
        self._antibodies: dict[str, Antibody] = {}
        self._antibody_history: list[Antibody] = []

        # Danger signal log
        self._danger_signals: list[DangerSignal] = []
        self._active_dangers: set[str] = set()

        # Statistics
        self._validation_count: int = 0
        self._total_shm_applied: int = 0
        self._total_clones_generated: int = 0

        # State
        self._immune_response: str = "tolerant"
        self._last_report: ImmuneValidationReport | None = None

    # ── Layer 1: Negative Selection ─────────────────────────────────────

    def update_self_profile(
        self,
        feature_vector: list[float],
        regime_label: str = "default",
    ) -> SelfProfile:
        """Update or create a self-profile through EMA learning.

        Like the thymus continuously updating its "self-antigen" library
        as the body's protein expression patterns change over time.

        Args:
            feature_vector: 32-dim feature representation of current market state
            regime_label: which market regime this profile belongs to

        Returns:
            Updated or created SelfProfile
        """
        f = list(feature_vector[:self.FEATURE_DIM])
        while len(f) < self.FEATURE_DIM:
            f.append(0.0)

        profile_id = f"self_{regime_label}"

        if profile_id in self._self_profiles:
            profile = self._self_profiles[profile_id]
            # Welford's online variance: compute deviation BEFORE updating centroid
            alpha = self.SELF_PROFILE_EMA
            old_centroid = list(profile.feature_centroid)
            profile.feature_centroid = [
                (1 - alpha) * old_centroid[i] + alpha * f[i]
                for i in range(self.FEATURE_DIM)
            ]
            profile.feature_variance = [
                (1 - alpha) * profile.feature_variance[i]
                + alpha * (f[i] - old_centroid[i]) ** 2  # use OLD centroid
                for i in range(self.FEATURE_DIM)
            ]
            profile.sample_count += 1
            profile.last_updated = time.time()
        else:
            profile = SelfProfile(
                profile_id=profile_id,
                feature_centroid=f[:],
                feature_variance=[0.5] * self.FEATURE_DIM,
                sample_count=1,
                last_updated=time.time(),
                regime_label=regime_label,
            )
            self._self_profiles[profile_id] = profile

        return profile

    def negative_selection(
        self,
        feature_vector: list[float],
        regime_label: str = "default",
    ) -> tuple[bool, float, str | None]:
        """Check if a feature vector is "self" or "non-self".

        Like T cell negative selection in the thymus:
        - T cells that strongly recognize self-antigens → apoptosis (deleted)
        - T cells that weakly recognize self-antigens → survive (released to periphery)
        - T cells that don't recognize any self → also survive (ready for non-self)

        Args:
            feature_vector: 32-dim feature to test
            regime_label: which self-profile to compare against

        Returns:
            (is_self, similarity_score, matched_profile_id)
        """
        f = list(feature_vector[:self.FEATURE_DIM])
        while len(f) < self.FEATURE_DIM:
            f.append(0.0)

        if not self._self_profiles:
            # No self-profile yet → everything is potentially non-self
            return False, 0.0, None

        # Find best-matching self profile
        best_similarity = 0.0
        best_profile_id: str | None = None

        for pid, profile in self._self_profiles.items():
            # Only check profiles matching the regime context
            if regime_label != "default" and profile.regime_label != regime_label:
                # Allow cross-regime checking with penalty
                similarity = self._compute_self_similarity(f, profile) * 0.8
            else:
                similarity = self._compute_self_similarity(f, profile)

            if similarity > best_similarity:
                best_similarity = similarity
                best_profile_id = pid

        is_self = best_similarity >= self.NEGATIVE_SELECTION_THRESHOLD

        self._logger.debug("negative_selection",
                          is_self=is_self,
                          similarity=round(best_similarity, 3),
                          profile=best_profile_id or "none")

        return is_self, best_similarity, best_profile_id

    def _compute_self_similarity(
        self, features: list[float], profile: SelfProfile
    ) -> float:
        """Compute how similar a feature vector is to a self-profile.

        Uses normalized Mahalanobis-like distance converted to similarity.
        """
        total_deviation = 0.0
        for i in range(self.FEATURE_DIM):
            std = math.sqrt(max(profile.feature_variance[i], 1e-6))
            deviation = abs(features[i] - profile.feature_centroid[i]) / std
            total_deviation += deviation

        avg_deviation = total_deviation / self.FEATURE_DIM
        # Convert deviation to similarity (0-1)
        similarity = 1.0 / (1.0 + avg_deviation)
        return similarity

    # ── Layer 2: Clonal Selection ───────────────────────────────────────

    def clonal_selection(
        self,
        claims: list[dict[str, Any]],
        feature_vectors: list[list[float]] | None = None,
    ) -> list[Antibody]:
        """Apply clonal selection to generate and mature antibodies from claims.

        Like B cells in the germinal center:
        1. Somatic Hypermutation (SHM): random mutation of antibody variable region
        2. Affinity Selection: high-affinity B cells selected by FDCs
        3. Class Switching: determine antibody class based on context

        Args:
            claims: list of claim dicts with claim_id, confidence, claim_type
            feature_vectors: optional per-claim feature vectors for specificity

        Returns:
            List of matured Antibody objects
        """
        antibodies: list[Antibody] = []

        for i, claim_data in enumerate(claims):
            claim_id = claim_data.get("claim_id", f"claim_{i}")
            confidence = claim_data.get("confidence", 0.5)
            claim_type = claim_data.get("claim_type", "neutral")

            # Determine initial affinity from claim confidence
            affinity = confidence

            # Get specificity pattern
            if feature_vectors and i < len(feature_vectors):
                specificity = list(feature_vectors[i][:self.FEATURE_DIM])
            else:
                specificity = [confidence] * min(8, self.FEATURE_DIM)
            while len(specificity) < self.FEATURE_DIM:
                specificity.append(0.0)

            # Determine antibody class (like immunoglobulin class switching)
            ab_class = self._determine_antibody_class(claim_type, confidence)

            # Apply somatic hypermutation
            mutation_rate = self._compute_mutation_rate(affinity)
            mutation_count = max(1, int(mutation_rate * 20))  # 1-20 mutations
            specificity = self._apply_hypermutation(specificity, mutation_rate, mutation_count)
            affinity = self._recompute_affinity(specificity, affinity, mutation_rate)

            # Determine clone size (proliferation)
            clone_size = self._compute_clone_size(affinity)

            antibody = Antibody(
                antibody_id=f"ab_{self._validation_count:04d}_{i:03d}",
                claim_id=claim_id,
                specificity=specificity,
                affinity=round(affinity, 6),
                antibody_class=ab_class,
                mutation_count=mutation_count,
                clone_size=clone_size,
                validated=False,  # will be set after negative selection
            )
            antibodies.append(antibody)
            self._antibodies[antibody.antibody_id] = antibody

            self._total_shm_applied += mutation_count
            self._total_clones_generated += clone_size

        # Apply affinity-based selection (FDC selection)
        # Sort by affinity descending, keep top performing
        antibodies.sort(key=lambda a: a.affinity, reverse=True)

        # Mark top antibodies (those approaching HAIS-IDS target)
        validated_count = 0
        for ab in antibodies:
            if ab.affinity >= self.AFFINITY_TARGET * 0.7:  # 70% of target
                ab.validated = True
                validated_count += 1

        self._antibody_history.extend(antibodies)
        if len(self._antibody_history) > 1000:
            self._antibody_history = self._antibody_history[-1000:]

        self._logger.info("clonal_selection_complete",
                         antibodies=len(antibodies),
                         validated=validated_count,
                         avg_affinity=round(
                             sum(a.affinity for a in antibodies) / max(len(antibodies), 1), 4
                         ))

        return antibodies

    def _compute_mutation_rate(self, affinity: float) -> float:
        """Compute somatic hypermutation rate: ∝ (1 - affinity).

        Low affinity → high mutation rate (need more exploration)
        High affinity → low mutation rate (already good, fine-tune)
        """
        rate = self.BASE_MUTATION_RATE * (1.0 - affinity)
        return max(self.MIN_MUTATION_RATE, min(self.BASE_MUTATION_RATE, rate))

    def _apply_hypermutation(
        self,
        specificity: list[float],
        mutation_rate: float,
        mutation_count: int,
    ) -> list[float]:
        """Apply somatic hypermutation to antibody specificity.

        Each mutation randomly perturbs one dimension of the specificity vector.
        Like AID (Activation-Induced Cytidine Deaminase) targeting
        immunoglobulin variable regions.
        """
        mutated = list(specificity)
        dims = len(mutated)

        for m in range(mutation_count):
            idx = _det_hash("mut", str(m), str(int(time.time() * 1000) % 1000000)) % dims
            delta = (_det_hash("delta", str(m), str(idx)) % 1000) / 1000 * 2 - 1
            delta *= mutation_rate * 0.5
            mutated[idx] = max(-1.0, min(1.0, mutated[idx] + delta))

        return mutated

    def _recompute_affinity(
        self,
        specificity: list[float],
        original_affinity: float,
        mutation_rate: float,
    ) -> float:
        """Recompute affinity after hypermutation.

        Most mutations are neutral or deleterious, some are beneficial.
        This models the selection pressure in the germinal center.
        """
        # Mutation effect: mostly small changes, rare large improvements
        effect = (_det_hash("aff", f"{specificity[0]:.6f}") % 1000) / 1000
        if effect < 0.05:  # 5% chance of significant improvement
            delta = mutation_rate * 0.3
        elif effect < 0.30:  # 25% chance of minor improvement
            delta = mutation_rate * 0.1
        elif effect < 0.70:  # 40% chance of neutral
            delta = 0.0
        else:  # 30% chance of deleterious
            delta = -mutation_rate * 0.15

        new_affinity = original_affinity + delta
        return max(0.01, min(1.0, new_affinity))

    def _compute_clone_size(self, affinity: float) -> int:
        """Compute clonal expansion size from affinity.

        High-affinity antibodies → massive clonal proliferation.
        Low-affinity antibodies → minimal proliferation (may undergo apoptosis).
        """
        # Exponential mapping: affinity 0.5 → ~3 clones, 0.99 → ~95 clones
        normalized = (affinity - 0.3) / 0.7  # map 0.3-1.0 to 0-1
        normalized = max(0.0, min(1.0, normalized))
        size = int(self.CLONE_BASE_SIZE + normalized ** 2 * self.CLONE_MAX_SIZE)
        return max(1, min(self.CLONE_MAX_SIZE, size))

    def _determine_antibody_class(self, claim_type: str, confidence: float) -> str:
        """Determine antibody class based on claim type (class switching).

        IgG: Trend claims — most abundant, long-lasting, crosses placenta (stable strategies)
        IgM: Momentum claims — first responder, pentameric (fast but short-lived)
        IgA: Volatility/risk claims — mucosal defense (barrier protection)
        IgE: Event-driven claims — allergy/parasite defense (rare but potent)
        """
        if claim_type == "bullish" and confidence > 0.6:
            return "IgG"  # strong trend signal
        elif claim_type == "bearish" and confidence > 0.6:
            return "IgG"
        elif claim_type in ("bullish", "bearish"):
            return "IgM"  # early momentum
        elif claim_type == "neutral":
            return "IgA"  # mucosal/barrier
        return "IgM"

    # ── Layer 3: Danger Theory ──────────────────────────────────────────

    def detect_danger(
        self,
        pnl_change_pct: float = 0.0,
        drawdown_pct: float = 0.0,
        signal_contradiction_level: float = 0.0,
        volatility_ratio: float = 1.0,
        liquidity_ratio: float = 1.0,
        correlation_breakdown: float = 0.0,
        regime_flip_detected: bool = False,
        execution_failure_rate: float = 0.0,
    ) -> list[DangerSignal]:
        """Detect danger signals (DAMPs) in the system.

        Like pattern recognition receptors (PRRs) on innate immune cells
        detecting DAMPs released by stressed/dying cells:
        - HMGB1 = PnL异常 (alarmin released by necrotic cells)
        - ATP = 回撤超标 (energy crisis signal)
        - Uric acid = 信号矛盾 (purine metabolism byproduct)
        - HSPs = 波动率暴涨 (heat shock proteins = stress)
        - DNA = 流动性枯竭 (nuclear debris from dead cells)

        Returns:
            List of DangerSignal objects for each triggered DAMP
        """
        signals: list[DangerSignal] = []

        # DAMP 1: PnL abnormal (tissue damage)
        if abs(pnl_change_pct) > 5.0:
            severity = min(1.0, abs(pnl_change_pct) / 20.0)
            signals.append(DangerSignal(
                signal_type="pnl_abnormal",
                severity=round(severity, 3),
                source="portfolio",
                description=f"PnL change {pnl_change_pct:+.2f}% exceeds threshold",
                triggered_protection=severity > 0.5,
            ))

        # DAMP 2: Drawdown exceeded (organ failure)
        if drawdown_pct > 10.0:
            severity = min(1.0, drawdown_pct / 30.0)
            signals.append(DangerSignal(
                signal_type="drawdown_exceeded",
                severity=round(severity, 3),
                source="risk_management",
                description=f"Drawdown {drawdown_pct:.2f}% exceeds safe limit",
                triggered_protection=severity > 0.4,
            ))

        # DAMP 3: Signal contradiction (cytokine storm)
        if signal_contradiction_level > 0.5:
            severity = signal_contradiction_level
            signals.append(DangerSignal(
                signal_type="signal_contradiction",
                severity=round(severity, 3),
                source="sensory_cortex",
                description="Conflicting signals detected across multiple channels",
                triggered_protection=severity > 0.6,
            ))

        # DAMP 4: Volatility spike (cellular stress)
        if volatility_ratio > 2.0:
            severity = min(1.0, (volatility_ratio - 1.0) / 4.0)
            signals.append(DangerSignal(
                signal_type="volatility_spike",
                severity=round(severity, 3),
                source="market_sensing",
                description=f"Volatility ratio {volatility_ratio:.2f}x indicates stress",
                triggered_protection=severity > 0.5,
            ))

        # DAMP 5: Liquidity dry-up (circulatory shock)
        if liquidity_ratio < 0.3:
            severity = 1.0 - liquidity_ratio
            signals.append(DangerSignal(
                signal_type="liquidity_dry_up",
                severity=round(severity, 3),
                source="market_access",
                description=f"Liquidity ratio {liquidity_ratio:.2f} — market access restricted",
                triggered_protection=True,
            ))

        # DAMP 6: Correlation breakdown (tissue architecture disruption)
        if correlation_breakdown > 0.5:
            severity = correlation_breakdown
            signals.append(DangerSignal(
                signal_type="correlation_breakdown",
                severity=round(severity, 3),
                source="portfolio",
                description="Cross-asset correlation structure breaking down",
                triggered_protection=severity > 0.6,
            ))

        # DAMP 7: Regime flip (homeostatic shock)
        if regime_flip_detected:
            signals.append(DangerSignal(
                signal_type="regime_flip",
                severity=0.7,
                source="regime_orchestrator",
                description="Sudden market regime transition detected",
                triggered_protection=True,
            ))

        # DAMP 8: Execution failure (immune effector failure)
        if execution_failure_rate > 0.1:
            severity = min(1.0, execution_failure_rate * 5)
            signals.append(DangerSignal(
                signal_type="execution_failure",
                severity=round(severity, 3),
                source="execution_engine",
                description=f"Execution failure rate {execution_failure_rate:.1%}",
                triggered_protection=severity > 0.5,
            ))

        # Update active dangers
        for sig in signals:
            self._danger_signals.append(sig)
            if sig.triggered_protection:
                self._active_dangers.add(sig.signal_type)
            elif sig.signal_type in self._active_dangers:
                self._active_dangers.discard(sig.signal_type)

        # Cap danger signal log
        if len(self._danger_signals) > 500:
            self._danger_signals = self._danger_signals[-500:]

        if signals:
            self._logger.warn("danger_signals_detected",
                            count=len(signals),
                            types=[s.signal_type for s in signals],
                            max_severity=max(s.severity for s in signals))

        return signals

    def compute_danger_level(self) -> float:
        """Compute aggregate danger level from active danger signals.

        Like the integrated stress response — multiple DAMPs synergize
        to trigger a systemic protective response.
        """
        if not self._danger_signals:
            return 0.0

        # Recent signals (last 100) weighted by recency and severity
        recent = self._danger_signals[-100:]
        if not recent:
            return 0.0

        now = time.time()
        total_weight = 0.0
        weighted_severity = 0.0

        for i, sig in enumerate(recent):
            # Time decay: older signals matter less
            age_hours = (now - sig.timestamp) / 3600
            time_weight = math.exp(-age_hours / 24)  # 24-hour half-life
            # Recency bias: most recent signals weighted more
            recency = (i + 1) / len(recent)
            weight = time_weight * recency * sig.severity

            weighted_severity += weight
            total_weight += recency

        if total_weight == 0:
            return 0.0

        danger_level = weighted_severity / total_weight

        # Nonlinear amplification: multiple simultaneous dangers > sum of parts
        active_count = len(self._active_dangers)
        if active_count >= 3:
            danger_level *= 1.0 + 0.15 * (active_count - 2)  # synergistic amplification

        return min(1.0, danger_level)

    # ── Full Validation Pipeline ────────────────────────────────────────

    def validate(
        self,
        feature_vector: list[float],
        claims: list[dict[str, Any]],
        claim_features: list[list[float]] | None = None,
        regime_label: str = "default",
        danger_params: dict[str, float] | None = None,
    ) -> ImmuneValidationReport:
        """Execute the full three-layer immune validation pipeline.

        Negative Selection → Clonal Selection → Danger Detection

        Args:
            feature_vector: current market state features
            claims: list of claim dicts to validate
            claim_features: per-claim feature vectors
            regime_label: current regime context
            danger_params: optional dict of danger detection parameters

        Returns:
            ImmuneValidationReport with complete validation results
        """
        self._validation_count += 1

        # Layer 1: Negative Selection
        is_self, self_similarity, matched_profile = self.negative_selection(
            feature_vector, regime_label
        )

        # Update self-profile only when confirmed self (prevent anomaly drift)
        if is_self and self_similarity > 0.9:
            self.update_self_profile(feature_vector, regime_label)

        # Layer 2: Clonal Selection
        antibodies = []
        if not is_self or self_similarity < 0.95:
            # Non-self or borderline → generate antibodies
            antibodies = self.clonal_selection(claims, claim_features)

        # Layer 3: Danger Theory
        dp = danger_params or {}
        danger_signals = self.detect_danger(
            pnl_change_pct=dp.get("pnl_change_pct", 0.0),
            drawdown_pct=dp.get("drawdown_pct", 0.0),
            signal_contradiction_level=dp.get("signal_contradiction_level", 0.0),
            volatility_ratio=dp.get("volatility_ratio", 1.0),
            liquidity_ratio=dp.get("liquidity_ratio", 1.0),
            correlation_breakdown=dp.get("correlation_breakdown", 0.0),
            regime_flip_detected=dp.get("regime_flip_detected", False),
            execution_failure_rate=dp.get("execution_failure_rate", 0.0),
        )
        danger_level = self.compute_danger_level()

        # Determine immune response state
        if danger_level > self.DANGER_THRESHOLD:
            self._immune_response = "active"  # fight mode
        elif is_self and self_similarity > 0.9:
            self._immune_response = "tolerant"  # rest mode
        else:
            self._immune_response = "suppressed"  # cautious mode

        report = ImmuneValidationReport(
            negative_selection_passed=is_self,
            self_similarity_score=round(self_similarity, 4),
            antibodies_generated=len(antibodies),
            antibodies_validated=sum(1 for a in antibodies if a.validated),
            clonal_expansion_count=sum(a.clone_size for a in antibodies),
            somatic_hypermutation_applied=sum(a.mutation_count for a in antibodies),
            danger_signals=[s.signal_type for s in danger_signals],
            danger_level=round(danger_level, 4),
            immune_response=self._immune_response,
        )
        self._last_report = report

        self._logger.info("immune_validation_complete",
                         response=report.immune_response,
                         self_similarity=round(self_similarity, 3),
                         antibodies=len(antibodies),
                         danger_level=round(danger_level, 3))

        return report

    @property
    def stats(self) -> dict[str, Any]:
        last_r = self._last_report
        return {
            "validation_count": self._validation_count,
            "self_profiles": len(self._self_profiles),
            "antibody_repertoire": len(self._antibodies),
            "total_shm_applied": self._total_shm_applied,
            "total_clones_generated": self._total_clones_generated,
            "active_dangers": list(self._active_dangers),
            "immune_response": self._immune_response,
            "last_report": {
                "self_similarity": last_r.self_similarity_score,
                "antibodies_validated": last_r.antibodies_validated,
                "danger_level": last_r.danger_level,
                "response": last_r.immune_response,
            } if last_r else None,
        }
