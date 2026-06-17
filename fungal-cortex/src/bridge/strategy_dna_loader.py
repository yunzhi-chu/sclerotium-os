"""Strategy DNA Loader — 689 strategy DNA vectors → catalytic graph nodes.

Each strategy is encoded as a 6-dimension DNA vector:
[picker, timer, risk_control, frequency, complexity, holding_period]

These vectors are loaded into the autocatalytic skill catalysis graph where
similar strategies catalyze each other through cosine-similarity edges.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any

from src.utils.logging import CortexLogger


@dataclass
class StrategyDNA:
    """A single strategy's DNA vector and metadata.

    The 6 dimensions:
    - picker: Stock selection strength (0-1)
    - timer: Market timing sensitivity (0-1)
    - risk_control: Risk management aggressiveness (0-1)
    - frequency: Trading frequency (0-1, 1=HFT)
    - complexity: Strategy complexity (0-1, 1=deep learning ensemble)
    - holding_period: Average holding period (0-1, 1=long-term)
    """

    strategy_id: str
    name: str
    vector: list[float]  # 6-dimension DNA
    category: str = ""  # momentum, mean_reversion, arbitrage, value, growth, etc.
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    annual_return: float = 0.0
    win_rate: float = 0.0
    backtest_period_days: int = 252
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.vector) != 6:
            raise ValueError(f"DNA vector must have 6 dimensions, got {len(self.vector)}")

    def cosine_similarity(self, other: StrategyDNA) -> float:
        """Compute cosine similarity between two strategy DNA vectors."""
        dot = sum(a * b for a, b in zip(self.vector, other.vector))
        norm_a = math.sqrt(sum(a ** 2 for a in self.vector))
        norm_b = math.sqrt(sum(b ** 2 for b in other.vector))
        if norm_a < 1e-10 or norm_b < 1e-10:
            return 0.0
        return dot / (norm_a * norm_b)

    def distance(self, other: StrategyDNA) -> float:
        """Cosine distance (1 - similarity)."""
        return 1.0 - self.cosine_similarity(other)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "vector": self.vector,
            "category": self.category,
            "sharpe": self.sharpe,
            "max_drawdown": self.max_drawdown,
            "annual_return": self.annual_return,
            "win_rate": self.win_rate,
            "backtest_period_days": self.backtest_period_days,
        }


class StrategyDNALoader:
    """Loads and indexes 689 strategy DNA vectors.

    The loader:
    1. Generates/loads strategy DNA vectors
    2. Builds a similarity index for fast k-NN lookup
    3. Maps strategies to catalytic graph nodes
    4. Detects strategy clusters (potential specialization niches)

    Each strategy acts as a node in the autocatalytic graph — strategies
    with high cosine similarity catalyze each other's execution.
    """

    STRATEGY_CATEGORIES = [
        "momentum", "mean_reversion", "arbitrage", "value",
        "growth", "quality", "volatility", "carry",
        "event_driven", "market_making", "trend_following",
        "statistical_arbitrage", "pairs_trading", "options",
    ]

    def __init__(self, batch_size: int = 100, seed: int | None = None) -> None:
        self._batch_size = batch_size
        self._strategies: dict[str, StrategyDNA] = {}
        self._logger = CortexLogger("strategy_dna_loader")
        if seed is not None:
            random.seed(seed)

    def load(self, count: int = 689) -> int:
        """Load or generate strategy DNA vectors. Returns count loaded."""
        existing = len(self._strategies)
        to_generate = count - existing
        if to_generate <= 0:
            return 0

        for i in range(existing, count):
            strategy_id = f"strategy-{i:04d}"
            category = random.choice(self.STRATEGY_CATEGORIES)
            dna = StrategyDNA(
                strategy_id=strategy_id,
                name=f"{category.replace('_', ' ').title()} #{i}",
                vector=self._generate_dna_vector(category),
                category=category,
                sharpe=random.uniform(0.5, 3.0),
                max_drawdown=random.uniform(0.05, 0.40),
                annual_return=random.uniform(0.05, 0.50),
                win_rate=random.uniform(0.40, 0.75),
                backtest_period_days=random.choice([126, 252, 504, 756]),
            )
            self._strategies[strategy_id] = dna

        self._logger.info("strategies_loaded", count=count, new=to_generate)
        return to_generate

    def _generate_dna_vector(self, category: str) -> list[float]:
        """Generate a plausible DNA vector based on the strategy category."""
        base = {
            "momentum": [0.3, 0.7, 0.4, 0.6, 0.3, 0.2],
            "mean_reversion": [0.6, 0.4, 0.5, 0.5, 0.4, 0.3],
            "arbitrage": [0.7, 0.3, 0.6, 0.8, 0.5, 0.1],
            "value": [0.8, 0.2, 0.3, 0.1, 0.3, 0.9],
            "growth": [0.7, 0.3, 0.3, 0.2, 0.4, 0.8],
            "quality": [0.8, 0.1, 0.4, 0.1, 0.5, 0.7],
            "volatility": [0.2, 0.6, 0.5, 0.7, 0.6, 0.2],
            "carry": [0.4, 0.5, 0.4, 0.3, 0.3, 0.5],
            "event_driven": [0.5, 0.5, 0.3, 0.2, 0.6, 0.5],
            "market_making": [0.1, 0.3, 0.7, 0.9, 0.4, 0.1],
            "trend_following": [0.2, 0.8, 0.4, 0.4, 0.2, 0.3],
            "statistical_arbitrage": [0.5, 0.4, 0.5, 0.7, 0.7, 0.1],
            "pairs_trading": [0.6, 0.3, 0.5, 0.5, 0.5, 0.3],
            "options": [0.3, 0.5, 0.6, 0.4, 0.8, 0.3],
        }

        center = base.get(category, [0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
        return [max(0.0, min(1.0, c + random.uniform(-0.2, 0.2))) for c in center]

    def list_all(self) -> list[StrategyDNA]:
        """Return all loaded strategies."""
        return list(self._strategies.values())

    def search(self, query: str, top_k: int = 50) -> list[StrategyDNA]:
        """Search strategies by name or category matching."""
        q = query.lower()
        results = [s for s in self._strategies.values() if q in s.name.lower() or q in s.category.lower()]
        return results[:top_k]

    def get_top_strategies(
        self, min_sharpe: float = 0.0, min_win_rate: float = 0.0, top_k: int = 20
    ) -> list[StrategyDNA]:
        """Get top strategies ranked by Sharpe ratio."""
        candidates = [
            s for s in self._strategies.values()
            if s.sharpe >= min_sharpe and s.win_rate >= min_win_rate
        ]
        candidates.sort(key=lambda s: s.sharpe, reverse=True)
        return candidates[:top_k]

    async def validate_top_strategies(
        self,
        sandbox: Any = None,
        final_bench: Any = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Run top strategies through sandbox + FINAL bench validation.

        This is the skills→execution chain:
        1. Pick top K strategies from loader
        2. Run each through SandboxVerificationPipeline
        3. Validate results with FINALBenchBridge
        4. Return execution reports

        Args:
            sandbox: SandboxVerificationPipeline instance (optional)
            final_bench: FINALBenchBridge instance (optional)
            top_k: Number of top strategies to validate
        Returns:
            List of execution reports with sandbox + FINAL results
        """
        top = self.get_top_strategies(top_k=top_k)
        reports: list[dict[str, Any]] = []

        for strategy in top:
            report = {
                "strategy_id": strategy.strategy_id,
                "name": strategy.name,
                "category": strategy.category,
                "dna": strategy.vector,
                "sharpe_claimed": strategy.sharpe,
                "sandbox_status": "skipped",
                "final_status": "skipped",
            }

            # Stage 1: Sandbox verification
            if sandbox is not None:
                try:
                    sandbox_result = await sandbox.deploy_to_sandbox(
                        strategy.strategy_id,
                        {"main.py": f"# Auto-generated strategy\nname = '{strategy.name}'\ncategory = '{strategy.category}'\ndna = {strategy.vector}"},
                        strategy.backtest_period_days,
                    )
                    report["sandbox_status"] = "passed" if sandbox_result.passed else "failed"
                    report["sandbox_sharpe"] = sandbox_result.sharpe_ratio
                except Exception as exc:
                    report["sandbox_status"] = "error"
                    report["sandbox_error"] = str(exc)

            # Stage 2: FINAL Bench validation
            if final_bench is not None and sandbox is not None:
                try:
                    bench_result = final_bench.validate(strategy.strategy_id, strategy.to_dict())
                    report["final_status"] = "passed" if bench_result.passed else "failed"
                    report["ma_score"] = bench_result.ma_score
                    report["er_score"] = bench_result.er_score
                except Exception as exc:
                    report["final_status"] = "error"
                    report["final_error"] = str(exc)

            reports.append(report)

        self._logger.info("strategies_validated", count=len(reports))
        return reports

    def get(self, strategy_id: str) -> StrategyDNA | None:
        return self._strategies.get(strategy_id)

    def find_similar(self, query: StrategyDNA, top_k: int = 5, min_similarity: float = 0.7) -> list[tuple[StrategyDNA, float]]:
        """Find top-k most similar strategies to the query DNA."""
        scored: list[tuple[StrategyDNA, float]] = []
        for s in self._strategies.values():
            if s.strategy_id == query.strategy_id:
                continue
            sim = query.cosine_similarity(s)
            if sim >= min_similarity:
                scored.append((s, sim))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def find_by_category(self, category: str) -> list[StrategyDNA]:
        """Get all strategies in a category."""
        return [s for s in self._strategies.values() if s.category == category]

    def get_clusters(self, similarity_threshold: float = 0.8) -> list[list[StrategyDNA]]:
        """Detect strategy clusters using similarity-based grouping."""
        visited: set[str] = set()
        clusters: list[list[StrategyDNA]] = []

        for sid, strategy in self._strategies.items():
            if sid in visited:
                continue
            cluster: list[StrategyDNA] = [strategy]
            visited.add(sid)
            for other_id, other in self._strategies.items():
                if other_id in visited:
                    continue
                if strategy.cosine_similarity(other) >= similarity_threshold:
                    cluster.append(other)
                    visited.add(other_id)
            clusters.append(cluster)

        return clusters

    def to_catalysis_edges(self, similarity_threshold: float = 0.75) -> list[tuple[str, str, float]]:
        """Convert strategy similarity to catalysis graph edges.

        Returns list of (source_id, target_id, similarity_weight) tuples.
        """
        edges: list[tuple[str, str, float]] = []
        loaded = list(self._strategies.values())

        for i, s1 in enumerate(loaded):
            for s2 in loaded[i + 1 :]:
                sim = s1.cosine_similarity(s2)
                if sim >= similarity_threshold:
                    edges.append((s1.strategy_id, s2.strategy_id, sim))

        return edges

    @property
    def count(self) -> int:
        return len(self._strategies)

    @property
    def stats(self) -> dict[str, Any]:
        categories = {}
        for s in self._strategies.values():
            categories[s.category] = categories.get(s.category, 0) + 1
        avg_sharpe = sum(s.sharpe for s in self._strategies.values()) / max(self.count, 1)
        return {
            "total_strategies": self.count,
            "categories": categories,
            "avg_sharpe": round(avg_sharpe, 3),
            "clusters": len(self.get_clusters()),
        }
