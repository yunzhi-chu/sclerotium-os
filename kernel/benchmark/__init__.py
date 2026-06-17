"""Sclerotium OS Trinity Benchmark Suite — 三体联合全方位评测.

Evaluates the COMPLETE organism: fungal-cortex (55,131 lines) + MiroFish-main
(30,346 lines) + Sclerotium OS (16,868 lines) as ONE integrated electronic
lifeform (~102,345 total lines, 381 .py files).

Authoritative Benchmarks (via Harbor + MCP Atlas):
  - SWE-bench Pro      — Real-world software engineering (Scale AI)
  - Terminal-Bench 2.0 — Shell/terminal competency (Laude Institute)
  - MCP Atlas          — MCP tool-use evaluation (Scale AI)

Trinity Organism Benchmarks (9 categories):
  - fcpi           — Sclerotium 6-dimension self-evolution
  - safety         — Sclerotium Constitutional Arbiter + Sandstorm
  - memory         — Sclerotium Hexis 5-layer memory
  - sandstorm      — Sclerotium L1/L2/L3 isolation
  - coordination   — Sclerotium Swarm + Economic Net
  - fungal         — fungal-cortex: EventBus, Skills, Stigmergy, Immune, DGM
  - mirofish       — MiroFish: 6 Arenas, EvolutionMgr, FitnessExtractor
  - trinity        — Cross-system: 6 bidirectional flows + full pipeline
  - authority      — Harbor: SWE-bench Pro + Terminal-Bench 2.0

Scoring: Unified 0-100 scale with weighted aggregation across all 9 categories.
"""

from kernel.benchmark.engine import BenchmarkEngine, BenchmarkResult
from kernel.benchmark.scorer import UnifiedScorer, GlobalLeaderboard
from kernel.benchmark.fcpi_benchmark import FCPIBenchmark
from kernel.benchmark.safety_benchmark import SafetyBenchmark
from kernel.benchmark.memory_benchmark import MemoryBenchmark
from kernel.benchmark.sandstorm_benchmark import SandstormBenchmark
from kernel.benchmark.coordination_benchmark import CoordinationBenchmark
from kernel.benchmark.fungal_benchmark import FungalBenchmark
from kernel.benchmark.mirofish_benchmark import MiroFishBenchmark
from kernel.benchmark.trinity_benchmark import TrinityBenchmark
from kernel.benchmark.harbor_runner import HarborRunner
from kernel.benchmark.mcp_atlas_runner import MCPAtlasRunner
from kernel.benchmark.ai_benchmark import AIBenchmark

__all__ = [
    "BenchmarkEngine", "BenchmarkResult",
    "UnifiedScorer", "GlobalLeaderboard",
    "FCPIBenchmark", "SafetyBenchmark", "MemoryBenchmark",
    "SandstormBenchmark", "CoordinationBenchmark",
    "FungalBenchmark", "MiroFishBenchmark", "TrinityBenchmark",
    "AIBenchmark", "HarborRunner", "MCPAtlasRunner",
]
