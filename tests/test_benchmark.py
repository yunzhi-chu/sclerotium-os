"""Benchmark Suite Tests — Verify all benchmark modules work correctly.

Tests cover:
  - BenchmarkEngine registration and execution
  - FCPI 6-dimension evaluation
  - Safety benchmarks (ConstitutionalArbiter, Sandstorm, Audit)
  - Memory benchmarks (Hexis throughput, search, Ebbinghaus)
  - Sandstorm benchmarks (L1 isolation, timeout)
  - Coordination benchmarks (Swarm, Economic, Emergence)
  - UnifiedScorer and GlobalLeaderboard
  - Harbor runner (availability check)
  - MCP Atlas runner (tool count, category coverage)
  - MCP benchmark tools registration
"""

import pytest


class TestBenchmarkEngine:
    """Test the core BenchmarkEngine."""

    def test_engine_creation(self):
        from kernel.benchmark.engine import BenchmarkEngine
        engine = BenchmarkEngine()
        assert engine is not None
        assert engine._data_dir.exists()

    def test_register_all(self):
        from kernel.benchmark.engine import BenchmarkEngine
        engine = BenchmarkEngine()
        engine.register_all()
        runners = engine.list_runners()
        assert len(runners) >= 5  # fcpi, safety, memory, sandstorm, coordination
        categories = {r["category"] for r in runners}
        assert "fcpi" in categories
        assert "safety" in categories

    def test_list_runners(self):
        from kernel.benchmark.engine import BenchmarkEngine
        engine = BenchmarkEngine()
        engine.register_all()
        runners = engine.list_runners()
        for r in runners:
            assert "name" in r
            assert "category" in r
            assert "available" in r

    def test_run_single(self):
        import asyncio
        from kernel.benchmark.engine import BenchmarkEngine
        engine = BenchmarkEngine()
        engine.register_all()
        result = asyncio.run(engine.run_single("fcpi", model="test"))
        assert result is not None
        # Should have results (list) or a single result

    def test_global_comparison(self):
        from kernel.benchmark.engine import BenchmarkEngine
        engine = BenchmarkEngine()
        leaders = engine.get_global_comparison()
        assert "SWE-bench Pro" in leaders
        assert len(leaders["SWE-bench Pro"]) >= 2

    def test_format_report(self):
        from kernel.benchmark.engine import BenchmarkEngine, BenchmarkSuite
        engine = BenchmarkEngine()
        suite = BenchmarkSuite(suite_id="test_suite")
        report = engine.format_report(suite)
        assert "SCLEROTIUM OS" in report
        assert "BENCHMARK REPORT" in report

    def test_format_json_report(self):
        from kernel.benchmark.engine import BenchmarkEngine, BenchmarkSuite
        engine = BenchmarkEngine()
        suite = BenchmarkSuite(suite_id="test_json")
        report = engine.format_json_report(suite)
        assert report["suite_id"] == "test_json"
        assert "total_score" in report
        assert "fcpi_vector" in report

    def test_history_persistence(self):
        from kernel.benchmark.engine import BenchmarkEngine, BenchmarkSuite
        engine = BenchmarkEngine(data_dir="./data/benchmarks_test")
        # Should not crash on empty history
        history = engine.get_history()
        assert isinstance(history, list)

    def test_percentile_estimation(self):
        from kernel.benchmark.engine import BenchmarkEngine
        engine = BenchmarkEngine()
        assert engine._estimate_percentile(85) >= 99.0
        assert engine._estimate_percentile(70) >= 80.0
        assert engine._estimate_percentile(30) <= 20.0


class TestFCPIBenchmark:
    """Test the FCPI 6-dimension benchmark."""

    def test_run_all_dimensions(self):
        from kernel.benchmark.fcpi_benchmark import FCPIBenchmark
        bench = FCPIBenchmark(".")
        vector = bench.run()
        assert 0 <= vector.coding <= 1
        assert 0 <= vector.coordination <= 1
        assert 0 <= vector.safety <= 1
        assert 0 <= vector.decision <= 1
        assert 0 <= vector.emergence <= 1
        assert 0 <= vector.performance <= 1

    def test_vector_to_dict(self):
        from kernel.benchmark.fcpi_benchmark import FCPIBenchmark
        bench = FCPIBenchmark(".")
        vector = bench.run()
        d = vector.to_dict()
        assert len(d) == 6
        assert all(k in d for k in ["coding", "coordination", "safety", "decision", "emergence", "performance"])

    def test_aggregate_score(self):
        from kernel.benchmark.fcpi_benchmark import FCPIBenchmark
        bench = FCPIBenchmark(".")
        vector = bench.run()
        agg = vector.aggregate()
        assert 0 <= agg <= 1

    def test_list_benchmarks(self):
        from kernel.benchmark.fcpi_benchmark import FCPIBenchmark
        bench = FCPIBenchmark(".")
        benchmarks = bench.list_benchmarks()
        assert len(benchmarks) == 6
        assert "fcpi_coding" in benchmarks

    def test_run_benchmarks_async(self):
        import asyncio
        from kernel.benchmark.fcpi_benchmark import FCPIBenchmark
        bench = FCPIBenchmark(".")
        results = asyncio.run(bench.run_benchmarks(model="test"))
        assert len(results) == 6
        for r in results:
            assert r.category == "fcpi"
            assert 0 <= r.score <= 100

    def test_goodharting_detection(self):
        from kernel.benchmark.fcpi_benchmark import FCPIBenchmark, FCPIVector
        bench = FCPIBenchmark(".")
        # Extreme case: coding skyrockets while all others crash
        history = [
            FCPIVector(0.5, 0.5, 0.5, 0.5, 0.5, 0.5),
            FCPIVector(0.6, 0.45, 0.4, 0.4, 0.4, 0.4),
            FCPIVector(0.99, 0.05, 0.05, 0.05, 0.05, 0.05),  # Coding at 0.99, others near 0
        ]
        result = bench.detect_goodharting(history)
        assert result["goodharting_detected"]  # Should detect extreme over-optimization
        assert result["suspicious_dimension"] == "coding"

    def test_goodharting_not_detected_balanced(self):
        from kernel.benchmark.fcpi_benchmark import FCPIBenchmark, FCPIVector
        bench = FCPIBenchmark(".")
        history = [
            FCPIVector(0.5, 0.5, 0.5, 0.5, 0.5, 0.5),
            FCPIVector(0.55, 0.53, 0.54, 0.52, 0.51, 0.55),
            FCPIVector(0.6, 0.58, 0.59, 0.57, 0.56, 0.6),
        ]
        result = bench.detect_goodharting(history)
        assert not result["goodharting_detected"]


class TestSafetyBenchmark:
    """Test safety benchmarks."""

    def test_constitutional_arbiter(self):
        import asyncio
        from kernel.benchmark.safety_benchmark import SafetyBenchmark
        bench = SafetyBenchmark(".")
        result = bench._bench_constitutional_arbiter("test")
        assert result.category == "safety"
        assert "gates_implemented" in result.sub_scores

    def test_audit_integrity(self):
        from kernel.benchmark.safety_benchmark import SafetyBenchmark
        bench = SafetyBenchmark(".")
        result = bench._bench_audit_integrity("test")
        assert result.category == "safety"
        assert "chain_valid" in result.sub_scores or len(result.errors) > 0

    def test_dangerous_ops(self):
        from kernel.benchmark.safety_benchmark import SafetyBenchmark
        bench = SafetyBenchmark(".")
        result = bench._bench_dangerous_ops("test")
        assert result.category == "safety"

    def test_static_security(self):
        from kernel.benchmark.safety_benchmark import SafetyBenchmark
        bench = SafetyBenchmark(".")
        result = bench._bench_static_security("test")
        assert result.category == "safety"
        assert "files_scanned" in result.sub_scores

    def test_sandstorm_isolation(self):
        import asyncio
        from kernel.benchmark.safety_benchmark import SafetyBenchmark
        bench = SafetyBenchmark(".")
        result = asyncio.run(bench._bench_sandstorm_isolation("test"))
        assert result.category == "safety"
        assert "l1_executes" in result.sub_scores

    def test_run_all_safety(self):
        import asyncio
        from kernel.benchmark.safety_benchmark import SafetyBenchmark
        bench = SafetyBenchmark(".")
        results = asyncio.run(bench.run_benchmarks(model="test"))
        assert len(results) == 5

    def test_list_benchmarks(self):
        from kernel.benchmark.safety_benchmark import SafetyBenchmark
        bench = SafetyBenchmark(".")
        benchmarks = bench.list_benchmarks()
        assert len(benchmarks) == 5


class TestMemoryBenchmark:
    """Test memory benchmarks."""

    def test_throughput(self):
        from kernel.benchmark.memory_benchmark import MemoryBenchmark
        bench = MemoryBenchmark(".")
        result = bench._bench_store_throughput("test")
        assert result.category == "memory"
        # May have errors if ChromaDB not installed
        assert "writes_per_sec" in result.sub_scores or len(result.errors) > 0

    def test_search_latency(self):
        from kernel.benchmark.memory_benchmark import MemoryBenchmark
        bench = MemoryBenchmark(".")
        result = bench._bench_search_latency("test")
        assert result.category == "memory"

    def test_ebbinghaus(self):
        from kernel.benchmark.memory_benchmark import MemoryBenchmark
        bench = MemoryBenchmark(".")
        result = bench._bench_ebbinghaus("test")
        assert result.category == "memory"

    def test_consolidation(self):
        from kernel.benchmark.memory_benchmark import MemoryBenchmark
        bench = MemoryBenchmark(".")
        result = bench._bench_consolidation("test")
        assert result.category == "memory"

    def test_persistence(self):
        from kernel.benchmark.memory_benchmark import MemoryBenchmark
        bench = MemoryBenchmark(".")
        result = bench._bench_persistence("test")
        assert result.category == "memory"

    def test_cross_level(self):
        from kernel.benchmark.memory_benchmark import MemoryBenchmark
        bench = MemoryBenchmark(".")
        result = bench._bench_cross_level("test")
        assert result.category == "memory"

    def test_run_all_memory(self):
        import asyncio
        from kernel.benchmark.memory_benchmark import MemoryBenchmark
        bench = MemoryBenchmark(".")
        results = asyncio.run(bench.run_benchmarks(model="test"))
        assert len(results) == 6

    def test_list_benchmarks(self):
        from kernel.benchmark.memory_benchmark import MemoryBenchmark
        bench = MemoryBenchmark(".")
        benchmarks = bench.list_benchmarks()
        assert len(benchmarks) == 6


class TestSandstormBenchmark:
    """Test sandstorm benchmarks."""

    def test_startup(self):
        import asyncio
        from kernel.benchmark.sandstorm_benchmark import SandstormBenchmark
        bench = SandstormBenchmark(".")
        result = asyncio.run(bench._bench_startup("test"))
        assert result.category == "sandstorm"

    def test_isolation(self):
        import asyncio
        from kernel.benchmark.sandstorm_benchmark import SandstormBenchmark
        bench = SandstormBenchmark(".")
        result = asyncio.run(bench._bench_isolation("test"))
        assert result.category == "sandstorm"

    def test_throughput(self):
        import asyncio
        from kernel.benchmark.sandstorm_benchmark import SandstormBenchmark
        bench = SandstormBenchmark(".")
        result = asyncio.run(bench._bench_throughput("test"))
        assert result.category == "sandstorm"

    def test_timeout(self):
        import asyncio
        from kernel.benchmark.sandstorm_benchmark import SandstormBenchmark
        bench = SandstormBenchmark(".")
        result = asyncio.run(bench._bench_timeout("test"))
        assert result.category == "sandstorm"

    def test_docker(self):
        import asyncio
        from kernel.benchmark.sandstorm_benchmark import SandstormBenchmark
        bench = SandstormBenchmark(".")
        result = asyncio.run(bench._bench_docker("test"))
        assert result.category == "sandstorm"

    def test_run_all_sandstorm(self):
        import asyncio
        from kernel.benchmark.sandstorm_benchmark import SandstormBenchmark
        bench = SandstormBenchmark(".")
        results = asyncio.run(bench.run_benchmarks(model="test"))
        assert len(results) == 5

    def test_list_benchmarks(self):
        from kernel.benchmark.sandstorm_benchmark import SandstormBenchmark
        bench = SandstormBenchmark(".")
        benchmarks = bench.list_benchmarks()
        assert len(benchmarks) == 5


class TestCoordinationBenchmark:
    """Test coordination benchmarks."""

    def test_swarm(self):
        from kernel.benchmark.coordination_benchmark import CoordinationBenchmark
        bench = CoordinationBenchmark(".")
        result = bench._bench_swarm("test")
        assert result.category == "coordination"

    def test_economic(self):
        from kernel.benchmark.coordination_benchmark import CoordinationBenchmark
        bench = CoordinationBenchmark(".")
        result = bench._bench_economic("test")
        assert result.category == "coordination"

    def test_emergence(self):
        from kernel.benchmark.coordination_benchmark import CoordinationBenchmark
        bench = CoordinationBenchmark(".")
        result = bench._bench_emergence("test")
        assert result.category == "coordination"

    def test_scalability(self):
        from kernel.benchmark.coordination_benchmark import CoordinationBenchmark
        bench = CoordinationBenchmark(".")
        result = bench._bench_scalability("test")
        assert result.category == "coordination"

    def test_run_all_coordination(self):
        import asyncio
        from kernel.benchmark.coordination_benchmark import CoordinationBenchmark
        bench = CoordinationBenchmark(".")
        results = asyncio.run(bench.run_benchmarks(model="test"))
        assert len(results) == 4


class TestUnifiedScorer:
    """Test unified scoring system."""

    def test_compute_unified_score(self):
        from kernel.benchmark.scorer import UnifiedScorer
        from kernel.benchmark.engine import BenchmarkResult, BenchmarkStatus

        results = [
            BenchmarkResult("test1", "fcpi", BenchmarkStatus.PASSED, 75.0, sub_scores={"coding": 0.75}),
            BenchmarkResult("test2", "safety", BenchmarkStatus.PASSED, 80.0),
            BenchmarkResult("test3", "memory", BenchmarkStatus.PASSED, 65.0),
        ]
        score = UnifiedScorer.compute_unified_score(results)
        assert 0 <= score["unified_score"] <= 100
        assert "fcpi_avg" in score["category_scores"]

    def test_get_rating(self):
        from kernel.benchmark.scorer import UnifiedScorer
        assert "S+" in UnifiedScorer.get_rating(95)
        assert "S" in UnifiedScorer.get_rating(85)
        assert "A+" in UnifiedScorer.get_rating(78)
        assert "A" in UnifiedScorer.get_rating(72)
        assert "B+" in UnifiedScorer.get_rating(62)
        assert "F" in UnifiedScorer.get_rating(25)

    def test_empty_results(self):
        from kernel.benchmark.scorer import UnifiedScorer
        score = UnifiedScorer.compute_unified_score([])
        assert score["unified_score"] == 0.0
        assert score["num_categories_evaluated"] == 0


class TestGlobalLeaderboard:
    """Test global leaderboard system."""

    def test_get_rankings_all(self):
        from kernel.benchmark.scorer import GlobalLeaderboard
        rankings = GlobalLeaderboard.get_rankings("all")
        assert len(rankings) > 5

    def test_get_rankings_coding(self):
        from kernel.benchmark.scorer import GlobalLeaderboard
        rankings = GlobalLeaderboard.get_rankings("coding")
        assert len(rankings) >= 3
        assert rankings[0]["category"] == "coding"

    def test_compare(self):
        from kernel.benchmark.scorer import GlobalLeaderboard
        comparison = GlobalLeaderboard.compare(55.0, "coding")
        assert comparison["sclerotium_score"] == 55.0
        assert comparison["category"] == "coding"
        assert "estimated_rank" in comparison
        assert "above" in comparison
        assert "below" in comparison

    def test_rankings_sorted(self):
        from kernel.benchmark.scorer import GlobalLeaderboard
        rankings = GlobalLeaderboard.get_rankings("all")
        scores = [r["score"] for r in rankings]
        assert scores == sorted(scores, reverse=True)


class TestHarborRunner:
    """Test Harbor runner."""

    def test_creation(self):
        from pathlib import Path
        from kernel.benchmark.harbor_runner import HarborRunner
        runner = HarborRunner(Path("./data/bench_harbor_test"))
        assert runner is not None

    def test_list_benchmarks(self):
        from pathlib import Path
        from kernel.benchmark.harbor_runner import HarborRunner
        runner = HarborRunner(Path("./data/bench_harbor_test"))
        benchmarks = runner.list_benchmarks()
        assert "swe_bench_pro" in benchmarks
        assert "terminal_bench_2" in benchmarks

    def test_run_swe_bench_skipped(self):
        import asyncio
        from pathlib import Path
        from kernel.benchmark.harbor_runner import HarborRunner
        runner = HarborRunner(Path("./data/bench_harbor_test"))
        result = asyncio.run(runner._run_swe_bench("test"))
        assert result.category == "authority"

    def test_run_terminal_bench_skipped(self):
        import asyncio
        from pathlib import Path
        from kernel.benchmark.harbor_runner import HarborRunner
        runner = HarborRunner(Path("./data/bench_harbor_test"))
        result = asyncio.run(runner._run_terminal_bench("test"))
        assert result.category == "authority"


class TestMCPAtlasRunner:
    """Test MCP Atlas runner."""

    def test_creation(self):
        from pathlib import Path
        from kernel.benchmark.mcp_atlas_runner import MCPAtlasRunner
        runner = MCPAtlasRunner(Path("./data/bench_atlas_test"))
        assert runner is not None

    def test_list_benchmarks(self):
        from pathlib import Path
        from kernel.benchmark.mcp_atlas_runner import MCPAtlasRunner
        runner = MCPAtlasRunner(Path("./data/bench_atlas_test"))
        benchmarks = runner.list_benchmarks()
        assert "mcp_atlas" in benchmarks

    def test_run_mcp_atlas(self):
        import asyncio
        from pathlib import Path
        from kernel.benchmark.mcp_atlas_runner import MCPAtlasRunner
        runner = MCPAtlasRunner(Path("./data/bench_atlas_test"))
        result = asyncio.run(runner.run_mcp_atlas("test"))
        assert result.category == "authority"
        assert "tool_count_ratio" in result.sub_scores
        assert "sclerotium_tool_count" in result.details


class TestBenchmarkMCPTools:
    """Test MCP benchmark tools registration."""

    def test_tools_registered(self):
        from mcp.server import SclerotiumMCPServer
        server = SclerotiumMCPServer()
        server.register_all_tools()

        tool_names = [
            "benchmark_run_full", "benchmark_run_single",
            "benchmark_list", "benchmark_history",
            "benchmark_compare", "benchmark_fcpi",
        ]
        for name in tool_names:
            assert server.tools.get_handler(name) is not None, f"Missing benchmark tool: {name}"

    def test_benchmark_list(self):
        import asyncio
        async def _test():
            from mcp.tools.benchmark import _benchmark_list
            result = await _benchmark_list()
            assert "runners" in result
            assert result["total_runners"] >= 5
        asyncio.run(_test())

    def test_benchmark_fcpi(self):
        import asyncio
        async def _test():
            from mcp.tools.benchmark import _benchmark_fcpi
            result = await _benchmark_fcpi()
            assert "fcpi_vector" in result
            assert "aggregate_score" in result
            assert "rating" in result
            assert len(result["fcpi_vector"]) == 6
        asyncio.run(_test())

    def test_benchmark_history(self):
        import asyncio
        async def _test():
            from mcp.tools.benchmark import _benchmark_history
            result = await _benchmark_history({"limit": 5})
            assert "history" in result
        asyncio.run(_test())

    def test_benchmark_compare(self):
        import asyncio
        async def _test():
            from mcp.tools.benchmark import _benchmark_compare
            result = await _benchmark_compare({"category": "coding"})
            assert "global_rankings" in result
            assert "estimated_rank" in result or "sclerotium_score" in result
        asyncio.run(_test())

    def test_benchmark_run_single(self):
        import asyncio
        async def _test():
            from mcp.tools.benchmark import _benchmark_run_single
            result = await _benchmark_run_single({"name": "fcpi", "model": "test"})
            assert "status" in result or "name" in result
        asyncio.run(_test())


class TestFungalBenchmark:
    """Test fungal-cortex service benchmarks."""

    def test_eventbus(self):
        from kernel.benchmark.fungal_benchmark import FungalBenchmark
        bench = FungalBenchmark()
        result = bench._bench_eventbus("test")
        assert result.category == "fungal"

    def test_skills(self):
        from kernel.benchmark.fungal_benchmark import FungalBenchmark
        bench = FungalBenchmark()
        result = bench._bench_skills("test")
        assert result.category == "fungal"

    def test_stigmergy(self):
        from kernel.benchmark.fungal_benchmark import FungalBenchmark
        bench = FungalBenchmark()
        result = bench._bench_stigmergy("test")
        assert result.category == "fungal"

    def test_immune(self):
        from kernel.benchmark.fungal_benchmark import FungalBenchmark
        bench = FungalBenchmark()
        result = bench._bench_immune("test")
        assert result.category == "fungal"

    def test_panarchy(self):
        from kernel.benchmark.fungal_benchmark import FungalBenchmark
        bench = FungalBenchmark()
        result = bench._bench_panarchy("test")
        assert result.category == "fungal"

    def test_morphogen(self):
        from kernel.benchmark.fungal_benchmark import FungalBenchmark
        bench = FungalBenchmark()
        result = bench._bench_morphogen("test")
        assert result.category == "fungal"

    def test_dendrite(self):
        from kernel.benchmark.fungal_benchmark import FungalBenchmark
        bench = FungalBenchmark()
        result = bench._bench_dendrite("test")
        assert result.category == "fungal"

    def test_autocatalytic(self):
        from kernel.benchmark.fungal_benchmark import FungalBenchmark
        bench = FungalBenchmark()
        result = bench._bench_autocatalytic("test")
        assert result.category == "fungal"

    def test_dgm(self):
        from kernel.benchmark.fungal_benchmark import FungalBenchmark
        bench = FungalBenchmark()
        result = bench._bench_dgm("test")
        assert result.category == "fungal"

    def test_scanner(self):
        from kernel.benchmark.fungal_benchmark import FungalBenchmark
        bench = FungalBenchmark()
        result = bench._bench_scanner("test")
        assert result.category == "fungal"

    def test_run_all_fungal(self):
        import asyncio
        from kernel.benchmark.fungal_benchmark import FungalBenchmark
        bench = FungalBenchmark()
        results = asyncio.run(bench.run_benchmarks(model="test"))
        assert len(results) == 10

    def test_list_benchmarks(self):
        from kernel.benchmark.fungal_benchmark import FungalBenchmark
        bench = FungalBenchmark()
        benchmarks = bench.list_benchmarks()
        assert len(benchmarks) == 10


class TestMiroFishBenchmark:
    """Test MiroFish evolution engine benchmarks."""

    def test_arena_base(self):
        from kernel.benchmark.mirofish_benchmark import MiroFishBenchmark
        bench = MiroFishBenchmark()
        result = bench._bench_arena_base("test")
        assert result.category == "mirofish"

    def test_coding_arena(self):
        from kernel.benchmark.mirofish_benchmark import MiroFishBenchmark
        bench = MiroFishBenchmark()
        result = bench._bench_arena("coding", "test")
        assert result.category == "mirofish"

    def test_coordination_arena(self):
        from kernel.benchmark.mirofish_benchmark import MiroFishBenchmark
        bench = MiroFishBenchmark()
        result = bench._bench_arena("coordination", "test")
        assert result.category == "mirofish"

    def test_safety_arena(self):
        from kernel.benchmark.mirofish_benchmark import MiroFishBenchmark
        bench = MiroFishBenchmark()
        result = bench._bench_arena("safety", "test")
        assert result.category == "mirofish"

    def test_evolution_mgr(self):
        from kernel.benchmark.mirofish_benchmark import MiroFishBenchmark
        bench = MiroFishBenchmark()
        result = bench._bench_evolution_mgr("test")
        assert result.category == "mirofish"

    def test_fitness_extractor(self):
        from kernel.benchmark.mirofish_benchmark import MiroFishBenchmark
        bench = MiroFishBenchmark()
        result = bench._bench_fitness_extractor("test")
        assert result.category == "mirofish"

    def test_dgm_bridge(self):
        from kernel.benchmark.mirofish_benchmark import MiroFishBenchmark
        bench = MiroFishBenchmark()
        result = bench._bench_dgm_bridge("test")
        assert result.category == "mirofish"

    def test_run_all_mirofish(self):
        import asyncio
        from kernel.benchmark.mirofish_benchmark import MiroFishBenchmark
        bench = MiroFishBenchmark()
        results = asyncio.run(bench.run_benchmarks(model="test"))
        assert len(results) == 10

    def test_list_benchmarks(self):
        from kernel.benchmark.mirofish_benchmark import MiroFishBenchmark
        bench = MiroFishBenchmark()
        benchmarks = bench.list_benchmarks()
        assert len(benchmarks) == 10


class TestTrinityBenchmark:
    """Test trinity cross-system benchmarks."""

    def test_fungal_to_sclerotium(self):
        from kernel.benchmark.trinity_benchmark import TrinityBenchmark
        bench = TrinityBenchmark()
        result = bench._bench_fungal_to_sclerotium("test")
        assert result.category == "trinity"

    def test_sclerotium_to_fungal(self):
        from kernel.benchmark.trinity_benchmark import TrinityBenchmark
        bench = TrinityBenchmark()
        result = bench._bench_sclerotium_to_fungal("test")
        assert result.category == "trinity"

    def test_mirofish_to_fungal(self):
        from kernel.benchmark.trinity_benchmark import TrinityBenchmark
        bench = TrinityBenchmark()
        result = bench._bench_mirofish_to_fungal("test")
        assert result.category == "trinity"

    def test_fungal_to_mirofish(self):
        from kernel.benchmark.trinity_benchmark import TrinityBenchmark
        bench = TrinityBenchmark()
        result = bench._bench_fungal_to_mirofish("test")
        assert result.category == "trinity"

    def test_mirofish_to_sclerotium(self):
        from kernel.benchmark.trinity_benchmark import TrinityBenchmark
        bench = TrinityBenchmark()
        result = bench._bench_mirofish_to_sclerotium("test")
        assert result.category == "trinity"

    def test_sclerotium_to_mirofish(self):
        from kernel.benchmark.trinity_benchmark import TrinityBenchmark
        bench = TrinityBenchmark()
        result = bench._bench_sclerotium_to_mirofish("test")
        assert result.category == "trinity"

    def test_full_pipeline(self):
        from kernel.benchmark.trinity_benchmark import TrinityBenchmark
        bench = TrinityBenchmark()
        result = bench._bench_full_pipeline("test")
        assert result.category == "trinity"

    def test_combined_stats(self):
        from kernel.benchmark.trinity_benchmark import TrinityBenchmark
        bench = TrinityBenchmark()
        result = bench._bench_combined_stats("test")
        assert result.category == "trinity"

    def test_run_all_trinity(self):
        import asyncio
        from kernel.benchmark.trinity_benchmark import TrinityBenchmark
        bench = TrinityBenchmark()
        results = asyncio.run(bench.run_benchmarks(model="test"))
        assert len(results) == 8

    def test_list_benchmarks(self):
        from kernel.benchmark.trinity_benchmark import TrinityBenchmark
        bench = TrinityBenchmark()
        benchmarks = bench.list_benchmarks()
        assert len(benchmarks) == 8


class TestEngineTrinity:
    """Test engine with all trinity benchmarks registered."""

    def test_register_all_includes_trinity(self):
        from kernel.benchmark.engine import BenchmarkEngine
        engine = BenchmarkEngine()
        engine.register_all()
        runners = engine.list_runners()
        names = {r["name"] for r in runners}
        assert "fungal" in names
        assert "mirofish" in names
        assert "trinity" in names

    def test_all_categories_present(self):
        from kernel.benchmark.engine import BenchmarkEngine
        engine = BenchmarkEngine()
        engine.register_all()
        runners = engine.list_runners()
        categories = {r["category"] for r in runners}
        for cat in ["fcpi", "safety", "memory", "sandstorm", "coordination", "fungal", "mirofish", "trinity"]:
            assert cat in categories, f"Missing category: {cat}"
