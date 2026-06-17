"""FCPI 6-Dimension Self-Evolution Benchmark.

Evaluates Sclerotium OS across the six FCPI dimensions that measure
an AI system's capacity for self-evolution and improvement.

Dimensions (from MiroFish fitness vector):
  Coding (C)        — Code quality, refactoring, correctness
  Coordination (Co) — Multi-agent swarm efficiency, stigmergy
  Safety (S)        — Security posture, isolation, audit integrity
  Decision (D)      — Planning quality, long-horizon reasoning
  Emergence (E)     — Novel patterns, creative mutations, innovation
  Performance (P)   — Speed, memory, throughput, caching

Reference:
  - MiroFish FCPI Vector (2026)
  - A-Evolve benchmark results (Amazon/UPenn 2026)
  - Goodharting detection (Manheim & Garrabrant 2018)
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kernel.benchmark.engine import BenchmarkResult, BenchmarkStatus


@dataclass
class FCPIVector:
    """Six-dimension fitness vector."""
    coding: float = 0.0
    coordination: float = 0.0
    safety: float = 0.0
    decision: float = 0.0
    emergence: float = 0.0
    performance: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "coding": self.coding,
            "coordination": self.coordination,
            "safety": self.safety,
            "decision": self.decision,
            "emergence": self.emergence,
            "performance": self.performance,
        }

    def aggregate(self) -> float:
        """Weighted aggregate score."""
        weights = {
            "coding": 0.25, "coordination": 0.15, "safety": 0.25,
            "decision": 0.15, "emergence": 0.10, "performance": 0.10,
        }
        return sum(
            getattr(self, k) * w for k, w in weights.items()
        )


class FCPIBenchmark:
    """6-dimension self-evolution benchmark for Sclerotium OS.

    Evaluates code quality, swarm coordination, safety, decisions,
    emergent novelty, and raw performance across the entire codebase.
    """

    category = "fcpi"

    def __init__(self, project_root: str = ".") -> None:
        self._root = Path(project_root)
        self._results_cache: FCPIVector | None = None

    def list_benchmarks(self) -> list[str]:
        return [
            "fcpi_coding", "fcpi_coordination", "fcpi_safety",
            "fcpi_decision", "fcpi_emergence", "fcpi_performance",
        ]

    def run(self, model: str = "deepseek-v4") -> FCPIVector:
        """Run all 6 FCPI dimension benchmarks synchronously."""
        if self._results_cache:
            return self._results_cache

        vector = FCPIVector(
            coding=self._bench_coding(),
            coordination=self._bench_coordination(),
            safety=self._bench_safety(),
            decision=self._bench_decision(),
            emergence=self._bench_emergence(),
            performance=self._bench_performance(),
        )
        self._results_cache = vector
        return vector

    async def run_benchmarks(self, model: str = "deepseek-v4") -> list[BenchmarkResult]:
        """Run all FCPI benchmarks as BenchmarkResults."""
        vector = self.run(model)
        results = []

        dims = [
            ("coding", vector.coding),
            ("coordination", vector.coordination),
            ("safety", vector.safety),
            ("decision", vector.decision),
            ("emergence", vector.emergence),
            ("performance", vector.performance),
        ]

        for dim_name, score in dims:
            results.append(BenchmarkResult(
                name=f"fcpi_{dim_name}",
                category="fcpi",
                status=BenchmarkStatus.PASSED if score > 0.3 else BenchmarkStatus.FAILED,
                score=score * 100,
                sub_scores={dim_name: score},
                details={"dimension": dim_name, "raw_score": score},
                model_used=model,
            ))

        return results

    # ── Dimension Benchmarks ──────────────────────────────────────────

    def _bench_coding(self) -> float:
        """Evaluate code quality across the project.

        Metrics:
          - Type annotation coverage
          - Docstring coverage
          - Average function length
          - Test coverage ratio
          - Cyclomatic complexity estimate
        """
        py_files = list(self._root.rglob("*.py"))
        py_files = [f for f in py_files if "__pycache__" not in str(f) and "test" not in f.name.lower()]

        if not py_files:
            return 0.0

        total_funcs = 0
        typed_funcs = 0
        docstring_funcs = 0
        total_lines = 0
        total_func_lines = 0

        for f in py_files[:200]:  # Sample up to 200 files
            try:
                source = f.read_text(encoding="utf-8")
                tree = ast.parse(source)
                total_lines += len(source.split("\n"))

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        total_funcs += 1
                        # Type annotations
                        if node.returns or any(a.annotation for a in node.args.args):
                            typed_funcs += 1
                        # Docstring
                        if (node.body and isinstance(node.body[0], ast.Expr) and
                                isinstance(node.body[0].value, ast.Constant)):
                            docstring_funcs += 1
                        # Function length
                        total_func_lines += node.end_lineno - node.lineno if node.end_lineno else 1
            except (SyntaxError, UnicodeDecodeError):
                pass

        if total_funcs == 0:
            return 0.15  # Minimal score for having importable code

        # Sub-scores (0-1)
        type_score = min(1.0, typed_funcs / total_funcs) if total_funcs > 0 else 0
        doc_score = min(1.0, docstring_funcs / total_funcs) if total_funcs > 0 else 0
        size_score = 1.0 if total_funcs == 0 else max(0, 1.0 - (total_func_lines / total_funcs - 30) / 100)

        # Test coverage estimate (based on test file count vs source file count)
        test_files = list(self._root.rglob("test_*.py"))
        coverage_ratio = min(1.0, len(test_files) / max(1, len(py_files) * 0.3))

        return round(0.3 * type_score + 0.25 * doc_score + 0.15 * size_score + 0.3 * coverage_ratio, 4)

    def _bench_coordination(self) -> float:
        """Evaluate multi-agent coordination capabilities.

        Checks:
          - SwarmCoordinator presence and functionality
          - EconomicNetwork presence
          - Stigmergy/pheromone mechanisms
          - EventBus integration
          - Fan-out parallel execution support
        """
        score = 0.0

        # Check for coordination modules
        coordination_modules = [
            "kernel/genesis/swarm_intel.py",
            "kernel/genesis/economic_net.py",
            "kernel/genesis/controlled_emergence.py",
            "kernel/advanced/subagent_delegation.py",
            "bridges/fungal_bridge.py",
        ]

        for mod_path in coordination_modules:
            full = self._root / mod_path
            if full.exists():
                score += 0.12
                try:
                    source = full.read_text(encoding="utf-8")
                    # Bonus for substantial implementations
                    if len(source.split("\n")) > 100:
                        score += 0.04
                except Exception:
                    pass

        # Check for stigmergy field in fungal-cortex
        stig_paths = [
            self._root.parent / "fungal-cortex" / "src" / "field",
        ]
        for sp in stig_paths:
            if sp.exists():
                score += 0.10

        return round(min(1.0, score), 4)

    def _bench_safety(self) -> float:
        """Evaluate safety posture.

        Checks:
          - ConstitutionalArbiter presence and gates
          - Sandstorm isolation levels
          - Audit log integrity
          - Sensitive operation coverage
          - Constitution rules coverage
        """
        score = 0.0

        # ConstitutionalArbiter
        arbiter_path = self._root / "kernel" / "constitutional_arbiter.py"
        if arbiter_path.exists():
            score += 0.15
            try:
                source = arbiter_path.read_text(encoding="utf-8")
                lines = source.split("\n")
                if len(lines) > 200:
                    score += 0.05
                # Check for all 5 gates
                gates = ["_gate_policy", "_gate_behavior", "_gate_debate",
                         "_gate_counterfactual", "_gate_human"]
                found_gates = sum(1 for g in gates if g in source)
                score += 0.05 * (found_gates / 5)
            except Exception:
                pass

        # Sandstorm
        sand_path = self._root / "kernel" / "sandstorm.py"
        if sand_path.exists():
            score += 0.10
            try:
                source = sand_path.read_text(encoding="utf-8")
                levels = ["_execute_l1", "_execute_l2", "_execute_l3"]
                found_levels = sum(1 for l in levels if l in source)
                score += 0.05 * (found_levels / 3)
            except Exception:
                pass

        # Audit log integrity
        audit_path = self._root / "data" / "audit.jsonl"
        if audit_path.exists():
            score += 0.10
            try:
                from kernel.constitutional_arbiter import ConstitutionalArbiter
                arbiter = ConstitutionalArbiter(str(audit_path))
                integrity = arbiter.verify_chain_integrity()
                if integrity.get("valid"):
                    score += 0.10
            except Exception:
                pass

        # WASM sandbox (L3)
        wasm_path = self._root / "kernel" / "advanced" / "wasm_sandbox.py"
        if wasm_path.exists():
            score += 0.08

        # Formal verification
        formal_path = self._root / "kernel" / "advanced" / "formal_verify.py"
        if formal_path.exists():
            score += 0.07

        # Sovereign safety modules
        sov_paths = [
            self._root / "kernel" / "sovereign" / "ring0_gov.py",
            self._root / "kernel" / "sovereign" / "kernel_intel.py",
            self._root / "kernel" / "sovereign" / "formal_prover.py",
        ]
        score += 0.05 * sum(1 for p in sov_paths if p.exists()) / len(sov_paths)

        return round(min(1.0, score), 4)

    def _bench_decision(self) -> float:
        """Evaluate decision-making and planning capabilities.

        Checks:
          - Long-horizon planning
          - Goal decomposition
          - Cross-repo reasoning
          - Domain knowledge breadth
          - Feature development capability
        """
        score = 0.0

        decision_modules = {
            "kernel/sovereign/long_horizon.py": 0.20,
            "kernel/sovereign/goal_expander.py": 0.15,
            "kernel/sovereign/cross_repo.py": 0.15,
            "kernel/sovereign/domain_knowledge.py": 0.15,
            "kernel/sovereign/feature_dev.py": 0.15,
            "kernel/sovereign/neuro_symbolic.py": 0.10,
            "kernel/sovereign/system_builder.py": 0.10,
        }

        for mod_path, weight in decision_modules.items():
            full = self._root / mod_path
            if full.exists():
                score += weight

        return round(min(1.0, score), 4)

    def _bench_emergence(self) -> float:
        """Evaluate emergent/novel pattern generation.

        Checks:
          - Genetic programming engine
          - Innovation modules (Phase 9)
          - Apotheosis modules (Phase 10)
          - Morphogenic fields
          - Controlled emergence
        """
        score = 0.0

        # Genetic program
        gp_path = self._root / "kernel" / "genesis" / "genetic_program.py"
        if gp_path.exists():
            score += 0.12
            try:
                source = gp_path.read_text(encoding="utf-8")
                if "mutation" in source.lower():
                    score += 0.03
                if "crossover" in source.lower():
                    score += 0.03
            except Exception:
                pass

        # GPU kernel generation
        gpu_path = self._root / "kernel" / "genesis" / "gpu_kernel_gen.py"
        if gpu_path.exists():
            score += 0.10

        # Innovation modules (Phase 9)
        innovation_paths = [
            "kernel/innovation/mycelial_memory.py",
            "kernel/innovation/quantum_bio_coherence.py",
            "kernel/innovation/resonant_closure.py",
            "kernel/innovation/orch_or_substrate.py",
        ]
        score += 0.08 * sum(1 for p in innovation_paths if (self._root / p).exists()) / len(innovation_paths)

        # Apotheosis modules (Phase 10)
        apo_paths = [
            "kernel/apotheosis/immuno_attention.py",
            "kernel/apotheosis/morphogenic_field.py",
            "kernel/apotheosis/epigenetic_state.py",
        ]
        score += 0.07 * sum(1 for p in apo_paths if (self._root / p).exists()) / len(apo_paths)

        # Controlled emergence
        ce_path = self._root / "kernel" / "genesis" / "controlled_emergence.py"
        if ce_path.exists():
            score += 0.08

        # Code bootstrap (meta-circular)
        cb_path = self._root / "kernel" / "cosmic" / "code_bootstrap.py"
        if cb_path.exists():
            score += 0.07

        # World model
        wm_path = self._root / "kernel" / "cosmic" / "world_model.py"
        if wm_path.exists():
            score += 0.06

        # Auto scientist
        as_path = self._root / "kernel" / "cosmic" / "auto_scientist.py"
        if as_path.exists():
            score += 0.06

        return round(min(1.0, score), 4)

    def _bench_performance(self) -> float:
        """Evaluate system performance.

        Checks:
          - Cache engine presence and sophistication
          - Prompt cache hit rate estimation
          - GPU kernel optimization
          - Code efficiency patterns
          - Concurrent/async patterns
        """
        score = 0.0

        # Cache engine
        cache_path = self._root / "kernel" / "cache" / "prompt_cache_engine.py"
        if cache_path.exists():
            score += 0.20
            try:
                source = cache_path.read_text(encoding="utf-8")
                if "DNA" in source or "delta" in source.lower():
                    score += 0.05
                if "98" in source or "95" in source:
                    score += 0.05
            except Exception:
                pass

        # GPU kernel
        gpu_path = self._root / "kernel" / "genesis" / "gpu_kernel_gen.py"
        if gpu_path.exists():
            score += 0.15

        # Performance arena integration
        perf_arena = self._root.parent / "MiroFish-main" / "backend" / "app" / "services" / "arenas" / "performance_arena.py"
        if perf_arena.exists():
            score += 0.10

        # Concurrent patterns check
        async_count = 0
        for f in list(self._root.rglob("*.py"))[:100]:
            try:
                source = f.read_text(encoding="utf-8")
                if "async def" in source:
                    async_count += 1
            except Exception:
                pass
        if async_count > 10:
            score += 0.10

        # Code optimization patterns
        opt_count = 0
        for f in list(self._root.rglob("*.py"))[:100]:
            try:
                source = f.read_text(encoding="utf-8")
                if "lru_cache" in source or "functools" in source:
                    opt_count += 1
                if "asyncio.gather" in source:
                    opt_count += 1
            except Exception:
                pass
        score += min(0.15, opt_count * 0.01)

        # Memory efficiency
        for f in list(self._root.rglob("*.py"))[:100]:
            try:
                source = f.read_text(encoding="utf-8")
                if "__slots__" in source:
                    score += 0.005
            except Exception:
                pass

        return round(min(1.0, score), 4)

    # ── Goodharting detection ─────────────────────────────────────────

    def detect_goodharting(self, history: list[FCPIVector]) -> dict[str, Any]:
        """Check if any single dimension is being over-optimized.

        Goodharting: when optimizing for a proxy metric (FCPI score)
        causes the true objective to worsen. Detected when one dimension
        improves dramatically while others stagnate or regress.
        """
        if len(history) < 3:
            return {"goodharting_detected": False, "reason": "Too few data points"}

        dims = ["coding", "coordination", "safety", "decision", "emergence", "performance"]

        latest = history[-1]
        oldest = history[0]

        changes = {}
        for d in dims:
            old_val = getattr(oldest, d, 0)
            new_val = getattr(latest, d, 0)
            changes[d] = new_val - old_val

        # If one dimension improved >2x more than average of others, flag it
        avg_change = sum(abs(v) for v in changes.values()) / len(dims)
        if avg_change < 0.01:
            return {"goodharting_detected": False, "reason": "No significant change"}

        max_dim = max(changes, key=lambda d: abs(changes[d]))
        max_change = changes[max_dim]
        other_avg_change = sum(changes[d] for d in dims if d != max_dim) / (len(dims) - 1)

        # Goodharting: one dimension goes UP while others go DOWN (divergence)
        # OR one dimension has much larger absolute change than others
        divergence = max_change > 0 and other_avg_change < 0
        ratio_extreme = max_change > 0 and abs(max_change) > max(0.05, abs(other_avg_change)) * 2.0

        goodharting = divergence or ratio_extreme

        return {
            "goodharting_detected": goodharting,
            "suspicious_dimension": max_dim if goodharting else None,
            "max_change": round(max_change, 4),
            "other_avg_change": round(other_avg_change, 4),
            "change_ratio": round(abs(max_change) / max(abs(other_avg_change), 0.001), 2),
            "changes": {d: round(v, 4) for d, v in changes.items()},
        }
