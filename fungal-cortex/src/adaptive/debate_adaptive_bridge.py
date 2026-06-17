"""L0↔L3 Bridge: AdaptiveDebateBridge — "下丘脑-垂体-肾上腺↔免疫系统" 自适应辩论桥.

Biological Metaphor:
  下丘脑-垂体-肾上腺轴(HPA)与免疫系统的双向对话:
    皮质醇(应激激素)直接抑制淋巴细胞活性
    促炎细胞因子(IL-1/IL-6/TNF-α)反过来激活HPA轴
    这是一个经典的"神经内分泌-免疫"反馈环

  我们映射:
    HPA轴 = L0 体制检测(RegimeOrchestrator → UnifiedRegimeReport)
    免疫系统 = L3 辩论引擎(MarketOfClaims → DebateConsensusEngine)
    皮质醇水平 = 熊市体制深度(bear_depth)
    免疫抑制/激活 = 辩论参数动态调整

  bear_trend(高皮质醇状态)→免疫抑制:
    辩论轮数 1→3(更谨慎), 对每个信号反复确认
    空方权重 1.0→1.3(偏保守), 如同免疫抑制时增强Treg活性
    置信度阈值 0.6→0.75, 如同低免疫状态需更强抗原刺激才能激活

  bull_trend(低皮质醇状态)→免疫激活:
    辩论轮数 2→1(更快速), 快速响应机会
    多方验证阈值放宽, 如同免疫激活时更易触发应答

Reference:
  Schuler et al. (2026), IJMS — HPA axis feedback loops;
  MoCA-Agent (arXiv 2606.11537, 2026)
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class ImmuneState(str, Enum):
    """Immune activation state — analogous to HPA-mediated immune modulation."""
    SUPPRESSED = "suppressed"    # High cortisol → conservative
    NORMAL = "normal"            # Homeostasis
    ACTIVATED = "activated"      # Low cortisol → aggressive


@dataclass
class DebateParams:
    """L3 debate parameters dynamically adjusted by L0 regime detection."""

    debate_rounds: int           # Number of verification rounds (1-5)
    bear_weight: float           # Bear argument weight multiplier
    bull_weight: float           # Bull argument weight multiplier
    confidence_threshold: float  # Minimum confidence for claim acceptance
    verification_agents: int     # Number of independent verification agents
    allowed_specialties: list[str]  # Allowed agent specialties for this regime

    # Adjustment source
    adjusted_by: str = ""
    adjusted_at: float = field(default_factory=time.time)


@dataclass
class RegimeImmuneMapping:
    """Mapping from market regime to immune state + debate parameters."""

    regime_label: str
    regime_index: int
    immune_state: ImmuneState
    cortisol_analog: float  # 0-1, higher = more cortisol/more suppressed
    debate_params: DebateParams

    # Evidence chain
    source_regime_confidence: float = 0.0
    created_at: float = field(default_factory=time.time)


class AdaptiveDebateBridge:
    """HPA axis ↔ Immune system bridge: L0 regime → L3 debate parameters.

    Config:
      - debate_rounds_base: default debate rounds in normal state
      - confidence_base: default confidence threshold
      - bear_suppression_factor: how much bear trend suppresses immune response
      - bull_activation_factor: how much bull trend activates immune response
      - history_size: rolling window for regime-adjusted performance tracking
    """

    # Default debate parameter sets per immune state
    _DEFAULT_PARAMS: dict[ImmuneState, dict[str, Any]] = {
        ImmuneState.SUPPRESSED: {
            "debate_rounds": 3,
            "bear_weight": 1.3,
            "bull_weight": 1.0,
            "confidence_threshold": 0.75,
            "verification_agents": 5,
            "allowed_specialties": ["fundamental", "technical", "risk", "macro", "sentiment"],
        },
        ImmuneState.NORMAL: {
            "debate_rounds": 2,
            "bear_weight": 1.0,
            "bull_weight": 1.0,
            "confidence_threshold": 0.60,
            "verification_agents": 3,
            "allowed_specialties": ["fundamental", "technical", "risk", "sentiment", "macro"],
        },
        ImmuneState.ACTIVATED: {
            "debate_rounds": 1,
            "bear_weight": 0.8,
            "bull_weight": 1.2,
            "confidence_threshold": 0.50,
            "verification_agents": 3,
            "allowed_specialties": ["fundamental", "technical", "sentiment", "macro", "risk"],
        },
    }

    def __init__(
        self,
        debate_rounds_base: int = 2,
        confidence_base: float = 0.60,
        bear_suppression_factor: float = 1.5,
        bull_activation_factor: float = 1.3,
        history_size: int = 100,
    ) -> None:
        self._rounds_base = debate_rounds_base
        self._confidence_base = confidence_base
        self._bear_factor = bear_suppression_factor
        self._bull_factor = bull_activation_factor

        self._current_immune_state = ImmuneState.NORMAL
        self._current_params = DebateParams(
            debate_rounds=debate_rounds_base,
            bear_weight=1.0,
            bull_weight=1.0,
            confidence_threshold=confidence_base,
            verification_agents=3,
            allowed_specialties=["fundamental", "technical", "risk", "sentiment", "macro"],
        )
        self._mapping_history: list[RegimeImmuneMapping] = []
        self._history_size = history_size
        self._logger = CortexLogger("debate_adaptive_bridge")

    # ── Core Bridge: Regime → Debate Parameters ────────────────────────

    def adapt_from_regime(
        self,
        regime_label: str,
        regime_index: int,
        regime_confidence: float,
        entropy: float,
    ) -> DebateParams:
        """Adapt L3 debate parameters based on L0 regime detection.

        The HPA axis analogy:
          regime_label → which hormone cascade to activate
          regime_confidence → certainty of the hormone signal
          entropy → cross-expert disagreement (like conflicting hormone signals)
        """
        regime_lower = regime_label.lower()

        # Determine immune state from regime
        if "bear" in regime_lower or "crash" in regime_lower:
            immune_state = ImmuneState.SUPPRESSED
        elif "bull" in regime_lower or "rally" in regime_lower:
            immune_state = ImmuneState.ACTIVATED
        else:
            immune_state = ImmuneState.NORMAL

        # Get base params for this immune state
        base = dict(self._DEFAULT_PARAMS[immune_state])

        # Fine-tune with cortisol analog (bear_depth / bull_strength)
        cortisol = self._compute_cortisol_analog(regime_label, regime_confidence, entropy)

        params = self._interpolate_params(base, cortisol, regime_confidence)
        params.adjusted_by = regime_label
        params.adjusted_at = time.time()

        # Store mapping
        mapping = RegimeImmuneMapping(
            regime_label=regime_label,
            regime_index=regime_index,
            immune_state=immune_state,
            cortisol_analog=cortisol,
            debate_params=params,
            source_regime_confidence=regime_confidence,
        )
        self._mapping_history.append(mapping)
        if len(self._mapping_history) > self._history_size:
            self._mapping_history = self._mapping_history[-self._history_size:]

        # Update current state
        self._current_immune_state = immune_state
        self._current_params = params

        self._logger.info(
            "debate_adapted",
            regime=regime_label,
            immune_state=immune_state.value,
            rounds=params.debate_rounds,
            confidence_threshold=params.confidence_threshold,
            cortisol=cortisol,
        )
        return params

    def adapt_from_regime_report(self, report: dict[str, Any]) -> DebateParams:
        """Convenience: adapt from a BayesianRegimeOrchestrator report dict."""
        return self.adapt_from_regime(
            regime_label=report.get("regime_label", "equilibrium"),
            regime_index=report.get("regime_index", 0),
            regime_confidence=report.get("confidence", 0.5),
            entropy=report.get("entropy", 1.0),
        )

    # ── Reverse Bridge: Debate Outcome → Regime Feedback ───────────────

    def feedback_to_regime(
        self, verified_claims: int, refuted_claims: int, total_claims: int,
    ) -> dict[str, Any]:
        """Reverse feedback: L3 debate outcome → L0 regime confidence adjustment.

        Like IL-1/IL-6/TNF-α cytokines feeding back to HPA axis:
          High refutation rate → increase HPA activity (more cautious)
          High verification rate → decrease HPA activity (less cautious)
        """
        if total_claims == 0:
            return {"adjustment": 0.0, "direction": "none"}

        refute_rate = refuted_claims / total_claims
        verify_rate = verified_claims / total_claims

        # If many claims refuted → need stronger immune suppression
        # → signal L0 to be more conservative
        if refute_rate > 0.6:
            adjustment = self._bear_factor * refute_rate
            direction = "tighten"  # Increase cortisol → more cautious
        elif verify_rate > 0.6:
            adjustment = -self._bull_factor * verify_rate
            direction = "relax"    # Decrease cortisol → more aggressive
        else:
            adjustment = 0.0
            direction = "hold"

        return {
            "adjustment": adjustment,
            "direction": direction,
            "verify_rate": verify_rate,
            "refute_rate": refute_rate,
            "immune_state": self._current_immune_state.value,
        }

    # ── Internal Helpers ───────────────────────────────────────────────

    def _compute_cortisol_analog(
        self, regime_label: str, confidence: float, entropy: float
    ) -> float:
        """Compute a 'cortisol analog' value (0-1) from regime characteristics.

        High cortisol = highly conservative/suppressed immune state.
        """
        regime_lower = regime_label.lower()

        # Base cortisol from regime type
        if "crash" in regime_lower:
            base_cortisol = 0.95
        elif "bear" in regime_lower:
            base_cortisol = 0.80
        elif "volatile" in regime_lower or "uncertain" in regime_lower:
            base_cortisol = 0.60
        elif "sideways" in regime_lower or "range" in regime_lower:
            base_cortisol = 0.35
        elif "bull" in regime_lower:
            base_cortisol = 0.15
        elif "rally" in regime_lower:
            base_cortisol = 0.05
        else:
            base_cortisol = 0.30  # equilibrium

        # Confidence and entropy modulate cortisol
        # High entropy (disagreement) → more cortisol (stress from uncertainty)
        entropy_mod = min(0.3, entropy * 0.1)
        # Low confidence → more cortisol
        confidence_mod = (1.0 - confidence) * 0.2

        return max(0.0, min(1.0, base_cortisol + entropy_mod + confidence_mod))

    def _interpolate_params(
        self, base: dict[str, Any], cortisol: float, confidence: float,
    ) -> DebateParams:
        """Interpolate debate parameters based on cortisol level.

        Cortex analogy: glucocorticoid receptors (GR) have dose-dependent effects:
          Low cortisol → permissive (allows immune activation)
          Medium cortisol → modulatory (fine-tunes)
          High cortisol → suppressive (strongly inhibits)
        """
        # Cortisol-driven adjustments
        # High cortisol → more rounds, higher threshold, bear-bias
        rounds = base["debate_rounds"]
        if cortisol > 0.7:
            rounds = min(5, rounds + 1)

        bear_w = base["bear_weight"] * (1.0 + (cortisol - 0.3) * self._bear_factor * 0.3)
        bull_w = base["bull_weight"] * (1.0 - (cortisol - 0.3) * self._bull_factor * 0.2)
        threshold = base["confidence_threshold"] + (cortisol - 0.3) * 0.3

        return DebateParams(
            debate_rounds=rounds,
            bear_weight=round(max(0.5, min(2.0, bear_w)), 2),
            bull_weight=round(max(0.5, min(2.0, bull_w)), 2),
            confidence_threshold=round(max(0.4, min(0.9, threshold)), 2),
            verification_agents=base["verification_agents"],
            allowed_specialties=list(base["allowed_specialties"]),
        )

    # ── Query Interface ────────────────────────────────────────────────

    def get_current_params(self) -> DebateParams:
        """Get the currently active debate parameters."""
        return self._current_params

    def get_immune_state(self) -> ImmuneState:
        """Get current immune state."""
        return self._current_immune_state

    def get_mapping_history(
        self, limit: int = 20,
    ) -> list[RegimeImmuneMapping]:
        """Get recent regime→immune mappings."""
        return self._mapping_history[-limit:]

    @staticmethod
    def _gen_id(prefix: str) -> str:
        return hashlib.md5(f"{prefix}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "immune_state": self._current_immune_state.value,
            "debate_rounds": self._current_params.debate_rounds,
            "confidence_threshold": self._current_params.confidence_threshold,
            "bear_weight": self._current_params.bear_weight,
            "bull_weight": self._current_params.bull_weight,
            "history_mappings": len(self._mapping_history),
        }
