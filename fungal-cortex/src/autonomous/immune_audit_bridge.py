"""L3↔L4 Bridge: ImmuneAuditBridge — "脾脏(免疫↔循环交汇)" 免疫审计桥.

Biological Metaphor:
  脾脏——同时属于免疫系统和循环系统:
    脾脏滤过血液中的病原体(免疫), 同时清除衰老红细胞(循环)
    是免疫记忆与血液循环的物理交汇点
    白髓(White Pulp) = 免疫细胞富集区, 红髓(Red Pulp) = 红细胞过滤区

  我们映射:
    白髓 = L3 辩论验证(每个Claim如同被呈递的抗原)
    红髓 = L4 审计追踪(每个事件如同被过滤的细胞)
    边缘区(Marginal Zone) = 本桥——免疫+审计的交汇点

  核心机制:
    L3辩论Claim → L4 AuditTrail记录(如同脾脏记录每个被清除的病原体)
    被驳倒的Claim → CausalTracer标记(如同被脾脏巨噬细胞吞噬的红细胞)
    验证通过的Claim → 自动写入知识图谱(如同免疫记忆B细胞的生成)

Reference:
  Singh & Arora (2025), "HAIS-IDS", 波兰科学院技术科学通报;
  Bronte & Pittet (2013), "The spleen in immunity", Nature Reviews Immunology
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class ClaimFate(str, Enum):
    """What happened to a claim in the spleen bridge."""
    VERIFIED_TO_KG = "verified_to_kg"       # Passed → written to knowledge graph
    REFUTED_TO_CAUSAL = "refuted_to_causal"  # Failed → causal trace marked
    PENDING = "pending"                       # Undecided → held in audit
    EXPIRED = "expired"                       # Timed out → archived


@dataclass
class SpleenRecord:
    """A single 'spleen filtration' record — claim → audit trace."""

    record_id: str
    claim_id: str
    claim_summary: str
    fate: ClaimFate

    # Source (L3 immune debate)
    debate_round: int = 0
    bull_votes: int = 0
    bear_votes: int = 0
    net_price: float = 0.0  # bull - bear, >0 = verified
    confidence: float = 0.0

    # Destination (L4 traces)
    audit_id: str = ""       # Linked AuditTrail record ID
    causal_id: str = ""      # Linked CausalTracer chain ID
    kg_entity_id: str = ""   # Linked FinancialKG entity ID

    timestamp: float = field(default_factory=time.time)


@dataclass
class ImmuneAuditStats:
    """Periodic statistics of the spleen bridge throughput."""

    total_processed: int = 0
    verified_count: int = 0
    refuted_count: int = 0
    pending_count: int = 0
    avg_confidence: float = 0.0
    verify_rate: float = 0.0


class ImmuneAuditBridge:
    """Spleen: L3 immune debate results → L4 audit trail + knowledge graph.

    Config:
      - verify_threshold: net_price above this → verified (passed to KG)
      - refute_threshold: net_price below this → refuted (marked in causal)
      - max_pending: maximum pending claims before forced resolution
      - auto_commit: automatically write to audit trail on classification
    """

    def __init__(
        self,
        verify_threshold: float = 0.3,
        refute_threshold: float = -0.3,
        max_pending: int = 200,
        auto_commit: bool = True,
    ) -> None:
        self._verify_threshold = verify_threshold
        self._refute_threshold = refute_threshold
        self._max_pending = max_pending
        self._auto_commit = auto_commit

        self._records: dict[str, SpleenRecord] = {}
        self._pending: dict[str, SpleenRecord] = {}
        self._audit_refs: list[dict[str, str]] = []  # [(record_id, audit_id)]
        self._causal_refs: list[dict[str, str]] = []
        self._kg_refs: list[dict[str, str]] = []

        self._logger = CortexLogger("immune_audit_bridge")

    # ── Core Bridge: L3 Claim → L4 Audit + KG ─────────────────────────

    def process_claim(
        self,
        claim_id: str,
        claim_summary: str,
        bull_votes: int,
        bear_votes: int,
        confidence: float,
        debate_round: int = 1,
        claim_metadata: dict[str, Any] | None = None,
    ) -> SpleenRecord:
        """Process an L3 debate claim through the spleen bridge.

        Like spleen filtering blood:
          1. Claim enters marginal zone (this method)
          2. Classified by net_price (immune decision)
          3. Routed to white pulp (KG) or red pulp (audit/causal)
        """
        net_price = bull_votes - bear_votes
        total_votes = bull_votes + bear_votes + 1  # +1 to avoid div-by-zero
        normalized_net = net_price / total_votes

        # Classify fate
        if normalized_net >= self._verify_threshold:
            fate = ClaimFate.VERIFIED_TO_KG
        elif normalized_net <= self._refute_threshold:
            fate = ClaimFate.REFUTED_TO_CAUSAL
        else:
            fate = ClaimFate.PENDING

        record = SpleenRecord(
            record_id=self._gen_id("spleen"),
            claim_id=claim_id,
            claim_summary=claim_summary,
            fate=fate,
            debate_round=debate_round,
            bull_votes=bull_votes,
            bear_votes=bear_votes,
            net_price=normalized_net,
            confidence=confidence,
        )

        if fate == ClaimFate.PENDING:
            self._pending[record.record_id] = record
            if len(self._pending) > self._max_pending:
                self._drain_pending()
        else:
            self._records[record.record_id] = record
            if self._auto_commit:
                record = self._commit_record(record, claim_metadata or {})

        self._logger.info(
            "claim_processed",
            claim_id=claim_id[:16],
            fate=fate.value,
            net_price=round(normalized_net, 3),
        )
        return record

    def process_claims_batch(
        self, claims: list[dict[str, Any]],
    ) -> list[SpleenRecord]:
        """Batch process multiple claims from a debate round."""
        results = []
        for c in claims:
            record = self.process_claim(
                claim_id=c.get("claim_id", self._gen_id("claim")),
                claim_summary=c.get("summary", c.get("description", "")),
                bull_votes=c.get("bull_votes", c.get("bull_count", 0)),
                bear_votes=c.get("bear_votes", c.get("bear_count", 0)),
                confidence=c.get("confidence", 0.5),
                debate_round=c.get("round", 1),
                claim_metadata=c.get("metadata", {}),
            )
            results.append(record)
        return results

    # ── Audit Trail Integration ───────────────────────────────────────

    def generate_audit_record(self, record: SpleenRecord) -> dict[str, Any]:
        """Generate an L4 AuditTrail-compatible record from a spleen record.

        The output dict can be passed directly to AuditTrail.record().
        """
        severity = "INFO"
        if record.fate == ClaimFate.REFUTED_TO_CAUSAL:
            severity = "WARN"
        elif record.fate == ClaimFate.PENDING:
            severity = "INFO"

        return {
            "event_type": f"immune_bridge.{record.fate.value}",
            "severity": severity,
            "source": "immune_audit_bridge",
            "claim_id": record.claim_id,
            "net_price": record.net_price,
            "confidence": record.confidence,
            "debate_round": record.debate_round,
            "bull_votes": record.bull_votes,
            "bear_votes": record.bear_votes,
            "summary": record.claim_summary,
        }

    def generate_causal_link(
        self, record: SpleenRecord, upstream_id: str = "",
    ) -> dict[str, Any]:
        """Generate an L4 CausalTracer link from a refuted claim.

        When a claim is refuted (like a pathogen cleared by the spleen),
        trace why it failed — this feeds into the causal chain.
        """
        return {
            "source_id": upstream_id or f"claim-{record.claim_id}",
            "target_id": f"refutation-{record.record_id}",
            "link_type": "immune_refutation" if record.fate == ClaimFate.REFUTED_TO_CAUSAL else "immune_verification",
            "strength": abs(record.net_price),
            "evidence": {
                "net_price": record.net_price,
                "confidence": record.confidence,
                "bear_votes": record.bear_votes,
                "bull_votes": record.bull_votes,
            },
        }

    def generate_kg_input(self, record: SpleenRecord) -> dict[str, Any]:
        """Generate FinancialKG insertion data from a verified claim.

        Verified claims → knowledge graph entities (like memory B cells).
        """
        return {
            "entity_type": "immune_claim",
            "name": f"claim_{record.claim_id[:12]}",
            "properties": {
                "net_price": record.net_price,
                "confidence": record.confidence,
                "summary": record.claim_summary,
                "debate_round": record.debate_round,
            },
        }

    # ── Query Interface ───────────────────────────────────────────────

    def get_record(self, record_id: str) -> SpleenRecord | None:
        return self._records.get(record_id) or self._pending.get(record_id)

    def get_by_fate(self, fate: ClaimFate, limit: int = 50) -> list[SpleenRecord]:
        """Get records by claim fate."""
        matching = [r for r in self._records.values() if r.fate == fate]
        return sorted(matching, key=lambda r: r.timestamp, reverse=True)[:limit]

    def get_pending(self) -> list[SpleenRecord]:
        """Get all pending (undecided) claims."""
        return list(self._pending.values())

    def resolve_pending(self, record_id: str, fate: ClaimFate) -> SpleenRecord | None:
        """Manually resolve a pending claim."""
        record = self._pending.pop(record_id, None)
        if record is None:
            return None
        record.fate = fate
        self._records[record_id] = record
        if self._auto_commit:
            record = self._commit_record(record, {})
        return record

    def get_statistics(self) -> ImmuneAuditStats:
        """Compute throughput statistics for the spleen bridge."""
        verified = sum(1 for r in self._records.values() if r.fate == ClaimFate.VERIFIED_TO_KG)
        refuted = sum(1 for r in self._records.values() if r.fate == ClaimFate.REFUTED_TO_CAUSAL)
        total = len(self._records)
        confidences = [r.confidence for r in self._records.values() if r.confidence > 0]
        return ImmuneAuditStats(
            total_processed=total,
            verified_count=verified,
            refuted_count=refuted,
            pending_count=len(self._pending),
            avg_confidence=sum(confidences) / max(len(confidences), 1),
            verify_rate=verified / max(total, 1),
        )

    # ── Internal ──────────────────────────────────────────────────────

    def _commit_record(
        self, record: SpleenRecord, metadata: dict[str, Any],
    ) -> SpleenRecord:
        """Commit a classified record to the appropriate L4 subsystem."""
        audit_data = self.generate_audit_record(record)
        record.audit_id = self._gen_id("audit")
        self._audit_refs.append({"record_id": record.record_id, "audit_id": record.audit_id})
        self._logger.debug("audit_linked", record_id=record.record_id[:16], audit_id=record.audit_id[:16])

        if record.fate == ClaimFate.REFUTED_TO_CAUSAL:
            causal_data = self.generate_causal_link(record)
            record.causal_id = self._gen_id("causal")
            self._causal_refs.append({"record_id": record.record_id, "causal_id": record.causal_id})
            self._logger.debug("causal_linked", record_id=record.record_id[:16])

        elif record.fate == ClaimFate.VERIFIED_TO_KG:
            kg_data = self.generate_kg_input(record)
            record.kg_entity_id = self._gen_id("kg")
            self._kg_refs.append({"record_id": record.record_id, "kg_id": record.kg_entity_id})
            self._logger.debug("kg_linked", record_id=record.record_id[:16])

        return record

    def _drain_pending(self) -> None:
        """Resolve oldest pending claims by expiry."""
        sorted_ids = sorted(
            self._pending.keys(),
            key=lambda rid: self._pending[rid].timestamp,
        )
        to_drain = sorted_ids[:max(1, len(sorted_ids) // 4)]
        for rid in to_drain:
            record = self._pending.pop(rid, None)
            if record:
                record.fate = ClaimFate.EXPIRED
                self._records[rid] = record

    @staticmethod
    def _gen_id(prefix: str) -> str:
        return hashlib.md5(f"{prefix}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        s = self.get_statistics()
        return {
            "total_processed": s.total_processed,
            "verified": s.verified_count,
            "refuted": s.refuted_count,
            "pending": s.pending_count,
            "verify_rate": round(s.verify_rate, 3),
            "avg_confidence": round(s.avg_confidence, 3),
            "audit_links": len(self._audit_refs),
            "causal_links": len(self._causal_refs),
            "kg_links": len(self._kg_refs),
        }
