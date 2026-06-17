"""Mechanism ⑱: Emergence Crystallizer — pattern → skill crystallization.

Inspired by crystal formation from supersaturated solutions:
- Emergence patterns are 'dissolved' in the interaction stream
- When confidence crosses threshold (≥0.6), spontaneous 'nucleation' occurs
- The crystallized pattern becomes a new Skill via M2 AbilityCreationFactory

Based on:
- Self-organized criticality (Bak): power-law distribution of emergence events
- Synergetics slaving principle (Haken): slow order parameters enslave fast variables
- Non-equilibrium phase transitions: symmetry breaking at critical thresholds
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from src.core.event_bus import EventBus
from src.l6.ability_factory import AbilityCreationFactory, CreationSpec
from src.l6.emergence_capture import EmergenceCapture, EmergencePattern
from src.utils.logging import CortexLogger


@dataclass
class CrystalRecord:
    """Record of a single crystallization event."""

    pattern_id: str
    pattern_type: str
    confidence: float
    skill_name: str
    crystallized_at: float = field(default_factory=time.time)
    success: bool = True
    error_message: str = ""


class EmergenceCrystallizer:
    """⑱: Transforms emergent patterns into formal skills.

    Operation:
    1. Poll EmergenceCapture for patterns with confidence ≥ threshold (default 0.6)
    2. Build a CreationSpec from the pattern
    3. Submit to M2 AbilityCreationFactory
    4. Record the crystallization

    The 'slaving principle' in action: the emergent pattern (order parameter)
    'enslaves' the skill creation machinery to materialize it.
    """

    def __init__(
        self,
        emergence_capture: EmergenceCapture,
        ability_factory: AbilityCreationFactory,
        event_bus: EventBus | None = None,
        confidence_threshold: float = 0.6,
        max_crystallizations_per_cycle: int = 5,
    ) -> None:
        self._emergence = emergence_capture
        self._factory = ability_factory
        self._event_bus = event_bus
        self.confidence_threshold = confidence_threshold
        self.max_per_cycle = max_crystallizations_per_cycle
        self._logger = CortexLogger("crystallizer")
        self._records: list[CrystalRecord] = []
        self._total_crystallized = 0

    async def crystallize(self, pattern: EmergencePattern) -> Optional[CrystalRecord]:
        """Crystallize a single emergence pattern into a skill.

        Returns CrystalRecord on success, None if confidence too low.
        """
        if pattern.confidence < self.confidence_threshold:
            self._logger.info("crystallize_skipped_low_confidence",
                              pattern_id=pattern.id,
                              confidence=pattern.confidence)
            return None

        if pattern.crystallized:
            self._logger.info("crystallize_skipped_already_done", pattern_id=pattern.id)
            return None

        # Build creation spec from pattern
        spec = self._pattern_to_spec(pattern)

        # Submit to ability factory
        task = await self._factory.create(spec)
        success = task.status.value == "complete"
        skill_name = task.registered_skill_name if success else ""

        record = CrystalRecord(
            pattern_id=pattern.id,
            pattern_type=pattern.pattern_type,
            confidence=pattern.confidence,
            skill_name=skill_name,
            success=success,
            error_message=task.error_message if not success else "",
        )
        self._records.append(record)

        if success:
            self._total_crystallized += 1
            self._emergence.mark_crystallized(pattern.id, skill_name)
            self._logger.info("crystallized",
                              pattern_id=pattern.id[:20],
                              skill_name=skill_name,
                              confidence=f"{pattern.confidence:.2f}")
            if self._event_bus:
                await self._event_bus.publish_nowait("l6.crystallized", {
                    "pattern_id": pattern.id,
                    "pattern_type": pattern.pattern_type,
                    "skill_name": skill_name,
                    "confidence": pattern.confidence,
                })
        else:
            self._logger.error("crystallize_failed",
                               pattern_id=pattern.id[:20],
                               error=task.error_message)

        return record

    def _pattern_to_spec(self, pattern: EmergencePattern) -> CreationSpec:
        """Convert an emergence pattern into a skill creation specification."""
        category_map = {
            "independent_discovery": "strategy",
            "collaboration": "core",
            "novel_topology": "utility",
        }
        return CreationSpec(
            name=f"emerged-{pattern.pattern_type}-{pattern.id[:12]}",
            category=category_map.get(pattern.pattern_type, "utility"),
            description=pattern.description,
            keywords=self._extract_keywords(pattern),
            dependencies=[],
        )

    @staticmethod
    def _extract_keywords(pattern: EmergencePattern) -> list[str]:
        """Extract relevant keywords from pattern evidence."""
        keywords: list[str] = []
        for key, value in pattern.evidence.items():
            if isinstance(value, str) and len(value) < 30:
                keywords.append(value)
            elif key in ("action", "signature"):
                keywords.append(str(value)[:30])
        return keywords[:10]

    async def run_cycle(self) -> dict[str, Any]:
        """Run one full crystallization cycle.

        Scans for high-confidence patterns and attempts to crystallize
        up to max_per_cycle of them.
        """
        candidates = self._emergence.high_confidence_patterns
        candidates.sort(key=lambda p: p.confidence, reverse=True)
        candidates = candidates[:self.max_per_cycle]

        results = {"attempted": len(candidates), "crystallized": 0, "failed": 0, "skipped": 0, "records": []}

        for pattern in candidates:
            record = await self.crystallize(pattern)
            if record is None:
                results["skipped"] += 1
            elif record.success:
                results["crystallized"] += 1
                results["records"].append(record.pattern_id)
            else:
                results["failed"] += 1

        return results

    def get_report(self) -> dict[str, Any]:
        """Generate a crystallization report."""
        emergence_report = self._emergence.get_emergence_report()
        return {
            "total_crystallized": self._total_crystallized,
            "records_count": len(self._records),
            "confidence_threshold": self.confidence_threshold,
            "emergence": emergence_report,
            "recent_crystallizations": [
                {"pattern_id": r.pattern_id[:20], "skill_name": r.skill_name, "confidence": r.confidence, "success": r.success}
                for r in self._records[-20:]
            ],
        }

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_crystallized": self._total_crystallized,
            "total_records": len(self._records),
            "success_rate": sum(1 for r in self._records if r.success) / max(len(self._records), 1),
            "avg_confidence": sum(r.confidence for r in self._records) / max(len(self._records), 1),
        }
