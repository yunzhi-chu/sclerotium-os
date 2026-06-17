"""Phase 6.1: CrossLayerEmergence — "意识涌现"(NCC: Neural Correlates of Consciousness).

Biological Metaphor:
  意识的涌现(NCC): 单个神经元不知道自己在思考——但当860亿个神经元
  通过100万亿个突触连接协同放电时→意识涌现
  "整体大于部分之和"(Aristotle)

  地衣全息体(Lichen Holobiont)的生态型(Ecotype)形成:
    当所有三个界(真菌+藻类+细菌)的基因同时发生表达变化
    → 可能正在形成新的生态型
    → 这是一个跨界的、同步的、结构性的转变

  我们映射:
    L0 新体制检测 = 真菌界基因表达变化(感知环境剧变)
    L3 辩论模式改变 = 藻类界光合作用路径切换(能量代谢重组)
    L5 Agent分布重组 = 细菌界群落结构重塑(功能分工变化)
    三者同时触发 → StructuralRegimeShift (结构性市场变迁)
    → 触发全系统重新校准 (如同身体启动"全身炎症反应")

机制:
  三层同时异常检测:
    L0检测到新体制(前期感觉异常)
    + L3辩论模式显著改变(认知冲突: "这个信号是什么意思?")
    + L5 Agent分布发生重组(行为改变: "我需要换一批工人")
    → 可能是结构性市场变迁(如同"生态系统的regime shift")
    → 触发全系统重新校准(如同身体启动"全身炎症反应")

Reference:
  Mawarda et al. (2026), "Lichen holobiont resilience", Env Microbiome;
  Dehaene & Changeux (2011), "Neural Correlates of Consciousness", Neuron;
  Koch et al. (2016), "Neural correlates of consciousness", Nature Reviews Neuroscience
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


# ── Emergence Level ────────────────────────────────────────────────────

class EmergenceLevel(str, Enum):
    """Consciousness level of the cross-layer emergence."""
    DORMANT = "dormant"          # No significant cross-layer signal
    PRE_CONSCIOUS = "pre_conscious"  # One or two layers anomalous
    CONSCIOUS = "conscious"       # Three layers simultaneously anomalous
    SELF_AWARE = "self_aware"    # Sustained conscious + pattern recognized
    RECALIBRATING = "recalibrating"  # System actively reconfiguring


class ShiftType(str, Enum):
    """Type of structural shift detected."""
    REGIME_SHIFT = "regime_shift"       # Market regime fundamentally changed
    PARADIGM_SHIFT = "paradigm_shift"    # Trading paradigm changed (e.g., new asset class)
    ECOTYPE_FORMATION = "ecotype_formation"  # New agent ecotype emerging
    NONE = "none"


# ── Data Classes ──────────────────────────────────────────────────────

@dataclass
class LayerSignal:
    """A signal from one layer — like a neuron's firing pattern."""

    layer: str  # L0, L3, L5
    signal_type: str
    value: float  # Normalized anomaly score 0-1
    confidence: float  # 0-1
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class EmergenceEvent:
    """A detected cross-layer emergence — like a moment of 'consciousness'."""

    event_id: str
    level: EmergenceLevel
    shift_type: ShiftType

    # Triple-layer signals
    l0_signals: list[LayerSignal] = field(default_factory=list)
    l3_signals: list[LayerSignal] = field(default_factory=list)
    l5_signals: list[LayerSignal] = field(default_factory=list)

    # Coherence score: how well the three layers' signals align
    coherence_score: float = 0.0

    # Action recommendation
    recommended_action: str = ""
    recalibration_plan: dict[str, Any] = field(default_factory=dict)

    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    resolved_at: float = 0.0


@dataclass
class EcotypeProfile:
    """A recognized cross-layer pattern — like a learned 'concept'."""

    ecotype_id: str
    name: str
    description: str

    # Signature: what combination of L0/L3/L5 signals defines this ecotype
    l0_signature: dict[str, Any]  # e.g., {"regime": "bear", "confidence_min": 0.7}
    l3_signature: dict[str, Any]  # e.g., {"refute_rate_min": 0.6}
    l5_signature: dict[str, Any]  # e.g., {"specialty_shift": ["strategy", "risk"]}

    occurrence_count: int = 0
    last_seen: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)


class CrossLayerEmergence:
    """NCC: Detects when L0 + L3 + L5 simultaneously signal structural change.

    Like the brain becoming 'conscious' of a pattern that no single
    neuron could perceive alone.

    Config:
      - anomaly_threshold: minimum signal value to count as anomalous
      - coherence_min: minimum coherence score to trigger emergence
      - conscious_window: time window (s) within which all 3 layers must fire
      - recalibration_cooldown: minimum time between recalibrations
      - history_size: max emergence events to retain
    """

    def __init__(
        self,
        anomaly_threshold: float = 0.5,
        coherence_min: float = 0.6,
        conscious_window: float = 300.0,  # 5 minutes
        recalibration_cooldown: float = 3600.0,  # 1 hour
        history_size: int = 200,
    ) -> None:
        self._anomaly_threshold = anomaly_threshold
        self._coherence_min = coherence_min
        self._conscious_window = conscious_window
        self._recalibration_cooldown = recalibration_cooldown

        # Signal buffers per layer (ring buffers)
        self._signals: dict[str, deque[LayerSignal]] = {
            "L0": deque(maxlen=500),
            "L3": deque(maxlen=500),
            "L5": deque(maxlen=500),
        }

        # Emergence state
        self._current_level = EmergenceLevel.DORMANT
        self._events: list[EmergenceEvent] = []
        self._ecotypes: dict[str, EcotypeProfile] = {}
        self._last_recalibration: float = 0.0
        self._level_history: list[tuple[float, str]] = []

        # Cross-layer statistics
        self._coherence_scores: deque[float] = deque(maxlen=100)

        self._logger = CortexLogger("cross_layer_emergence")

    # ── Signal Input (from each layer) ──────────────────────────────

    def observe_l0(self, signal_type: str, value: float, confidence: float,
                   description: str = "", metadata: dict[str, Any] | None = None) -> None:
        """Receive an L0 signal — like sensory input entering consciousness."""
        signal = LayerSignal(
            layer="L0", signal_type=signal_type,
            value=value, confidence=confidence,
            description=description, metadata=metadata or {},
        )
        self._signals["L0"].append(signal)
        self._check_emergence()

    def observe_l3(self, signal_type: str, value: float, confidence: float,
                   description: str = "", metadata: dict[str, Any] | None = None) -> None:
        """Receive an L3 signal — like cognitive conflict detection."""
        signal = LayerSignal(
            layer="L3", signal_type=signal_type,
            value=value, confidence=confidence,
            description=description, metadata=metadata or {},
        )
        self._signals["L3"].append(signal)
        self._check_emergence()

    def observe_l5(self, signal_type: str, value: float, confidence: float,
                   description: str = "", metadata: dict[str, Any] | None = None) -> None:
        """Receive an L5 signal — like behavioral change detection."""
        signal = LayerSignal(
            layer="L5", signal_type=signal_type,
            value=value, confidence=confidence,
            description=description, metadata=metadata or {},
        )
        self._signals["L5"].append(signal)
        self._check_emergence()

    # ── Observation from structured reports ────────────────────────

    def observe_regime_change(self, from_regime: str, to_regime: str,
                              confidence: float, entropy: float = 0.0) -> None:
        """Observe L0 regime change via structured data."""
        is_new = to_regime not in ("equilibrium", "sideways", "range")
        anomaly_value = confidence * (1.0 if is_new else 0.3)
        self.observe_l0(
            signal_type="regime_change",
            value=anomaly_value,
            confidence=confidence,
            description=f"Regime: {from_regime} → {to_regime}",
            metadata={"from": from_regime, "to": to_regime, "entropy": entropy},
        )

    def observe_debate_shift(self, verify_rate: float, refute_rate: float,
                             avg_net_price: float, confidence: float) -> None:
        """Observe L3 debate pattern shift."""
        # High refute rate or unusual net_price → anomalous
        anomaly = max(
            abs(refute_rate - 0.3),  # Deviation from normal 30% refute rate
            abs(avg_net_price),       # Unusual conviction
        )
        self.observe_l3(
            signal_type="debate_shift",
            value=min(1.0, anomaly),
            confidence=confidence,
            description=f"Refute={refute_rate:.1%}, NetPrice={avg_net_price:.3f}",
            metadata={"verify_rate": verify_rate, "refute_rate": refute_rate, "net_price": avg_net_price},
        )

    def observe_agent_reorganization(self, specialty_changes: dict[str, float],
                                     agent_count_delta: int, confidence: float) -> None:
        """Observe L5 agent distribution reorganization."""
        max_change = max(abs(v) for v in specialty_changes.values()) if specialty_changes else 0
        anomaly = min(1.0, max_change + abs(agent_count_delta) / 50)
        self.observe_l5(
            signal_type="agent_reorganization",
            value=anomaly,
            confidence=confidence,
            description=f"Agent count delta={agent_count_delta}, specialty changes={specialty_changes}",
            metadata={"specialty_changes": specialty_changes, "agent_delta": agent_count_delta},
        )

    # ── Core Emergence Detection ───────────────────────────────────

    def _check_emergence(self) -> EmergenceEvent | None:
        """Check if all three layers are simultaneously anomalous.

        Like the brain integrating sensory, cognitive, and behavioral signals
        into a unified conscious percept.
        """
        now = time.time()
        window_start = now - self._conscious_window

        # Extract recent anomalous signals from each layer
        l0_anomalies = [s for s in self._signals["L0"]
                        if s.timestamp > window_start and s.value >= self._anomaly_threshold]
        l3_anomalies = [s for s in self._signals["L3"]
                        if s.timestamp > window_start and s.value >= self._anomaly_threshold]
        l5_anomalies = [s for s in self._signals["L5"]
                        if s.timestamp > window_start and s.value >= self._anomaly_threshold]

        # Determine emergence level
        active_layers = sum(1 for sigs in [l0_anomalies, l3_anomalies, l5_anomalies] if sigs)

        if active_layers == 0:
            new_level = EmergenceLevel.DORMANT
        elif active_layers == 1:
            new_level = EmergenceLevel.PRE_CONSCIOUS
        elif active_layers == 2:
            new_level = EmergenceLevel.PRE_CONSCIOUS
        else:
            # All 3 layers active — compute coherence
            coherence = self._compute_coherence(l0_anomalies, l3_anomalies, l5_anomalies)
            self._coherence_scores.append(coherence)

            if coherence >= self._coherence_min:
                new_level = EmergenceLevel.CONSCIOUS
            else:
                new_level = EmergenceLevel.PRE_CONSCIOUS

        # Detect sustained consciousness → self-aware
        if (new_level == EmergenceLevel.CONSCIOUS and
                self._current_level == EmergenceLevel.CONSCIOUS):
            new_level = EmergenceLevel.SELF_AWARE

        self._current_level = new_level
        self._level_history.append((now, new_level.value))

        # If conscious or self-aware → generate emergence event
        if new_level in (EmergenceLevel.CONSCIOUS, EmergenceLevel.SELF_AWARE):
            event = self._generate_emergence_event(
                new_level, l0_anomalies, l3_anomalies, l5_anomalies,
            )
            return event

        return None

    def _compute_coherence(
        self,
        l0_signals: list[LayerSignal],
        l3_signals: list[LayerSignal],
        l5_signals: list[LayerSignal],
    ) -> float:
        """Compute cross-layer coherence score.

        High coherence = the three layers are telling a consistent story.
        Like measuring how synchronized different brain regions are.
        """
        # Average anomaly values
        l0_val = sum(s.value for s in l0_signals) / max(len(l0_signals), 1)
        l3_val = sum(s.value for s in l3_signals) / max(len(l3_signals), 1)
        l5_val = sum(s.value for s in l5_signals) / max(len(l5_signals), 1)

        # Average confidences
        l0_conf = sum(s.confidence for s in l0_signals) / max(len(l0_signals), 1)
        l3_conf = sum(s.confidence for s in l3_signals) / max(len(l3_signals), 1)
        l5_conf = sum(s.confidence for s in l5_signals) / max(len(l5_signals), 1)

        # Coherence = how similar the anomaly values are (low variance = high coherence)
        vals = [l0_val, l3_val, l5_val]
        mean_val = sum(vals) / 3
        variance = sum((v - mean_val) ** 2 for v in vals) / 3
        value_coherence = 1.0 - min(1.0, math.sqrt(variance) * 2)

        # Also factor in confidence (low confidence → lower coherence)
        avg_conf = (l0_conf + l3_conf + l5_conf) / 3

        return value_coherence * 0.6 + avg_conf * 0.4

    def _generate_emergence_event(
        self,
        level: EmergenceLevel,
        l0_signals: list[LayerSignal],
        l3_signals: list[LayerSignal],
        l5_signals: list[LayerSignal],
    ) -> EmergenceEvent:
        """Generate an emergence event with analysis and recommendations."""
        coherence = self._compute_coherence(l0_signals, l3_signals, l5_signals)

        # Determine shift type
        shift_type = self._classify_shift(l0_signals, l3_signals, l5_signals)

        # Generate recalibration plan if needed
        plan: dict[str, Any] = {}
        action = "monitor"
        if level in (EmergenceLevel.CONSCIOUS, EmergenceLevel.SELF_AWARE):
            action, plan = self._generate_recalibration_plan(
                shift_type, l0_signals, l3_signals, l5_signals,
            )

        event = EmergenceEvent(
            event_id=self._gen_id("emergence"),
            level=level,
            shift_type=shift_type,
            l0_signals=list(l0_signals[-5:]),
            l3_signals=list(l3_signals[-5:]),
            l5_signals=list(l5_signals[-5:]),
            coherence_score=round(coherence, 4),
            recommended_action=action,
            recalibration_plan=plan,
        )

        self._events.append(event)
        if len(self._events) > 200:
            self._events = self._events[-200:]

        self._logger.info(
            "emergence_detected",
            emergence_level=level.value,
            shift=shift_type.value,
            coherence=round(coherence, 3),
            action=action,
        )
        return event

    def _classify_shift(
        self,
        l0_signals: list[LayerSignal],
        l3_signals: list[LayerSignal],
        l5_signals: list[LayerSignal],
    ) -> ShiftType:
        """Classify the type of structural shift."""
        # Check for regime shift (L0-dominated)
        regime_signals = [s for s in l0_signals if s.signal_type == "regime_change"]
        if regime_signals and any(s.value > 0.7 for s in regime_signals):
            return ShiftType.REGIME_SHIFT

        # Check for ecotype formation (L5-dominated with L3 support)
        agent_signals = [s for s in l5_signals if s.signal_type == "agent_reorganization"]
        debate_signals = [s for s in l3_signals if s.signal_type == "debate_shift"]
        if agent_signals and debate_signals:
            return ShiftType.ECOTYPE_FORMATION

        # Check for paradigm shift (all three equally strong)
        if l0_signals and l3_signals and l5_signals:
            avg_val = (
                sum(s.value for s in l0_signals) / len(l0_signals) +
                sum(s.value for s in l3_signals) / len(l3_signals) +
                sum(s.value for s in l5_signals) / len(l5_signals)
            ) / 3
            if avg_val > 0.8:
                return ShiftType.PARADIGM_SHIFT

        return ShiftType.REGIME_SHIFT

    def _generate_recalibration_plan(
        self,
        shift_type: ShiftType,
        l0_signals: list[LayerSignal],
        l3_signals: list[LayerSignal],
        l5_signals: list[LayerSignal],
    ) -> tuple[str, dict[str, Any]]:
        """Generate a system-wide recalibration plan.

        Like the body initiating a systemic inflammatory response.
        """
        now = time.time()
        if now - self._last_recalibration < self._recalibration_cooldown:
            return "cooldown", {"reason": "Recalibration too soon", "next_available": self._last_recalibration + self._recalibration_cooldown}

        plan: dict[str, Any] = {
            "shift_type": shift_type.value,
            "layers_affected": [],
            "steps": [],
        }

        if shift_type == ShiftType.REGIME_SHIFT:
            plan["layers_affected"] = ["L0", "L3"]
            plan["steps"] = [
                {"order": 1, "layer": "L0", "action": "recalibrate_regime_detectors",
                 "detail": "Reset HMM/CUSUM/GTH-Net baselines with 50% weight to recent window"},
                {"order": 2, "layer": "L3", "action": "reset_debate_thresholds",
                 "detail": "Lower confidence threshold temporarily to allow new signal patterns"},
                {"order": 3, "layer": "L5", "action": "diversify_agent_specialties",
                 "detail": "Spawn exploratory agents in underweighted specialties"},
            ]
            action = "recalibrate_all"

        elif shift_type == ShiftType.ECOTYPE_FORMATION:
            plan["layers_affected"] = ["L5", "L3"]
            plan["steps"] = [
                {"order": 1, "layer": "L5", "action": "create_ecotype_niche",
                 "detail": "Allocate 20% resource budget to new agent ecotype"},
                {"order": 2, "layer": "L3", "action": "validate_ecotype",
                 "detail": "Run 3-round debate on new ecotype's edge over existing"},
                {"order": 3, "layer": "L0", "action": "register_pattern",
                 "detail": "Record cross-layer pattern as new regime candidate"},
            ]
            action = "cultivate_ecotype"

        elif shift_type == ShiftType.PARADIGM_SHIFT:
            plan["layers_affected"] = ["L0", "L3", "L5"]
            plan["steps"] = [
                {"order": 1, "layer": "ALL", "action": "emergency_recalibration",
                 "detail": "Full system recalibration: reset all detectors, clear short-term memory, restart debate engines"},
                {"order": 2, "layer": "L5", "action": "purge_underperformers",
                 "detail": "Apoptose bottom 30% agents and respawn with new parameters"},
                {"order": 3, "layer": "L0", "action": "cold_start_regime_learning",
                 "detail": "Restart regime detection from scratch with 2x learning rate"},
            ]
            action = "emergency_recalibration"

        else:
            action = "monitor"

        self._last_recalibration = now
        return action, plan

    # ── Ecotype Management ──────────────────────────────────────────

    def recognize_ecotype(self, name: str, description: str,
                          l0_sig: dict[str, Any], l3_sig: dict[str, Any],
                          l5_sig: dict[str, Any]) -> EcotypeProfile:
        """Register a recognized cross-layer pattern (ecotype).

        Like forming a new 'concept' in neocortical semantic memory.
        """
        ecotype = EcotypeProfile(
            ecotype_id=self._gen_id("ecotype"),
            name=name,
            description=description,
            l0_signature=l0_sig,
            l3_signature=l3_sig,
            l5_signature=l5_sig,
        )
        self._ecotypes[ecotype.ecotype_id] = ecotype
        self._logger.info("ecotype_registered", name=name)
        return ecotype

    def match_ecotype(self, l0_signals: list[LayerSignal],
                      l3_signals: list[LayerSignal],
                      l5_signals: list[LayerSignal]) -> list[EcotypeProfile]:
        """Match current signals against known ecotype signatures."""
        matches = []
        for eco in self._ecotypes.values():
            score = self._match_ecotype_score(eco, l0_signals, l3_signals, l5_signals)
            if score > 0.5:
                eco.occurrence_count += 1
                eco.last_seen = time.time()
                matches.append((score, eco))
        return [m[1] for m in sorted(matches, key=lambda x: x[0], reverse=True)]

    def _match_ecotype_score(self, eco: EcotypeProfile,
                             l0_signals: list[LayerSignal],
                             l3_signals: list[LayerSignal],
                             l5_signals: list[LayerSignal]) -> float:
        """Compute how well signals match an ecotype signature."""
        score = 0.0
        checks = 0

        # L0 match
        if eco.l0_signature and l0_signals:
            l0_regime = eco.l0_signature.get("regime", "")
            for s in l0_signals:
                if l0_regime and l0_regime in s.description.lower():
                    score += 1.0
                    break
            checks += 1

        # L3 match
        if eco.l3_signature and l3_signals:
            min_refute = eco.l3_signature.get("refute_rate_min", 0)
            for s in l3_signals:
                refute = s.metadata.get("refute_rate", 0)
                if refute >= min_refute:
                    score += 1.0
                    break
            checks += 1

        # L5 match
        if eco.l5_signature and l5_signals:
            target_specialties = eco.l5_signature.get("specialty_shift", [])
            for s in l5_signals:
                changes = s.metadata.get("specialty_changes", {})
                if any(sp in changes for sp in target_specialties):
                    score += 1.0
                    break
            checks += 1

        return score / max(checks, 1)

    # ── Recalibration Execution ────────────────────────────────────

    def execute_recalibration(self, event: EmergenceEvent) -> dict[str, Any]:
        """Execute the recalibration plan from an emergence event.

        Returns a structured result that can be dispatched to layer controllers.
        """
        if not event.recalibration_plan:
            return {"status": "no_plan"}

        plan = event.recalibration_plan
        results: dict[str, list[dict[str, Any]]] = {"completed": [], "failed": []}

        for step in plan.get("steps", []):
            try:
                results["completed"].append({
                    "step": step["order"],
                    "layer": step["layer"],
                    "action": step["action"],
                    "result": "dispatched",
                })
                self._logger.info(
                    "recalibration_step",
                    step=step["order"],
                    layer=step["layer"],
                    action=step["action"],
                )
            except Exception as exc:
                results["failed"].append({
                    "step": step["order"],
                    "action": step["action"],
                    "error": str(exc),
                })

        event.resolved = True
        event.resolved_at = time.time()

        self._current_level = EmergenceLevel.RECALIBRATING
        self._level_history.append((time.time(), EmergenceLevel.RECALIBRATING.value))

        return {
            "status": "completed",
            "shift_type": plan.get("shift_type", "unknown"),
            "completed_steps": len(results["completed"]),
            "failed_steps": len(results["failed"]),
            "results": results,
        }

    # ── Query Interface ─────────────────────────────────────────────

    def get_current_level(self) -> EmergenceLevel:
        return self._current_level

    def get_recent_events(self, limit: int = 20,
                          level: EmergenceLevel | None = None) -> list[EmergenceEvent]:
        events = self._events
        if level:
            events = [e for e in events if e.level == level]
        return events[-limit:]

    def get_coherence_trend(self, window: int = 20) -> list[float]:
        return list(self._coherence_scores)[-window:]

    def get_level_history(self, lookback: int = 100) -> list[tuple[float, str]]:
        return self._level_history[-lookback:]

    def get_ecotypes(self) -> list[EcotypeProfile]:
        return sorted(self._ecotypes.values(), key=lambda e: e.occurrence_count, reverse=True)

    _id_counter: int = 0

    @classmethod
    def _gen_id(cls, prefix: str) -> str:
        cls._id_counter += 1
        return hashlib.md5(f"{prefix}|{time.time()}|{cls._id_counter}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "current_level": self._current_level.value,
            "total_events": len(self._events),
            "conscious_events": sum(1 for e in self._events if e.level in (EmergenceLevel.CONSCIOUS, EmergenceLevel.SELF_AWARE)),
            "ecotypes_known": len(self._ecotypes),
            "avg_coherence": round(sum(self._coherence_scores) / max(len(self._coherence_scores), 1), 3),
            "signals_buffered": {layer: len(buf) for layer, buf in self._signals.items()},
        }
