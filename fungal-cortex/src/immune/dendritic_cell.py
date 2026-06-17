"""Dendritic Cell Algorithm — three-signal danger theory.

Inspired by dendritic cells in the adaptive immune system:
- PAMP (Pathogen-Associated Molecular Patterns): known danger signatures
  e.g., strategy drawdown > 20%, Sharpe < 0, consecutive losses > 5
- DAMP (Damage-Associated Molecular Patterns): tissue damage signals
  e.g., unusual volatility, correlation breakdown, liquidity dry-up
- Co-stimulation: confirmation from other immune cells / multi-agent consensus

Three output states: Mature (immune response), Tolerogenic (no response),
Regulatory (modulate other immune cells).

Based on RL-DCA (AAAI 2026): Q-learning for dynamic signal classification.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any


class DCSignal(Enum):
    PAMP = "pamp"
    DAMP = "damp"
    CO_STIMULATION = "co_stimulation"
    SAFE = "safe"


class DCMaturationState(Enum):
    MATURE = "mature"           # Trigger immune response
    TOLEROGENIC = "tolerogenic"  # No response (tolerate)
    REGULATORY = "regulatory"    # Modulate other cells
    IMMATURE = "immature"        # Not yet decided


class DendriticCell:
    """Dendritic cell integrating PAMP + DAMP + co-stimulation.

    Three-signal model:
    1. PAMP: known danger patterns (pre-defined signatures)
    2. DAMP: tissue/cellular damage indicators
    3. Co-stimulation: consensus from other detectors

    Integration: weighted sum → maturation decision.
    RL extension: Q-learning adjusts signal weights over time.
    """

    # Known PAMP signatures
    PAMP_SIGNATURES: dict[str, dict[str, Any]] = {
        "sharpe_crash": {"threshold": -1.0, "weight": 0.9},
        "drawdown_deep": {"threshold": 0.20, "weight": 0.8},
        "consecutive_losses": {"threshold": 5, "weight": 0.7},
        "volatility_spike": {"threshold": 0.40, "weight": 0.6},
        "correlation_breakdown": {"threshold": 0.90, "weight": 0.5},
        "liquidity_dryup": {"threshold": 0.70, "weight": 0.7},
    }

    # Known DAMP signatures
    DAMP_SIGNATURES: dict[str, dict[str, Any]] = {
        "unusual_drawdown": {"threshold": 0.10, "weight": 0.6},
        "strategy_divergence": {"threshold": 0.30, "weight": 0.5},
        "signal_noise_ratio": {"threshold": 0.50, "weight": 0.4},
        "execution_slippage": {"threshold": 0.05, "weight": 0.5},
        "model_decay": {"threshold": 0.15, "weight": 0.6},
    }

    def __init__(self, cell_id: str = "", learning_rate: float = 0.1) -> None:
        self.cell_id = cell_id or f"dc-{int(time.time() * 1000) % 10000:04d}"
        self._maturation_state = DCMaturationState.IMMATURE
        self._signal_history: list[dict[str, Any]] = []
        self._last_decision_time: float | None = None
        self._pamp_level = 0.0
        self._damp_level = 0.0
        self._co_stim_level = 0.0
        self._cumulative_danger = 0.0

        # Q-learning weights for dynamic signal adaptation
        self._lr = learning_rate
        self._q_weights: dict[str, float] = {
            "pamp": 0.5,
            "damp": 0.3,
            "co_stim": 0.2,
        }

    def process_signals(
        self, pamp_signals: dict[str, float], damp_signals: dict[str, float], co_stimulation: float = 0.0
    ) -> dict[str, Any]:
        """Process three signal types and decide maturation state.

        Args:
            pamp_signals: dict of detected PAMP signatures → measured values
            damp_signals: dict of detected DAMP signatures → measured values
            co_stimulation: consensus score from other immune cells [0, 1]
        """
        self._pamp_level = self._compute_signal_strength(pamp_signals, self.PAMP_SIGNATURES)
        self._damp_level = self._compute_signal_strength(damp_signals, self.DAMP_SIGNATURES)
        self._co_stim_level = co_stimulation

        # Weighted integration
        integrated_danger = (
            self._q_weights["pamp"] * self._pamp_level
            + self._q_weights["damp"] * self._damp_level
            + self._q_weights["co_stim"] * self._co_stim_level
        )

        self._cumulative_danger = 0.9 * self._cumulative_danger + 0.1 * integrated_danger

        # Maturation decision
        prev_state = self._maturation_state
        self._maturation_state = self._decide_maturation(integrated_danger, co_stimulation)
        self._last_decision_time = time.time()

        # Q-learning update
        reward = self._compute_reward()
        self._update_q_weights(reward)

        self._signal_history.append({
            "timestamp": time.time(),
            "pamp": round(self._pamp_level, 4),
            "damp": round(self._damp_level, 4),
            "co_stim": round(self._co_stim_level, 4),
            "integrated": round(integrated_danger, 4),
            "cumulative": round(self._cumulative_danger, 4),
            "state": self._maturation_state.value,
            "prev_state": prev_state.value,
        })

        # Keep history bounded
        if len(self._signal_history) > 500:
            self._signal_history = self._signal_history[-500:]

        return {
            "cell_id": self.cell_id,
            "maturation_state": self._maturation_state.value,
            "pamp_level": round(self._pamp_level, 4),
            "damp_level": round(self._damp_level, 4),
            "co_stimulation": round(self._co_stim_level, 4),
            "integrated_danger": round(integrated_danger, 4),
            "cumulative_danger": round(self._cumulative_danger, 4),
            "trigger_immune_response": self._maturation_state == DCMaturationState.MATURE,
            "state_changed": prev_state != self._maturation_state,
        }

    def _compute_signal_strength(
        self, measured: dict[str, float], signatures: dict[str, dict[str, Any]]
    ) -> float:
        """Compute aggregate signal strength from measured values vs thresholds."""
        if not measured:
            return 0.0
        total = 0.0
        total_weight = 0.0
        for name, sig in signatures.items():
            if name in measured:
                # Normalize: how far above threshold?
                threshold = sig["threshold"]
                value = abs(measured[name])
                if threshold > 0:
                    excess = max(0.0, value - threshold) / threshold
                else:
                    excess = float(value > threshold)
                total += sig["weight"] * min(1.0, excess)
                total_weight += sig["weight"]
        return total / max(total_weight, 0.01)

    def _decide_maturation(self, danger: float, co_stim: float) -> DCMaturationState:
        """Decide maturation state based on integrated danger."""
        if danger > 0.7 and co_stim > 0.3:
            return DCMaturationState.MATURE
        if danger > 0.4 and co_stim > 0.5:
            return DCMaturationState.MATURE
        if danger < 0.2 and co_stim < 0.3:
            return DCMaturationState.TOLEROGENIC
        if self._cumulative_danger > 0.6:
            return DCMaturationState.MATURE
        return DCMaturationState.REGULATORY if danger > 0.3 else DCMaturationState.IMMATURE

    def _compute_reward(self) -> float:
        """Compute reward for Q-learning: +1 for correct maturation, -0.5 for false alarm."""
        if self._maturation_state == DCMaturationState.MATURE:
            if self._pamp_level > 0.5:
                return 1.0
            return -0.3
        if self._maturation_state == DCMaturationState.TOLEROGENIC:
            if self._pamp_level < 0.2:
                return 0.5
            return -0.5
        return 0.0

    def _update_q_weights(self, reward: float) -> None:
        """Q-learning update for signal weights."""
        for key in self._q_weights:
            signal_value = {"pamp": self._pamp_level, "damp": self._damp_level, "co_stim": self._co_stim_level}[key]
            # Simple gradient: increase weight if signal was informative
            delta = self._lr * reward * signal_value
            self._q_weights[key] = max(0.05, min(0.8, self._q_weights[key] + delta))
        # Normalize
        total = sum(self._q_weights.values())
        if total > 0:
            self._q_weights = {k: v / total for k, v in self._q_weights.items()}

    @property
    def maturation_state(self) -> DCMaturationState:
        return self._maturation_state

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "state": self._maturation_state.value,
            "pamp_level": round(self._pamp_level, 4),
            "damp_level": round(self._damp_level, 4),
            "co_stim_level": round(self._co_stim_level, 4),
            "cumulative_danger": round(self._cumulative_danger, 4),
            "signal_history_len": len(self._signal_history),
            "q_weights": {k: round(v, 4) for k, v in self._q_weights.items()},
        }
