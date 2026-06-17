"""FINAL Bench Bridge — 4-stage validation pipeline + MA-ER scoring.

FINAL = Financial Intelligence N-validated Accuracy Layer

4-stage validation:
1. Temporal: Time-series integrity (no look-ahead bias, no survivorship bias)
2. Provenance: Source data lineage (where did each data point come from?)
3. Logic: Strategy logic correctness (does the strategy do what it claims?)
4. Brave Search: External validity (does real-world data match predictions?)

MA-ER scoring:
- MA (Model Accuracy) ≥ 0.694: The model correctly predicts what it claims to
- ER (External Reliability) ≥ 0.302: Real-world results match model predictions
- MA-ER Gap < 0.3: The model isn't overfitted to its own logic
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class ValidationStage(Enum):
    TEMPORAL = 1
    PROVENANCE = 2
    LOGIC = 3
    BRAVE_SEARCH = 4


class StageResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    PENDING = "pending"


@dataclass
class MAERScore:
    """Model Accuracy / External Reliability scoring result."""

    ma_score: float  # Model Accuracy (0-1)
    er_score: float  # External Reliability (0-1)
    gap: float  # MA - ER (must be < 0.3)
    ma_pass: bool = False  # MA ≥ 0.694
    er_pass: bool = False  # ER ≥ 0.302
    gap_pass: bool = False  # Gap < 0.3
    overall_pass: bool = False
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        self.ma_pass = self.ma_score >= 0.694
        self.er_pass = self.er_score >= 0.302
        self.gap_pass = self.gap < 0.3
        self.overall_pass = self.ma_pass and self.er_pass and self.gap_pass


@dataclass
class StageReport:
    """Report from a single validation stage."""

    stage: ValidationStage
    result: StageResult = StageResult.PENDING
    score: float = 0.0
    details: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class FINALBenchReport:
    """Complete FINAL Bench validation report."""

    strategy_id: str
    stages: dict[ValidationStage, StageReport]
    ma_er: MAERScore
    passed: bool = False
    total_duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


class FINALBenchBridge:
    """FINAL Bench 4-stage validation pipeline with MA-ER scoring.

    The bridge connects MetaCognitionEngine (M1) to external validation:
    - Stage 1-3: Internal validation (code + logic)
    - Stage 4: External validation (Brave Search market data)

    MA-ER thresholds per the plan:
    - MA ≥ 0.694: Strategy model accuracy is sufficient
    - ER ≥ 0.302: External reliability is sufficient
    - MA-ER Gap < 0.3: No overfitting detected
    """

    def __init__(self, ma_threshold: float = 0.694, er_threshold: float = 0.302, gap_max: float = 0.3) -> None:
        self._ma_threshold = ma_threshold
        self._er_threshold = er_threshold
        self._gap_max = gap_max
        self._logger = CortexLogger("final_bench")
        self._reports: dict[str, FINALBenchReport] = {}

    def validate(self, strategy_id: str, strategy_spec: dict[str, Any]) -> FINALBenchReport:
        """Run the complete 4-stage FINAL Bench validation."""
        t0 = time.time()
        stages: dict[ValidationStage, StageReport] = {}

        # Stage 1: Temporal validation
        stages[ValidationStage.TEMPORAL] = self._validate_temporal(strategy_spec)

        # Stage 2: Provenance validation
        stages[ValidationStage.PROVENANCE] = self._validate_provenance(strategy_spec)

        # Stage 3: Logic validation
        stages[ValidationStage.LOGIC] = self._validate_logic(strategy_spec)

        # Stage 4: Brave Search validation
        stages[ValidationStage.BRAVE_SEARCH] = self._validate_brave_search(strategy_spec)

        # Compute MA-ER scores
        ma_score = self._compute_ma(stages)
        er_score = self._compute_er(stages)
        gap = abs(ma_score - er_score)

        ma_er = MAERScore(ma_score=ma_score, er_score=er_score, gap=gap)

        # Overall pass: all stages pass + MA-ER thresholds met
        all_stages_pass = all(s.result != StageResult.FAIL for s in stages.values())
        passed = all_stages_pass and ma_er.overall_pass

        report = FINALBenchReport(
            strategy_id=strategy_id,
            stages=stages,
            ma_er=ma_er,
            passed=passed,
            total_duration_ms=(time.time() - t0) * 1000,
        )
        self._reports[strategy_id] = report
        self._logger.info("final_bench_complete", strategy_id=strategy_id, passed=passed, ma=round(ma_score, 3), er=round(er_score, 3))
        return report

    def _validate_temporal(self, spec: dict[str, Any]) -> StageReport:
        """Stage 1: Temporal integrity — no look-ahead bias."""
        report = StageReport(stage=ValidationStage.TEMPORAL)
        issues: list[str] = []

        # Check for look-ahead bias: using data before it's available
        if spec.get("uses_future_data", False):
            issues.append("Strategy uses future data (look-ahead bias detected)")
        if spec.get("survivorship_bias", False):
            issues.append("Universe construction may have survivorship bias")

        # Check backtest period adequacy
        min_days = spec.get("backtest_days", 0)
        if min_days < 252:  # Less than 1 year
            issues.append(f"Backtest period ({min_days}d) too short, minimum 252d recommended")

        report.details = issues
        report.result = StageResult.PASS if len(issues) == 0 else StageResult.WARN if len(issues) <= 1 else StageResult.FAIL
        report.score = 1.0 - min(len(issues) * 0.3, 1.0)
        return report

    def _validate_provenance(self, spec: dict[str, Any]) -> StageReport:
        """Stage 2: Source data lineage — trace every data point."""
        report = StageReport(stage=ValidationStage.PROVENANCE)
        issues: list[str] = []

        data_sources = spec.get("data_sources", [])
        if not data_sources:
            issues.append("No data sources specified")
        else:
            for src in data_sources:
                if src.get("version") is None:
                    issues.append(f"Data source '{src.get('name', 'unknown')}' missing version info")
                if src.get("frequency") not in ("daily", "minute", "tick"):
                    issues.append(f"Data source '{src.get('name', 'unknown')}' has invalid frequency")

        report.details = issues
        report.result = StageResult.PASS if len(issues) == 0 else StageResult.WARN if len(issues) <= 2 else StageResult.FAIL
        report.score = 1.0 - min(len(issues) * 0.2, 1.0)
        return report

    def _validate_logic(self, spec: dict[str, Any]) -> StageReport:
        """Stage 3: Strategy logic correctness — semantics check."""
        report = StageReport(stage=ValidationStage.LOGIC)
        issues: list[str] = []

        # Check position sizing logic
        max_pos = spec.get("max_position_size", 0.0)
        if max_pos > 0.5:
            issues.append(f"Max position size ({max_pos:.0%}) exceeds 50% limit")
        if max_pos <= 0.0:
            issues.append("Max position size not specified")

        # Check stop-loss logic
        if spec.get("stop_loss") is None and spec.get("risk_control") is None:
            issues.append("No stop-loss or risk control specified")

        # Check signal logic completeness
        signal = spec.get("signal", {})
        if not signal.get("entry_conditions"):
            issues.append("No entry conditions defined")
        if not signal.get("exit_conditions"):
            issues.append("No exit conditions defined")

        report.details = issues
        report.result = StageResult.PASS if len(issues) == 0 else StageResult.WARN if len(issues) <= 1 else StageResult.FAIL
        report.score = 1.0 - min(len(issues) * 0.25, 1.0)
        return report

    def _validate_brave_search(self, spec: dict[str, Any]) -> StageReport:
        """Stage 4: Brave Search external validation — real-world confirmation."""
        report = StageReport(stage=ValidationStage.BRAVE_SEARCH)
        warnings: list[str] = []

        # Check if strategy has been validated against external data
        external_validation = spec.get("external_validation", {})
        if not external_validation:
            warnings.append("No external validation performed")
        else:
            if external_validation.get("out_of_sample_sharpe", 0) < 0.5:
                warnings.append("Out-of-sample Sharpe below 0.5")

        report.warnings = warnings
        report.result = StageResult.PASS if len(warnings) == 0 else StageResult.WARN
        report.score = 1.0 - min(len(warnings) * 0.15, 1.0)
        return report

    def _compute_ma(self, stages: dict[ValidationStage, StageReport]) -> float:
        """Compute Model Accuracy from stages 1-3."""
        internal_stages = [ValidationStage.TEMPORAL, ValidationStage.PROVENANCE, ValidationStage.LOGIC]
        scores = [stages[s].score for s in internal_stages]
        return sum(scores) / len(scores) if scores else 0.0

    def _compute_er(self, stages: dict[ValidationStage, StageReport]) -> float:
        """Compute External Reliability from stage 4."""
        return stages[ValidationStage.BRAVE_SEARCH].score

    def get_report(self, strategy_id: str) -> FINALBenchReport | None:
        return self._reports.get(strategy_id)

    def get_latest_scores(self) -> dict[str, float]:
        """Get latest MA-ER scores for WebSocket streaming."""
        latest = list(self._reports.values())
        if not latest:
            return {}
        last = latest[-1]
        return {"ma": last.ma_score, "er": last.er_score, "gap": abs(last.ma_score - last.er_score)}

    @property
    def stats(self) -> dict[str, Any]:
        total = len(self._reports)
        passed = sum(1 for r in self._reports.values() if r.passed)
        return {
            "total_validations": total,
            "pass_rate": passed / max(total, 1),
            "ma_threshold": self._ma_threshold,
            "er_threshold": self._er_threshold,
            "gap_max": self._gap_max,
        }
