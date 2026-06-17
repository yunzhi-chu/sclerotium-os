"""Benchmark Engine — unified evaluation harness for Sclerotium OS.

Runs authority benchmarks (Harbor, MCP Atlas) and custom Sclerotium-specific
benchmarks with consistent scoring, reporting, and historical tracking.

Architecture:
  BenchmarkEngine
    ├── HarborRunner      → SWE-bench Pro, Terminal-Bench 2.0
    ├── MCPAtlasRunner    → MCP tool-use evaluation
    ├── FCPIBenchmark     → 6-dimension self-evolution
    ├── SafetyBenchmark   → Constitutional Arbiter + Sandstorm
    ├── MemoryBenchmark   → Hexis 5-layer memory
    ├── SandstormBenchmark→ 3-level isolation
    └── CoordinationBenchmark → Swarm + Economic Net

Reference:
  - Harbor Framework (Laude Institute 2026)
  - MCP Atlas (Scale AI 2026)
  - A-Evolve self-evolution framework (Amazon/UPenn 2026)
  - FCPI Vector (MiroFish 2026)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class BenchmarkStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BenchmarkResult:
    """Single benchmark run result."""
    name: str
    category: str  # "authority" | "fcpi" | "safety" | "memory" | "sandstorm" | "coordination"
    status: BenchmarkStatus
    score: float  # 0-100
    max_score: float = 100.0
    duration_ms: float = 0.0
    sub_scores: dict[str, float] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    model_used: str = ""
    comparison_rank: int | None = None  # Global rank if available
    comparison_total: int | None = None


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results forming a complete evaluation."""
    suite_id: str
    results: list[BenchmarkResult] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    total_score: float = 0.0
    fcpi_vector: dict[str, float] = field(default_factory=dict)
    global_percentile: float | None = None


class BenchmarkEngine:
    """Unified benchmark evaluation engine.

    Usage:
        engine = BenchmarkEngine()
        engine.register_all()
        suite = await engine.run_full_suite(model="deepseek-v4")
        print(engine.format_report(suite))
    """

    def __init__(self, data_dir: str = "./data/benchmarks") -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._runners: dict[str, Any] = {}
        self._history: list[BenchmarkSuite] = []
        self._load_history()

    # ── Registration ──────────────────────────────────────────────────

    def register_all(self) -> None:
        """Register all available benchmark runners."""
        # MCP Atlas self-assessment (no Docker needed)
        try:
            from kernel.benchmark.mcp_atlas_runner import MCPAtlasRunner
            self._runners["mcp_atlas"] = MCPAtlasRunner(self._data_dir / "mcp_atlas")
        except ImportError:
            pass

        # Custom Sclerotium benchmarks (always available)
        from kernel.benchmark.fcpi_benchmark import FCPIBenchmark
        self._runners["fcpi"] = FCPIBenchmark()

        from kernel.benchmark.safety_benchmark import SafetyBenchmark
        self._runners["safety"] = SafetyBenchmark()

        from kernel.benchmark.memory_benchmark import MemoryBenchmark
        self._runners["memory"] = MemoryBenchmark()

        from kernel.benchmark.sandstorm_benchmark import SandstormBenchmark
        self._runners["sandstorm"] = SandstormBenchmark()

        from kernel.benchmark.coordination_benchmark import CoordinationBenchmark
        self._runners["coordination"] = CoordinationBenchmark()

        # Trinity benchmarks — fungal-cortex + MiroFish + cross-system
        try:
            from kernel.benchmark.fungal_benchmark import FungalBenchmark
            self._runners["fungal"] = FungalBenchmark()
        except ImportError:
            pass

        try:
            from kernel.benchmark.mirofish_benchmark import MiroFishBenchmark
            self._runners["mirofish"] = MiroFishBenchmark()
        except ImportError:
            pass

        try:
            from kernel.benchmark.trinity_benchmark import TrinityBenchmark
            self._runners["trinity"] = TrinityBenchmark()
        except ImportError:
            pass

        # AI-driven benchmarks (require API key)
        try:
            from kernel.benchmark.ai_benchmark import AIBenchmark
            self._runners["ai"] = AIBenchmark()
        except ImportError:
            pass

        try:
            from kernel.benchmark.ai_benchmark_full import AIBenchmarkFull
            self._runners["ai_full"] = AIBenchmarkFull()
        except ImportError:
            pass

        # Organism benchmark (LLM through FULL Sclerotium body)
        try:
            from kernel.benchmark.organism_benchmark import OrganismBenchmark
            self._runners["organism"] = OrganismBenchmark()
        except ImportError:
            pass

        # LiveCodeBench (contamination-free, 880 tasks)
        try:
            from kernel.benchmark.livecode_benchmark import LiveCodeBenchmark
            self._runners["livecode"] = LiveCodeBenchmark()
        except ImportError:
            pass

    def list_runners(self) -> list[dict[str, Any]]:
        """List all registered benchmark runners."""
        result = []
        for name, runner in self._runners.items():
            info = {
                "name": name,
                "category": getattr(runner, "category", "custom"),
                "available": True,
            }
            if hasattr(runner, "list_benchmarks"):
                info["benchmarks"] = runner.list_benchmarks()
            result.append(info)
        return result

    # ── Execution ─────────────────────────────────────────────────────

    async def run_full_suite(
        self,
        model: str = "deepseek-v4",
        include_authority: bool = False,
        parallel: bool = True,
    ) -> BenchmarkSuite:
        """Run the complete benchmark suite.

        Args:
            model: Model name for comparison tracking
            include_authority: Run Harbor/MCP Atlas benchmarks (needs API keys)
            parallel: Run benchmarks in parallel where possible
        """
        import asyncio

        suite = BenchmarkSuite(
            suite_id=f"bench_{int(time.time())}",
            started_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        )

        # Filter runners
        runners_to_run = {}
        for name, runner in self._runners.items():
            if name in ("harbor", "mcp_atlas") and not include_authority:
                continue
            runners_to_run[name] = runner

        # Run benchmarks
        if parallel:
            tasks = []
            for name, runner in runners_to_run.items():
                tasks.append(self._run_runner(name, runner, model))
            results_nested = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results_nested:
                if isinstance(result, Exception):
                    suite.results.append(BenchmarkResult(
                        name="error", category="system",
                        status=BenchmarkStatus.FAILED, score=0,
                        errors=[str(result)],
                    ))
                elif isinstance(result, list):
                    suite.results.extend(result)
                elif result is not None:
                    suite.results.append(result)
        else:
            for name, runner in runners_to_run.items():
                try:
                    r = await self._run_runner(name, runner, model)
                    if isinstance(r, list):
                        suite.results.extend(r)
                    elif r is not None:
                        suite.results.append(r)
                except Exception as e:
                    suite.results.append(BenchmarkResult(
                        name=name, category="system",
                        status=BenchmarkStatus.FAILED, score=0,
                        errors=[str(e)],
                    ))

        # Calculate totals
        suite.completed_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if suite.results:
            suite.total_score = sum(r.score for r in suite.results) / len(suite.results)

        # Extract FCPI vector from FCPI benchmark results
        fcpi_results = [r for r in suite.results if r.category == "fcpi"]
        if fcpi_results:
            for r in fcpi_results:
                suite.fcpi_vector.update(r.sub_scores)

        # Compute global percentile
        suite.global_percentile = self._estimate_percentile(suite.total_score)

        # Save
        self._history.append(suite)
        self._save_history()

        return suite

    async def _run_runner(
        self, name: str, runner: Any, model: str
    ) -> list[BenchmarkResult] | BenchmarkResult | None:
        """Run a single benchmark runner."""
        if hasattr(runner, "run_benchmarks"):
            results = await runner.run_benchmarks(model=model)
            for r in (results if isinstance(results, list) else [results]):
                if isinstance(r, BenchmarkResult):
                    r.model_used = model
            return results
        elif hasattr(runner, "run"):
            result = runner.run()
            if isinstance(result, BenchmarkResult):
                result.model_used = model
            return result
        return None

    async def run_single(self, benchmark_name: str, model: str = "deepseek-v4") -> BenchmarkResult:
        """Run a single named benchmark."""
        for name, runner in self._runners.items():
            if name == benchmark_name:
                result = await self._run_runner(name, runner, model)
                if isinstance(result, list):
                    return result[0] if result else BenchmarkResult(
                        name=name, category="system",
                        status=BenchmarkStatus.FAILED, score=0,
                        errors=["No results"],
                    )
                return result if result else BenchmarkResult(
                    name=name, category="system",
                    status=BenchmarkStatus.FAILED, score=0,
                    errors=["Runner returned None"],
                )
        return BenchmarkResult(
            name=benchmark_name, category="system",
            status=BenchmarkStatus.SKIPPED, score=0,
            errors=[f"Benchmark '{benchmark_name}' not found"],
        )

    # ── Scoring ───────────────────────────────────────────────────────

    def _estimate_percentile(self, score: float) -> float:
        """Estimate global percentile based on known benchmarks.

        Reference points (May 2026):
          - Claude Opus 4.7 Adaptive: ~78% on SWE-bench Pro
          - GPT-5.4 xHigh: ~59% on SWE-bench Pro
          - Qwen3.7 Max: ~61% on SWE-bench Pro
          - A-Evolve + Claude Opus 4.6: 79.4% on MCP Atlas
        """
        if score >= 85:
            return 99.0  # Top 1%
        elif score >= 78:
            return 95.0  # Top 5%
        elif score >= 70:
            return 85.0  # Top 15%
        elif score >= 60:
            return 70.0  # Top 30%
        elif score >= 50:
            return 50.0
        elif score >= 40:
            return 30.0
        elif score >= 30:
            return 15.0
        else:
            return 5.0

    # ── Reporting ─────────────────────────────────────────────────────

    def format_report(self, suite: BenchmarkSuite) -> str:
        """Generate a formatted benchmark report."""
        lines = [
            "╔══════════════════════════════════════════════════════════════════╗",
            "║  SCLEROTIUM OS - BENCHMARK REPORT                                ║",
            "╠══════════════════════════════════════════════════════════════════╣",
            f"║  Suite: {suite.suite_id:<52}║",
            f"║  Started:  {suite.started_at:<48}║",
            f"║  Completed: {suite.completed_at:<46}║",
            f"║  Total Score: {suite.total_score:>5.1f}/100 | Global Percentile: {suite.global_percentile or 0:>5.1f}%  ║",
            "╠══════════════════════════════════════════════════════════════════╣",
        ]

        # FCPI Vector
        if suite.fcpi_vector:
            lines.append("║  FCPI 6-DIMENSION VECTOR:                                        ║")
            dims = ["coding", "coordination", "safety", "decision", "emergence", "performance"]
            fcpi_str = "  ".join(
                f"{d[:4].upper()}:{suite.fcpi_vector.get(d, 0):.2f}"
                for d in dims
            )
            lines.append(f"║  {fcpi_str[:62]:<62}║")
            lines.append("╠══════════════════════════════════════════════════════════════════╣")

        # Per-benchmark results
        by_category: dict[str, list[BenchmarkResult]] = {}
        for r in suite.results:
            by_category.setdefault(r.category, []).append(r)

        for cat, results in by_category.items():
            lines.append(f"║  [{cat.upper():<12}]                                               ║")
            for r in results:
                bar = "#" * int(r.score / 5) + "-" * (20 - int(r.score / 5))
                status_icon = "[PASS]" if r.status == BenchmarkStatus.PASSED else "[FAIL]" if r.status == BenchmarkStatus.FAILED else "[WARN]"
                lines.append(f"║  {status_icon} {r.name:<30} {bar} {r.score:>5.1f}%  ║")
                if r.errors:
                    for err in r.errors[:2]:
                        lines.append(f"║     ⚡ {err[:56]:<56}║")
            lines.append("║                                                                  ║")

        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append("║  COMPARISON WITH GLOBAL LEADERS (May 2026):                      ║")
        lines.append("║  #1 Claude Opus 4.7 Adaptive    SWE-bench Pro: 64.3%             ║")
        lines.append("║  #1 GPT-5.4 xHigh                SWE-bench Pro: 59.1%             ║")
        lines.append("║  #1 A-Evolve + Opus 4.6          MCP Atlas:    79.4%             ║")
        lines.append("║  #1 Claude Mythos Preview         SWE-bench Pro: 77.8%            ║")
        lines.append("║  #1 Gemini 3.5 Flash             MCP Atlas:    83.6%             ║")
        lines.append("╚══════════════════════════════════════════════════════════════════╝")

        return "\n".join(lines)

    def format_json_report(self, suite: BenchmarkSuite) -> dict[str, Any]:
        """Generate JSON report for programmatic consumption."""
        return {
            "suite_id": suite.suite_id,
            "started_at": suite.started_at,
            "completed_at": suite.completed_at,
            "total_score": round(suite.total_score, 2),
            "global_percentile": suite.global_percentile,
            "fcpi_vector": suite.fcpi_vector,
            "results": [
                {
                    "name": r.name,
                    "category": r.category,
                    "status": r.status.value,
                    "score": r.score,
                    "sub_scores": r.sub_scores,
                    "duration_ms": r.duration_ms,
                    "errors": r.errors,
                    "model_used": r.model_used,
                }
                for r in suite.results
            ],
        }

    # ── History ───────────────────────────────────────────────────────

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get benchmark history with scores."""
        return [
            {
                "suite_id": s.suite_id,
                "started_at": s.started_at,
                "total_score": round(s.total_score, 2),
                "fcpi_vector": s.fcpi_vector,
                "global_percentile": s.global_percentile,
            }
            for s in self._history[-limit:]
        ]

    def get_best_scores(self) -> dict[str, float]:
        """Get best scores across all benchmark runs."""
        best: dict[str, float] = {}
        for suite in self._history:
            for r in suite.results:
                current = best.get(r.name, 0)
                if r.score > current:
                    best[r.name] = r.score
        return best

    def _save_history(self) -> None:
        """Persist benchmark history to disk."""
        history_path = self._data_dir / "history.json"
        data = []
        for suite in self._history[-50:]:
            data.append({
                "suite_id": suite.suite_id,
                "started_at": suite.started_at,
                "completed_at": suite.completed_at,
                "total_score": suite.total_score,
                "fcpi_vector": suite.fcpi_vector,
                "global_percentile": suite.global_percentile,
                "results": [
                    {
                        "name": r.name,
                        "category": r.category,
                        "status": r.status.value,
                        "score": r.score,
                        "sub_scores": r.sub_scores,
                        "duration_ms": r.duration_ms,
                        "errors": r.errors,
                        "model_used": r.model_used,
                    }
                    for r in suite.results
                ],
            })
        history_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load_history(self) -> None:
        """Load benchmark history from disk."""
        history_path = self._data_dir / "history.json"
        if not history_path.exists():
            return
        try:
            data = json.loads(history_path.read_text(encoding="utf-8"))
            for entry in data:
                suite = BenchmarkSuite(
                    suite_id=entry.get("suite_id", ""),
                    started_at=entry.get("started_at", ""),
                    completed_at=entry.get("completed_at", ""),
                    total_score=entry.get("total_score", 0),
                    fcpi_vector=entry.get("fcpi_vector", {}),
                    global_percentile=entry.get("global_percentile"),
                )
                for r in entry.get("results", []):
                    suite.results.append(BenchmarkResult(
                        name=r.get("name", ""),
                        category=r.get("category", ""),
                        status=BenchmarkStatus(r.get("status", "failed")),
                        score=r.get("score", 0),
                        sub_scores=r.get("sub_scores", {}),
                        duration_ms=r.get("duration_ms", 0),
                        errors=r.get("errors", []),
                        model_used=r.get("model_used", ""),
                    ))
                self._history.append(suite)
        except (json.JSONDecodeError, KeyError):
            pass

    # ── Comparison ────────────────────────────────────────────────────

    GLOBAL_LEADERS = {
        "SWE-bench Pro": [
            ("Claude Mythos Preview", 77.8),
            ("Claude Opus 4.7 Adaptive", 64.3),
            ("Qwen3.7 Max", 60.6),
            ("GPT-5.4 xHigh", 59.1),
        ],
        "Terminal-Bench 2.0": [
            ("GPT-5.5", 82.7),
            ("A-Evolve + Opus 4.6", 76.5),
            ("Claude Opus 4.7 Adaptive", 74.6),
        ],
        "MCP Atlas": [
            ("Gemini 3.5 Flash", 83.6),
            ("A-Evolve + Opus 4.6", 79.4),
        ],
        "SWE-bench Verified": [
            ("A-Evolve + Opus 4.6", 76.8),
            ("Claude Opus 4.7 Adaptive", 74.5),
        ],
        "Aider Polyglot": [
            ("Claude Opus 4.7 Adaptive", 78.5),
            ("GPT-5.4 xHigh", 74.2),
        ],
    }

    def get_global_comparison(self) -> dict[str, list[tuple[str, float]]]:
        """Get global leaderboard for comparison."""
        return dict(self.GLOBAL_LEADERS)
