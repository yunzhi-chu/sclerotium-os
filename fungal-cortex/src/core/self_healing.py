"""Phase 6.2: SelfHealingOrchestrator — "伤口愈合级联"(Wound Healing Cascade).

Biological Metaphor:
  伤口愈合的四个重叠阶段——止血→炎症→增殖→重塑:
    每个阶段由不同的细胞/分子主导, 但无缝衔接
    最终: 恢复组织完整性(虽然可能有疤痕)

  我们映射:
    1. 止血期(Hemostasis):
       血小板聚集→形成血栓封堵伤口
       = 各层健康报告聚合→确定"伤口"位置和严重度
       → 隔离故障模块(如同血凝块局限损伤范围)

    2. 炎症期(Inflammation):
       中性粒细胞+巨噬细胞→清理碎片+细菌
       = FINAL Bench MA-ER评分定位→免疫细胞清理碎片
       → 凋亡失败Agent, 撤销错误策略, 清理知识图谱污染节点

    3. 增殖期(Proliferation):
       成纤维细胞合成胶原蛋白→填补伤口
       = M2能力工厂生成新能力 + L5集群重组Agent分布
       → 肉芽组织形成(新毛细血管+新基质)

    4. 重塑期(Remodeling):
       III型胶原→I型胶原重塑, 瘢痕成熟
       = 沙箱回测 + A/B对比→确认修复有效且不会产生"瘢痕"(技术债务)
       → 组织拉伸强度恢复到原组织的80%(无法100%——任何修复都有痕迹)

Reference:
  Gurtner et al. (2008), "Wound healing", Nature 453:314-321;
  Singer & Clark (1999), "Cutaneous wound healing", NEJM 341:738-746;
  Mawarda et al. (2026), "Lichen holobiont resilience", Env Microbiome
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


# ── Wound Healing Phases ──────────────────────────────────────────────

class HealingPhase(str, Enum):
    HEALTHY = "healthy"          # No wound detected
    HEMOSTASIS = "hemostasis"     # Detecting and isolating the wound
    INFLAMMATION = "inflammation"  # Diagnosing and cleaning debris
    PROLIFERATION = "proliferation"  # Repairing with new tissue
    REMODELING = "remodeling"     # Verifying and strengthening repair
    FAILED = "failed"             # Healing failed, manual intervention needed


class WoundSeverity(str, Enum):
    MILD = "mild"          # Small scrape — auto-healable
    MODERATE = "moderate"  # Deep cut — needs careful repair
    SEVERE = "severe"      # Major wound — may leave scar
    CRITICAL = "critical"  # Life-threatening — requires all hands


class WoundType(str, Enum):
    AGENT_FAILURE = "agent_failure"              # Agents dying en masse
    STRATEGY_DEGRADATION = "strategy_degradation"  # Strategy performance collapse
    KNOWLEDGE_CONTAMINATION = "knowledge_contamination"  # Bad knowledge spreading
    RESOURCE_EXHAUSTION = "resource_exhaustion"    # System resources depleted
    COORDINATION_BREAKDOWN = "coordination_breakdown"  # Cross-layer communication failure
    DRIFT_AVALANCHE = "drift_avalanche"           # Cascading parameter drift


# ── Data Classes ──────────────────────────────────────────────────────

@dataclass
class HealthReport:
    """Health report from a single layer — like a tissue biopsy."""

    report_id: str
    layer: str  # L0, L3, L4, L5
    component: str  # specific module name
    health_score: float  # 0-1, 1 = perfectly healthy
    anomaly_count: int = 0
    failure_count: int = 0
    error_messages: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Wound:
    """A detected wound — damage that needs healing."""

    wound_id: str
    wound_type: WoundType
    severity: WoundSeverity
    location: str  # Which layer/component
    description: str

    # Affected area
    affected_components: list[str] = field(default_factory=list)
    health_before: float = 1.0  # Health score before wound

    # Detection details
    detected_at: float = field(default_factory=time.time)
    detected_by: str = ""  # Which phase detected it

    # Healing tracking
    current_phase: HealingPhase = HealingPhase.HEMOSTASIS
    phase_started: dict[str, float] = field(default_factory=dict)
    healing_complete: bool = False
    scar_tissue: bool = False  # Did healing leave a scar (tech debt)?


@dataclass
class HealingCycle:
    """A complete healing cycle — from wound to recovery."""

    cycle_id: str
    wound: Wound

    # Phase results
    hemostasis_result: dict[str, Any] = field(default_factory=dict)
    inflammation_result: dict[str, Any] = field(default_factory=dict)
    proliferation_result: dict[str, Any] = field(default_factory=dict)
    remodeling_result: dict[str, Any] = field(default_factory=dict)

    # Final outcome
    healed: bool = False
    scar_severity: float = 0.0  # 0 = no scar, 1 = severe scar
    time_to_heal: float = 0.0

    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0


class SelfHealingOrchestrator:
    """Wound Healing Cascade: Detect → Diagnose → Repair → Verify.

    Config:
      - health_check_interval: seconds between health assessments
      - mild_threshold: health score below this → mild wound
      - moderate_threshold: health score below this → moderate wound
      - severe_threshold: health score below this → severe wound
      - auto_heal_max_severity: maximum severity to auto-heal without human approval
      - max_concurrent_wounds: maximum wounds to heal simultaneously
      - verification_timeout: max time for remodeling phase
    """

    def __init__(
        self,
        health_check_interval: float = 60.0,
        mild_threshold: float = 0.8,
        moderate_threshold: float = 0.6,
        severe_threshold: float = 0.4,
        auto_heal_max_severity: WoundSeverity | None = None,
        max_concurrent_wounds: int = 3,
        verification_timeout: float = 3600.0,
    ) -> None:
        self._health_interval = health_check_interval
        self._mild_threshold = mild_threshold
        self._moderate_threshold = moderate_threshold
        self._severe_threshold = severe_threshold
        self._auto_heal_max = auto_heal_max_severity or WoundSeverity.MODERATE
        self._max_concurrent = max_concurrent_wounds
        self._verification_timeout = verification_timeout

        # Current health state
        self._health_reports: dict[str, HealthReport] = {}  # {component: report}
        self._layer_health: dict[str, float] = defaultdict(lambda: 1.0)

        # Wounds and healing cycles
        self._active_wounds: dict[str, Wound] = {}
        self._healing_history: list[HealingCycle] = []
        self._scar_registry: list[dict[str, Any]] = []  # Track scar tissue / tech debt

        # Current phase for each active wound
        self._wound_phase: dict[str, HealingPhase] = {}

        self._logger = CortexLogger("self_healing")

    # ── Health Monitoring (Continuous) ─────────────────────────────

    def report_health(self, layer: str, component: str,
                      health_score: float, anomaly_count: int = 0,
                      failure_count: int = 0, error_messages: list[str] | None = None,
                      metrics: dict[str, Any] | None = None) -> Wound | None:
        """Submit a health report from any layer component.

        Like sensory nerves continuously reporting tissue integrity.
        Returns a Wound if one is detected, else None.
        """
        report = HealthReport(
            report_id=self._gen_id("health"),
            layer=layer,
            component=component,
            health_score=health_score,
            anomaly_count=anomaly_count,
            failure_count=failure_count,
            error_messages=error_messages or [],
            metrics=metrics or {},
        )
        self._health_reports[component] = report

        # Update layer aggregate health
        layer_reports = [r for r in self._health_reports.values() if r.layer == layer]
        self._layer_health[layer] = sum(r.health_score for r in layer_reports) / max(len(layer_reports), 1)

        # Check for wound
        wound = self._detect_wound(report)
        if wound:
            self._active_wounds[wound.wound_id] = wound
            self._wound_phase[wound.wound_id] = HealingPhase.HEMOSTASIS
            wound.phase_started[HealingPhase.HEMOSTASIS.value] = time.time()
            self._logger.warn(
                "wound_detected",
                wound_id=wound.wound_id[:16],
                type=wound.wound_type.value,
                severity=wound.severity.value,
                location=wound.location,
            )
        return wound

    def _detect_wound(self, report: HealthReport) -> Wound | None:
        """Detect if a health report indicates a wound.

        Phase 1: Hemostasis begins — like platelets detecting vessel rupture.
        """
        score = report.health_score

        if score >= self._mild_threshold:
            return None  # Healthy

        # Determine severity
        if score < self._severe_threshold:
            severity = WoundSeverity.CRITICAL if score < 0.2 else WoundSeverity.SEVERE
        elif score < self._moderate_threshold:
            severity = WoundSeverity.MODERATE
        else:
            severity = WoundSeverity.MILD

        # Determine wound type from failure patterns
        wound_type = self._classify_wound_type(report)

        # Limit concurrent wounds
        active_count = len([w for w in self._active_wounds.values() if not w.healing_complete])
        if active_count >= self._max_concurrent:
            self._logger.warn("max_concurrent_wounds_reached", active=active_count)
            return None

        return Wound(
            wound_id=self._gen_id("wound"),
            wound_type=wound_type,
            severity=severity,
            location=f"{report.layer}/{report.component}",
            description=f"{wound_type.value} in {report.component}: health={score:.2f}",
            affected_components=[report.component],
            health_before=score,
            detected_by="health_report",
        )

    @staticmethod
    def _classify_wound_type(report: HealthReport) -> WoundType:
        """Classify the type of wound from error patterns."""
        errors = " ".join(report.error_messages).lower() if report.error_messages else ""
        if "agent" in errors or report.failure_count > 5:
            return WoundType.AGENT_FAILURE
        if "strategy" in errors or "degrad" in errors:
            return WoundType.STRATEGY_DEGRADATION
        if "knowledge" in errors or "contamination" in errors:
            return WoundType.KNOWLEDGE_CONTAMINATION
        if "resource" in errors or "exhaust" in errors:
            return WoundType.RESOURCE_EXHAUSTION
        if "coordination" in errors or "bridge" in errors:
            return WoundType.COORDINATION_BREAKDOWN
        if report.anomaly_count > 3:
            return WoundType.DRIFT_AVALANCHE
        return WoundType.AGENT_FAILURE

    # ── Phase 2: Inflammation (Diagnosis) ───────────────────────────

    def diagnose(self, wound_id: str) -> dict[str, Any]:
        """Run the inflammation phase — diagnose root cause.

        Like neutrophils and macrophages infiltrating the wound,
        cleaning debris and identifying pathogens.
        """
        wound = self._active_wounds.get(wound_id)
        if wound is None:
            return {"error": "wound_not_found"}

        wound.current_phase = HealingPhase.INFLAMMATION
        wound.phase_started[HealingPhase.INFLAMMATION.value] = time.time()
        self._wound_phase[wound_id] = HealingPhase.INFLAMMATION

        # Gather all relevant health reports
        component_reports = [
            r for c, r in self._health_reports.items()
            if c in wound.affected_components
        ]

        # Diagnose root cause
        diagnosis = {
            "wound_type": wound.wound_type.value,
            "severity": wound.severity.value,
            "root_cause": self._diagnose_root_cause(wound, component_reports),
            "affected_components": wound.affected_components,
            "contaminated_items": self._identify_contamination(wound, component_reports),
            "recommended_actions": self._recommend_inflammation_actions(wound, component_reports),
        }

        self._logger.info(
            "wound_diagnosed",
            wound_id=wound_id[:16],
            root_cause=diagnosis["root_cause"],
            actions=len(diagnosis["recommended_actions"]),
        )
        return diagnosis

    def _diagnose_root_cause(
        self, wound: Wound, reports: list[HealthReport],
    ) -> str:
        """Identify the root cause of the wound."""
        if wound.wound_type == WoundType.AGENT_FAILURE:
            fail_components = [r.component for r in reports if r.failure_count > 0]
            return f"Agent failures concentrated in: {fail_components}" if fail_components else "Unknown agent failure source"
        elif wound.wound_type == WoundType.STRATEGY_DEGRADATION:
            return "Strategy performance decay detected, likely due to regime mismatch"
        elif wound.wound_type == WoundType.KNOWLEDGE_CONTAMINATION:
            return "Corrupted knowledge nodes propagating through mycorrhizal network"
        elif wound.wound_type == WoundType.RESOURCE_EXHAUSTION:
            return "Resource pool depleted below safe threshold"
        elif wound.wound_type == WoundType.COORDINATION_BREAKDOWN:
            return "Cross-layer bridge failure causing communication loss"
        else:
            return "Cascading parameter drift from uncaught anomaly propagation"

    def _identify_contamination(
        self, wound: Wound, reports: list[HealthReport],
    ) -> list[dict[str, str]]:
        """Identify contaminated items that need to be cleared.

        Like macrophages identifying and phagocytosing bacteria.
        """
        contaminated = []
        for report in reports:
            for err in report.error_messages:
                if any(kw in err.lower() for kw in ("bad", "corrupt", "stale", "wrong", "fail")):
                    contaminated.append({"component": report.component, "error": err[:200]})
        return contaminated[:20]

    def _recommend_inflammation_actions(
        self, wound: Wound, reports: list[HealthReport],
    ) -> list[dict[str, Any]]:
        """Recommend cleanup actions for the inflammation phase."""
        actions = []
        if wound.wound_type == WoundType.AGENT_FAILURE:
            actions.append({"action": "apoptose_failed_agents", "target": wound.location})
        if wound.wound_type == WoundType.KNOWLEDGE_CONTAMINATION:
            actions.append({"action": "quarantine_bad_knowledge", "target": "knowledge_network"})
        if wound.wound_type == WoundType.STRATEGY_DEGRADATION:
            actions.append({"action": "rollback_strategy_params", "target": wound.location})
        if wound.wound_type == WoundType.COORDINATION_BREAKDOWN:
            actions.append({"action": "reset_bridge_state", "target": wound.location})
        actions.append({"action": "flag_for_proliferation", "target": wound.location})
        return actions

    # ── Phase 3: Proliferation (Repair) ─────────────────────────────

    def repair(self, wound_id: str, available_abilities: list[str] | None = None) -> dict[str, Any]:
        """Run the proliferation phase — generate new tissue to fill the wound.

        Like fibroblasts synthesizing collagen to form granulation tissue.
        """
        wound = self._active_wounds.get(wound_id)
        if wound is None:
            return {"error": "wound_not_found"}

        # Check if auto-healing is allowed
        if wound.severity.value > self._auto_heal_max.value:
            return {
                "status": "human_approval_required",
                "reason": f"Severity {wound.severity.value} exceeds auto-heal max {self._auto_heal_max.value}",
            }

        wound.current_phase = HealingPhase.PROLIFERATION
        wound.phase_started[HealingPhase.PROLIFERATION.value] = time.time()
        self._wound_phase[wound_id] = HealingPhase.PROLIFERATION

        abilities = available_abilities or []
        repair_plan: dict[str, Any] = {
            "wound_type": wound.wound_type.value,
            "actions_taken": [],
            "new_components": [],
            "reconfigured_components": [],
        }

        # Action depends on wound type
        if wound.wound_type == WoundType.AGENT_FAILURE:
            repair_plan["actions_taken"].append({
                "action": "respawn_agents",
                "detail": f"Spawn replacement agents for {wound.location}",
                "count": max(1, wound.severity.value == "critical" and 5 or 2),
            })

        elif wound.wound_type == WoundType.STRATEGY_DEGRADATION:
            repair_plan["actions_taken"].append({
                "action": "evolve_strategy",
                "detail": "Trigger micro-evolution on degraded strategy parameters",
            })
            repair_plan["actions_taken"].append({
                "action": "cross_validate",
                "detail": "A/B test evolved strategy against baseline",
            })

        elif wound.wound_type == WoundType.KNOWLEDGE_CONTAMINATION:
            repair_plan["actions_taken"].append({
                "action": "purge_contaminated_nodes",
                "detail": "Remove quarantined knowledge nodes from mycorrhizal network",
            })
            repair_plan["actions_taken"].append({
                "action": "relearn_from_immune_memory",
                "detail": "Restore knowledge from validated immune memory B-cells",
            })

        elif wound.wound_type == WoundType.RESOURCE_EXHAUSTION:
            repair_plan["actions_taken"].append({
                "action": "trigger_autophagy",
                "detail": "Activate endogenous engine to recycle idle resources",
            })

        elif wound.wound_type == WoundType.COORDINATION_BREAKDOWN:
            repair_plan["actions_taken"].append({
                "action": "reset_bridges",
                "detail": "Reset cross-layer bridge state and clear stale queues",
            })

        elif wound.wound_type == WoundType.DRIFT_AVALANCHE:
            repair_plan["actions_taken"].append({
                "action": "recalibrate_detectors",
                "detail": "Reset parameter baselines and retrain drift detectors",
            })

        # Generate new capabilities if abilities available
        if abilities:
            repair_plan["new_components"].append({
                "action": "create_ability",
                "detail": f"Generate new ability from {len(abilities)} available templates",
                "candidates": abilities[:5],
            })

        self._logger.info(
            "wound_repairing",
            wound_id=wound_id[:16],
            actions=len(repair_plan["actions_taken"]),
        )
        return repair_plan

    # ── Phase 4: Remodeling (Verification) ──────────────────────────

    def verify(self, wound_id: str, test_results: dict[str, Any] | None = None) -> dict[str, Any]:
        """Run the remodeling phase — verify the repair is sound.

        Like type III collagen being replaced by stronger type I collagen,
        and the wound gaining tensile strength.
        """
        wound = self._active_wounds.get(wound_id)
        if wound is None:
            return {"error": "wound_not_found"}

        wound.current_phase = HealingPhase.REMODELING
        wound.phase_started[HealingPhase.REMODELING.value] = time.time()
        self._wound_phase[wound_id] = HealingPhase.REMODELING

        verification: dict[str, Any] = {
            "tests_run": [],
            "passed": True,
            "scar_detected": False,
            "scar_severity": 0.0,
        }

        # 1. Sandbox backtest check
        if test_results:
            verification["tests_run"].append({
                "test": "sandbox_backtest",
                "result": "passed" if test_results.get("sharpe", 0) > 0 else "warning",
            })

        # 2. A/B comparison (before vs after)
        health_after = self._calculate_current_health(wound)
        health_delta = health_after - wound.health_before
        verification["tests_run"].append({
            "test": "health_comparison",
            "before": round(wound.health_before, 3),
            "after": round(health_after, 3),
            "delta": round(health_delta, 3),
            "result": "passed" if health_delta > -0.1 else "warning",
        })

        # 3. Scar detection (tech debt assessment)
        scar_score = self._assess_scar(wound)
        verification["scar_detected"] = scar_score > 0.3
        verification["scar_severity"] = scar_score

        if scar_score > 0.3:
            verification["passed"] = False
            wound.scar_tissue = True
            verification["scar_note"] = (
                f"Scar tissue detected (score={scar_score:.2f}). "
                "The repair holds but has introduced technical debt. "
                "Like a healed wound — functional but not as strong as original tissue."
            )

        # 4. Complete healing
        wound.healing_complete = True
        wound.current_phase = HealingPhase.HEALTHY

        time_to_heal = time.time() - wound.detected_at
        cycle = HealingCycle(
            cycle_id=self._gen_id("cycle"),
            wound=wound,
            remodeling_result=verification,
            healed=verification["passed"],
            scar_severity=scar_score,
            time_to_heal=time_to_heal,
            completed_at=time.time(),
        )
        self._healing_history.append(cycle)
        if len(self._healing_history) > 100:
            self._healing_history = self._healing_history[-100:]

        # Register scar
        if wound.scar_tissue:
            self._scar_registry.append({
                "wound_id": wound_id,
                "type": wound.wound_type.value,
                "scar_score": scar_score,
                "healed_at": time.time(),
            })

        self._logger.info(
            "wound_healed",
            wound_id=wound_id[:16],
            healed=verification["passed"],
            scar=scar_score,
            time_to_heal=round(time_to_heal, 1),
        )
        return verification

    # ── Full Auto-Healing Pipeline ──────────────────────────────────

    def auto_heal(self, wound_id: str,
                  available_abilities: list[str] | None = None,
                  test_results: dict[str, Any] | None = None) -> HealingCycle:
        """Run the complete healing cascade automatically.

        Hemostasis (detect) → Inflammation (diagnose) → Proliferation (repair) → Remodeling (verify).
        """
        wound = self._active_wounds.get(wound_id)
        if wound is None:
            raise ValueError(f"Wound {wound_id} not found")

        cycle = HealingCycle(cycle_id=self._gen_id("cycle"), wound=wound)

        # Phase 2: Diagnose
        cycle.inflammation_result = self.diagnose(wound_id)

        # Phase 3: Repair
        cycle.proliferation_result = self.repair(wound_id, available_abilities)

        # Phase 4: Verify
        cycle.remodeling_result = self.verify(wound_id, test_results)

        cycle.healed = cycle.remodeling_result.get("passed", False)
        cycle.completed_at = time.time()
        cycle.time_to_heal = cycle.completed_at - cycle.started_at

        return cycle

    # ── Health Query ────────────────────────────────────────────────

    def _calculate_current_health(self, wound: Wound) -> float:
        """Calculate current health of the affected components."""
        scores = [
            r.health_score
            for c, r in self._health_reports.items()
            if c in wound.affected_components
        ]
        return sum(scores) / max(len(scores), 1)

    def _assess_scar(self, wound: Wound) -> float:
        """Assess scar tissue severity (tech debt).

        A scar is inevitable with any repair — the question is how bad.
        Score 0 = perfect healing, 1 = severe scarring.
        """
        score = 0.0
        # Speed of healing: rapid healing → more likely to scar
        elapsed = time.time() - wound.detected_at
        if elapsed < 60:  # Healed too fast → likely superficial fix
            score += 0.3
        # Severity: more severe → more likely to scar
        severity_weights = {"mild": 0.1, "moderate": 0.3, "severe": 0.5, "critical": 0.8}
        score += severity_weights.get(wound.severity.value, 0.3) * 0.5
        # Type: some wounds scar more
        type_weights = {
            "agent_failure": 0.2, "strategy_degradation": 0.4,
            "knowledge_contamination": 0.5, "resource_exhaustion": 0.1,
            "coordination_breakdown": 0.6, "drift_avalanche": 0.7,
        }
        score += type_weights.get(wound.wound_type.value, 0.3) * 0.2
        return round(min(1.0, score), 2)

    def get_layer_health(self) -> dict[str, float]:
        return dict(self._layer_health)

    def get_active_wounds(self) -> list[Wound]:
        return [w for w in self._active_wounds.values() if not w.healing_complete]

    def get_wound(self, wound_id: str) -> Wound | None:
        return self._active_wounds.get(wound_id)

    def get_healing_history(self, limit: int = 20) -> list[HealingCycle]:
        return self._healing_history[-limit:]

    def get_scar_registry(self) -> list[dict[str, Any]]:
        """Get all known scars (tech debt registry)."""
        return list(self._scar_registry)

    def get_current_phase(self, wound_id: str) -> HealingPhase | None:
        return self._wound_phase.get(wound_id)

    _id_counter: int = 0

    @classmethod
    def _gen_id(cls, prefix: str) -> str:
        cls._id_counter += 1
        return hashlib.md5(f"{prefix}|{time.time()}|{cls._id_counter}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        active = self.get_active_wounds()
        return {
            "layer_health": dict(self._layer_health),
            "active_wounds": len(active),
            "wounds_by_severity": {
                s.value: sum(1 for w in active if w.severity == s)
                for s in WoundSeverity
            },
            "wounds_by_phase": {
                p.value: sum(1 for wid, p in self._wound_phase.items()
                            if wid in self._active_wounds and not self._active_wounds[wid].healing_complete)
                for p in HealingPhase
            },
            "total_healed": len(self._healing_history),
            "scar_count": len(self._scar_registry),
            "avg_time_to_heal": (
                sum(c.time_to_heal for c in self._healing_history[-20:]) /
                max(len(self._healing_history[-20:]), 1)
            ),
        }
