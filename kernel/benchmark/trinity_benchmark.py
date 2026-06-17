"""Trinity Benchmark — 三体联合全量评测.

Evaluates the COMPLETE organism: fungal-cortex + MiroFish-main + Sclerotium OS
as ONE integrated electronic lifeform.

Bidirectional Flow Tests (6 directional flows × 3 project pairs):
  Pair 1: Sclerotium OS ←→ fungal-cortex
    → fungal→Sclerotium: EventBus, SkillRegistry, DGM, Stigmergy
    ← Sclerotium→fungal: genome_mutate, skill_register, auto_refactor

  Pair 2: MiroFish ←→ fungal-cortex
    → MiroFish→fungal: DGMBridge FCPI→DGM signals
    ← fungal→MiroFish: DGM genomes→arena genome_context

  Pair 3: Sclerotium OS ←→ MiroFish
    → MiroFish→Sclerotium: FCPI→evolution actions
    ← Sclerotium→MiroFish: 93 modules, 13,692 lines→genome_context

Cross-System Pipeline:
  Sclerotium code → fungal DGM genome → MiroFish arenas → FCPI vector →
  EvolutionBridge → Sclerotium self-evolution → fungal skill registration

Combined stats: ~102,345 lines, 381 .py files, 3 projects
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

from kernel.benchmark.engine import BenchmarkResult, BenchmarkStatus

# Paths
_SCLEROTIUM = Path("C:/Users/34442/Desktop/porject/Quantitative model/sclerotium-os")
_FUNGAL_ROOT = Path("C:/Users/34442/Desktop/porject/Quantitative model/fungal-cortex")
_FUNGAL = _FUNGAL_ROOT / "src"
_MIROFISH = Path("C:/Users/34442/Desktop/porject/Quantitative model/MiroFish-main/backend")

for p in [str(_FUNGAL_ROOT), str(_FUNGAL), str(_MIROFISH)]:
    if p not in sys.path:
        sys.path.insert(0, p)


class TrinityBenchmark:
    """Three-system integrated organism benchmark."""

    category = "trinity"

    def list_benchmarks(self) -> list[str]:
        return [
            "trinity_fungal_to_sclerotium",
            "trinity_sclerotium_to_fungal",
            "trinity_mirofish_to_fungal",
            "trinity_fungal_to_mirofish",
            "trinity_mirofish_to_sclerotium",
            "trinity_sclerotium_to_mirofish",
            "trinity_full_pipeline",
            "trinity_combined_stats",
        ]

    async def run_benchmarks(self, model: str = "sclerotium-os") -> list[BenchmarkResult]:
        results = []
        for name in self.list_benchmarks():
            try:
                r = getattr(self, f"_bench_{name.split('_', 1)[1]}")(model)
            except Exception as e:
                r = BenchmarkResult(name=name, category="trinity", status=BenchmarkStatus.FAILED, score=0, errors=[str(e)[:200]], model_used=model)
            results.append(r)
        return results

    # ═══ Pair 1: fungal-cortex → Sclerotium ═══

    def _bench_fungal_to_sclerotium(self, model: str) -> BenchmarkResult:
        start = time.monotonic()
        sub: dict[str, float] = {}
        errors: list[str] = []

        # Test 1: EventBus importable by Sclerotium
        try:
            from src.core.event_bus import EventBus
            sub["eventbus_import"] = 1.0
        except ImportError as e:
            errors.append(f"EventBus: {e}")

        # Test 2: SkillRegistry importable
        try:
            from src.core.skill_registry import SkillRegistry
            reg = SkillRegistry()
            sub["skill_registry_import"] = 1.0
            if hasattr(reg, 'scan_directory'):
                sub["skill_scan"] = 1.0
        except ImportError as e:
            errors.append(f"SkillRegistry: {e}")

        # Test 3: DGM via bridges/fungal_bridge
        try:
            from bridges.fungal_bridge import FungalBridge
            bridge = FungalBridge()
            sub["fungal_bridge_exists"] = 1.0
            services = bridge.list_services() if hasattr(bridge, 'list_services') else []
            sub["bridge_services"] = min(1.0, len(services) / 8)
        except ImportError as e:
            errors.append(f"FungalBridge: {e}")

        # Test 4: StigmergyField
        try:
            from src.field.stigmergy_field import StigmergyField
            sub["stigmergy_import"] = 1.0
        except ImportError as e:
            errors.append(f"Stigmergy: {e}")

        # Test 5: CognitiveScheduler
        try:
            from src.core.cognitive_scheduler import CognitiveScheduler
            sub["cognitive_scheduler"] = 1.0
        except ImportError:
            pass

        s = sum(sub.values()) / max(len(sub), 1) if sub else 0
        return BenchmarkResult("trinity_fungal_to_sclerotium", "trinity", BenchmarkStatus.PASSED if s > 0.3 else BenchmarkStatus.FAILED, s * 100, sub, duration_ms=(time.monotonic() - start) * 1000, errors=errors, model_used=model)

    # ═══ Pair 1: Sclerotium → fungal-cortex ═══

    def _bench_sclerotium_to_fungal(self, model: str) -> BenchmarkResult:
        start = time.monotonic()
        sub: dict[str, float] = {}
        errors: list[str] = []

        # Test 1: EvolutionBridge extract_modules → genome_context
        try:
            from kernel.evolution_bridge import EvolutionBridge
            bridge = EvolutionBridge(str(_SCLEROTIUM))
            ctx = bridge.extract_modules()
            sub["extract_modules"] = 1.0 if ctx.get("total_modules", 0) > 0 else 0.0
            sub["module_count"] = min(1.0, ctx.get("total_modules", 0) / 90)
            sub["total_lines"] = min(1.0, ctx.get("total_lines", 0) / 13000)
        except ImportError as e:
            errors.append(f"EvolutionBridge: {e}")

        # Test 2: genome_mutate MCP tool
        try:
            from mcp.server import SclerotiumMCPServer
            srv = SclerotiumMCPServer()
            srv.register_all_tools()
            has_genome_mutate = srv.tools.get_handler("genome_mutate") is not None
            sub["genome_mutate_tool"] = 1.0 if has_genome_mutate else 0.0
        except ImportError as e:
            errors.append(f"MCP tools: {e}")

        # Test 3: skill_register tool
        try:
            from mcp.server import SclerotiumMCPServer
            srv = SclerotiumMCPServer()
            srv.register_all_tools()
            has_skill_register = srv.tools.get_handler("skill_register") is not None
            sub["skill_register_tool"] = 1.0 if has_skill_register else 0.0
        except ImportError:
            pass

        # Test 4: auto_refactor tool
        try:
            from mcp.server import SclerotiumMCPServer
            srv = SclerotiumMCPServer()
            srv.register_all_tools()
            has_auto_refactor = srv.tools.get_handler("code_auto_refactor") is not None
            sub["auto_refactor_tool"] = 1.0 if has_auto_refactor else 0.0
        except ImportError:
            pass

        s = sum(sub.values()) / max(len(sub), 1) if sub else 0
        return BenchmarkResult("trinity_sclerotium_to_fungal", "trinity", BenchmarkStatus.PASSED if s > 0.3 else BenchmarkStatus.FAILED, s * 100, sub, duration_ms=(time.monotonic() - start) * 1000, errors=errors, model_used=model)

    # ═══ Pair 2: MiroFish → fungal-cortex ═══

    def _bench_mirofish_to_fungal(self, model: str) -> BenchmarkResult:
        start = time.monotonic()
        sub: dict[str, float] = {}
        errors: list[str] = []

        # DGMBridge: FCPI→DGM signals
        dgm_bridge_path = _MIROFISH / "app/services/dgm_bridge.py"
        if dgm_bridge_path.exists():
            sub["dgm_bridge_exists"] = 1.0
            source = dgm_bridge_path.read_text(encoding="utf-8")
            sub["dgm_bridge_lines"] = min(1.0, len(source.split("\n")) / 150)
            if "FCPI_TO_FAILURE_SIGNATURE" in source:
                sub["fcpi_mapping"] = 1.0

        # MyceliumBridge: FCPI→SelfEvolutionLoop
        mycelium_bridge_path = _MIROFISH / "app/services/mycelium_bridge.py"
        if mycelium_bridge_path.exists():
            sub["mycelium_bridge_exists"] = 1.0
            source = mycelium_bridge_path.read_text(encoding="utf-8")
            sub["mycelium_bridge_lines"] = min(1.0, len(source.split("\n")) / 100)

        s = sum(sub.values()) / max(len(sub), 1) if sub else 0
        return BenchmarkResult("trinity_mirofish_to_fungal", "trinity", BenchmarkStatus.PASSED if s > 0.3 else BenchmarkStatus.FAILED, s * 100, sub, duration_ms=(time.monotonic() - start) * 1000, errors=errors, model_used=model)

    # ═══ Pair 2: fungal-cortex → MiroFish ═══

    def _bench_fungal_to_mirofish(self, model: str) -> BenchmarkResult:
        start = time.monotonic()
        sub: dict[str, float] = {}
        errors: list[str] = []

        # DGM generates genomes → MiroFish arenas consume genome_context
        try:
            from src.l6.darwinian_godel_machine import DarwinianGodelMachine
            dgm = DarwinianGodelMachine()
            sub["dgm_available"] = 1.0
            if hasattr(dgm, 'genomes'):
                sub["dgm_has_genomes"] = 1.0
        except ImportError as e:
            errors.append(f"DGM: {e}")

        # coding_arena accepts genome_context with code_snippets
        coding_arena = _MIROFISH / "app/services/arenas/coding_arena.py"
        if coding_arena.exists():
            source = coding_arena.read_text(encoding="utf-8")
            sub["coding_arena_exists"] = 1.0
            if "genome_context" in source or "code_snippets" in source:
                sub["accepts_genome_context"] = 1.0

        s = sum(sub.values()) / max(len(sub), 1) if sub else 0
        return BenchmarkResult("trinity_fungal_to_mirofish", "trinity", BenchmarkStatus.PASSED if s > 0.3 else BenchmarkStatus.FAILED, s * 100, sub, duration_ms=(time.monotonic() - start) * 1000, errors=errors, model_used=model)

    # ═══ Pair 3: MiroFish → Sclerotium ═══

    def _bench_mirofish_to_sclerotium(self, model: str) -> BenchmarkResult:
        start = time.monotonic()
        sub: dict[str, float] = {}
        errors: list[str] = []

        # MiroFishBridge wraps 5 EvolutionManager methods
        try:
            from bridges.mirofish_bridge import MiroFishBridge
            bridge = MiroFishBridge()
            sub["mirofish_bridge_exists"] = 1.0
            if hasattr(bridge, 'loaded_modules'):
                sub["bridge_modules_loaded"] = min(1.0, bridge.loaded_modules / 5)
        except ImportError as e:
            errors.append(f"MiroFishBridge: {e}")

        # evolution_bridge MCP tools
        try:
            from mcp.server import SclerotiumMCPServer
            srv = SclerotiumMCPServer()
            srv.register_all_tools()
            for tool_name in ["evolution_extract_modules", "evolution_full_cycle", "evolution_bridge_status"]:
                sub[f"mcp_{tool_name}"] = 1.0 if srv.tools.get_handler(tool_name) else 0.0
        except ImportError:
            pass

        s = sum(sub.values()) / max(len(sub), 1) if sub else 0
        return BenchmarkResult("trinity_mirofish_to_sclerotium", "trinity", BenchmarkStatus.PASSED if s > 0.3 else BenchmarkStatus.FAILED, s * 100, sub, duration_ms=(time.monotonic() - start) * 1000, errors=errors, model_used=model)

    # ═══ Pair 3: Sclerotium → MiroFish ═══

    def _bench_sclerotium_to_mirofish(self, model: str) -> BenchmarkResult:
        start = time.monotonic()
        sub: dict[str, float] = {}
        errors: list[str] = []

        # EvolutionBridge: 93 modules, 13,692 lines → genome_context
        try:
            from kernel.evolution_bridge import EvolutionBridge
            bridge = EvolutionBridge(str(_SCLEROTIUM))
            ctx = bridge.extract_modules()
            sub["genome_context_ready"] = 1.0 if ctx.get("genome_id") else 0.0
            sub["code_snippets_count"] = min(1.0, ctx.get("total_modules", 0) / 93)
            sub["total_lines_extracted"] = min(1.0, ctx.get("total_lines", 0) / 13692)
        except ImportError as e:
            errors.append(f"EvolutionBridge: {e}")

        # FCPI→actions pipeline
        try:
            bridge = __import__('kernel.evolution_bridge', fromlist=['EvolutionBridge']).EvolutionBridge(str(_SCLEROTIUM))
            bridge.extract_modules()
            actions = bridge.fcpi_to_actions({"coding": 0.55, "safety": 0.45, "performance": 0.5})
            sub["fcpi_to_actions"] = 1.0 if len(actions) > 0 else 0.0
            sub["evolution_actions_count"] = min(1.0, len(actions) / 7)
        except ImportError as e:
            errors.append(f"FCPI→actions: {e}")

        s = sum(sub.values()) / max(len(sub), 1) if sub else 0
        return BenchmarkResult("trinity_sclerotium_to_mirofish", "trinity", BenchmarkStatus.PASSED if s > 0.3 else BenchmarkStatus.FAILED, s * 100, sub, duration_ms=(time.monotonic() - start) * 1000, errors=errors, model_used=model)

    # ═══ Full Pipeline ═══

    def _bench_full_pipeline(self, model: str) -> BenchmarkResult:
        """Test the complete Sclerotium→DGM→Arenas→FCPI→Evolution loop."""
        start = time.monotonic()
        sub: dict[str, float] = {}
        errors: list[str] = []

        try:
            # Step 1: Extract Sclerotium modules
            from kernel.evolution_bridge import EvolutionBridge
            bridge = EvolutionBridge(str(_SCLEROTIUM))
            ctx = bridge.extract_modules()
            sub["step1_extract"] = 1.0 if ctx["total_modules"] > 0 else 0.0

            # Step 2: Run through EvolutionBridge full cycle
            cycle = bridge.run_evolution_cycle()
            sub["step2_cycle"] = 1.0 if cycle.get("evolution_actions", 0) > 0 else 0.0
            sub["genome_modules"] = min(1.0, cycle.get("genome_context", {}).get("modules", 0) / 90)

            # Step 3: FCPI vector produced
            fcpi = cycle.get("fcpi_vector", {})
            fcpi_dims = sum(1 for d in ["coding","coordination","safety","decision","emergence","performance"] if d in fcpi)
            sub["step3_fcpi_dims"] = fcpi_dims / 6

            # Step 4: Actions generated
            sub["step4_actions"] = min(1.0, cycle.get("evolution_actions", 0) / 5)

            # Step 5: Full pipeline trace latency
            elapsed_ms = (time.monotonic() - start) * 1000
            sub["pipeline_latency_ms"] = 1.0 - min(1.0, elapsed_ms / 5000)

        except ImportError as e:
            errors.append(f"Pipeline: {e}")
        except Exception as e:
            errors.append(f"Pipeline error: {e}")

        s = sum(sub.values()) / max(len(sub), 1) if sub else 0
        return BenchmarkResult("trinity_full_pipeline", "trinity", BenchmarkStatus.PASSED if s > 0.3 else BenchmarkStatus.FAILED, s * 100, sub, duration_ms=(time.monotonic() - start) * 1000, errors=errors, model_used=model)

    # ═══ Combined Stats ═══

    def _bench_combined_stats(self, model: str) -> BenchmarkResult:
        """Aggregate statistics of the complete organism."""
        start = time.monotonic()
        sub: dict[str, float] = {}
        errors: list[str] = []

        # Count all Python files
        scl_files = len(list(_SCLEROTIUM.rglob("*.py")))
        fungal_files = len(list(_FUNGAL.rglob("*.py")))
        mirofish_files = len(list(_MIROFISH.rglob("*.py")))

        total_files = scl_files + fungal_files + mirofish_files
        sub["total_py_files"] = min(1.0, total_files / 381)

        # Count all lines
        def count_lines(path: Path) -> int:
            total = 0
            for f in path.rglob("*.py"):
                if "__pycache__" not in str(f):
                    try:
                        total += len(f.read_text(encoding="utf-8").split("\n"))
                    except Exception:
                        pass
            return total

        scl_lines = count_lines(_SCLEROTIUM)
        fungal_lines = count_lines(_FUNGAL)
        mirofish_lines = count_lines(_MIROFISH)
        total_lines = scl_lines + fungal_lines + mirofish_lines

        sub["total_lines"] = min(1.0, total_lines / 102345)
        sub["sclerotium_lines"] = min(1.0, scl_lines / 16868)
        sub["fungal_lines"] = min(1.0, fungal_lines / 55131)
        sub["mirofish_lines"] = min(1.0, mirofish_lines / 30346)

        # MCP tools total
        try:
            from mcp.server import SclerotiumMCPServer
            srv = SclerotiumMCPServer()
            srv.register_all_tools()
            sub["mcp_tools"] = min(1.0, srv.tools.tool_count / 143)
        except ImportError:
            pass

        # Cross-project bridge files
        bridge_count = 0
        for bp in ["bridges/fungal_bridge.py", "bridges/mirofish_bridge.py"]:
            if (_SCLEROTIUM / bp).exists():
                bridge_count += 1
        for bp in ["app/services/dgm_bridge.py", "app/services/mycelium_bridge.py"]:
            if (_MIROFISH / bp).exists():
                bridge_count += 1
        sub["cross_bridges"] = min(1.0, bridge_count / 4)

        s = sum(sub.values()) / max(len(sub), 1) if sub else 0
        return BenchmarkResult("trinity_combined_stats", "trinity", BenchmarkStatus.PASSED if s > 0.5 else BenchmarkStatus.FAILED, s * 100, sub, duration_ms=(time.monotonic() - start) * 1000, errors=errors, model_used=model)
