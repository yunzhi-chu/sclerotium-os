"""L5 4.4: EndogenousTargetEngine — "自噬+代谢稳态"(Autophagy) 内生目标引擎.

Biological Metaphor:
  自噬(Autophagy): 细胞在营养匮乏时自我消化受损线粒体和错误折叠蛋白质,
    回收氨基酸和ATP供生存所需。是身体的"春季大扫除"(Spring Cleaning)。

  空腹代谢模式: 酮体替代葡萄糖作为大脑燃料
    - 进食状态: 胰岛素高, 葡萄糖→糖原合成+脂肪合成
    - 空腹状态: 胰岛素低, 酮体↑, 自噬↑, 糖异生↑

  5个LONG_TERM_TARGETS = 五种代谢适应模式:
    improve_generalization = 线粒体生物合成(增加能量储备)
    expand_strategies = 糖原合成(储存快速可用能量)
    optimize_drift_detection = 抗氧化酶上调(增强应激抵抗)
    prune_indicators = 自噬(清除冗余, 回收资源)
    discover_regimes = 酮体代谢(启用替代代谢通路)

  触发条件: 空闲率>50%(资源充沛但无任务)→启动内生代谢
  优先级=8(低于人工指令): 如同自噬永远让位于"战斗/逃跑"应激反应

Reference:
  BCAA catabolism feedback (2026), Nature Communications;
  Endogenous metabolism models
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

class MetabolicMode(str, Enum):
    """Metabolic states — fed/fasting cycle analogs."""
    FED = "fed"          # 进食: 合成代谢
    FASTING = "fasting"  # 空腹: 自噬清洁
    EXERCISE = "exercise"  # 运动: 高能耗
    RECOVERY = "recovery"  # 恢复: 组织修复


class TargetType(str, Enum):
    """Long-term endogenous targets."""
    IMPROVE_GENERALIZATION = "improve_generalization"   # 线粒体生物合成
    EXPAND_STRATEGIES = "expand_strategies"             # 糖原合成
    OPTIMIZE_DRIFT_DETECTION = "optimize_drift_detection"  # 抗氧化酶上调
    PRUNE_INDICATORS = "prune_indicators"               # 自噬清除
    DISCOVER_REGIMES = "discover_regimes"               # 酮体代谢


# Target priorities (lower = more important)
TARGET_PRIORITY = 8  # endogenous targets are below explicit commands
IDLE_THRESHOLD = 0.5  # >50% idle triggers endogenous mode
EXECUTION_INTERVAL = 3600.0  # 1 hour between endogenous cycles
MAX_TARGETS = 10


# ── Data Structures ──────────────────────────────────────────────────


@dataclass
class EndogenousTarget:
    """A self-generated improvement target — like a metabolic adaptation program."""

    target_id: str
    target_type: TargetType
    description: str
    priority: int = TARGET_PRIORITY
    progress: float = 0.0  # 0-1
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    status: str = "pending"  # "pending", "active", "completed", "aborted"
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Main Class ───────────────────────────────────────────────────────


class EndogenousTargetEngine:
    """Self-improvement engine based on autophagy and metabolic homeostasis.

    When system is idle (>50% capacity unused), triggers self-improvement
    cycles: prune, optimize, discover, expand, generalize.

    Config:
      - idle_threshold: utilization below this triggers endogenous mode
      - execution_interval: seconds between cycles
      - target_priority: base priority for endogenous targets
    """

    _TARGET_DEFINITIONS: dict[TargetType, dict[str, Any]] = {
        TargetType.IMPROVE_GENERALIZATION: {
            "desc": "Improve strategy generalization across regimes",
            "actions": ["validate_cross_regime", "merge_similar_strategies", "regularize_params"],
            "mode": MetabolicMode.RECOVERY,
        },
        TargetType.EXPAND_STRATEGIES: {
            "desc": "Expand strategy library with new variants",
            "actions": ["mutate_top_strategies", "explore_parameter_space", "backtest_variants"],
            "mode": MetabolicMode.FED,
        },
        TargetType.OPTIMIZE_DRIFT_DETECTION: {
            "desc": "Optimize drift detection sensitivity",
            "actions": ["tune_detection_thresholds", "update_baselines", "validate_false_positives"],
            "mode": MetabolicMode.EXERCISE,
        },
        TargetType.PRUNE_INDICATORS: {
            "desc": "Prune unused/low-value indicators",
            "actions": ["identify_low_usage", "remove_redundant", "consolidate_remaining"],
            "mode": MetabolicMode.FASTING,
        },
        TargetType.DISCOVER_REGIMES: {
            "desc": "Discover new market regimes",
            "actions": ["cluster_unknown_patterns", "evaluate_stability", "register_new_regime"],
            "mode": MetabolicMode.FASTING,
        },
    }

    def __init__(
        self,
        idle_threshold: float = IDLE_THRESHOLD,
        execution_interval: float = EXECUTION_INTERVAL,
    ) -> None:
        self._idle_threshold = idle_threshold
        self._execution_interval = execution_interval

        self._targets: dict[str, EndogenousTarget] = []
        self._active_targets: list[EndogenousTarget] = []
        self._completed_targets: list[EndogenousTarget] = []
        self._mode = MetabolicMode.FED
        self._last_execution = 0.0
        self._logger = CortexLogger("endogenous_engine")

    # ── Public API ──────────────────────────────────────────────────

    def evaluate(self, system_utilization: float, market_regime: str = "neutral") -> dict[str, Any]:
        """Evaluate whether to trigger endogenous improvement cycle.

        Called periodically to check if system is idle enough for self-maintenance.
        """
        now = time.time()
        should_run = (
            system_utilization < self._idle_threshold
            and (now - self._last_execution) >= self._execution_interval
        )

        if not should_run:
            return {"triggered": False, "reason": "utilization_too_high_or_cooldown"}

        self._last_execution = now

        # Select metabolic mode based on market regime
        if market_regime in ("bear", "crash"):
            self._mode = MetabolicMode.FASTING  # conserve energy, clean up
            selected = [TargetType.PRUNE_INDICATORS, TargetType.OPTIMIZE_DRIFT_DETECTION]
        elif market_regime in ("bull", "recovery"):
            self._mode = MetabolicMode.FED  # expand, grow
            selected = [TargetType.EXPAND_STRATEGIES, TargetType.DISCOVER_REGIMES]
        else:
            self._mode = MetabolicMode.EXERCISE
            selected = [TargetType.IMPROVE_GENERALIZATION, TargetType.OPTIMIZE_DRIFT_DETECTION]

        generated = 0
        for ttype in selected:
            target = self._create_target(ttype)
            self._active_targets.append(target)
            generated += 1

        self._logger.info(
            "endogenous_cycle_triggered",
            mode=self._mode.value,
            targets=generated,
            utilization=round(system_utilization, 3),
        )
        return {
            "triggered": True,
            "mode": self._mode.value,
            "targets_generated": generated,
            "active_targets": len(self._active_targets),
        }

    def execute_next(self) -> EndogenousTarget | None:
        """Get the next pending target to execute. Returns None if all done."""
        pending = [t for t in self._active_targets if t.status == "pending"]
        if not pending:
            return None

        target = pending[0]  # FIFO
        target.status = "active"
        target.started_at = time.time()
        return target

    def complete(self, target_id: str, success: bool = True) -> bool:
        """Mark a target as completed."""
        for target in self._active_targets:
            if target.target_id == target_id:
                target.status = "completed" if success else "aborted"
                target.completed_at = time.time()
                target.progress = 1.0 if success else target.progress
                self._completed_targets.append(target)
                self._active_targets.remove(target)
                return True
        return False

    def get_targets(self, status: str | None = None) -> list[EndogenousTarget]:
        """Get targets filtered by status."""
        if status == "active":
            return list(self._active_targets)
        elif status == "completed":
            return list(self._completed_targets)
        return self._active_targets + self._completed_targets

    def cancel_all(self) -> int:
        """Cancel all active targets (e.g., when market stress detected)."""
        count = 0
        for target in self._active_targets:
            target.status = "aborted"
            count += 1
        self._completed_targets.extend(self._active_targets)
        self._active_targets.clear()
        return count

    # ── Private Methods ─────────────────────────────────────────────

    def _create_target(self, ttype: TargetType) -> EndogenousTarget:
        info = self._TARGET_DEFINITIONS.get(ttype, {})
        target = EndogenousTarget(
            target_id=self._gen_target_id(ttype.value),
            target_type=ttype,
            description=info.get("desc", str(ttype)),
            priority=TARGET_PRIORITY,
        )
        return target

    @staticmethod
    def _gen_target_id(ttype: str) -> str:
        raw = f"{ttype}|{time.time()}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @property
    def mode(self) -> MetabolicMode:
        return self._mode

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "mode": self._mode.value,
            "active_targets": len(self._active_targets),
            "completed_targets": len(self._completed_targets),
            "last_execution": self._last_execution,
            "target_breakdown": {
                ttype.value: sum(
                    1 for t in self._active_targets + self._completed_targets
                    if t.target_type == ttype
                )
                for ttype in TargetType
            },
        }
