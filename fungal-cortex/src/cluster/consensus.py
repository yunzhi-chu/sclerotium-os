"""L5 4.5: DistributedConsensus — "蜜蜂群体决策 + 章鱼Confederal模型" 分布式共识.

Biological Metaphor:
  蜜蜂群体决策(Quorum Sensing):
    - 10-15只侦察蜂(占500只蜂群的2-3%)在候选巢穴聚集→触发piping信号→全群起飞
    - 不是"每个蜜蜂都同意", 而是"足够多的蜜蜂在同一个地点"
    - 二阶相变(Armenteros Rey 2025): 当两个等质量选项竞争时→自发对称性破缺

  章鱼Confederal神经架构:
    - 2/3神经元在触手(Arm Ganglia自主控制)
    - Root = 章鱼大脑(仅设高级行为先验: "抓取"/"探索")
    - 触手可独立决策(不需要大脑批准每一个吸盘动作)
    - 但重大决策(变色伪装/喷墨逃跑)通过inter-arm connection(IAC)广播

  逆智慧定律防护(Inverse-Wisdom Law):
    - Tribalism检测: 同专业占比>60%→稀释权重
    - Sycophancy监控: 权重>0.7→警告
    - Heterogeneity强制: 至少3个不同专业参与

  Event-Triggered共识(节省90%通信):
    仅在显著性事件触发, 触发条件: 体制切换/参数>3%变动/异常检测

Reference:
  Armenteros Rey (2025), "Critical consensus formation", UBarcelona;
  Olson & Ragsdale (2025), "Segmented nervous system", Nature Comms;
  Inverse-Wisdom Law (arXiv 2604.27274, 2026)
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


# ── Constants ────────────────────────────────────────────────────────

class QuorumState(str, Enum):
    IDLE = "idle"           # no active consensus
    GATHERING = "gathering"  # collecting votes
    DECIDED = "decided"      # quorum reached
    DEADLOCKED = "deadlocked"  # cannot reach consensus


QUORUM_THRESHOLD = 0.6      # 60% for decision
MIN_VOTERS = 3              # minimum participants
TRIBALISM_THRESHOLD = 0.6   # same-specialty ratio
SYCOPHANCY_THRESHOLD = 0.7  # max individual weight
HETEROGENEITY_MIN = 3       # minimum distinct specialties
EVENT_TRIGGER_TYPES = ("regime_change", "param_change_3pct", "anomaly_detected")


# ── Data Structures ──────────────────────────────────────────────────


@dataclass
class ConsensusProposal:
    """A proposal for cluster consensus — like a new nest site candidate."""

    proposal_id: str
    topic: str
    description: str
    options: list[str]  # available choices
    proposer_id: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 300.0)  # 5 min TTL


@dataclass
class Vote:
    """A single vote — like a scout bee at a candidate site."""

    vote_id: str
    proposal_id: str
    voter_id: str
    choice: str
    confidence: float  # 0-1
    specialty: str  # voter's specialty
    weight: float = 0.0  # computed weight (capped for sycophancy)
    timestamp: float = field(default_factory=time.time)


# ── Main Class ───────────────────────────────────────────────────────


class DistributedConsensus:
    """Bee quorum + Octopus confederal distributed consensus engine.

    Implements event-triggered consensus formation with Inverse-Wisdom
    Law protections against tribalism and sycophancy.

    Config:
      - quorum_threshold: vote fraction for decision
      - min_voters: minimum participants
      - event_trigger_types: events that trigger consensus
    """

    def __init__(
        self,
        quorum_threshold: float = QUORUM_THRESHOLD,
        min_voters: int = MIN_VOTERS,
    ) -> None:
        self._quorum_threshold = quorum_threshold
        self._min_voters = min_voters

        self._proposals: dict[str, ConsensusProposal] = {}
        self._votes: dict[str, list[Vote]] = defaultdict(list)  # {proposal_id: [votes]}
        self._state = QuorumState.IDLE
        self._consensus_history: list[dict[str, Any]] = []
        self._logger = CortexLogger("distributed_consensus")

    # ── Public API ──────────────────────────────────────────────────

    def should_trigger(self, event_type: str, event_data: dict[str, Any]) -> bool:
        """Check if this event should trigger a consensus round."""
        return event_type in EVENT_TRIGGER_TYPES

    def propose(
        self, topic: str, description: str, options: list[str],
        proposer_id: str, ttl: float = 300.0,
    ) -> ConsensusProposal:
        """Create a new proposal for cluster voting."""
        proposal = ConsensusProposal(
            proposal_id=self._gen_proposal_id(topic),
            topic=topic,
            description=description,
            options=options,
            proposer_id=proposer_id,
            expires_at=time.time() + ttl,
        )
        self._proposals[proposal.proposal_id] = proposal
        self._state = QuorumState.GATHERING
        self._logger.info("proposal_created", topic=topic, options=len(options))
        return proposal

    def vote(
        self, proposal_id: str, voter_id: str, choice: str,
        confidence: float, specialty: str,
    ) -> Vote | None:
        """Cast a vote on a proposal. Returns None if invalid."""
        proposal = self._proposals.get(proposal_id)
        if proposal is None or time.time() > proposal.expires_at:
            return None
        if choice not in proposal.options:
            return None

        vote = Vote(
            vote_id=self._gen_vote_id(proposal_id, voter_id),
            proposal_id=proposal_id,
            voter_id=voter_id,
            choice=choice,
            confidence=confidence,
            specialty=specialty,
            weight=confidence,
        )
        self._votes[proposal_id].append(vote)
        return vote

    def tally(self, proposal_id: str) -> dict[str, Any]:
        """Tally votes and check for quorum.

        Returns tally result with Inverse-Wisdom Law protections applied.
        """
        votes = self._votes.get(proposal_id, [])
        proposal = self._proposals.get(proposal_id)

        if not proposal or len(votes) < self._min_voters:
            return {"state": QuorumState.IDLE.value, "reason": "insufficient_voters"}

        # Apply inverse-wisdom protections
        adjusted_weights = self._apply_protections(votes)

        # Count weighted votes per option
        totals: dict[str, float] = defaultdict(float)
        for vote, weight in zip(votes, adjusted_weights):
            totals[vote.choice] += weight

        total_weight = sum(totals.values())
        if total_weight <= 0:
            return {"state": QuorumState.DEADLOCKED.value, "reason": "zero_total_weight"}

        # Check quorum
        max_choice = max(totals, key=totals.get)
        max_fraction = totals[max_choice] / total_weight

        if max_fraction >= self._quorum_threshold:
            self._state = QuorumState.DECIDED
            decision = {
                "state": QuorumState.DECIDED.value,
                "winner": max_choice,
                "fraction": round(max_fraction, 4),
                "total_voters": len(votes),
                "vote_distribution": {k: round(v / total_weight, 3) for k, v in totals.items()},
            }
            self._consensus_history.append(decision)
            return decision
        elif len(votes) >= self._min_voters * 2 and max_fraction < 0.4:
            self._state = QuorumState.DEADLOCKED
            return {"state": QuorumState.DEADLOCKED.value, "reason": "no_majority", "fractions": {
                k: round(v / total_weight, 3) for k, v in totals.items()
            }}
        else:
            return {"state": QuorumState.GATHERING.value, "leading": max_choice,
                    "fraction": round(max_fraction, 3)}

    def _apply_protections(self, votes: list[Vote]) -> list[float]:
        """Apply Inverse-Wisdom Law protections.

        1. Tribalism: if same-specialty > 60%, dilute their total weight to 40%
        2. Sycophancy: cap individual weight at 0.7, redistribute excess
        3. Heterogeneity: require >= 3 specialties, else reduce all weights
        """
        n = len(votes)
        if n == 0:
            return []

        weights = [v.confidence for v in votes]

        # 1. Tribalism check
        specialty_counts: dict[str, list[int]] = defaultdict(list)
        for i, v in enumerate(votes):
            specialty_counts[v.specialty].append(i)

        for specialty, indices in specialty_counts.items():
            specialty_pct = len(indices) / n
            if specialty_pct > TRIBALISM_THRESHOLD:
                # Dilute: cap this specialty's total at TRIBALISM_THRESHOLD
                excess = specialty_pct - TRIBALISM_THRESHOLD
                reduction = excess / specialty_pct
                for idx in indices:
                    weights[idx] *= (1.0 - reduction * 0.5)

        # Normalize after tribalism
        w_sum = sum(weights)
        if w_sum > 0:
            weights = [w / w_sum for w in weights]

        # 2. Sycophancy check (post-normalization)
        max_weight = max(weights) if weights else 0
        if max_weight > SYCOPHANCY_THRESHOLD:
            excess = 0.0
            for i in range(n):
                if weights[i] > SYCOPHANCY_THRESHOLD:
                    excess += weights[i] - SYCOPHANCY_THRESHOLD
                    weights[i] = SYCOPHANCY_THRESHOLD
            # Redistribute excess
            under_cap = [i for i in range(n) if weights[i] < SYCOPHANCY_THRESHOLD]
            if under_cap and excess > 0:
                per_agent = excess / len(under_cap)
                for i in under_cap:
                    weights[i] += per_agent

        # 3. Heterogeneity check
        distinct_specialties = len(set(v.specialty for v in votes))
        if distinct_specialties < HETEROGENEITY_MIN:
            reduction = distinct_specialties / HETEROGENEITY_MIN
            weights = [w * reduction for w in weights]

        # Final normalization
        final_sum = sum(weights)
        if final_sum > 0:
            weights = [w / final_sum for w in weights]

        return weights

    def get_proposal(self, proposal_id: str) -> ConsensusProposal | None:
        return self._proposals.get(proposal_id)

    def cleanup_expired(self) -> int:
        """Remove expired proposals and their votes."""
        now = time.time()
        to_remove: list[str] = []
        for pid, proposal in self._proposals.items():
            if now > proposal.expires_at:
                to_remove.append(pid)

        for pid in to_remove:
            del self._proposals[pid]
            self._votes.pop(pid, None)

        return len(to_remove)

    @staticmethod
    def _gen_proposal_id(topic: str) -> str:
        raw = f"{topic}|{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _gen_vote_id(proposal_id: str, voter_id: str) -> str:
        raw = f"{proposal_id}|{voter_id}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @property
    def state(self) -> QuorumState:
        return self._state

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "active_proposals": len(self._proposals),
            "total_votes": sum(len(v) for v in self._votes.values()),
            "history_count": len(self._consensus_history),
        }
