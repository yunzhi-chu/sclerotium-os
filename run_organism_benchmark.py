"""Run the FULL ORGANISM benchmark — DeepSeek through Sclerotium body."""
import asyncio
import time
from kernel.benchmark.organism_benchmark import OrganismBenchmark, _init_body

async def main():
    print()
    print("=" * 72)
    print("  SCLEROTIUM OS — FULL ORGANISM BENCHMARK")
    print("  DeepSeek v4 Pro through the COMPLETE Sclerotium body")
    print()
    print("  Pipeline: Gateway → Arbiter → Sandstorm → Memory → EvolutionBridge")
    print("  Each HumanEval task flows through ALL 5 organs")
    print("=" * 72)
    print()

    # Init body
    print("Initializing Sclerotium organism body...")
    stats = _init_body()
    print(f"  Gateway:    {stats['gateway_providers']} providers")
    print(f"  Arbiter:    5 gates ready")
    print(f"  Sandstorm:  {stats['sandstorm_levels']} isolation levels")
    print(f"  Memory:     {stats['memory_levels']} layers + ChromaDB vector")
    print(f"  Evolution:  {'READY' if stats['evolution_ready'] else 'PENDING'}")
    print(f"  Init time:  {stats['init_time_ms']:.0f}ms")
    print()

    bench = OrganismBenchmark()
    results = await bench.run_benchmarks()

    print()
    print("=" * 72)
    print("  ORGANISM BENCHMARK RESULTS")
    print("=" * 72)

    total_score = 0
    for r in results:
        bar = "#" * int(r.score / 5) + "-" * (20 - int(r.score / 5))
        print(f"  [{r.status.value.upper()}] {r.name:<35} [{bar}] {r.score:>5.1f}%")
        if r.sub_scores:
            for k, v in r.sub_scores.items():
                print(f"         {k}: {v:.3f}" if isinstance(v, float) else f"         {k}: {v}")
        if r.errors:
            for e in r.errors[:2]:
                print(f"         Error: {e[:120]}")
        total_score += r.score
        print()

    avg = total_score / len(results) if results else 0
    print(f"  ORGANISM AVERAGE: {avg:.1f}% across {len(results)} benchmarks")
    print()
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(main())
