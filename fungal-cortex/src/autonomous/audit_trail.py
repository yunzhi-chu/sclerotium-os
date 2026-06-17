"""L4 M3a: AuditTrail — "信息素沉积+情景记忆"(Stigmergy+Hippocampus) 审计追踪.

Biological Metaphor:
  蚁群信息素(Pheromone)沉积系统——每只蚂蚁走过留下信息素,
  后续蚂蚁根据信息素浓度做决策, 信息素随时间蒸发。

  人类海马体的情景记忆——每个记忆有时间戳+位置+情感标记, 可通过线索回溯。

  record(event_type, source, input, output, trace_id):
    每步操作记录 = 蚂蚁走过留下信息素
    input_hash/output_hash = 信息素的化学组成(可验证是否为同一只蚂蚁)
    trace_id = 信息素路径的编码(从巢穴→食物源的完整路径)

  Stigmergy(间接通信):
    高频路径→强信息素(可靠执行链) = 蚁群高速公路
    异常路径→弱/负信息素(故障标记) = 回避信息素
    信息素蒸发(60秒半衰期) = 旧信息不再可靠→需要新鲜数据

Reference: S-MADRL (AROB 2026); Freire-Obregón (2026), ICAART
"""

from __future__ import annotations

import hashlib
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class AuditSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditRecord:
    """A single audit log entry — like a pheromone deposited on the trail."""

    record_id: str
    event_type: str
    source: str  # agent/module
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    trace_id: str  # complete path encoding
    input_hash: str = ""
    output_hash: str = ""
    timestamp: float = field(default_factory=time.time)
    prev_hash: str = ""

    def compute_hash(self) -> str:
        raw = f"{self.record_id}|{self.event_type}|{self.trace_id}|{self.prev_hash}|{self.timestamp}"
        return hashlib.sha256(raw.encode()).hexdigest()


class AuditTrail:
    """Stigmergic memory — pheromone-based audit trail with evaporation.

    Config:
      - evaporation_halflife: seconds for pheromone half-life
      - max_records: hard limit on stored records
    """

    def __init__(self, evaporation_halflife: float = 60.0, max_records: int = 100_000) -> None:
        self._halflife = evaporation_halflife
        self._max_records = max_records
        self._records: list[AuditRecord] = []
        self._pheromone_strength: dict[str, float] = {}  # {trace_id: strength}
        self._logger = CortexLogger("audit_trail")

    def record(
        self, event_type: str, source: str, input_data: dict[str, Any],
        output_data: dict[str, Any], trace_id: str = "",
    ) -> AuditRecord:
        """Record an event — ant depositing pheromone."""
        input_hash = hashlib.md5(str(sorted(input_data.items())).encode()).hexdigest()[:16]
        output_hash = hashlib.md5(str(sorted(output_data.items())).encode()).hexdigest()[:16]
        prev_hash = self._records[-1].compute_hash() if self._records else "0" * 64

        rec = AuditRecord(
            record_id=self._gen_id(event_type),
            event_type=event_type,
            source=source,
            input_data=input_data,
            output_data=output_data,
            trace_id=trace_id,
            input_hash=input_hash,
            output_hash=output_hash,
            prev_hash=prev_hash,
        )
        self._records.append(rec)

        # Update pheromone strength (reinforce or weaken)
        if trace_id:
            current = self._pheromone_strength.get(trace_id, 0)
            # High-frequency paths get stronger pheromones
            self._pheromone_strength[trace_id] = current + 1.0

        # Evaporate old pheromones
        self._evaporate()

        # Enforce limit
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

        return rec

    def export_evidence_chain(self, trace_id: str) -> list[AuditRecord]:
        """Export complete evidence chain — backtrack from food to nest."""
        return [r for r in self._records if r.trace_id == trace_id]

    def get_trace_strength(self, trace_id: str) -> float:
        """Get current pheromone strength for a trace (after evaporation)."""
        return self._pheromone_strength.get(trace_id, 0)

    def verify_integrity(self) -> dict[str, Any]:
        """Verify hash chain integrity (linear).

        Like DNA polymerase 3'→5' exonuclease proofreading — each step
        is verified against the previous before proceeding.
        """
        violations = []
        for i in range(1, len(self._records)):
            expected = self._records[i - 1].compute_hash()
            if self._records[i].prev_hash != expected:
                violations.append(i)
        return {"valid": len(violations) == 0, "total": len(self._records), "violations": violations}

    # ── Phase 7.2c: Merkle Tree Verification (DNA Proofreading) ─────

    def build_merkle_tree(self, record_ids: list[str] | None = None) -> dict[str, Any]:
        """Build a Merkle tree for batch integrity verification.

        Like DNA's double-helix proofreading: each base pair is verified
        independently, but the whole strand's integrity can be checked
        via the root hash.
        """
        if record_ids:
            records = [r for r in self._records if r.record_id in record_ids]
        else:
            records = list(self._records)

        if not records:
            return {"root_hash": "", "levels": 0, "records": 0}

        # Compute leaf hashes
        leaves = [r.compute_hash() for r in records]
        levels = [leaves]
        current = leaves

        while len(current) > 1:
            next_level = []
            for i in range(0, len(current), 2):
                left = current[i]
                right = current[i + 1] if i + 1 < len(current) else left
                combined = hashlib.sha256(f"{left}|{right}".encode()).hexdigest()
                next_level.append(combined)
            levels.append(next_level)
            current = next_level

        return {
            "root_hash": current[0] if current else "",
            "levels": len(levels),
            "records": len(records),
            "leaf_count": len(leaves),
            "merkle_root": current[0] if current else "",
        }

    def verify_merkle_proof(self, record_id: str, root_hash: str) -> bool:
        """Verify a single record against a known Merkle root.

        Like checking a single base pair against the reference genome.
        """
        record = next((r for r in self._records if r.record_id == record_id), None)
        if record is None:
            return False
        tree = self.build_merkle_tree()
        return tree.get("merkle_root", "") == root_hash

    def export_immutable_chain(self) -> dict[str, Any]:
        """Export the complete immutable audit chain for external verification.

        Like producing a certified DNA sequence for forensic analysis.
        """
        chain_data = []
        for i, r in enumerate(self._records):
            chain_data.append({
                "index": i,
                "record_id": r.record_id,
                "event_type": r.event_type,
                "source": r.source,
                "trace_id": r.trace_id,
                "timestamp": r.timestamp,
                "input_hash": r.input_hash,
                "output_hash": r.output_hash,
                "prev_hash": r.prev_hash,
                "current_hash": r.compute_hash(),
            })

        merkle = self.build_merkle_tree()
        return {
            "chain_length": len(chain_data),
            "merkle_root": merkle.get("merkle_root", ""),
            "exported_at": time.time(),
            "records": chain_data,
        }

    def _evaporate(self) -> None:
        """Evaporate pheromones — decay strength exponentially."""
        now = time.time()
        for trace_id in list(self._pheromone_strength.keys()):
            # Estimate time since last deposit from records
            relevant = [r for r in self._records if r.trace_id == trace_id]
            if relevant:
                age = now - relevant[-1].timestamp
                decay = math.exp(-age * math.log(2) / self._halflife)
                self._pheromone_strength[trace_id] *= decay
                if self._pheromone_strength[trace_id] < 0.001:
                    del self._pheromone_strength[trace_id]

    @staticmethod
    def _gen_id(event_type: str) -> str:
        return hashlib.md5(f"{event_type}|{time.time()}".encode()).hexdigest()[:24]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_records": len(self._records),
            "active_traces": len(self._pheromone_strength),
            "strongest_trace": max(self._pheromone_strength, key=self._pheromone_strength.get, default=""),
        }
