"""L0/L2d: SafetyGateAdapter — "5道生理屏障" (5 Physiological Barriers).

Biological Metaphor:
  5道安全门 = 5道生理屏障:
    G1 仓位上限 = 血脑屏障(BBB)——最严格, 只允许必需营养通过
    G2 止损线 = 肾小球滤过——加法调整: ±0.01, 如同RAAS调控
    G3 不确定性阈值 = 免疫耐受——自身抗原不攻击的阈值
    G4 市场限制 = 肠道屏障——动态开放/关闭紧密连接
    G5 隔夜限制 = 肺泡屏障——气体交换效率随运动状态变化

  每一道都有不同的通透性阈值, 且随身体状态动态调整
  如同人在剧烈运动时:
  - BBB保持严格(保护大脑)
  - 肾小球滤过增强(排出代谢废物)
  - 肠道屏障暂时减弱(血液流向肌肉)
  - 肺泡气体交换加速(供氧)

Reference:
  Blood-Brain Barrier physiology;
  Renin-Angiotensin-Aldosterone System (RAAS);
  Danger Theory (Matzinger 2002)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class SafetyGateConfig:
    """Configuration for all 5 safety gates."""

    # G1: Position size limit (BBB — strictest barrier)
    max_position_pct: float  # 0-1, max position as fraction of portfolio
    # G2: Stop-loss level (Glomerular filtration — additive adjustment)
    stop_loss_pct: float  # 0-1, stop-loss threshold
    # G3: Uncertainty threshold (Immune tolerance — self/non-self threshold)
    uncertainty_threshold: float  # 0-1, max acceptable uncertainty
    # G4: Market access (Intestinal barrier — dynamically open/close)
    market_access_score: float  # 0-1, 1=full access, 0=no access
    # G5: Overnight exposure (Alveolar barrier — gas exchange efficiency)
    overnight_exposure_pct: float  # 0-1, max overnight position

    gate_activations: list[float]  # softplus activation per gate
    adaptation_strength: float  # how much HyperNetwork modified baseline
    timestamp: float = field(default_factory=time.time)


class SafetyGateAdapter:
    """5-gate safety barrier adapter — the physiological barriers of the system.

    Each gate corresponds to a biological barrier with its own permeability
    characteristics, dynamically adjusted by market regime (like exercise state).

    Architecture:
      - 5 safety gates with configurable baseline thresholds
      - Gate activations from HyperNetwork safety_head (Softplus outputs)
      - Regime-dependent baseline adjustments
      - Gate interlock: critical gates cannot all be open simultaneously
    """

    N_GATES = 5
    N_REGIMES = 6

    GATE_NAMES = [
        "G1_position_limit",    # Blood-Brain Barrier
        "G2_stop_loss",         # Glomerular Filtration
        "G3_uncertainty",       # Immune Tolerance
        "G4_market_access",     # Intestinal Barrier
        "G5_overnight",         # Alveolar Barrier
    ]

    REGIME_NAMES = [
        "trending_up", "trending_down", "high_volatility",
        "low_volatility", "sideways", "transition",
    ]

    def __init__(self) -> None:
        self._logger = CortexLogger("safety_gate")

        # Baseline gate thresholds per regime [regime][gate]
        # These are the "resting" barrier permeability levels
        self._baseline_thresholds: list[list[float]] = [
            # G1_pos  G2_sl   G3_unc  G4_mkt  G5_ovn
            [0.25,   0.05,   0.30,   0.90,   0.30],   # trending_up: moderate risk
            [0.15,   0.08,   0.35,   0.70,   0.20],   # trending_down: defensive
            [0.10,   0.10,   0.50,   0.50,   0.10],   # high_volatility: very defensive
            [0.30,   0.03,   0.20,   0.95,   0.40],   # low_volatility: relaxed
            [0.20,   0.05,   0.30,   0.80,   0.25],   # sideways: balanced
            [0.15,   0.06,   0.40,   0.60,   0.15],   # transition: cautious
        ]

        # Gate interlock rules: which gates conflict at high activation
        # e.g., high position limit + low uncertainty = contradictory
        self._interlock_pairs: list[tuple[int, int]] = [(0, 2), (0, 4), (1, 3)]

        self._last_config: SafetyGateConfig | None = None
        self._gate_history: list[SafetyGateConfig] = []
        self._call_count: int = 0

    # ── Gate Computation ──────────────────────────────────────────────

    def evaluate(
        self,
        regime_distribution: list[float],
        hypernetwork_thresholds: list[float] | None = None,
        override_gates: dict[int, float] | None = None,
    ) -> SafetyGateConfig:
        """Evaluate all 5 safety gates given current regime.

        Args:
            regime_distribution: 6-dim regime probabilities
            hypernetwork_thresholds: 5-dim Softplus thresholds from HyperNetwork
            override_gates: Manual gate overrides {gate_index: value}

        Returns:
            SafetyGateConfig with all gate thresholds
        """
        self._call_count += 1

        r = list(regime_distribution[:self.N_REGIMES])
        while len(r) < self.N_REGIMES:
            r.append(0.0)

        # 1. Baseline thresholds: weighted average across regimes
        baseline = [0.0] * self.N_GATES
        for g in range(self.N_GATES):
            for j in range(self.N_REGIMES):
                baseline[g] += r[j] * self._baseline_thresholds[j][g]

        # 2. HyperNetwork modulation (ADH-like → gate permeability)
        if hypernetwork_thresholds and len(hypernetwork_thresholds) >= self.N_GATES:
            hn = hypernetwork_thresholds[:self.N_GATES]
        else:
            hn = [0.5] * self.N_GATES

        # Convert Softplus thresholds to gate adjustment factors
        # Softplus ranges ~0-∞, we map to 0.5-1.5 adjustment
        gate_activations = [0.0] * self.N_GATES
        adapted = [0.0] * self.N_GATES
        for g in range(self.N_GATES):
            # Map Softplus to adjustment factor
            sp_val = hn[g]
            adj = 0.5 + sp_val / (sp_val + 2.0)  # maps to 0.5-1.5
            adapted[g] = baseline[g] * adj
            gate_activations[g] = adj

        # 3. Apply manual overrides (emergency intervention)
        if override_gates:
            for g, val in override_gates.items():
                if 0 <= g < self.N_GATES:
                    adapted[g] = val

        # 4. Enforce gate interlock (no contradictory high activations)
        # Use regime-weighted baseline (already computed above), NOT hardcoded index 0
        for g1, g2 in self._interlock_pairs:
            if adapted[g1] > 0.7 * baseline[g1] and \
               adapted[g2] > 0.7 * baseline[g2]:
                # Reduce both proportionally
                factor = 0.7
                adapted[g1] *= factor
                adapted[g2] *= factor

        # 5. Clamp to [0.01, 1.0]
        for g in range(self.N_GATES):
            adapted[g] = max(0.01, min(1.0, adapted[g]))

        # 6. Adaptation strength
        if hypernetwork_thresholds:
            adapt_strength = sum(abs(a - 0.5) for a in gate_activations) / self.N_GATES * 2
        else:
            adapt_strength = 0.0

        config = SafetyGateConfig(
            max_position_pct=round(adapted[0], 4),
            stop_loss_pct=round(adapted[1], 4),
            uncertainty_threshold=round(adapted[2], 4),
            market_access_score=round(adapted[3], 4),
            overnight_exposure_pct=round(adapted[4], 4),
            gate_activations=[round(a, 4) for a in gate_activations],
            adaptation_strength=round(adapt_strength, 3),
        )
        self._last_config = config
        self._gate_history.append(config)
        if len(self._gate_history) > 500:
            self._gate_history = self._gate_history[-500:]

        # Log gate changes
        active_gates = sum(1 for g in range(self.N_GATES)
                          if gate_activations[g] > 1.0)  # above baseline
        self._logger.debug("safety_gates_evaluated",
                          active_gates=active_gates,
                          adapt_strength=round(adapt_strength, 3))

        return config

    def check_position(self, proposed_position_pct: float) -> tuple[bool, str]:
        """G1: Check if proposed position size passes the BBB.

        Like the blood-brain barrier blocking large molecules.
        """
        if self._last_config is None:
            return True, "no_config"
        if proposed_position_pct <= self._last_config.max_position_pct:
            return True, "pass"
        return False, f"Position {proposed_position_pct:.1%} exceeds limit {self._last_config.max_position_pct:.1%}"

    def check_stop_loss(self, current_loss_pct: float) -> tuple[bool, str]:
        """G2: Check if stop-loss triggered.

        Like glomerular filtration detecting excessive waste products.
        """
        if self._last_config is None:
            return False, "no_config"
        if abs(current_loss_pct) >= self._last_config.stop_loss_pct:
            return True, f"Stop-loss triggered at {current_loss_pct:.1%}"
        return False, "within_limit"

    def check_uncertainty(self, model_uncertainty: float) -> tuple[bool, str]:
        """G3: Check if model uncertainty is acceptable.

        Like immune tolerance deciding whether to attack.
        """
        if self._last_config is None:
            return True, "no_config"
        if model_uncertainty <= self._last_config.uncertainty_threshold:
            return True, "tolerated"
        return False, f"Uncertainty {model_uncertainty:.3f} exceeds tolerance {self._last_config.uncertainty_threshold:.3f}"

    def check_market_access(self) -> tuple[bool, str]:
        """G4: Check if market access is currently allowed.

        Like the intestinal barrier deciding what to absorb.
        """
        if self._last_config is None:
            return True, "no_config"
        if self._last_config.market_access_score >= 0.3:
            return True, "access_granted"
        return False, "market_access_restricted"

    def check_overnight(self, proposed_overnight_pct: float) -> tuple[bool, str]:
        """G5: Check if overnight exposure is within limits.

        Like the alveolar barrier regulating gas exchange.
        """
        if self._last_config is None:
            return True, "no_config"
        if proposed_overnight_pct <= self._last_config.overnight_exposure_pct:
            return True, "pass"
        return False, f"Overnight {proposed_overnight_pct:.1%} exceeds limit {self._last_config.overnight_exposure_pct:.1%}"

    def all_gates_pass(
        self,
        position_pct: float = 0.0,
        loss_pct: float = 0.0,
        uncertainty: float = 0.0,
        overnight_pct: float = 0.0,
    ) -> tuple[bool, list[str]]:
        """Check all gates simultaneously.

        Returns:
            (all_pass, list_of_violations)
        """
        violations: list[str] = []

        ok, msg = self.check_position(position_pct)
        if not ok:
            violations.append(f"G1: {msg}")

        triggered, msg = self.check_stop_loss(loss_pct)
        if triggered:
            violations.append(f"G2: {msg}")

        ok, msg = self.check_uncertainty(uncertainty)
        if not ok:
            violations.append(f"G3: {msg}")

        ok, msg = self.check_market_access()
        if not ok:
            violations.append(f"G4: {msg}")

        ok, msg = self.check_overnight(overnight_pct)
        if not ok:
            violations.append(f"G5: {msg}")

        return len(violations) == 0, violations

    @property
    def stats(self) -> dict[str, Any]:
        last = self._last_config
        return {
            "call_count": self._call_count,
            "n_gates": self.N_GATES,
            "gate_names": self.GATE_NAMES,
            "last_config": {
                "max_position_pct": last.max_position_pct,
                "stop_loss_pct": last.stop_loss_pct,
                "uncertainty_threshold": last.uncertainty_threshold,
                "market_access_score": last.market_access_score,
                "overnight_exposure_pct": last.overnight_exposure_pct,
                "adaptation_strength": last.adaptation_strength,
            } if last else None,
        }
