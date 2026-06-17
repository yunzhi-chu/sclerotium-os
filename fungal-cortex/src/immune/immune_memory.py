"""Immune Memory — fast secondary response to known threats.

Inspired by immunological memory:
- First encounter → slow primary response (hours-days)
- Memory cells formed from successful response
- Second encounter → fast secondary response (< 1/10 of primary time)
- Long-lived plasma cells maintain antibody levels for years

MemoryCell stores: pathogen signature + successful response recipe + last seen time.
Retention: 90 days (configurable). Re-encounter resets the clock.
"""

from __future__ import annotations

import time
from typing import Any


class MemoryCell:
    """A single immune memory cell — stores one known threat pattern."""

    def __init__(self, threat_id: str, signature: list[float], response: dict[str, Any]) -> None:
        self.threat_id = threat_id
        self.signature = list(signature)
        self.response = dict(response)
        self.created_at = time.time()
        self.last_seen = time.time()
        self.encounter_count = 1
        self.response_latency_ms: float = 0.0  # Track for secondary response speed

    def re_encounter(self, new_signature: list[float] | None = None) -> None:
        """Record re-encounter with this threat (resets decay clock)."""
        self.last_seen = time.time()
        self.encounter_count += 1
        if new_signature:
            # Exponential moving average to adapt to drifting threats
            alpha = 0.3
            self.signature = [
                alpha * ns + (1 - alpha) * os
                for ns, os in zip(new_signature, self.signature)
            ]

    def secondary_response(self) -> dict[str, Any]:
        """Get the cached response for known threat (fast path).

        Secondary response is < 1/10 of primary response time.
        """
        return {
            **self.response,
            "memory_cell_id": self.threat_id,
            "encounter_count": self.encounter_count,
            "is_secondary_response": True,
            "estimated_latency_ms": max(1.0, self.response_latency_ms * 0.08),
        }

    def is_expired(self, retention_days: float = 90.0) -> bool:
        """Check if memory has decayed beyond retention period."""
        age_days = (time.time() - self.last_seen) / 86400.0
        return age_days > retention_days

    @property
    def age_days(self) -> float:
        return (time.time() - self.created_at) / 86400.0

    @property
    def days_since_last_seen(self) -> float:
        return (time.time() - self.last_seen) / 86400.0


class ImmuneMemory:
    """Immune memory bank — stores known threats for fast secondary response.

    Key principle:
    - Primary response: full detection pipeline (seconds-minutes)
    - Secondary response: memory lookup (< 1/10 primary time)
    - Retention: 90 days. Re-encounter resets clock.
    - Cosine similarity matching for threat recognition.
    """

    def __init__(self, retention_days: int = 90, similarity_threshold: float = 0.85) -> None:
        self._retention_days = retention_days
        self._similarity_threshold = similarity_threshold
        self._memory_cells: dict[str, MemoryCell] = {}
        self._purge_count = 0

    def store(self, threat_id: str, signature: list[float], response: dict[str, Any]) -> MemoryCell:
        """Store a new threat memory or update existing.

        Primary response: record what we learned for next time.
        """
        if threat_id in self._memory_cells:
            cell = self._memory_cells[threat_id]
            cell.re_encounter(signature)
            return cell

        cell = MemoryCell(threat_id, signature, response)
        self._memory_cells[threat_id] = cell
        return cell

    def recall(self, signature: list[float]) -> dict[str, Any] | None:
        """Try to recall a known threat by signature similarity (fast path).

        Returns cached response if match found, None otherwise.
        This is the secondary response — < 1/10 of primary response time.
        """
        best_match = None
        best_similarity = 0.0

        for cell_id, cell in self._memory_cells.items():
            if cell.is_expired(self._retention_days):
                continue
            sim = self._cosine_similarity(signature, cell.signature)
            if sim > best_similarity and sim >= self._similarity_threshold:
                best_similarity = sim
                best_match = cell

        if best_match is None:
            return None

        best_match.re_encounter(signature)
        return best_match.secondary_response()

    def query(self, threat_id: str) -> MemoryCell | None:
        """Direct lookup by threat ID."""
        cell = self._memory_cells.get(threat_id)
        if cell and cell.is_expired(self._retention_days):
            return None
        return cell

    def forget(self, threat_id: str) -> bool:
        """Explicitly forget a threat (manual override)."""
        if threat_id in self._memory_cells:
            del self._memory_cells[threat_id]
            return True
        return False

    def purge_expired(self) -> int:
        """Remove all expired memory cells."""
        expired = [
            tid for tid, cell in self._memory_cells.items()
            if cell.is_expired(self._retention_days)
        ]
        for tid in expired:
            del self._memory_cells[tid]
        self._purge_count += len(expired)
        return len(expired)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b) or len(a) == 0:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x ** 2 for x in a) ** 0.5
        norm_b = sum(y ** 2 for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @property
    def cell_count(self) -> int:
        return len(self._memory_cells)

    @property
    def stats(self) -> dict[str, Any]:
        cells = list(self._memory_cells.values())
        active = [c for c in cells if not c.is_expired(self._retention_days)]
        expired = [c for c in cells if c.is_expired(self._retention_days)]

        return {
            "total_cells": len(cells),
            "active_cells": len(active),
            "expired_cells": len(expired),
            "total_encounters": sum(c.encounter_count for c in cells),
            "avg_encounters": sum(c.encounter_count for c in cells) / max(len(cells), 1),
            "retention_days": self._retention_days,
            "similarity_threshold": self._similarity_threshold,
            "purge_count": self._purge_count,
            "oldest_cell_days": max((c.age_days for c in cells), default=0.0),
        }
