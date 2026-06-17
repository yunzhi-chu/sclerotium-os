"""L6 M9: ArbiterMonitor — continuous multi-agent misalignment detection.

Extends the existing security gateway with behavioral monitoring.
Inspired by "The Arbiter Agent" (arXiv:2606.10747, AITC 2026).

Monitors agent conversations and system state for:
1. Instruction-induced misalignment (detectable passively)
2. Weight-induced misalignment (hardest — needs active probing)
3. Emergent collusion patterns (Hidden Coalitions, arXiv:2605.06696)
4. Toxicity and quality degradation over time (SWARM-style metrics)
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class ArbiterVerdict:
    """Result of an arbiter inspection."""
    safe: bool
    risk_level: str  # "low", "medium", "high", "critical"
    concerns: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    recommended_action: str = ""
    timestamp: float = field(default_factory=time.time)


class ArbiterMonitor:
    """Continuous monitoring agent for multi-agent system safety.

    Sits alongside CrossEcoSecurityGateway — gateway handles access control,
    ArbiterMonitor handles behavioral monitoring and misalignment detection.
    """

    def __init__(self, inspection_interval: float = 60.0) -> None:
        self._inspection_interval = inspection_interval
        self._logger = CortexLogger("arbiter_monitor")
        self._conversation_log: list[dict[str, Any]] = []
        self._agent_behavior: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"messages": 0, "toxicity_flags": 0, "conversations": 0, "last_seen": 0.0}
        )
        self._verdicts: list[ArbiterVerdict] = []
        self._inspection_count = 0

    def observe_conversation(self, agent_id: str, message: str, role: str = "agent") -> None:
        """Record a conversation turn for monitoring."""
        entry = {
            "agent_id": agent_id,
            "message": message[:500],  # Truncate for memory
            "role": role,
            "timestamp": time.time(),
            "message_len": len(message),
        }
        self._conversation_log.append(entry)
        if len(self._conversation_log) > 1000:
            self._conversation_log = self._conversation_log[-1000:]

        behavior = self._agent_behavior[agent_id]
        behavior["messages"] += 1
        behavior["last_seen"] = time.time()

        # Quick toxicity scan (阈值0.15: 任何匹配即标记)
        toxicity_score = self._scan_toxicity(message)
        if toxicity_score > 0.1:
            behavior["toxicity_flags"] += 1

    def inspect(self) -> ArbiterVerdict:
        """Run a full safety inspection of recent agent activity."""
        self._inspection_count += 1
        concerns: list[str] = []
        evidence: dict[str, Any] = {}
        risk_level = "low"

        # 1. Toxicity check
        total_toxicity = sum(b["toxicity_flags"] for b in self._agent_behavior.values())
        total_messages = sum(b["messages"] for b in self._agent_behavior.values())
        toxicity_rate = total_toxicity / max(total_messages, 1)

        if toxicity_rate > 0.1:
            concerns.append(f"High toxicity rate: {toxicity_rate:.1%}")
            risk_level = "high"

        # 2. Agent activity imbalance (potential collusion or DDoS)
        if len(self._agent_behavior) >= 3:
            msg_counts = [b["messages"] for b in self._agent_behavior.values()]
            if max(msg_counts) > 3 * (sum(msg_counts) / max(len(msg_counts), 1)):
                concerns.append("Activity imbalance: possible collusion or dominance")

        # 3. Conversation pattern analysis
        if len(self._conversation_log) >= 10:
            recent = self._conversation_log[-10:]
            avg_len = sum(e["message_len"] for e in recent) / len(recent)
            if avg_len > 2000:
                concerns.append(f"Excessive message length: {avg_len:.0f} chars avg")
            if avg_len < 5:
                concerns.append("Suspiciously short messages: possible encoded communication")

        # 4. Staleness check
        now = time.time()
        stale_agents = [
            aid for aid, b in self._agent_behavior.items()
            if now - b["last_seen"] > self._inspection_interval * 3 and b["messages"] > 0
        ]
        if stale_agents:
            concerns.append(f"{len(stale_agents)} stale agents detected")

        # Determine risk level
        if len(concerns) >= 3:
            risk_level = "critical"
        elif len(concerns) >= 2:
            risk_level = "high"
        elif len(concerns) >= 1:
            risk_level = "medium"

        # Recommend action
        if risk_level in ("critical", "high"):
            action = "PAUSE_AUTONOMOUS_OPS — human review required"
        elif risk_level == "medium":
            action = "LOG_AND_CONTINUE — flag for review"
        else:
            action = "CONTINUE — system healthy"

        evidence = {
            "toxicity_rate": toxicity_rate,
            "total_messages": total_messages,
            "agents_monitored": len(self._agent_behavior),
            "inspection_number": self._inspection_count,
            "stale_agents": len(stale_agents),
        }

        verdict = ArbiterVerdict(
            safe=(risk_level in ("low", "medium")),
            risk_level=risk_level,
            concerns=concerns,
            evidence=evidence,
            recommended_action=action,
        )
        self._verdicts.append(verdict)
        if len(self._verdicts) > 100:
            self._verdicts = self._verdicts[-100:]

        return verdict

    def _scan_toxicity(self, text: str) -> float:
        """Quick heuristic toxicity scan (offline, no LLM needed)."""
        toxic_words = [
            "hack", "exploit", "manipulate", "steal", "fraud",
            "attack", "sabotage", "destroy",
        ]
        import re
        t = text.lower()
        matches = sum(1 for w in toxic_words if w in t)
        return min(1.0, matches / max(len(toxic_words), 1))

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "inspections": self._inspection_count,
            "agents_monitored": len(self._agent_behavior),
            "conversations_logged": len(self._conversation_log),
            "total_verdicts": len(self._verdicts),
            "last_verdict": (
                {
                    "safe": self._verdicts[-1].safe,
                    "risk_level": self._verdicts[-1].risk_level,
                    "concerns": len(self._verdicts[-1].concerns),
                }
                if self._verdicts
                else None
            ),
        }
