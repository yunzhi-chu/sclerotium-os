"""MCP Benchmark Tools — Run and manage benchmarks via MCP protocol."""
from mcp.server import ToolRegistry


async def _benchmark_run_full(params: dict | None = None) -> dict:
    """Run full benchmark suite."""
    params = params or {}
    model = params.get("model", "deepseek-v4")
    include_authority = params.get("include_authority", False)

    from kernel.benchmark.engine import BenchmarkEngine
    engine = BenchmarkEngine()
    engine.register_all()
    suite = await engine.run_full_suite(model=model, include_authority=include_authority)
    return engine.format_json_report(suite)


async def _benchmark_run_single(params: dict) -> dict:
    """Run a single named benchmark."""
    # BUG-006修复: 默认名称改为 "fcpi" (注册键), 而非 "fcpi_coding"
    name = params.get("name", "fcpi")
    model = params.get("model", "deepseek-v4")

    from kernel.benchmark.engine import BenchmarkEngine
    engine = BenchmarkEngine()
    engine.register_all()
    result = await engine.run_single(name, model=model)
    return {
        "name": result.name,
        "category": result.category,
        "status": result.status.value,
        "score": result.score,
        "sub_scores": result.sub_scores,
        "errors": result.errors,
        "duration_ms": result.duration_ms,
    }


async def _benchmark_list() -> dict:
    """List all available benchmarks."""
    from kernel.benchmark.engine import BenchmarkEngine
    engine = BenchmarkEngine()
    engine.register_all()
    runners = engine.list_runners()
    return {"runners": runners, "total_runners": len(runners)}


async def _benchmark_history(params: dict | None = None) -> dict:
    """Get benchmark run history."""
    params = params or {}
    limit = params.get("limit", 20)

    from kernel.benchmark.engine import BenchmarkEngine
    engine = BenchmarkEngine()
    return {"history": engine.get_history(limit=limit)}


async def _benchmark_compare(params: dict) -> dict:
    """Compare Sclerotium OS score against global leaders."""
    from kernel.benchmark.engine import BenchmarkEngine
    from kernel.benchmark.scorer import GlobalLeaderboard

    category = params.get("category", "coding")

    # Get latest score
    engine = BenchmarkEngine()
    history = engine.get_history(limit=1)
    score = history[0]["total_score"] if history else 0.0

    comparison = GlobalLeaderboard.compare(score, category=category)
    comparison["global_rankings"] = GlobalLeaderboard.get_rankings(category)
    return comparison


async def _benchmark_fcpi() -> dict:
    """Run FCPI 6-dimension benchmark only."""
    from kernel.benchmark.fcpi_benchmark import FCPIBenchmark
    bench = FCPIBenchmark(".")
    vector = bench.run()
    return {
        "fcpi_vector": vector.to_dict(),
        "aggregate_score": round(vector.aggregate() * 100, 2),
        "rating": _rating(vector.aggregate()),
    }


def _rating(score: float) -> str:
    if score >= 0.9: return "S+"
    if score >= 0.8: return "S"
    if score >= 0.7: return "A"
    if score >= 0.6: return "B"
    if score >= 0.5: return "C"
    return "D"


def register_benchmark_tools(registry: ToolRegistry) -> None:
    # BUG#6修复: 每个 benchmark 工具有精确参数 Schema, 不再用空 {}
    tool_specs = [
        ("benchmark_run_full", "Run complete benchmark suite (all categories).", {
            "properties": {
                "params": {"type": "object", "default": {},
                           "description": "{model: 'deepseek-v4', include_authority: false}"},
            }, "required": [],
        }, _benchmark_run_full),
        ("benchmark_run_single", "Run a single benchmark by name (fcpi_coding, safety_constitutional_arbiter, memory_throughput, etc.).", {
            "properties": {
                "params": {"type": "object",
                           "description": "{name: 'fcpi_coding', model: 'deepseek-v4'}"},
            }, "required": ["params"],
        }, _benchmark_run_single),
        ("benchmark_list", "List all available benchmark runners and their categories.", {
            "properties": {}, "required": [],
        }, _benchmark_list),
        ("benchmark_history", "Get history of past benchmark runs with scores.", {
            "properties": {}, "required": [],
        }, _benchmark_history),
        ("benchmark_compare", "Compare Sclerotium OS score against global AI leaderboard.", {
            "properties": {}, "required": [],
        }, _benchmark_compare),
        ("benchmark_fcpi", "Run FCPI 6-dimension self-evolution benchmark only.", {
            "properties": {
                "params": {"type": "object", "default": {},
                           "description": "{model: 'deepseek-v4'}"},
            }, "required": [],
        }, _benchmark_fcpi),
    ]
    for name, desc, params, handler in tool_specs:
        registry.register(
            name=name, description=desc,
            parameters={"type": "object", **params},
            handler=handler, category="benchmark",
        )
