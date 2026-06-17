"""L5 4.8: GlobalAuditTrail — "集群免疫记忆"(AIS Memory) 全局审计追踪.

Biological Metaphor:
  免疫系统的全身体记忆——一旦感染过某种病原体, 记忆B细胞和记忆T细胞
  遍布全身淋巴组织(淋巴结/脾脏/骨髓), 可以持续数十年(如天花疫苗接种)。

  免疫球蛋白(IgG)结构映射:
    可变区(Fab): 病原体特异性信息(event_type/details)
    恒定区(Fc): 通用效应功能(timestamp/agent_id)

  T细胞监控:
    任何一个细胞的MHC异常→被T细胞识别→诱导凋亡
    任何一个Agent的参数异常→被AuditTrail标记→触发自愈

  朊病毒构象记忆:
    错误折叠的构象本身就是一种"记忆"——可以从正常PrP^C转化更多的PrP^Sc
    → 异常检测 = 识别"构象错误"的Agent行为

Reference:
  HAIS-IDS (2025); Maury (2025), FEBS Letters;
  Kolli et al. (2025), "Functional Amyloids", Advanced Science
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


# ── Constants ────────────────────────────────────────────────────────

class AuditEventType(str, Enum):
    AGENT_CREATED = "agent_created"
    AGENT_APOPTOSED = "agent_apoptosed"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    KNOWLEDGE_SYNCED = "knowledge_synced"
    CONSENSUS_REACHED = "consensus_reached"
    EVOLUTION_APPLIED = "evolution_applied"
    PARAM_CHANGE = "param_change"
    ANOMALY_DETECTED = "anomaly_detected"
    SYSTEM_EVENT = "system_event"


MAX_RECORDS = 100_000
MAX_ANOMALIES = 1000
PARAM_DRIFT_THRESHOLD = 0.05  # 5% drift = anomaly
NEW_RULE_RISK_THRESHOLD = 0.8
AUDIT_RETENTION_DAYS = 365


# ── Data Structures ──────────────────────────────────────────────────


@dataclass
class ClusterAuditRecord:
    """A single cluster audit entry — like an IgG antibody recording a pathogen encounter.

    Fab region: event_type + details (pathogen-specific)
    Fc region: timestamp + agent_id + trace_id (universal effector)
    """

    record_id: str
    event_type: AuditEventType
    agent_id: str
    details: dict[str, Any]
    trace_id: str = ""  # for end-to-end tracing
    prev_hash: str = ""  # chain of custody (like antibody affinity maturation record)
    timestamp: float = field(default_factory=time.time)

    def compute_hash(self) -> str:
        raw = f"{self.record_id}|{self.event_type.value}|{self.agent_id}|{self.trace_id}|{self.prev_hash}|{self.timestamp}"
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class AnomalyDetection:
    """Detected anomaly — like a T cell recognizing abnormal MHC-peptide complex."""

    detection_id: str
    agent_id: str
    anomaly_type: str  # "param_drift", "new_rule_risk", "frequency_spike"
    severity: float  # 0-1
    evidence: dict[str, Any]
    detected_at: float = field(default_factory=time.time)
    acknowledged: bool = False
    resolved: bool = False


# ── Main Class ───────────────────────────────────────────────────────


class GlobalAuditTrail:
    """Cluster-wide immune memory — records all events, detects anomalies.

    Config:
      - max_records: max stored audit records
      - retention_days: how long to keep records
      - param_drift_threshold: triggers anomaly detection
    """

    def __init__(
        self,
        max_records: int = MAX_RECORDS,
        retention_days: int = AUDIT_RETENTION_DAYS,
        param_drift_threshold: float = PARAM_DRIFT_THRESHOLD,
    ) -> None:
        self._max_records = max_records
        self._retention_days = retention_days
        self._param_drift_threshold = param_drift_threshold

        self._records: list[ClusterAuditRecord] = []
        self._anomalies: list[AnomalyDetection] = []
        self._param_history: dict[str, deque[tuple[float, float]]] = defaultdict(
            lambda: deque(maxlen=100)
        )  # {agent_id: [(timestamp, param_snapshot), ...]}
        self._trace_map: dict[str, list[ClusterAuditRecord]] = defaultdict(list)  # {trace_id: [records]}
        self._logger = CortexLogger("global_audit")

    # ── Public API ──────────────────────────────────────────────────

    def record(
        self, event_type: AuditEventType, agent_id: str,
        details: dict[str, Any], trace_id: str = "",
    ) -> ClusterAuditRecord:
        """Record a cluster event — like depositing an immune memory."""
        prev_hash = self._records[-1].compute_hash() if self._records else "0" * 64

        rec = ClusterAuditRecord(
            record_id=self._gen_record_id(event_type.value, agent_id),
            event_type=event_type,
            agent_id=agent_id,
            details=details,
            trace_id=trace_id,
            prev_hash=prev_hash,
        )

        self._records.append(rec)
        if trace_id:
            self._trace_map[trace_id].append(rec)

        # Enforce limits
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

        # Check for anomalies
        anomaly = self._check_anomaly(rec)
        if anomaly:
            self._anomalies.append(anomaly)
            self._logger.warn(
                "anomaly_detected",
                agent=agent_id[:12],
                anomaly_type=anomaly.anomaly_type,
                severity=round(anomaly.severity, 3),
            )

        return rec

    def trace_event(self, trace_id: str) -> list[ClusterAuditRecord]:
        """Trace all records for a given trace — epidemiological investigation."""
        return self._trace_map.get(trace_id, [])

    def get_agent_history(
        self, agent_id: str, limit: int = 100, event_type: AuditEventType | None = None
    ) -> list[ClusterAuditRecord]:
        """Get audit history for a specific agent."""
        results: list[ClusterAuditRecord] = []
        for rec in reversed(self._records):
            if rec.agent_id == agent_id:
                if event_type is None or rec.event_type == event_type:
                    results.append(rec)
                    if len(results) >= limit:
                        break
        return results

    def detect_anomalies(
        self, agent_id: str, current_params: dict[str, float]
    ) -> list[AnomalyDetection]:
        """Check for anomalies in an agent's parameters — like T cell immune surveillance.

        Checks:
          - param_drift: significant change from historical baseline
          - frequency_spike: sudden increase in event frequency
          - new_rule_risk: high-risk untested parameters
        """
        detections: list[AnomalyDetection] = []

        # 1. Parameter drift
        param_snapshot = sum(current_params.values()) / max(len(current_params), 1)
        self._param_history[agent_id].append((time.time(), param_snapshot))

        if len(self._param_history[agent_id]) >= 20:
            history = list(self._param_history[agent_id])
            recent = [v for _, v in history[-10:]]
            older = [v for _, v in history[:-10]]

            recent_mean = sum(recent) / len(recent)
            older_mean = sum(older) / len(older)

            if older_mean > 0 and abs(recent_mean - older_mean) / older_mean > self._param_drift_threshold:
                detections.append(AnomalyDetection(
                    detection_id=self._gen_detection_id(agent_id, "param_drift"),
                    agent_id=agent_id,
                    anomaly_type="param_drift",
                    severity=min(1.0, abs(recent_mean - older_mean) / max(older_mean, 0.001)),
                    evidence={"recent_mean": recent_mean, "older_mean": older_mean},
                ))

        # 2. Frequency spike
        recent_events = sum(
            1 for rec in self._records[-100:]
            if rec.agent_id == agent_id and time.time() - rec.timestamp < 300
        )
        if recent_events > 50:
            detections.append(AnomalyDetection(
                detection_id=self._gen_detection_id(agent_id, "frequency_spike"),
                agent_id=agent_id,
                anomaly_type="frequency_spike",
                severity=min(1.0, recent_events / 100),
                evidence={"events_in_5min": recent_events},
            ))

        # 3. New rule risk
        for key, value in current_params.items():
            if abs(value) > 0.95:
                detections.append(AnomalyDetection(
                    detection_id=self._gen_detection_id(agent_id, "new_rule_risk"),
                    agent_id=agent_id,
                    anomaly_type="new_rule_risk",
                    severity=abs(value),
                    evidence={"param": key, "value": value, "threshold": NEW_RULE_RISK_THRESHOLD},
                ))

        for det in detections:
            self._anomalies.append(det)
            if len(self._anomalies) > MAX_ANOMALIES:
                self._anomalies = self._anomalies[-MAX_ANOMALIES:]

        return detections

    def verify_integrity(self) -> dict[str, Any]:
        """Verify the hash chain integrity of all records."""
        violations: list[int] = []
        for i in range(1, len(self._records)):
            expected_prev = self._records[i - 1].compute_hash()
            if self._records[i].prev_hash != expected_prev:
                violations.append(i)

        return {
            "valid": len(violations) == 0,
            "total": len(self._records),
            "violations": violations,
        }

    def prune_old_records(self) -> int:
        """Remove records older than retention period."""
        cutoff = time.time() - self._retention_days * 86400
        before = len(self._records)
        self._records = [r for r in self._records if r.timestamp >= cutoff]
        return before - len(self._records)

    def acknowledge_anomaly(self, detection_id: str) -> bool:
        for a in self._anomalies:
            if a.detection_id == detection_id:
                a.acknowledged = True
                return True
        return False

    def resolve_anomaly(self, detection_id: str) -> bool:
        for a in self._anomalies:
            if a.detection_id == detection_id:
                a.resolved = True
                return True
        return False

    # ── Private Methods ─────────────────────────────────────────────

    def _check_anomaly(self, record: ClusterAuditRecord) -> AnomalyDetection | None:
        """Check if a single record triggers an anomaly."""
        if record.event_type == AuditEventType.PARAM_CHANGE:
            change_pct = record.details.get("change_pct", 0)
            if abs(change_pct) > self._param_drift_threshold * 2:
                return AnomalyDetection(
                    detection_id=self._gen_detection_id(record.agent_id, "param_drift"),
                    agent_id=record.agent_id,
                    anomaly_type="param_drift",
                    severity=min(1.0, abs(change_pct)),
                    evidence=record.details,
                )
        return None

    @staticmethod
    def _gen_record_id(event_type: str, agent_id: str) -> str:
        raw = f"{event_type}|{agent_id}|{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _gen_detection_id(agent_id: str, anomaly_type: str) -> str:
        raw = f"{agent_id}|{anomaly_type}|{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @property
    def anomalies(self) -> list[AnomalyDetection]:
        return list(self._anomalies)

    @property
    def stats(self) -> dict[str, Any]:
        event_counts: dict[str, int] = defaultdict(int)
        for rec in self._records[-1000:]:
            event_counts[rec.event_type.value] += 1

        return {
            "total_records": len(self._records),
            "anomalies": len(self._anomalies),
            "unresolved_anomalies": sum(1 for a in self._anomalies if not a.resolved),
            "traces": len(self._trace_map),
            "recent_event_distribution": dict(event_counts),
        }
