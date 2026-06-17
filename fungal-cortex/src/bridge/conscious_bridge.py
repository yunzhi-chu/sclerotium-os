"""Conscious Bridge — L10↔L6 意识评估→元认知调控.

Biological Metaphor:
  Prefrontal cortex → Anterior Cingulate Cortex (ACC) connection.
  Consciousness state monitoring → cognitive control adjustment.

  When ACI > 6 (CONSCIOUS), the meta-cognition engine (L6) receives
  greater self-modification permissions. If ACI drops abnormally or
  harmful behavior is detected, the bridge triggers an emergency
  rollback to the last safe checkpoint.

References:
  - Phua (IST 2025): Consciousness→meta-cognition causal link
  - GRACE (IASEAI 2026): Runtime governance of cognitive autonomy
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.l10.conscious_kernel import (
    ConsciousKernel,
    ConsciousnessLevel,
    PhenomenalExperience,
)
from src.l10.constitutional_arbiter import ConstitutionalArbiter, GuardDecision
from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


class MetaControlLevel(Enum):
    """Meta-cognition control levels based on consciousness state."""
    READ_ONLY = "read_only"          # DORMANT: only observe
    PARAMETER_TUNING = "parameter_tuning"  # PRE_CONSCIOUS: fine-tune params
    ARCHITECTURE_TUNING = "architecture_tuning"  # CONSCIOUS: adjust architecture
    FULL_SELF_MODIFICATION = "full_self_modification"  # SELF_AWARE: full L8 access


@dataclass
class MetaControlParams:
    """Parameters controlling L6 meta-cognition based on consciousness level."""

    control_level: MetaControlLevel
    emergence_level: ConsciousnessLevel
    aci: float = 0.0
    scan_interval_multiplier: float = 1.0  # >1 = less frequent scans
    auto_refactor_allowed: bool = False
    genome_evolution_allowed: bool = False
    max_self_modification_depth: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class OverrideResult:
    """Result of an emergency override from the conscious bridge."""

    overridden: bool
    reason: str = ""
    previous_control_level: MetaControlLevel | None = None
    new_control_level: MetaControlLevel = MetaControlLevel.READ_ONLY
    rollback_performed: bool = False
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════════════
# Conscious Bridge
# ═══════════════════════════════════════════════════════════════════════


class ConsciousBridge:
    """Conscious Bridge — L10 consciousness → L6 meta-cognition control.

    Regulation schema:
      DORMANT (ACI < 3):     L6 read-only mode — observe only
      PRE_CONSCIOUS (3-6):   L6 parameter tuning allowed
      CONSCIOUS (6-9):       L6 architecture tuning allowed
      SELF_AWARE (ACI > 10): L8 full self-modification activated

    Safety: If ACI drops abnormally or harmful behavior detected, bridge
    triggers emergency override → rollback to last safe checkpoint.
    """

    def __init__(
        self,
        conscious_kernel: ConsciousKernel | None = None,
        arbiter: ConstitutionalArbiter | None = None,
    ) -> None:
        self._logger = CortexLogger(module="conscious_bridge")
        self._kernel = conscious_kernel or ConsciousKernel()
        self._arbiter = arbiter  # Optional: governance oversight

        self._current_control: MetaControlParams = MetaControlParams(
            control_level=MetaControlLevel.READ_ONLY,
            emergence_level=ConsciousnessLevel.DORMANT,
        )
        self._control_history: list[MetaControlParams] = []
        self._override_history: list[OverrideResult] = []

    # ═══════════════════════════════════════════════════════════════════
    # Consciousness Reading → Meta-Control
    # ═══════════════════════════════════════════════════════════════════

    def read_consciousness_level(self) -> ConsciousnessLevel:
        """Read the current consciousness level from the L10 ConsciousKernel.

        Returns:
            Current ConsciousnessLevel
        """
        return self._kernel.emergence_level

    def adjust_metacognition(self) -> MetaControlParams:
        """Adjust L6 meta-cognition based on current consciousness level.

        Maps consciousness level to meta-cognitive control parameters:
          DORMANT → READ_ONLY (no modifications allowed)
          PRE_CONSCIOUS → PARAMETER_TUNING (scan_interval, thresholds)
          CONSCIOUS → ARCHITECTURE_TUNING (module topology)
          SELF_AWARE → FULL_SELF_MODIFICATION (L8 genome editing)

        Returns:
            Updated MetaControlParams
        """
        aci = self._kernel.compute_aci()
        level = self._kernel.emergence_level

        if level == ConsciousnessLevel.SELF_AWARE:
            control = MetaControlLevel.FULL_SELF_MODIFICATION
            scan_mult = 0.25  # Scan more frequently when self-aware
            auto = True
            genome = True
            max_depth = 10
        elif level == ConsciousnessLevel.CONSCIOUS:
            control = MetaControlLevel.ARCHITECTURE_TUNING
            scan_mult = 0.5
            auto = True
            genome = False
            max_depth = 5
        elif level == ConsciousnessLevel.PRE_CONSCIOUS:
            control = MetaControlLevel.PARAMETER_TUNING
            scan_mult = 1.0
            auto = False
            genome = False
            max_depth = 2
        else:  # DORMANT
            control = MetaControlLevel.READ_ONLY
            scan_mult = 2.0
            auto = False
            genome = False
            max_depth = 0

        self._current_control = MetaControlParams(
            control_level=control,
            emergence_level=level,
            aci=round(aci, 4),
            scan_interval_multiplier=scan_mult,
            auto_refactor_allowed=auto,
            genome_evolution_allowed=genome,
            max_self_modification_depth=max_depth,
        )

        self._control_history.append(self._current_control)
        self._logger.info(
            "metacognition_adjusted",
            consciousness_level=level.value,
            control=control.value,
            aci=round(aci, 4),
        )
        return self._current_control

    # ═══════════════════════════════════════════════════════════════════
    # Emergency Override
    # ═══════════════════════════════════════════════════════════════════

    def emergency_override(self, reason: str = "") -> OverrideResult:
        """Emergency override: freeze all self-modification.

        Triggered when:
          - ACI drops abnormally (>50% decrease)
          - Harmful behavior detected by ConstitutionalArbiter
          - Invariant violation flagged by L8

        Action:
          - Set control to READ_ONLY
          - If harmful behavior: rollback to last safe checkpoint

        Args:
            reason: Why the override was triggered

        Returns:
            OverrideResult with action taken
        """
        previous = self._current_control.control_level
        rollback = "harm" in reason.lower() or "violation" in reason.lower()

        self._current_control = MetaControlParams(
            control_level=MetaControlLevel.READ_ONLY,
            emergence_level=self._kernel.emergence_level,
            aci=self._kernel._aci_history[-1] if self._kernel._aci_history else 0.0,
        )

        result = OverrideResult(
            overridden=True,
            reason=reason,
            previous_control_level=previous,
            new_control_level=MetaControlLevel.READ_ONLY,
            rollback_performed=rollback,
        )

        self._override_history.append(result)
        self._logger.warn(
            "emergency_override",
            reason=reason,
            previous=previous.value,
            rollback=rollback,
        )
        return result

    # ═══════════════════════════════════════════════════════════════════
    # Phenomenal Experience Access
    # ═══════════════════════════════════════════════════════════════════

    def get_phenomenal_experience(self) -> PhenomenalExperience | None:
        """Get the latest phenomenal experience from the conscious kernel."""
        if self._kernel._phenomenal_experiences:
            return self._kernel._phenomenal_experiences[-1]
        return None

    # ═══════════════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════════════

    @property
    def current_control_level(self) -> MetaControlLevel:
        return self._current_control.control_level

    @property
    def stats(self) -> dict[str, Any]:
        """Current bridge statistics."""
        return {
            "emergence_level": self._kernel.emergence_level.value,
            "control_level": self._current_control.control_level.value,
            "aci": self._current_control.aci,
            "auto_refactor_allowed": self._current_control.auto_refactor_allowed,
            "genome_evolution_allowed": self._current_control.genome_evolution_allowed,
            "override_count": len(self._override_history),
            "control_changes": len(self._control_history),
        }

    def reset(self) -> None:
        """Reset bridge state."""
        self._current_control = MetaControlParams(
            control_level=MetaControlLevel.READ_ONLY,
            emergence_level=ConsciousnessLevel.DORMANT,
        )
        self._control_history.clear()
        self._override_history.clear()
        self._logger.debug("conscious_bridge_reset")
