"""L5→L0 Bridge: ClusterFeedbackBridge — "肌肉→大脑本体感觉" 集群反馈自适应桥.

Biological Metaphor:
  本体感觉(Proprioception)——肌肉中的肌梭和腱器官:
    持续向大脑报告: 肌肉长度/张力/运动速度
    大脑据此调整下一个运动指令(闭环控制)
    这就是为什么你闭着眼睛也能摸到自己的鼻子

  我们映射:
    肌梭(Muscle Spindle) = Agent性能指标(Sharpe, 胜率, 执行延迟)
    腱器官(Golgi Tendon Organ) = 集群全局健康(成功率, 资源利用率)
    背柱-内侧丘系通路 = 本桥(L5→L0反馈信道)
    小脑 = L0自适应引擎(根据反馈微调参数)

  核心机制:
    集群总体Sharpe<0 → L0收紧安全门(如同疼痛反馈→减少活动幅度)
    某类Agent频繁失败 → L0降低该类策略权重(如同肌无力→减少负重)
    涌现模式检测 → L0标记为新体制候选(如同新运动模式的"肌肉记忆")

Reference:
  Proske & Gandevia (2012), "The proprioceptive senses", Journal of Physiology;
  Schuler et al. (2026), "EAS", IJMS 27(3):1345 — endocrine feedback loops
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


class FeedbackSignal(str, Enum):
    """Types of proprioceptive signals sent back to L0."""
    SAFETY_TIGHTEN = "safety_tighten"        # Like pain → reduce range of motion
    SAFETY_RELAX = "safety_relax"            # Like comfort → increase activity
    WEIGHT_DECREASE = "weight_decrease"      # Like muscle weakness → reduce load
    WEIGHT_INCREASE = "weight_increase"      # Like muscle strength → increase load
    REGIME_CANDIDATE = "regime_candidate"     # Like new motor pattern → muscle memory
    RESOURCE_REBALANCE = "resource_rebalance"  # Like fatigue → redistribute workload
    NO_CHANGE = "no_change"                   # Homeostasis maintained


class MuscleTone(str, Enum):
    """Analogous to muscle tone — the baseline tension in the system."""
    HYPOTONIC = "hypotonic"    # Too relaxed, under-responsive
    NORMOTONIC = "normotonic"  # Healthy balance
    HYPERTONIC = "hypertonic"  # Too tense, over-reactive
    SPASTIC = "spastic"        # Dangerously over-reactive


@dataclass
class ProprioceptiveReading:
    """A single 'proprioceptive' reading from the cluster.

    Like a muscle spindle reporting length/tension to the spinal cord.
    """

    reading_id: str
    source: str  # "agent_pool", "consensus", "evolution", "global"

    # Muscle spindle analogs (agent performance)
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    avg_return: float = 0.0
    max_drawdown: float = 0.0

    # Golgi tendon organ analogs (global health)
    success_rate: float = 1.0
    resource_utilization: float = 0.0
    agent_count: int = 0
    failure_count: int = 0

    # Specialty breakdown (like muscle groups)
    specialty_performance: dict[str, float] = field(default_factory=dict)
    specialty_failures: dict[str, int] = field(default_factory=dict)

    # Emergence detection
    emergent_patterns: list[dict[str, Any]] = field(default_factory=list)

    timestamp: float = field(default_factory=time.time)


@dataclass
class FeedbackAction:
    """An action sent from L5 back to L0 adaptive engine.

    Like the cerebellum sending a corrective signal to the motor cortex.
    """

    action_id: str
    signal: FeedbackSignal
    target: str  # Which L0 component to adjust (safety_gate, strategy_adapter, etc.)
    parameter: str  # Which parameter to adjust
    current_value: float
    recommended_value: float
    adjustment_magnitude: float  # 0-1, how strong the adjustment
    confidence: float  # 0-1, how confident we are in this recommendation
    reason: str
    source_reading_id: str = ""
    timestamp: float = field(default_factory=time.time)


class ClusterFeedbackBridge:
    """Proprioception: L5 cluster execution → L0 adaptive parameter adjustment.

    Config:
      - sharpe_danger_threshold: below this → tighten safety gate
      - failure_rate_threshold: above this per-specialty → reduce weight
      - emergence_min_occurrences: pattern occurrences to flag as regime candidate
      - cooldown_period: minimum seconds between successive adjustment signals of same type
    """

    def __init__(
        self,
        sharpe_danger_threshold: float = 0.0,
        failure_rate_threshold: float = 0.3,
        emergence_min_occurrences: int = 3,
        cooldown_period: float = 300.0,
    ) -> None:
        self._sharpe_danger = sharpe_danger_threshold
        self._failure_threshold = failure_rate_threshold
        self._emergence_min = emergence_min_occurrences
        self._cooldown = cooldown_period

        self._readings: list[ProprioceptiveReading] = []
        self._actions: list[FeedbackAction] = []
        self._last_signal_time: dict[str, float] = {}  # signal_type → last sent time
        self._muscle_tone = MuscleTone.NORMOTONIC
        self._muscle_tone_history: list[tuple[float, str]] = []  # [(timestamp, tone)]

        self._logger = CortexLogger("feedback_adaptive_bridge")

    # ── Core Bridge: Cluster State → L0 Adjustments ──────────────────

    def sense(self, reading: ProprioceptiveReading) -> list[FeedbackAction]:
        """Read the cluster's 'proprioceptive state' and generate corrective actions.

        Like the muscle spindle + Golgi tendon organ sending signals
        through the dorsal column-medial lemniscus pathway to the brain.
        """
        self._readings.append(reading)
        if len(self._readings) > 1000:
            self._readings = self._readings[-1000:]

        actions: list[FeedbackAction] = []

        # 1. Safety gate adjustment (Golgi tendon organ — tension sensing)
        safety_action = self._check_safety_gate(reading)
        if safety_action:
            actions.append(safety_action)

        # 2. Strategy weight adjustment (muscle spindle — length/load sensing)
        weight_actions = self._check_specialty_weights(reading)
        actions.extend(weight_actions)

        # 3. Emergence detection (new motor pattern — muscle memory formation)
        emergence_action = self._check_emergence(reading)
        if emergence_action:
            actions.append(emergence_action)

        # 4. Resource rebalancing (fatigue sensing)
        resource_action = self._check_resource_balance(reading)
        if resource_action:
            actions.append(resource_action)

        # Update muscle tone
        self._update_muscle_tone(reading)

        # Apply cooldown filter
        filtered = self._apply_cooldown(actions)
        self._actions.extend(filtered)

        if filtered:
            self._logger.info(
                "feedback_generated",
                reading_id=reading.reading_id[:16],
                actions=len(filtered),
                signals=[a.signal.value for a in filtered],
            )
        return filtered

    def sense_from_stats(
        self,
        sharpe: float,
        win_rate: float,
        success_rate: float,
        agent_count: int,
        failure_count: int,
        specialty_perf: dict[str, float] | None = None,
        specialty_fail: dict[str, int] | None = None,
    ) -> list[FeedbackAction]:
        """Convenience method: create a reading from raw stats and process."""
        reading = ProprioceptiveReading(
            reading_id=self._gen_id("reading"),
            source="manual",
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            success_rate=success_rate,
            agent_count=agent_count,
            failure_count=failure_count,
            specialty_performance=specialty_perf or {},
            specialty_failures=specialty_fail or {},
        )
        return self.sense(reading)

    # ── Proprioceptive Checks ────────────────────────────────────────

    def _check_safety_gate(
        self, reading: ProprioceptiveReading,
    ) -> FeedbackAction | None:
        """Check if safety gate needs adjustment (like Golgi tendon organ).

        If Sharpe < danger threshold → tighten safety (reduce position sizes)
        If Sharpe > healthy and previously tightened → relax safety
        """
        if reading.sharpe_ratio < self._sharpe_danger:
            magnitude = min(1.0, abs(reading.sharpe_ratio - self._sharpe_danger) / 1.0)
            return FeedbackAction(
                action_id=self._gen_id("action"),
                signal=FeedbackSignal.SAFETY_TIGHTEN,
                target="safety_gate",
                parameter="max_position_pct",
                current_value=0.15,  # default from PolicyEngine
                recommended_value=max(0.03, 0.15 * (1.0 - magnitude * 0.5)),
                adjustment_magnitude=round(magnitude, 3),
                confidence=min(0.9, abs(reading.sharpe_ratio) / 2.0),
                reason=f"Sharpe {reading.sharpe_ratio:.3f} < danger {self._sharpe_danger}",
                source_reading_id=reading.reading_id,
            )

        if reading.sharpe_ratio > 1.0 and self._muscle_tone in (MuscleTone.HYPERTONIC, MuscleTone.SPASTIC):
            return FeedbackAction(
                action_id=self._gen_id("action"),
                signal=FeedbackSignal.SAFETY_RELAX,
                target="safety_gate",
                parameter="max_position_pct",
                current_value=0.15,
                recommended_value=0.20,
                adjustment_magnitude=0.3,
                confidence=0.6,
                reason=f"Sharpe healthy ({reading.sharpe_ratio:.2f}), relaxing from {self._muscle_tone.value}",
                source_reading_id=reading.reading_id,
            )
        return None

    def _check_specialty_weights(
        self, reading: ProprioceptiveReading,
    ) -> list[FeedbackAction]:
        """Check if any specialty needs weight adjustment (like muscle weakness).

        If a specialty's failure rate > threshold → reduce its weight.
        If a specialty consistently outperforms → increase its weight.
        """
        actions: list[FeedbackAction] = []

        for specialty, perf in reading.specialty_performance.items():
            failures = reading.specialty_failures.get(specialty, 0)
            # Estimate failure rate
            total_agents = max(1, reading.agent_count // max(1, len(reading.specialty_performance)))
            fail_rate = failures / max(total_agents, 1)

            if fail_rate > self._failure_threshold:
                actions.append(FeedbackAction(
                    action_id=self._gen_id("action"),
                    signal=FeedbackSignal.WEIGHT_DECREASE,
                    target="strategy_adapter",
                    parameter=f"weight_{specialty}",
                    current_value=perf,
                    recommended_value=max(0.1, perf * (1.0 - fail_rate)),
                    adjustment_magnitude=round(min(0.5, fail_rate), 3),
                    confidence=round(min(0.8, fail_rate * 1.5), 3),
                    reason=f"Specialty '{specialty}' failure rate {fail_rate:.1%} > {self._failure_threshold:.1%}",
                    source_reading_id=reading.reading_id,
                ))
            elif perf > 0.8 and fail_rate < 0.1:
                actions.append(FeedbackAction(
                    action_id=self._gen_id("action"),
                    signal=FeedbackSignal.WEIGHT_INCREASE,
                    target="strategy_adapter",
                    parameter=f"weight_{specialty}",
                    current_value=perf,
                    recommended_value=min(1.0, perf * 1.1),
                    adjustment_magnitude=0.1,
                    confidence=0.7,
                    reason=f"Specialty '{specialty}' performing well (perf={perf:.2f}, low failures)",
                    source_reading_id=reading.reading_id,
                ))

        return actions

    def _check_emergence(
        self, reading: ProprioceptiveReading,
    ) -> FeedbackAction | None:
        """Check for emergent patterns that might indicate new regime (like muscle memory).

        When the same pattern appears multiple times across different readings,
        it may be worth flagging to L0 as a regime candidate.
        """
        if len(reading.emergent_patterns) < self._emergence_min:
            return None

        # Check if similar patterns existed in recent readings
        pattern_names = [p.get("name", "") for p in reading.emergent_patterns]
        recent_patterns: dict[str, int] = defaultdict(int)
        for r in self._readings[-20:]:
            for p in r.emergent_patterns:
                recent_patterns[p.get("name", "")] += 1

        for name in pattern_names:
            if recent_patterns.get(name, 0) >= self._emergence_min:
                return FeedbackAction(
                    action_id=self._gen_id("action"),
                    signal=FeedbackSignal.REGIME_CANDIDATE,
                    target="regime_orchestrator",
                    parameter="regime_candidate",
                    current_value=0.0,
                    recommended_value=1.0,
                    adjustment_magnitude=0.5,
                    confidence=min(0.8, recent_patterns[name] / 10),
                    reason=f"Emergent pattern '{name}' detected {recent_patterns[name]} times",
                    source_reading_id=reading.reading_id,
                )
        return None

    def _check_resource_balance(
        self, reading: ProprioceptiveReading,
    ) -> FeedbackAction | None:
        """Check if resources need rebalancing (like fatigue redistribution).

        High utilization → signal to redistribute workload.
        """
        if reading.resource_utilization > 0.85:
            return FeedbackAction(
                action_id=self._gen_id("action"),
                signal=FeedbackSignal.RESOURCE_REBALANCE,
                target="resource_allocator",
                parameter="resource_budget",
                current_value=reading.resource_utilization,
                recommended_value=min(1.0, reading.resource_utilization + 0.1),
                adjustment_magnitude=0.3,
                confidence=0.75,
                reason=f"High resource utilization: {reading.resource_utilization:.1%}",
                source_reading_id=reading.reading_id,
            )
        if reading.resource_utilization < 0.2 and reading.agent_count > 5:
            return FeedbackAction(
                action_id=self._gen_id("action"),
                signal=FeedbackSignal.RESOURCE_REBALANCE,
                target="resource_allocator",
                parameter="resource_budget",
                current_value=reading.resource_utilization,
                recommended_value=0.3,
                adjustment_magnitude=0.2,
                confidence=0.5,
                reason=f"Low resource utilization: {reading.resource_utilization:.1%}",
                source_reading_id=reading.reading_id,
            )
        return None

    # ── Muscle Tone (System-Level State) ─────────────────────────────

    def _update_muscle_tone(self, reading: ProprioceptiveReading) -> None:
        """Update the system's 'muscle tone' based on cluster health.

        Like the nervous system maintaining baseline muscle tension.
        """
        if reading.sharpe_ratio < -0.5 or reading.failure_count > reading.agent_count * 0.5:
            tone = MuscleTone.SPASTIC
        elif reading.sharpe_ratio < 0.0 or reading.success_rate < 0.6:
            tone = MuscleTone.HYPERTONIC
        elif reading.sharpe_ratio > 1.0 and reading.success_rate > 0.9:
            tone = MuscleTone.HYPOTONIC
        else:
            tone = MuscleTone.NORMOTONIC

        self._muscle_tone = tone
        self._muscle_tone_history.append((time.time(), tone.value))
        if len(self._muscle_tone_history) > 200:
            self._muscle_tone_history = self._muscle_tone_history[-200:]

    def get_muscle_tone(self) -> MuscleTone:
        """Get current muscle tone."""
        return self._muscle_tone

    # ── Cooldown Management ──────────────────────────────────────────

    def _apply_cooldown(self, actions: list[FeedbackAction]) -> list[FeedbackAction]:
        """Filter out actions that violate cooldown periods.

        Like the refractory period after a neuron fires.
        """
        now = time.time()
        filtered: list[FeedbackAction] = []
        for action in actions:
            signal_key = f"{action.signal.value}:{action.parameter}"
            last = self._last_signal_time.get(signal_key, 0)
            if now - last >= self._cooldown:
                self._last_signal_time[signal_key] = now
                filtered.append(action)
            else:
                self._logger.debug("cooldown_skipped", signal=action.signal.value, remaining=round(self._cooldown - (now - last), 1))
        return filtered

    # ── Query Interface ───────────────────────────────────────────────

    def get_recent_readings(self, limit: int = 20) -> list[ProprioceptiveReading]:
        return self._readings[-limit:]

    def get_recent_actions(
        self, limit: int = 50, signal: FeedbackSignal | None = None,
    ) -> list[FeedbackAction]:
        """Get recent feedback actions, optionally filtered by signal type."""
        actions = self._actions
        if signal:
            actions = [a for a in actions if a.signal == signal]
        return actions[-limit:]

    def get_muscle_tone_timeline(
        self, lookback: int = 20,
    ) -> list[tuple[float, str]]:
        """Get recent muscle tone history."""
        return self._muscle_tone_history[-lookback:]

    def get_l0_adjustment_summary(self) -> dict[str, Any]:
        """Generate a summary of recommended L0 adjustments.

        This can be consumed by L0 adaptive components directly.
        """
        recent = self._actions[-50:]
        by_target: dict[str, list[FeedbackAction]] = defaultdict(list)
        for a in recent:
            by_target[a.target].append(a)

        summary: dict[str, Any] = {}
        for target, actions in by_target.items():
            params: dict[str, float] = {}
            for a in actions:
                if a.parameter not in params:
                    params[a.parameter] = a.recommended_value
                else:
                    # Average repeated recommendations with recency weight
                    params[a.parameter] = params[a.parameter] * 0.7 + a.recommended_value * 0.3
            summary[target] = {
                "params": params,
                "last_signal": actions[-1].signal.value if actions else "none",
                "count": len(actions),
            }

        return {
            "muscle_tone": self._muscle_tone.value,
            "adjustments": summary,
            "total_actions": len(self._actions),
        }

    @staticmethod
    def _gen_id(prefix: str) -> str:
        return hashlib.md5(f"{prefix}|{time.time()}".encode()).hexdigest()[:16]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "readings": len(self._readings),
            "actions": len(self._actions),
            "muscle_tone": self._muscle_tone.value,
            "last_reading_at": self._readings[-1].timestamp if self._readings else 0,
        }
