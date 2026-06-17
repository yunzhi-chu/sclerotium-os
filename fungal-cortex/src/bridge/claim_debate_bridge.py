"""Claim Debate Bridge — Market-of-Claims: BULL vs BEAR atomic debate.

The claim debate bridge implements the "Market of Claims" mechanism where:
- BULL agents argue FOR a strategy/indicator/investment thesis
- BEAR agents argue AGAINST it
- Both occupy the same position on the Stigmergy field (competitive excretion)
- The winner is determined by evidence weight + argument coherence
- Winning claims gain field strength; losing claims are excreted (decay)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class DebatePosition(Enum):
    BULL = "bull"  # Argues FOR the claim
    BEAR = "bear"  # Argues AGAINST the claim


class ClaimStatus(Enum):
    OPEN = "open"  # Claim is being debated
    RESOLVED_BULL = "resolved_bull"  # BULL position won
    RESOLVED_BEAR = "resolved_bear"  # BEAR position won
    STALEMATE = "stalemate"  # No clear winner
    EXCRETED = "excreted"  # Claim removed from field (both weak)


@dataclass
class Argument:
    """A single argument in a claim debate."""

    position: DebatePosition
    content: str
    evidence_strength: float  # 0-1, higher = stronger evidence
    citations: list[str] = field(default_factory=list)
    agent_id: str = ""
    round_number: int = 1


@dataclass
class Claim:
    """A claim being debated on the Stigmergy field."""

    claim_id: str
    topic: str
    description: str = ""
    bull_arguments: list[Argument] = field(default_factory=list)
    bear_arguments: list[Argument] = field(default_factory=list)
    status: ClaimStatus = ClaimStatus.OPEN
    bull_score: float = 0.0
    bear_score: float = 0.0
    field_strength: float = 0.5  # Initial strength on Stigmergy field
    max_rounds: int = 5
    current_round: int = 0
    resolved_at: float = 0.0

    @property
    def winner(self) -> DebatePosition | None:
        if self.status == ClaimStatus.RESOLVED_BULL:
            return DebatePosition.BULL
        if self.status == ClaimStatus.RESOLVED_BEAR:
            return DebatePosition.BEAR
        return None

    @property
    def confidence_margin(self) -> float:
        """Absolute difference between bull and bear scores."""
        return abs(self.bull_score - self.bear_score)


class ClaimDebateBridge:
    """Market-of-Claims debate bridge.

    The debate process:
    1. A claim is placed on the Stigmergy field (initial strength = 0.5)
    2. BULL and BEAR agents take positions on the SAME field location
    3. Each round: both sides submit arguments with evidence
    4. Scoring: evidence_strength × citation_count / (1 + round)
    5. After max_rounds: winner determined by score ratio
    6. Winner's field strength increases; loser's decays (competitive excretion)
    7. Stalemate → both decay (excretion)

    Claims with field_strength > 0.8 are "established knowledge"
    Claims with field_strength < 0.2 are "excreted" (removed from field)
    """

    def __init__(self, max_concurrent_claims: int = 10) -> None:
        self._max_claims = max_concurrent_claims
        self._claims: dict[str, Claim] = {}
        self._logger = CortexLogger("claim_debate")
        self._total_debates = 0
        self._resolved_count = 0

    def create_claim(self, topic: str, description: str = "", max_rounds: int = 5) -> Claim:
        """Create a new claim for debate."""
        import time
        claim_id = f"claim-{self._total_debates + 1:04d}"
        claim = Claim(
            claim_id=claim_id,
            topic=topic,
            description=description,
            max_rounds=max_rounds,
        )
        self._claims[claim_id] = claim
        self._total_debates += 1
        self._logger.info("claim_created", claim_id=claim_id, topic=topic)
        return claim

    def submit_argument(self, claim_id: str, position: DebatePosition, content: str, evidence_strength: float, citations: list[str] | None = None, agent_id: str = "") -> Argument:
        """Submit an argument to an ongoing debate."""
        claim = self._claims.get(claim_id)
        if claim is None:
            raise ValueError(f"Claim {claim_id} not found")
        if claim.status != ClaimStatus.OPEN:
            raise ValueError(f"Claim {claim_id} is already {claim.status.value}")

        arg = Argument(
            position=position,
            content=content,
            evidence_strength=evidence_strength,
            citations=citations or [],
            agent_id=agent_id,
            round_number=claim.current_round + 1,
        )

        if position == DebatePosition.BULL:
            claim.bull_arguments.append(arg)
            self._update_bull_score(claim, arg)
        else:
            claim.bear_arguments.append(arg)
            self._update_bear_score(claim, arg)

        return arg

    def advance_round(self, claim_id: str) -> ClaimStatus | None:
        """Advance to the next debate round. Returns new status if debate concludes."""
        claim = self._claims.get(claim_id)
        if claim is None or claim.status != ClaimStatus.OPEN:
            return claim.status if claim else None

        claim.current_round += 1

        if claim.current_round >= claim.max_rounds:
            return self._resolve(claim_id)

        return None

    def _resolve(self, claim_id: str) -> ClaimStatus:
        """Resolve a claim debate after all rounds complete."""
        claim = self._claims[claim_id]
        ratio = claim.bull_score / max(claim.bear_score, 1e-10)

        if ratio > 1.5:
            claim.status = ClaimStatus.RESOLVED_BULL
            claim.field_strength = min(1.0, claim.field_strength + 0.3)
        elif ratio < 0.67:
            claim.status = ClaimStatus.RESOLVED_BEAR
            claim.field_strength = max(0.0, claim.field_strength - 0.3)
        else:
            claim.status = ClaimStatus.STALEMATE
            claim.field_strength *= 0.5  # Both decay

        if claim.field_strength < 0.2:
            claim.status = ClaimStatus.EXCRETED

        import time
        claim.resolved_at = time.time()
        self._resolved_count += 1
        self._logger.info("claim_resolved", claim_id=claim_id, status=claim.status.value, field_strength=round(claim.field_strength, 3))
        return claim.status

    def _update_bull_score(self, claim: Claim, arg: Argument) -> None:
        """Update BULL score based on a new argument."""
        weight = arg.evidence_strength * (1.0 + 0.1 * len(arg.citations)) / (1.0 + claim.current_round * 0.2)
        claim.bull_score += weight

    def _update_bear_score(self, claim: Claim, arg: Argument) -> None:
        """Update BEAR score based on a new argument."""
        weight = arg.evidence_strength * (1.0 + 0.1 * len(arg.citations)) / (1.0 + claim.current_round * 0.2)
        claim.bear_score += weight

    def get_open_claims(self) -> list[Claim]:
        """Get all currently open claims."""
        return [c for c in self._claims.values() if c.status == ClaimStatus.OPEN]

    def get_established_claims(self) -> list[Claim]:
        """Get claims that have been established (field_strength > 0.8)."""
        return [c for c in self._claims.values() if c.field_strength > 0.8 and c.status != ClaimStatus.EXCRETED]

    def get_claim(self, claim_id: str) -> Claim | None:
        return self._claims.get(claim_id)

    async def submit_arguments_batch(
        self,
        claim_id: str,
        bull_args: list[tuple[str, float, list[str] | None]],
        bear_args: list[tuple[str, float, list[str] | None]],
    ) -> tuple[list[Argument], list[Argument]]:
        """★批量异步提交BULL+BEAR论点 — 并行处理双方论证。

        Args:
            claim_id: Target claim
            bull_args: List of (content, evidence_strength, citations) for BULL
            bear_args: List of (content, evidence_strength, citations) for BEAR

        Returns:
            (bull_arguments, bear_arguments) submitted
        """
        bull_results = [
            self.submit_argument(
                claim_id, DebatePosition.BULL, content, strength, citations or [],
                agent_id=f"bull-batch-{i}",
            )
            for i, (content, strength, citations) in enumerate(bull_args)
        ]
        bear_results = [
            self.submit_argument(
                claim_id, DebatePosition.BEAR, content, strength, citations or [],
                agent_id=f"bear-batch-{i}",
            )
            for i, (content, strength, citations) in enumerate(bear_args)
        ]
        return bull_results, bear_results

    async def debate_with_llm_batch(
        self,
        claim_id: str,
        bull_callback,
        bear_callback,
        rounds: int = 5,
    ) -> Claim | None:
        """★批量LLM辩论: 每轮BULL+BEAR并行调用LLM，延迟减半。

        Args:
            claim_id: Target claim
            bull_callback: Async function(topic, round) -> str for BULL argument
            bear_callback: Async function(topic, round) -> str for BEAR argument
            rounds: Number of debate rounds

        Returns:
            Resolved claim or None
        """
        import asyncio as _asyncio

        claim = self._claims.get(claim_id)
        if claim is None:
            return None

        topic = claim.topic
        for round_num in range(rounds):
            if claim.status != ClaimStatus.OPEN:
                break

            # ★并行调用BULL和BEAR (兼容同步和异步回调)
            async def _call_bull():
                result = bull_callback(topic, round_num + 1)
                if _asyncio.iscoroutine(result):
                    return await result
                return result

            async def _call_bear():
                result = bear_callback(topic, round_num + 1)
                if _asyncio.iscoroutine(result):
                    return await result
                return result

            bull_content, bear_content = await _asyncio.gather(
                _call_bull(), _call_bear(),
            )

            self.submit_argument(
                claim_id, DebatePosition.BULL, bull_content,
                evidence_strength=0.6 + round_num * 0.05,
                citations=["market_data"], agent_id=f"bull-{round_num}",
            )
            self.submit_argument(
                claim_id, DebatePosition.BEAR, bear_content,
                evidence_strength=0.55 + round_num * 0.05,
                citations=["risk_metrics"], agent_id=f"bear-{round_num}",
            )
            self.advance_round(claim_id)
            claim = self._claims.get(claim_id)

        return claim

    @property
    def stats(self) -> dict[str, Any]:
        open_count = len(self.get_open_claims())
        established = len(self.get_established_claims())
        resolved_bull = sum(1 for c in self._claims.values() if c.status == ClaimStatus.RESOLVED_BULL)
        resolved_bear = sum(1 for c in self._claims.values() if c.status == ClaimStatus.RESOLVED_BEAR)
        stalemate = sum(1 for c in self._claims.values() if c.status == ClaimStatus.STALEMATE)
        excreted = sum(1 for c in self._claims.values() if c.status == ClaimStatus.EXCRETED)
        return {
            "total_claims": len(self._claims),
            "open": open_count,
            "resolved_bull": resolved_bull,
            "resolved_bear": resolved_bear,
            "stalemate": stalemate,
            "excreted": excreted,
            "established": established,
        }
