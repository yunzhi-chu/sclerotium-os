"""Run the AI-driven benchmark suite with DeepSeek v4 Pro."""
import asyncio
import time
from kernel.benchmark.engine import BenchmarkEngine

async def main():
    print()
    print("=" * 72)
    print("  SCLEROTIUM OS -- AI-DRIVEN BENCHMARK")
    print("  Model: DeepSeek v4 Pro")
    print("  Benchmarks: HumanEval+ (20 tasks) + MCP Tool-Calling (5 tasks)")
    print("             + Code Generation (5 tasks) + Refactoring (2 tasks)")
    print("             + Trinity Pipeline (5 steps)")
    print("=" * 72)
    print()

    engine = BenchmarkEngine()
    engine.register_all()

    # Run AI benchmarks with real DeepSeek API
    t0 = time.monotonic()
    suite = await engine.run_full_suite(model="deepseek-v4-pro", include_authority=False)
    elapsed = time.monotonic() - t0

    report = engine.format_json_report(suite)

    # Print results
    ai_results = [r for r in report["results"] if r["category"] == "ai"]
    non_ai = [r for r in report["results"] if r["category"] != "ai"]

    if ai_results:
        print("-" * 72)
        print("  AI BENCHMARK RESULTS (DeepSeek v4 Pro)")
        print("-" * 72)
        for r in ai_results:
            bar = "#" * int(r["score"] / 5) + "-" * (20 - int(r["score"] / 5))
            print(f"  [{r['status'].upper()}] {r['name']:<35} [{bar}] {r['score']:>5.1f}%")
            if r.get("sub_scores"):
                for k, v in r["sub_scores"].items():
                    print(f"         {k}: {v:.3f}" if isinstance(v, float) else f"         {k}: {v}")
            if r.get("errors"):
                for e in r["errors"][:2]:
                    print(f"         Error: {e[:100]}")
        print()

    print("-" * 72)
    print(f"  Full Suite Summary ({len(report['results'])} benchmarks, {elapsed:.0f}s)")
    print("-" * 72)
    print(f"  Unified Score:  {report['total_score']:.1f}/100")
    print(f"  Percentile:     {report['global_percentile']}%")
    print(f"  Rating:         {_rating(report['total_score'])}")
    print()

    # Category breakdown with AI weighted at 30%
    cats = {}
    for r in report["results"]:
        cats.setdefault(r["category"], []).append(r["score"])
    for cat, scores in sorted(cats.items()):
        avg = sum(scores) / len(scores)
        bar = "#" * int(avg / 5) + "-" * (20 - int(avg / 5))
        label = f"{cat} ({'30%' if cat == 'ai' else '15%' if cat in ('authority','fcpi') else '4-10%'})"
        print(f"  {label:<24} [{bar}] {avg:>5.1f}% ({len(scores)} benchmarks)")

    print()
    print("  Note: ai_humaneval_plus uses 20 representative tasks from the")
    print("  full 164-task HumanEval+ benchmark. Score = pass@1 on this subset.")
    print("  DeepSeek v4 Pro estimated HumanEval+ full score: ~92% (2026 leaderboard)")
    print()
    print("=" * 72)


def _rating(s: float) -> str:
    if s >= 90: return "S+ (Transcendent)"
    if s >= 85: return "S (World-Class)"
    if s >= 78: return "A+ (Excellent)"
    if s >= 70: return "A (Very Good)"
    if s >= 60: return "B+ (Good)"
    return "B (Above Average)"


if __name__ == "__main__":
    asyncio.run(main())
