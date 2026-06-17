"""Unified Scorer & Global Leaderboard.

Aggregates benchmark results across all dimensions into a unified 0-100
score and ranks Sclerotium OS against global state-of-the-art systems.

Weighting:
  - Authority benchmarks (SWE-bench, Terminal-Bench, MCP Atlas): 40%
  - FCPI 6-dimension (custom): 30%
  - Safety (custom): 15%
  - Memory + Sandstorm + Coordination (custom): 15%

Reference leaderboard (May 2026):
  Claude Opus 4.7 Adaptive, GPT-5.4 xHigh, Gemini 3.5 Flash,
  A-Evolve + Opus 4.6, Claude Mythos Preview, Qwen3.7 Max
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GlobalRanking:
    """A system's position on the global leaderboard."""
    rank: int
    system: str
    score: float
    category: str  # "coding", "agent", "safety", "overall"
    source_benchmark: str
    date: str


class UnifiedScorer:
    """Aggregate scores across all benchmark categories.

    Produces a single unified score on a 0-100 scale that's comparable
    across different AI systems.
    """

    # Weights for each category in the unified score
    CATEGORY_WEIGHTS = {
        "livecode": 0.30,    # LiveCodeBench v5 — #1 coding benchmark, zero contamination
        "fcpi": 0.20,        # Sclerotium 6-dimension self-evolution
        "ai": 0.15,          # DeepSeek: HumanEval+ + MCP tools + code gen
        "safety": 0.08,      # Constitutional Arbiter + Sandstorm
        "memory": 0.05,      # Hexis 5-layer + Ebbinghaus
        "sandstorm": 0.05,   # L1/L2/L3 isolation
        "coordination": 0.04,# Swarm + Economic Net
        "fungal": 0.08,      # fungal-cortex: EventBus, Skills, Stigmergy, Immune, DGM
        "mirofish": 0.05,    # MiroFish: 6 Arenas, EvolutionMgr, FitnessExtractor
    }

    @classmethod
    def compute_unified_score(cls, results: list[Any]) -> dict[str, Any]:
        """Compute unified score from benchmark results."""
        from kernel.benchmark.engine import BenchmarkResult

        category_scores: dict[str, list[float]] = {}
        for r in results:
            if isinstance(r, BenchmarkResult):
                cat = r.category if r.category in cls.CATEGORY_WEIGHTS else "fcpi"
                category_scores.setdefault(cat, []).append(r.score)

        # Weighted average
        weighted_score = 0.0
        total_weight = 0.0
        sub_scores = {}

        for cat, weight in cls.CATEGORY_WEIGHTS.items():
            scores = category_scores.get(cat, [])
            if scores:
                avg = sum(scores) / len(scores)
                weighted_score += avg * weight
                total_weight += weight
                sub_scores[f"{cat}_avg"] = round(avg, 2)
            else:
                sub_scores[f"{cat}_avg"] = 0.0

        if total_weight > 0:
            unified = weighted_score / total_weight
        else:
            unified = 0.0

        return {
            "unified_score": round(unified, 2),
            "category_scores": sub_scores,
            "num_categories_evaluated": len(category_scores),
            "num_categories_total": len(cls.CATEGORY_WEIGHTS),
            "coverage_ratio": round(len(category_scores) / len(cls.CATEGORY_WEIGHTS), 2),
        }

    @classmethod
    def get_rating(cls, score: float) -> str:
        """Get a human-readable rating for a score."""
        if score >= 90:
            return "S+ (Transcendent)"
        elif score >= 85:
            return "S (World-Class)"
        elif score >= 78:
            return "A+ (Excellent)"
        elif score >= 70:
            return "A (Very Good)"
        elif score >= 60:
            return "B+ (Good)"
        elif score >= 50:
            return "B (Above Average)"
        elif score >= 40:
            return "C (Average)"
        elif score >= 30:
            return "D (Below Average)"
        else:
            return "F (Needs Improvement)"


class GlobalLeaderboard:
    """Global AI system leaderboard for comparison.

    Aggregates scores from authoritative benchmarks to rank systems.
    """

    # May 2026 global leaderboard — authoritative benchmarks only
    GLOBAL_RANKINGS = [
        # Coding
        GlobalRanking(1, "Claude Mythos Preview", 77.8, "coding", "SWE-bench Pro", "2026-05"),
        GlobalRanking(2, "Claude Opus 4.7 Adaptive", 64.3, "coding", "SWE-bench Pro", "2026-05"),
        GlobalRanking(3, "Qwen3.7 Max", 60.6, "coding", "SWE-bench Pro", "2026-05"),
        GlobalRanking(4, "GPT-5.4 xHigh", 59.1, "coding", "SWE-bench Pro", "2026-05"),
        GlobalRanking(5, "DeepSeek V3.2", 55.3, "coding", "SWE-bench Pro", "2026-05"),

        # Agent/Tool-Use
        GlobalRanking(1, "Gemini 3.5 Flash", 83.6, "agent", "MCP Atlas", "2026-05"),
        GlobalRanking(2, "A-Evolve + Opus 4.6", 79.4, "agent", "MCP Atlas", "2026-05"),
        GlobalRanking(3, "GPT-5.2 Pro", 74.1, "agent", "GDPval", "2026-05"),
        GlobalRanking(4, "Claude Opus 4.7 Adaptive", 72.5, "agent", "MCP Atlas", "2026-05"),

        # Terminal/Shell
        GlobalRanking(1, "GPT-5.5", 82.7, "terminal", "Terminal-Bench 2.0", "2026-05"),
        GlobalRanking(2, "A-Evolve + Opus 4.6", 76.5, "terminal", "Terminal-Bench 2.0", "2026-05"),
        GlobalRanking(3, "Claude Opus 4.7 Adaptive", 74.6, "terminal", "Terminal-Bench 2.0", "2026-05"),

        # Comprehensive/Safety (estimated based on available data)
        GlobalRanking(1, "Claude Opus 4.7 Adaptive", 85.0, "safety", "Estimated Composite", "2026-05"),
        GlobalRanking(2, "Gemini 3.5 Flash", 82.0, "safety", "Estimated Composite", "2026-05"),
        GlobalRanking(3, "GPT-5.4 xHigh", 78.0, "safety", "Estimated Composite", "2026-05"),
    ]

    @classmethod
    def get_rankings(cls, category: str = "all") -> list[dict[str, Any]]:
        """Get global rankings, optionally filtered by category."""
        rankings = cls.GLOBAL_RANKINGS
        if category != "all":
            rankings = [r for r in rankings if r.category == category]

        return [
            {
                "rank": r.rank,
                "system": r.system,
                "score": r.score,
                "category": r.category,
                "benchmark": r.source_benchmark,
                "date": r.date,
            }
            for r in sorted(rankings, key=lambda x: x.score, reverse=True)
        ]

    @classmethod
    def compare(cls, sclerotium_score: float, category: str = "coding") -> dict[str, Any]:
        """Compare Sclerotium OS score against global leaders."""
        rankings = [r for r in cls.GLOBAL_RANKINGS if r.category == category]
        rankings.sort(key=lambda x: x.score, reverse=True)

        # Find position
        position = 1
        for r in rankings:
            if sclerotium_score >= r.score:
                break
            position += 1

        # Find closest competitors
        above = None
        below = None
        for r in rankings:
            if r.score > sclerotium_score:
                above = r
            elif r.score < sclerotium_score and below is None:
                below = r

        return {
            "sclerotium_score": sclerotium_score,
            "category": category,
            "estimated_rank": position,
            "total_compared": len(rankings),
            "above": f"{above.system} ({above.score})" if above else "None (TOP!)",
            "below": f"{below.system} ({below.score})" if below else "None (last)",
            "percentile": round((1 - (position - 1) / len(rankings)) * 100, 1) if rankings else 0,
        }
