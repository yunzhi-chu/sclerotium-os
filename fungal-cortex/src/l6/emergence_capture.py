"""L6 M7: EmergenceCapture — detect novel patterns from agent interactions.

Observes the continuous interaction stream between agents and detects:
- Independent discovery: ≥N agents find the same pattern independently
- Self-organized collaboration: agents converge on a behavior > T times
- Novel pattern emergence: previously unseen interaction topology

Inspired by ant colony path formation — no ant plans the path,
but the path emerges from thousands of individual decisions.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class InteractionEvent:
    """A single observed interaction between agents or with the field."""

    event_type: str
    source_agent_id: str
    target_agent_id: str = ""
    action: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class EmergencePattern:
    """A detected emergent pattern — candidate for crystallization."""

    id: str
    pattern_type: str  # "independent_discovery", "collaboration", "novel_topology"
    description: str
    involved_agents: list[str]
    evidence: dict[str, Any]
    confidence: float  # 0.0 to 1.0
    detection_count: int
    first_detected: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    crystallized: bool = False
    crystallized_skill_name: str = ""


class EmergenceCapture:
    """M7: Observes agent interaction stream and detects emergent patterns.

    Maintains a sliding window of interaction events (configurable size).
    Runs detection algorithms periodically to identify candidate patterns.
    """

    def __init__(
        self,
        stream_size: int = 10000,
        min_agents: int = 3,
        min_collaborations: int = 10,
    ) -> None:
        self._stream: list[InteractionEvent] = []
        self._stream_size = stream_size
        self._min_agents = min_agents
        self._min_collaborations = min_collaborations
        self._logger = CortexLogger("emergence_capture")

        # Detection state
        self._action_frequency: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))  # action → agent_id → count
        self._agent_interactions: dict[tuple[str, str], int] = {}  # (agent_a, agent_b) → count
        self._pattern_clusters: dict[str, list[str]] = defaultdict(list)  # pattern signature → agent_ids
        self._detected_patterns: dict[str, EmergencePattern] = {}

    def observe(self, event: InteractionEvent) -> None:
        """Record a single interaction event.

        Called by the event bus handler or directly by agents.
        """
        self._stream.append(event)
        if len(self._stream) > self._stream_size:
            self._stream = self._stream[-self._stream_size:]

        # Incrementally update frequency counts
        if event.action:
            self._action_frequency[event.action][event.source_agent_id] += 1

        if event.source_agent_id and event.target_agent_id:
            pair = tuple(sorted([event.source_agent_id, event.target_agent_id]))
            self._agent_interactions[pair] = self._agent_interactions.get(pair, 0) + 1

        # Cluster by action+data signature
        signature = self._compute_signature(event)
        if signature:
            if event.source_agent_id not in self._pattern_clusters[signature]:
                self._pattern_clusters[signature].append(event.source_agent_id)

    def observe_raw(self, event_type: str, source: str, action: str = "", data: dict[str, Any] | None = None) -> None:
        """Convenience method — construct and observe in one call."""
        event = InteractionEvent(
            event_type=event_type,
            source_agent_id=source,
            action=action,
            data=data or {},
        )
        self.observe(event)

    def _compute_signature(self, event: InteractionEvent) -> str:
        """Compute a pattern signature for clustering similar interactions."""
        parts = [event.event_type, event.action]
        if event.data:
            parts.append(str(sorted(event.data.keys())))
        return "::".join(filter(None, parts))

    async def _detect_emergence(self) -> list[EmergencePattern]:
        """Scan the interaction stream for emergent patterns.

        Returns newly detected patterns. Called periodically.
        """
        new_patterns: list[EmergencePattern] = []

        # 1. Independent discovery: ≥N agents doing same novel action
        for action, agents in self._action_frequency.items():
            agent_count = len(agents)
            total_actions = sum(agents.values())
            if agent_count >= self._min_agents and total_actions >= self._min_collaborations:
                pattern_id = f"indep_disc-{action}"
                if pattern_id not in self._detected_patterns:
                    confidence = min(agent_count / 10.0, 1.0) * min(total_actions / 50.0, 1.0)
                    pattern = EmergencePattern(
                        id=pattern_id,
                        pattern_type="independent_discovery",
                        description=f"≥{agent_count} agents independently discovered action '{action}' ({total_actions} occurrences)",
                        involved_agents=list(agents.keys()),
                        evidence={"action": action, "agent_count": agent_count, "total_actions": total_actions},
                        confidence=confidence,
                        detection_count=total_actions,
                    )
                    new_patterns.append(pattern)
                    self._detected_patterns[pattern_id] = pattern

        # 2. Self-organized collaboration: agent pairs interacting repeatedly
        for (a_id, b_id), count in self._agent_interactions.items():
            if count >= self._min_collaborations:
                pattern_id = f"collab-{a_id[:8]}-{b_id[:8]}"
                if pattern_id not in self._detected_patterns:
                    confidence = min(count / 50.0, 1.0)
                    pattern = EmergencePattern(
                        id=pattern_id,
                        pattern_type="collaboration",
                        description=f"Sustained collaboration between agents ({count} interactions)",
                        involved_agents=[a_id, b_id],
                        evidence={"agent_a": a_id, "agent_b": b_id, "interaction_count": count},
                        confidence=confidence,
                        detection_count=count,
                    )
                    new_patterns.append(pattern)
                    self._detected_patterns[pattern_id] = pattern

        # 3. Pattern clusters: groups doing the same thing
        for signature, agent_ids in self._pattern_clusters.items():
            if len(agent_ids) >= self._min_agents:
                pattern_id = f"cluster-{signature[:40]}"
                if pattern_id not in self._detected_patterns:
                    confidence = min(len(agent_ids) / 10.0, 1.0)
                    pattern = EmergencePattern(
                        id=pattern_id,
                        pattern_type="novel_topology",
                        description=f"Pattern cluster: {len(agent_ids)} agents sharing signature '{signature[:50]}'",
                        involved_agents=list(agent_ids),
                        evidence={"signature": signature, "agent_count": len(agent_ids)},
                        confidence=confidence,
                        detection_count=len(agent_ids),
                    )
                    new_patterns.append(pattern)
                    self._detected_patterns[pattern_id] = pattern

        return new_patterns

    def get_emergence_report(self) -> dict[str, Any]:
        """Generate a report of all detected emergent patterns."""
        patterns = list(self._detected_patterns.values())
        crystallized = [p for p in patterns if p.crystallized]
        pending = [p for p in patterns if not p.crystallized and p.confidence >= 0.6]
        low_conf = [p for p in patterns if not p.crystallized and p.confidence < 0.6]

        return {
            "total_patterns": len(patterns),
            "crystallized": len(crystallized),
            "pending_crystallization": len(pending),
            "low_confidence": len(low_conf),
            "stream_size": len(self._stream),
            "patterns": [
                {
                    "id": p.id,
                    "type": p.pattern_type,
                    "description": p.description,
                    "confidence": p.confidence,
                    "agent_count": len(p.involved_agents),
                    "crystallized": p.crystallized,
                }
                for p in sorted(patterns, key=lambda p: p.confidence, reverse=True)
            ],
        }

    def mark_crystallized(self, pattern_id: str, skill_name: str) -> None:
        """Mark a pattern as having been crystallized into a skill."""
        pattern = self._detected_patterns.get(pattern_id)
        if pattern:
            pattern.crystallized = True
            pattern.crystallized_skill_name = skill_name
            pattern.last_updated = time.time()

    @property
    def stream_len(self) -> int:
        return len(self._stream)

    @property
    def high_confidence_patterns(self) -> list[EmergencePattern]:
        """Patterns ready for crystallization (confidence >= 0.6)."""
        return [p for p in self._detected_patterns.values() if p.confidence >= 0.6 and not p.crystallized]
