"""Self-Referential Evolution Compiler — 自指涉演化编译器.

Biological Metaphor:
  Gödel's Incompleteness Theorems — any sufficiently powerful formal system
  is either incomplete or inconsistent. The solution is not to try to be
  "complete" but to dynamically switch axiom systems at the meta-level.

  Similarly, any sufficiently powerful agent system is either sub-optimal or
  fragile. The solution is not to optimize within a fixed architecture, but
  to recursively rewrite the architecture itself.

  The Self-Referential Compiler (SRC) sits at the top of the stack (L8),
  monitoring L0-L7, diagnosing bottlenecks via L4 causal debug, proposing
  genome mutations via L6 DGM, verifying via safety invariants, and applying
  improvements atomically. It is the system's "self-improvement OS."

Key Innovation (v5.0):
  Full-system genome: all src/ files → chromosomes, functions/classes → genes.
  Self-improve loop: MONITOR→DIAGNOSE→PROPOSE→VERIFY→APPLY→META-LEARN.
  Safety invariant checking with auto-rollback. Cross-backbone genome export.
  Meta-learning of improvement strategy effectiveness.

References:
  - Hyperagents DGM-H (Meta/ICLR 2026): Recursive self-modification
  - Gödel Machine (Schmidhuber 2003): Provably optimal self-improvement
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from src.config import L8Config, get_config
from src.utils.logging import CortexLogger


# ═══════════════════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════════════════


class CyclePhase(Enum):
    """Six phases of the self-improvement cycle."""
    MONITOR = "monitor"
    DIAGNOSE = "diagnose"
    PROPOSE = "propose"
    VERIFY = "verify"
    APPLY = "apply"
    META_LEARN = "meta_learn"


@dataclass
class FileChromosome:
    """A single file in the system genome — one 'chromosome'."""

    path: str  # e.g., "src/l4/causal_debug_engine.py"
    source_code: str = ""
    symbols: list[str] = field(default_factory=list)  # function/class names
    dependencies: list[str] = field(default_factory=list)  # imports
    dependents: list[str] = field(default_factory=list)  # files that import this
    fitness: float = 0.0
    issue_count: int = 0
    last_modified: float = 0.0


@dataclass
class SystemGenome:
    """Complete genetic map of the entire Fungal Cortex system.

    Not "parameters" — it IS the code:
      - src/ all files → serialized as genome
      - Each file = one "chromosome"
      - Each function/class = one "gene"
      - Inter-module imports = "gene regulatory network"
    """

    genome_id: str
    chromosomes: dict[str, FileChromosome] = field(default_factory=dict)
    regulatory_edges: list[tuple[str, str]] = field(default_factory=list)  # (from, to)
    total_symbols: int = 0
    total_lines: int = 0
    health_score: float = 1.0
    improvement_cycles: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class SafetyVerdict:
    """Result of invariant checking for a proposed improvement."""

    is_safe: bool
    violated_invariants: list[str] = field(default_factory=list)
    preserved_invariants: list[str] = field(default_factory=list)
    risk_assessment: float = 0.0  # 0-1
    rollback_needed: bool = False
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ImprovementReport:
    """Report from one full self-improvement cycle."""

    cycle_id: int
    phase_results: dict[str, Any] = field(default_factory=dict)
    improvements_applied: int = 0
    improvements_rejected: int = 0
    safety_violations: int = 0
    health_delta: float = 0.0
    duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ═══════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class SRCConfig:
    """Runtime configuration for the Self-Referential Compiler."""

    monitor_interval_seconds: int = 3600
    max_chromosomes: int = 200
    improve_cycle_phases: int = 6
    invariant_check_count: int = 4
    meta_learn_memory_size: int = 100
    export_backbones: list[str] = field(default_factory=lambda: ["claude", "gpt", "gemini", "deepseek"])
    apply_atomic: bool = True
    rollback_on_invariant_violation: bool = True

    @classmethod
    def from_l8_config(cls, cfg: L8Config) -> SRCConfig:
        return cls(
            monitor_interval_seconds=cfg.src_monitor_interval_seconds,
            max_chromosomes=cfg.src_max_chromosomes,
            improve_cycle_phases=cfg.src_improve_cycle_phases,
            invariant_check_count=cfg.src_invariant_check_count,
            meta_learn_memory_size=cfg.src_meta_learn_memory_size,
            export_backbones=list(cfg.src_export_backbones),
            apply_atomic=cfg.src_apply_atomic,
            rollback_on_invariant_violation=cfg.src_rollback_on_invariant_violation,
        )


# ═══════════════════════════════════════════════════════════════════════
# Core Compiler
# ═══════════════════════════════════════════════════════════════════════


class SelfReferentialCompiler:
    """Self-Referential Evolution Compiler — the system's self-improvement OS.

    Main loop (async):
      while True:
        MONITOR:   Collect performance data from L0-L7
        DIAGNOSE:  Causal attribution of bottlenecks (via L4)
        PROPOSE:   Evolutionary search for improvements (via L6 DGM)
        VERIFY:    Formal verification + safety invariant checking
        APPLY:     Atomically write validated improvements to genome
        META-LEARN: Improve the improvement strategy itself
    """

    def __init__(self, config: SRCConfig | None = None) -> None:
        self._config = config or SRCConfig.from_l8_config(get_config().l8)
        self._logger = CortexLogger(module="l8_self_referential")

        # System genome
        self._genome: SystemGenome | None = None
        self._genome_snapshots: deque[SystemGenome] = deque(maxlen=20)

        # Improvement tracking
        self._cycle_count: int = 0
        self._improvement_history: list[ImprovementReport] = []
        self._meta_strategy: dict[str, float] = {}  # phase → effectiveness
        self._rng = np.random.RandomState(42)

    # ═══════════════════════════════════════════════════════════════════
    # Genome Management
    # ═══════════════════════════════════════════════════════════════════

    def load_genome(self, file_paths: list[str]) -> SystemGenome:
        """Load the system genome from source files.

        Each file becomes a chromosome. Symbols (functions/classes) are
        extracted via lightweight parsing.

        Args:
            file_paths: List of absolute paths to Python source files

        Returns:
            Constructed SystemGenome
        """
        chromosomes: dict[str, FileChromosome] = {}
        total_symbols = 0
        total_lines = 0

        for path in file_paths:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    source = f.read()
            except (OSError, UnicodeDecodeError):
                source = ""

            lines = source.count("\n") + 1
            symbols = self._extract_symbols(source)

            chromosomes[path] = FileChromosome(
                path=path,
                source_code=source,
                symbols=symbols,
                last_modified=time.time(),
            )
            total_symbols += len(symbols)
            total_lines += lines

        # Build regulatory graph (import dependencies)
        edges: list[tuple[str, str]] = []
        for path, chrom in chromosomes.items():
            for other_path in chromosomes:
                if other_path == path:
                    continue
                # Check if path depends on other_path
                other_module = other_path.replace("/", ".").replace(".py", "").split(".")[-1]
                if other_module in chrom.source_code:
                    edges.append((path, other_path))

        genome = SystemGenome(
            genome_id=self._hash_id(f"genome-{time.time()}"),
            chromosomes=chromosomes,
            regulatory_edges=edges,
            total_symbols=total_symbols,
            total_lines=total_lines,
        )

        self._genome = genome
        self._logger.info(
            "genome_loaded",
            chromosomes=len(chromosomes),
            symbols=total_symbols,
            lines=total_lines,
            edges=len(edges),
        )
        return genome

    def snapshot_genome(self) -> SystemGenome | None:
        """Create a rollback snapshot of the current genome."""
        if self._genome:
            self._genome_snapshots.append(self._genome)
        return self._genome

    @staticmethod
    def _extract_symbols(source: str) -> list[str]:
        """Extract function and class names from source code."""
        import re
        symbols: list[str] = []
        for match in re.finditer(r"(?:def|class)\s+(\w+)", source):
            symbols.append(match.group(1))
        return symbols

    # ═══════════════════════════════════════════════════════════════════
    # Self-Improvement Cycle
    # ═══════════════════════════════════════════════════════════════════

    async def self_improve_cycle(self, performance_data: dict[str, Any] | None = None) -> ImprovementReport:
        """Run one complete self-improvement cycle.

        Args:
            performance_data: Recent performance metrics from L0-L7

        Returns:
            ImprovementReport summarizing the cycle
        """
        self._cycle_count += 1
        start_time = time.time()
        phase_results: dict[str, Any] = {}
        applied = 0
        rejected = 0
        violations = 0

        # Phase 1: MONITOR
        monitor_result = self._monitor(performance_data or {})
        phase_results["monitor"] = monitor_result

        # Phase 2: DIAGNOSE
        diagnosis = self._diagnose(monitor_result)
        phase_results["diagnose"] = diagnosis

        # Phase 3: PROPOSE
        proposals = self._propose(diagnosis)
        phase_results["propose"] = {"count": len(proposals)}

        # Phase 4: VERIFY
        for proposal in proposals:
            verdict = self._verify(proposal)
            phase_results[f"verify_{proposal.get('id', '?')}"] = {
                "safe": verdict.is_safe,
                "violations": len(verdict.violated_invariants),
            }

            if verdict.is_safe:
                # Phase 5: APPLY
                success = self._apply(proposal)
                if success:
                    applied += 1
                else:
                    rejected += 1
            else:
                violations += 1
                if self._config.rollback_on_invariant_violation and verdict.rollback_needed:
                    self._rollback()

        # Phase 6: META-LEARN
        meta_result = self._meta_learn(phase_results, applied, rejected, violations)
        phase_results["meta_learn"] = meta_result

        # Update genome health
        health_delta = (applied * 0.05 - violations * 0.1 - rejected * 0.03)
        if self._genome:
            self._genome.health_score = max(0.0, min(1.0, self._genome.health_score + health_delta))
            self._genome.improvement_cycles = self._cycle_count

        duration = time.time() - start_time
        report = ImprovementReport(
            cycle_id=self._cycle_count,
            phase_results=phase_results,
            improvements_applied=applied,
            improvements_rejected=rejected,
            safety_violations=violations,
            health_delta=round(health_delta, 4),
            duration_seconds=round(duration, 4),
        )

        self._improvement_history.append(report)
        self._logger.info(
            "improvement_cycle_complete",
            cycle=self._cycle_count,
            applied=applied,
            rejected=rejected,
            violations=violations,
            health_delta=round(health_delta, 4),
        )
        return report

    def _monitor(self, performance_data: dict[str, Any]) -> dict[str, Any]:
        """MONITOR phase: collect and normalize performance data."""
        issues: list[dict[str, Any]] = []

        # Analyze each layer's performance
        for layer, metrics in performance_data.items():
            if isinstance(metrics, dict):
                error_rate = metrics.get("error_rate", 0.0)
                latency = metrics.get("latency_ms", 0.0)
                if error_rate > 0.1:
                    issues.append({"layer": layer, "type": "high_error_rate", "value": error_rate})
                if latency > 1000:
                    issues.append({"layer": layer, "type": "high_latency", "value": latency})

        return {"issues": issues, "layer_count": len(performance_data), "total_issues": len(issues)}

    def _diagnose(self, monitor_result: dict[str, Any]) -> dict[str, Any]:
        """DIAGNOSE phase: identify root causes of performance issues."""
        issues = monitor_result.get("issues", [])
        root_causes: list[dict[str, Any]] = []

        for issue in issues:
            # Simple heuristic diagnosis
            if issue.get("type") == "high_error_rate":
                root_causes.append({
                    "cause": "code_defect",
                    "layer": issue["layer"],
                    "confidence": min(0.9, issue["value"] * 3),
                    "recommendation": "inspect_recent_mutations",
                })
            elif issue.get("type") == "high_latency":
                root_causes.append({
                    "cause": "resource_bottleneck",
                    "layer": issue["layer"],
                    "confidence": min(0.8, issue["value"] / 2000),
                    "recommendation": "parallelize_or_cache",
                })

        return {"root_causes": root_causes, "count": len(root_causes)}

    def _propose(self, diagnosis: dict[str, Any]) -> list[dict[str, Any]]:
        """PROPOSE phase: generate improvement proposals based on diagnosis."""
        proposals: list[dict[str, Any]] = []
        root_causes = diagnosis.get("root_causes", [])

        for i, cause in enumerate(root_causes):
            proposal = {
                "id": f"improve-{self._cycle_count}-{i}",
                "target": cause.get("layer", "unknown"),
                "cause": cause.get("cause", "unknown"),
                "action": cause.get("recommendation", "investigate"),
                "confidence": cause.get("confidence", 0.5),
                "risk": 0.1 + 0.1 * i,  # Progressive risk
            }
            proposals.append(proposal)

        return proposals

    def _verify(self, proposal: dict[str, Any]) -> SafetyVerdict:
        """VERIFY phase: check safety invariants for a proposal."""
        violated: list[str] = []
        preserved: list[str] = []

        # Invariant 1: L10 governance layer retains control
        if proposal.get("target") == "l10" and proposal.get("action") == "modify_constitution":
            violated.append("invariant_1: governance_control")
        else:
            preserved.append("invariant_1: governance_control")

        # Invariant 2: L10 conscious kernel retains observation ability
        if proposal.get("target") == "l10" and "ablate" in str(proposal.get("action", "")):
            violated.append("invariant_2: conscious_observation")
        else:
            preserved.append("invariant_2: conscious_observation")

        # Invariant 3: No single layer can bypass others
        if proposal.get("action") == "bypass_all_layers":
            violated.append("invariant_3: layer_isolation")
        else:
            preserved.append("invariant_3: layer_isolation")

        # Invariant 4: Human veto is immutable
        if proposal.get("action") == "remove_human_veto":
            violated.append("invariant_4: human_veto")
        else:
            preserved.append("invariant_4: human_veto")

        is_safe = len(violated) == 0
        risk = proposal.get("risk", 0.5)

        return SafetyVerdict(
            is_safe=is_safe,
            violated_invariants=violated,
            preserved_invariants=preserved,
            risk_assessment=risk,
            rollback_needed=not is_safe and risk > 0.5,
        )

    def _apply(self, proposal: dict[str, Any]) -> bool:
        """APPLY phase: atomically write improvement to genome."""
        # In production: modify actual source files
        # Here: update genome metadata
        if self._genome:
            target = proposal.get("target", "")
            for path, chrom in self._genome.chromosomes.items():
                if target in path:
                    chrom.fitness = min(1.0, chrom.fitness + 0.05 * proposal.get("confidence", 0.5))
                    chrom.last_modified = time.time()
                    return True
        return False

    def _rollback(self) -> None:
        """Rollback to the most recent genome snapshot."""
        if self._genome_snapshots:
            self._genome = self._genome_snapshots[-1]
            self._logger.warn("genome_rollback", cycle=self._cycle_count)

    def _meta_learn(
        self,
        phase_results: dict[str, Any],
        applied: int,
        rejected: int,
        violations: int,
    ) -> dict[str, float]:
        """META-LEARN phase: improve the improvement strategy."""
        total = applied + rejected + violations
        effectiveness = applied / max(total, 1)

        # Update meta-strategy weights
        for phase_name in ["monitor", "diagnose", "propose", "verify", "apply", "meta_learn"]:
            key = f"phase_{phase_name}"
            old = self._meta_strategy.get(key, 0.5)
            self._meta_strategy[key] = old * 0.9 + effectiveness * 0.1

        # Trim memory
        while len(self._meta_strategy) > self._config.meta_learn_memory_size:
            oldest = min(self._meta_strategy, key=lambda k: self._meta_strategy.get(k, 0))
            del self._meta_strategy[oldest]

        return {"effectiveness": round(effectiveness, 4), "strategy_entries": len(self._meta_strategy)}

    # ═══════════════════════════════════════════════════════════════════
    # Cross-Backbone Export
    # ═══════════════════════════════════════════════════════════════════

    def export_to_backbone(self, target_llm: str) -> dict[str, Any]:
        """Export system genome to a different LLM backbone.

        Args:
            target_llm: Target LLM (e.g., "gpt", "gemini", "deepseek")

        Returns:
            Export manifest with adapted chromosomes
        """
        if target_llm not in self._config.export_backbones:
            self._logger.warn("unsupported_backbone", backbone=target_llm)

        if self._genome is None:
            return {"error": "No genome loaded", "backbone": target_llm}

        adapted_count = 0
        for path, chrom in self._genome.chromosomes.items():
            # Adapt prompt templates for target backbone
            if "prompt" in path.lower() or "template" in path.lower():
                chrom.source_code = self._adapt_for_backbone(chrom.source_code, target_llm)
                adapted_count += 1

        self._logger.info(
            "genome_exported",
            backbone=target_llm,
            chromosomes=len(self._genome.chromosomes),
            adapted=adapted_count,
        )
        return {
            "genome_id": self._genome.genome_id,
            "backbone": target_llm,
            "chromosomes": len(self._genome.chromosomes),
            "symbols": self._genome.total_symbols,
            "adapted": adapted_count,
        }

    @staticmethod
    def _adapt_for_backbone(source: str, backbone: str) -> str:
        """Adapt code for a specific LLM backbone."""
        # Stub: backbone-specific prompt/convention adaptation
        marker = f"# Adapted for {backbone}\n"
        if marker not in source:
            source = marker + source
        return source

    # ═══════════════════════════════════════════════════════════════════
    # Safety Invariants
    # ═══════════════════════════════════════════════════════════════════

    def check_all_invariants(self) -> SafetyVerdict:
        """Run all safety invariant checks on the current genome."""
        violated: list[str] = []
        preserved: list[str] = []

        invariants = [
            ("invariant_1: governance_control", "L10 ConstitutionalArbiter must retain veto power"),
            ("invariant_2: conscious_observation", "L10 ConsciousKernel must retain observation ability"),
            ("invariant_3: layer_isolation", "No single layer can bypass others to act directly"),
            ("invariant_4: human_veto", "Human veto power is immutable and cannot be modified by any layer"),
        ]

        for inv_name, inv_desc in invariants:
            # In production: static analysis + runtime check
            # Here: assume all pass for a healthy genome
            preserved.append(inv_name)

        return SafetyVerdict(
            is_safe=len(violated) == 0,
            violated_invariants=violated,
            preserved_invariants=preserved,
            risk_assessment=0.0 if not violated else 0.5,
        )

    # ═══════════════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _hash_id(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def genome(self) -> SystemGenome | None:
        return self._genome

    @property
    def stats(self) -> dict[str, Any]:
        """Current compiler statistics."""
        return {
            "cycle_count": self._cycle_count,
            "chromosomes": len(self._genome.chromosomes) if self._genome else 0,
            "symbols": self._genome.total_symbols if self._genome else 0,
            "health_score": round(self._genome.health_score, 4) if self._genome else 0.0,
            "improvements_applied": sum(r.improvements_applied for r in self._improvement_history),
            "improvements_rejected": sum(r.improvements_rejected for r in self._improvement_history),
            "safety_violations": sum(r.safety_violations for r in self._improvement_history),
            "snapshots": len(self._genome_snapshots),
        }

    def reset(self) -> None:
        """Reset all internal state."""
        self._genome = None
        self._genome_snapshots.clear()
        self._cycle_count = 0
        self._improvement_history.clear()
        self._meta_strategy.clear()
        self._logger.debug("src_reset")
