"""Dual-Mode Engine — quantum superposition exploration + classical sequential execution.

Quantum mode:
- Maintains N parallel hypothesis states (superposition)
- Low confidence (< threshold) → explore multiple possibilities simultaneously
- Superradiance boost: computational advantage from coherent superposition
- Decoherence rate limits how long superposition can be maintained

Classical mode:
- Single deterministic state (collapsed from quantum or directly set)
- High confidence (≥ threshold) → execute deterministically
- Standard sequential reasoning

Recurrence condition (Speed 2026): After quantum collapse, the system must
revisit the possibility space before generating conscious experience.
This prevents premature convergence to local optima.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ModeType(str, Enum):
    QUANTUM = "quantum"
    CLASSICAL = "classical"


@dataclass
class QuantumState:
    """A superposition of hypothesis states with complex amplitudes."""

    hypotheses: list[dict[str, Any]]  # Parallel hypothesis states
    amplitudes: list[float]  # |ψ_i|² = probability of each hypothesis
    phases: list[float]  # φ_i = relative phase (interference)
    coherence: float  # Overall quantum coherence (0-1)
    superposition_count: int
    timestamp: float = field(default_factory=time.time)

    def normalize(self) -> None:
        """Normalize amplitudes so Σ|ψ_i|² = 1."""
        total = sum(a ** 2 for a in self.amplitudes)
        if total > 0:
            self.amplitudes = [a / math.sqrt(total) for a in self.amplitudes]


@dataclass
class ClassicalState:
    """A single collapsed (deterministic) state."""

    selected_hypothesis: dict[str, Any]
    confidence: float
    collapsed_from_quantum: bool
    timestamp: float = field(default_factory=time.time)


class DualModeEngine:
    """Quantum-classical dual-mode cognitive engine.

    Usage flow:
    1. When confidence < threshold → enter QUANTUM mode
       - Initialize N parallel hypothesis states in superposition
       - Evolve with interference and decoherence
       - Measure (collapse) when confidence rises or time runs out
    2. When confidence ≥ threshold → enter CLASSICAL mode
       - Execute deterministic sequential reasoning
       - Monitor confidence — if it drops, re-enter quantum mode
    3. Recurrence condition: after collapse, revisit superposition before final decision
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        superposition_states: int = 8,
        decoherence_rate: float = 0.05,
        recurrence_depth: int = 3,
        superradiance_boost: float = 2.0,
        seed: int | None = None,
    ) -> None:
        self._confidence_threshold = confidence_threshold
        self._n_states = superposition_states
        self._decoherence_rate = decoherence_rate
        self._recurrence_depth = recurrence_depth
        self._superradiance_boost = superradiance_boost
        self._mode = ModeType.CLASSICAL
        self._confidence: float = 1.0
        self._quantum_state: QuantumState | None = None
        self._classical_state: ClassicalState | None = None
        self._recurrence_count = 0
        self._collapse_history: list[ClassicalState] = []
        if seed is not None:
            random.seed(seed)

    @property
    def mode(self) -> ModeType:
        return self._mode

    @property
    def confidence(self) -> float:
        return self._confidence

    def evaluate_confidence(self, evidence_strength: float, uncertainty: float) -> float:
        """Evaluate current confidence from evidence and uncertainty.

        confidence = evidence_strength / (1 + uncertainty)
        """
        self._confidence = evidence_strength / (1.0 + uncertainty)
        self._confidence = min(1.0, max(0.0, self._confidence))
        return self._confidence

    def decide_mode(self) -> tuple[ModeType, str]:
        """Decide whether to use quantum or classical mode based on confidence."""
        if self._confidence < self._confidence_threshold:
            reason = f"low_confidence({self._confidence:.2f} < {self._confidence_threshold})"
            self._enter_quantum()
            return self._mode, reason
        else:
            reason = f"sufficient_confidence({self._confidence:.2f} ≥ {self._confidence_threshold})"
            self._enter_classical()
            return self._mode, reason

    def _enter_quantum(self) -> None:
        """Enter quantum superposition mode — initialize parallel hypotheses."""
        self._mode = ModeType.QUANTUM
        if self._quantum_state is None:
            hypotheses = [{"id": f"h{i}", "state": {}} for i in range(self._n_states)]
            amplitudes = [1.0 / math.sqrt(self._n_states)] * self._n_states
            phases = [2.0 * math.pi * i / self._n_states for i in range(self._n_states)]
            self._quantum_state = QuantumState(
                hypotheses=hypotheses,
                amplitudes=amplitudes,
                phases=phases,
                coherence=1.0,
                superposition_count=self._n_states,
            )

    def _enter_classical(self) -> None:
        """Enter classical mode — collapse or continue deterministic execution."""
        prev_mode = self._mode
        self._mode = ModeType.CLASSICAL

        if prev_mode == ModeType.QUANTUM and self._quantum_state is not None:
            self._collapse()

    def evolve_quantum(self, steps: int = 1) -> QuantumState:
        """Evolve the quantum superposition (apply decoherence + interference)."""
        if self._quantum_state is None:
            self._enter_quantum()

        qs = self._quantum_state
        assert qs is not None

        for _ in range(steps):
            # Decoherence: amplitudes leak toward classical probabilities
            for i in range(len(qs.amplitudes)):
                noise = random.gauss(0.0, self._decoherence_rate)
                qs.amplitudes[i] = max(0.0, qs.amplitudes[i] + noise)
                # Phase diffusion
                qs.phases[i] += random.gauss(0.0, self._decoherence_rate * 0.5)

            # Coherence decays
            qs.coherence = max(0.0, qs.coherence - self._decoherence_rate)

            qs.normalize()

            # Superradiance boost: reinforce dominant amplitudes (positive feedback)
            if qs.coherence > 0.3:
                max_idx = qs.amplitudes.index(max(qs.amplitudes))
                boost = self._superradiance_boost * qs.coherence * self._decoherence_rate
                qs.amplitudes[max_idx] += boost
                qs.normalize()

        return qs

    def _collapse(self) -> ClassicalState:
        """Collapse quantum superposition → single classical state (measurement)."""
        qs = self._quantum_state
        assert qs is not None

        # Probability-weighted selection (Born rule)
        probs = [a ** 2 for a in qs.amplitudes]
        total = sum(probs)
        if total == 0:
            selected_idx = 0
        else:
            r = random.random() * total
            cumulative = 0.0
            selected_idx = 0
            for i, p in enumerate(probs):
                cumulative += p
                if r <= cumulative:
                    selected_idx = i
                    break

        selected_hypothesis = dict(qs.hypotheses[selected_idx])
        selected_hypothesis["collapse_amplitude"] = qs.amplitudes[selected_idx]
        selected_hypothesis["collapse_phase"] = qs.phases[selected_idx]

        cs = ClassicalState(
            selected_hypothesis=selected_hypothesis,
            confidence=self._confidence,
            collapsed_from_quantum=True,
        )
        self._classical_state = cs
        self._collapse_history.append(cs)
        if len(self._collapse_history) > 20:
            self._collapse_history = self._collapse_history[-20:]

        # Recurrence condition: after collapse, track revisits
        self._recurrence_count = self._recurrence_depth

        return cs

    def check_recurrence(self) -> bool:
        """Check if recurrence condition is satisfied.

        Speed 2026: After quantum collapse, the system must revisit the
        possibility space before generating conscious experience.
        This prevents premature convergence.
        """
        if self._recurrence_count > 0:
            self._recurrence_count -= 1
            return False
        return True

    def set_classical_state(self, hypothesis: dict[str, Any], confidence: float) -> ClassicalState:
        """Directly set a classical state (bypass quantum mode)."""
        cs = ClassicalState(
            selected_hypothesis=dict(hypothesis),
            confidence=confidence,
            collapsed_from_quantum=False,
        )
        self._classical_state = cs
        self._confidence = confidence
        self._mode = ModeType.CLASSICAL
        return cs

    @property
    def current_hypothesis(self) -> dict[str, Any]:
        """Get current best hypothesis regardless of mode."""
        if self._mode == ModeType.CLASSICAL and self._classical_state:
            return self._classical_state.selected_hypothesis
        if self._quantum_state:
            max_idx = max(range(len(self._quantum_state.amplitudes)), key=lambda i: self._quantum_state.amplitudes[i])  # type: ignore[operator]
            return self._quantum_state.hypotheses[max_idx]
        return {}

    @property
    def stats(self) -> dict[str, Any]:
        qs = self._quantum_state
        return {
            "mode": self._mode.value,
            "confidence": self._confidence,
            "threshold": self._confidence_threshold,
            "quantum_coherence": qs.coherence if qs else 0.0,
            "superposition_states": qs.superposition_count if qs else 0,
            "collapse_count": len(self._collapse_history),
            "recurrence_remaining": self._recurrence_count,
            "recurrence_satisfied": self.check_recurrence(),
        }
