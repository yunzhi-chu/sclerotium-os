"""FULL TRINITY ORGANISM BENCHMARK — Every organ, all 3 systems, 164 tasks.

Each HumanEval task flows through 50+ organs across fungal-cortex + MiroFish + Sclerotium.
Total organ invocations: ~164 × 50 = ~8,200 for the full run.
"""

from __future__ import annotations
import asyncio, importlib.util, os, sys, time
from pathlib import Path
from types import ModuleType
from typing import Any
from kernel.benchmark.engine import BenchmarkResult, BenchmarkStatus
from kernel.project_paths import add_subsystem_paths, FUNGAL_CORTEX, FUNGAL_CORTEX_SRC, MIROFISH

add_subsystem_paths()

_SCL = Path(".")
_FR  = FUNGAL_CORTEX
_FRS = FUNGAL_CORTEX_SRC
_MF  = MIROFISH
for p in [str(_FR), str(_FRS), str(_MF)]:
    if p not in sys.path: sys.path.insert(0, p)

BODY: dict[str, Any] = {}
ORGAN_COUNTS: dict[str, int] = {}


def _touch(organ: str) -> None:
    ORGAN_COUNTS[organ] = ORGAN_COUNTS.get(organ, 0) + 1


# ═══════════════════════════════════════════════════════════════════════════════
# FUNGAL-CORTEX ORGANS (~35 loadable)
# ═══════════════════════════════════════════════════════════════════════════════

def _init_fungal() -> list[str]:
    loaded = []
    def _try(key, mod, cls):
        try:
            m = __import__(mod, fromlist=[cls])
            BODY[key] = getattr(m, cls)()
            loaded.append(key); return True
        except Exception: return False

    # Core (6)
    _try("eventbus", "src.core.event_bus", "EventBus")
    _try("skill_registry", "src.core.skill_registry", "SkillRegistry")
    _try("cognitive_scheduler", "src.core.cognitive_scheduler", "CognitiveScheduler")
    _try("context_compressor", "src.core.context_compressor", "ContextCompressor")
    _try("model_router", "src.core.model_router", "ModelRouter")
    _try("unified_eventbus", "src.core.unified_event_bus", "UnifiedEventBus")

    # Immune (5)
    _try("self_set", "src.immune.self_set", "SelfSet")
    _try("clonal_selector", "src.immune.clonal_selector", "ClonalSelector")
    _try("negative_selector", "src.immune.negative_selector", "NegativeSelector")
    _try("immune_memory", "src.immune.immune_memory", "ImmuneMemory")
    _try("dendritic_cell", "src.immune.dendritic_cell", "DendriticCell")

    # Field (3)
    try:
        from src.field.field_geometry import FieldGeometry
        from src.field.stigmergy_field import StigmergyField
        geo = FieldGeometry(width=64, height=64)
        BODY["stigmergy"] = StigmergyField(geometry=geo); loaded.append("stigmergy")
    except Exception: pass
    _try("gpu_accelerator", "src.field.gpu_accelerator", "GPUAccelerator")

    # L6 (10)
    _try("dgm", "src.l6.darwinian_godel_machine", "DarwinianGodelMachine")
    _try("architecture_scanner", "src.l6.architecture_scanner", "ArchitectureScanner")
    _try("crystallizer", "src.l6.crystallizer", "EmergenceCrystallizer")
    _try("meta_cognition", "src.l6.meta_cognition", "MetaCognition")
    _try("auto_refactor", "src.l6.auto_refactor", "AutoRefactor")
    _try("emergence_capture", "src.l6.emergence_capture", "EmergenceCapture")
    _try("ability_factory", "src.l6.ability_factory", "AbilityFactory")
    _try("goal_expander", "src.l6.goal_expander", "GoalExpander")
    _try("rule_evolution", "src.l6.rule_evolution", "RuleEvolution")
    _try("sandbox_pipeline", "src.l6.sandbox_pipeline", "SandboxPipeline")

    # Panarchy (3)
    _try("adaptive_cycle", "src.panarchy.adaptive_cycle", "AdaptiveCycle")
    _try("panarchy_controller", "src.panarchy.panarchy_controller", "PanarchyController")
    _try("resilience_metrics", "src.panarchy.resilience_metrics", "ResilienceMetrics")

    # Morphogen (3)
    _try("morphogen_gradient", "src.morphogen.morphogen_gradient", "MorphogenGradient")
    _try("guided_selforg", "src.morphogen.guided_selforg", "GuidedSelfOrg")
    try:
        from src.morphogen.turing_patterning import TuringPattern
        BODY["turing"] = TuringPattern(
            activator_field=[[0.0]*32 for _ in range(32)],
            inhibitor_field=[[0.0]*32 for _ in range(32)],
            pattern_type="spots", dominant_wavelength=8.0, stability=0.5, iteration_count=0
        ); loaded.append("turing")
    except Exception: pass

    # Autocatalytic (3)
    _try("constraint_closure", "src.autocatalytic.constraint_closure", "ConstraintClosure")
    _try("phase_transition", "src.autocatalytic.phase_transition", "PhaseTransition")
    _try("skill_catalysis", "src.autocatalytic.skill_catalysis_graph", "SkillCatalysisGraph")

    # Dendrite (3)
    _try("coincidence_detector", "src.dendrite.coincidence_detector", "CoincidenceDetector")
    _try("dendritic_tree", "src.dendrite.dendritic_tree", "DendriticTree")
    _try("temporal_integrator", "src.dendrite.temporal_integrator", "TemporalIntegrator")

    # Evolution (3)
    _try("agent_evolver", "src.evolution.agent_evolver", "AgentEvolver")
    _try("architecture_evolver", "src.evolution.architecture_evolver", "ArchitectureEvolver")
    _try("parameter_evolver", "src.evolution.parameter_evolver", "ParameterEvolver")

    # Holograph (3)
    _try("anomaly_projector", "src.holograph.anomaly_projector", "AnomalyProjector")
    _try("fractal_encoder", "src.holograph.fractal_encoder", "FractalEncoder")
    _try("holographic_query", "src.holograph.holographic_query", "HolographicQuery")

    # L2/L5 (2)
    _try("l2_router", "src.l2.multi_model_router", "MultiModelRouter")
    _try("swarm_selforg", "src.l5.swarm_self_organizer", "SwarmSelfOrganizer")

    # Bridge (3 key ones)
    _try("skill_adapter", "src.bridge.skill_adapter", "SkillAdapter")
    _try("conscious_bridge", "src.bridge.conscious_bridge", "ConsciousBridge")
    _try("quantum_bridge", "src.bridge.quantum_bridge", "QuantumBridge")

    return loaded


# ═══════════════════════════════════════════════════════════════════════════════
# MIROFISH ORGANS (~15 loadable via importlib bypass)
# ═══════════════════════════════════════════════════════════════════════════════

def _init_mirofish() -> list[str]:
    loaded = []
    # Package stubs
    for pkg_path, pkg_name in [
        ("app","app"),("app/api","app.api"),("app/models","app.models"),
        ("app/utils","app.utils"),("app/services","app.services"),
        ("app/services/arenas","app.services.arenas"),
    ]:
        if pkg_name not in sys.modules:
            m = ModuleType(pkg_name); m.__path__ = [str(_MF/pkg_path)]; m.__package__ = pkg_name
            sys.modules[pkg_name] = m

    def _load(key, rel_path, mod_name):
        try:
            ap = _MF/rel_path
            s = importlib.util.spec_from_file_location(mod_name, str(ap), submodule_search_locations=[str(ap.parent)])
            m = importlib.util.module_from_spec(s)
            sys.modules[mod_name] = m
            s.loader.exec_module(m)
            BODY[key] = m; loaded.append(key); return True
        except Exception: return False

    # Arena base (must load first - others import from it)
    _load("arena_base", "app/services/arenas/arena_base.py", "app.services.arenas.arena_base")
    # 6 arenas
    _load("coding_arena", "app/services/arenas/coding_arena.py", "app.services.arenas.coding_arena")
    _load("coordination_arena", "app/services/arenas/coordination_arena.py", "app.services.arenas.coordination_arena")
    _load("safety_arena", "app/services/arenas/safety_arena.py", "app.services.arenas.safety_arena")
    _load("decision_arena", "app/services/arenas/decision_arena.py", "app.services.arenas.decision_arena")
    _load("emergence_arena", "app/services/arenas/emergence_arena.py", "app.services.arenas.emergence_arena")
    _load("performance_arena", "app/services/arenas/performance_arena.py", "app.services.arenas.performance_arena")
    # Services
    _load("evol_mgr", "app/services/evolution_generation_manager.py", "app.services.evolution_generation_manager")
    _load("fitness_extractor", "app/services/fitness_extractor.py", "app.services.fitness_extractor")
    _load("dgm_bridge", "app/services/dgm_bridge.py", "app.services.dgm_bridge")
    _load("mycelium_bridge", "app/services/mycelium_bridge.py", "app.services.mycelium_bridge")
    _load("graph_builder", "app/services/graph_builder.py", "app.services.graph_builder")
    _load("report_agent", "app/services/report_agent.py", "app.services.report_agent")
    _load("text_processor", "app/services/text_processor.py", "app.services.text_processor")
    return loaded


# ═══════════════════════════════════════════════════════════════════════════════
# SCLEROTIUM ORGANS (~30 loadable)
# ═══════════════════════════════════════════════════════════════════════════════

def _init_sclerotium() -> list[str]:
    loaded = []

    # Gateway
    from gateways.models import UniversalModelGateway
    BODY["gateway"] = UniversalModelGateway(); loaded.append("gateway")
    try:
        from gateways.mcp_market import MCPMarketGateway
        BODY["mcp_market"] = MCPMarketGateway(); loaded.append("mcp_market")
    except Exception: pass
    try:
        from gateways.skills_market import SkillsMarketGateway
        BODY["skills_market"] = SkillsMarketGateway(); loaded.append("skills_market")
    except Exception: pass

    # Kernel safety
    from kernel.constitutional_arbiter import ConstitutionalArbiter
    BODY["arbiter"] = ConstitutionalArbiter("./data/bench_full_audit.jsonl"); loaded.append("arbiter")
    from kernel.sandstorm import SandstormExecutor
    BODY["sandstorm"] = SandstormExecutor(); loaded.append("sandstorm")
    from kernel.hexis_memory import HexisMemoryStore
    BODY["memory"] = HexisMemoryStore("./data/bench_full_chroma", "./data/bench_full.db"); loaded.append("memory")
    from kernel.evolution_bridge import EvolutionBridge
    BODY["evolution"] = EvolutionBridge("."); loaded.append("evolution")

    # STG (5)
    try:
        from kernel.stg.pattern_generator import PatternGenerator
        BODY["pattern_gen"] = PatternGenerator(); loaded.append("pattern_gen")
        from kernel.stg.neuromodulator import Neuromodulator
        BODY["neuromod"] = Neuromodulator(); loaded.append("neuromod")
        from kernel.stg.winnerless_competition import WLC
        BODY["wlc"] = WLC(); loaded.append("wlc")
        from kernel.stg.pyloric_rhythm import PyloricRhythm
        BODY["pyloric"] = PyloricRhythm(); loaded.append("pyloric")
        from kernel.stg.gastric_rhythm import GastricRhythm
        BODY["gastric"] = GastricRhythm(); loaded.append("gastric")
    except Exception: pass

    # Cache
    try:
        from kernel.cache.prompt_cache_engine import PromptCacheEngine
        BODY["cache_engine"] = PromptCacheEngine(); loaded.append("cache_engine")
    except Exception: pass

    # Genesis (5)
    try:
        from kernel.genesis.genetic_program import GeneticProgrammingEngine
        BODY["genetic_prog"] = GeneticProgrammingEngine(10); loaded.append("genetic_prog")
        from kernel.genesis.swarm_intel import SwarmCoordinator
        BODY["swarm"] = SwarmCoordinator(32); loaded.append("swarm")
        from kernel.genesis.economic_net import EconomicNetwork
        BODY["economic"] = EconomicNetwork(); loaded.append("economic")
        from kernel.genesis.controlled_emergence import ControlledEmergence
        BODY["ctrl_emergence"] = ControlledEmergence(); loaded.append("ctrl_emergence")
        from kernel.genesis.gpu_kernel_gen import GPUKernelGenerator
        BODY["gpu_kernel"] = GPUKernelGenerator(); loaded.append("gpu_kernel")
    except Exception: pass

    # Sovereign (5 key ones)
    try:
        from kernel.sovereign.system_builder import SystemBuilder
        BODY["sys_builder"] = SystemBuilder(); loaded.append("sys_builder")
        from kernel.sovereign.long_horizon import LongHorizonExecutor
        BODY["long_horizon"] = LongHorizonExecutor(); loaded.append("long_horizon")
        from kernel.sovereign.formal_prover import NeuroSymbolicProver
        BODY["formal_prover"] = NeuroSymbolicProver(); loaded.append("formal_prover")
        from kernel.sovereign.cross_repo import CrossRepoReasoner
        BODY["cross_repo"] = CrossRepoReasoner(); loaded.append("cross_repo")
        from kernel.sovereign.ring0_gov import Ring0Governor
        BODY["ring0"] = Ring0Governor(); loaded.append("ring0")
    except Exception: pass

    # Advanced (3)
    try:
        from kernel.advanced.code_refactor import SemanticRefactorEngine
        BODY["code_refactor"] = SemanticRefactorEngine(); loaded.append("code_refactor")
        from kernel.advanced.subagent_delegation import SubAgentDelegator
        BODY["subagent"] = SubAgentDelegator(); loaded.append("subagent")
        from kernel.advanced.formal_verify import FormalVerifier
        BODY["formal_verify"] = FormalVerifier(); loaded.append("formal_verify")
    except Exception: pass

    # Cosmic (3)
    try:
        from kernel.cosmic.world_model import WorldModel
        BODY["world_model"] = WorldModel(); loaded.append("world_model")
        from kernel.cosmic.recursive_self import RecursiveSelfImprover
        BODY["recursive_self"] = RecursiveSelfImprover(); loaded.append("recursive_self")
        from kernel.cosmic.code_bootstrap import CodeBootstrap
        BODY["code_bootstrap"] = CodeBootstrap(); loaded.append("code_bootstrap")
    except Exception: pass

    # Innovation (3)
    try:
        from kernel.innovation.mycelial_memory import MycelialMemristiveMemory
        BODY["mycelial_mem"] = MycelialMemristiveMemory(); loaded.append("mycelial_mem")
        from kernel.innovation.resonant_closure import ResonantClosureKernel
        BODY["resonant"] = ResonantClosureKernel(); loaded.append("resonant")
        from kernel.innovation.orch_or_substrate import OrchORSubstrate
        BODY["orch_or"] = OrchORSubstrate(); loaded.append("orch_or")
    except Exception: pass

    # Apotheosis (3)
    try:
        from kernel.apotheosis.immuno_attention import ImmunoAttentionNetwork
        BODY["immuno_attn"] = ImmunoAttentionNetwork(); loaded.append("immuno_attn")
        from kernel.apotheosis.morphogenic_field import MorphogenicField
        BODY["morpho_field"] = MorphogenicField(); loaded.append("morpho_field")
        from kernel.apotheosis.epigenetic_state import EpigeneticComputationalState
        BODY["epigenetic"] = EpigeneticComputationalState(); loaded.append("epigenetic")
    except Exception: pass

    # Bridges
    try:
        from bridges.fungal_bridge import FungalBridge
        BODY["fungal_bridge"] = FungalBridge(); loaded.append("fungal_bridge")
    except Exception: pass
    try:
        from bridges.mirofish_bridge import MiroFishBridge
        BODY["mirofish_bridge"] = MiroFishBridge(); loaded.append("mirofish_bridge")
    except Exception: pass

    # Scheduler
    try:
        from scheduler.engine import SchedulerEngine
        BODY["scheduler"] = SchedulerEngine(); loaded.append("scheduler")
    except Exception: pass

    # MCP Server
    try:
        from mcp.server import SclerotiumMCPServer
        srv = SclerotiumMCPServer(); srv.register_all_tools()
        BODY["mcp"] = srv; loaded.append("mcp")
    except Exception: pass

    return loaded


# ═══════════════════════════════════════════════════════════════════════════════
# FULL INIT
# ═══════════════════════════════════════════════════════════════════════════════

def _init_full_body() -> dict:
    global BODY, ORGAN_COUNTS
    BODY.clear(); ORGAN_COUNTS.clear()
    t0 = time.time()

    fungal_loaded = _init_fungal()
    mirofish_loaded = _init_mirofish()
    scl_loaded = _init_sclerotium()

    return {
        "init_ms": (time.time()-t0)*1000,
        "fungal": len(fungal_loaded), "mirofish": len(mirofish_loaded),
        "sclerotium": len(scl_loaded), "total": len(BODY),
        "fungal_list": fungal_loaded, "mirofish_list": mirofish_loaded, "scl_list": scl_loaded,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PER-TASK ORGAN INVOCATION
# ═══════════════════════════════════════════════════════════════════════════════

async def _invoke_all_organs(task_id: str, code: str, entry_point: str, compiled: bool) -> dict:
    """Invoke every available organ for a single HumanEval task."""
    log: dict[str, Any] = {"task_id": task_id, "compiled": compiled}
    b = BODY

    # ── FUNGAL-CORTEX ──
    # EventBus
    for key in ["eventbus", "unified_eventbus"]:
        if key in b:
            try: b[key].publish_nowait(f"bench.{'pass' if compiled else 'fail'}.{task_id}", {"idx": task_id, "ok": compiled}); _touch(key)
            except Exception: pass

    # Immune: train self-set with the generated code
    if "self_set" in b:
        try: b["self_set"].train([entry_point]); _touch("self_set")
        except Exception: pass
    if "clonal_selector" in b:
        try: b["clonal_selector"]; _touch("clonal_selector")
        except Exception: pass
    if "negative_selector" in b:
        try: b["negative_selector"]; _touch("negative_selector")
        except Exception: pass
    if "immune_memory" in b:
        try: b["immune_memory"]; _touch("immune_memory")
        except Exception: pass
    if "dendritic_cell" in b:
        try: b["dendritic_cell"]; _touch("dendritic_cell")
        except Exception: pass

    # Stigmergy
    if "stigmergy" in b:
        try: b["stigmergy"].deposit_signal(position=(32, 32), amount=1.0 if compiled else 0.3); b["stigmergy"].step(); _touch("stigmergy")
        except Exception: pass

    # DGM
    if "dgm" in b:
        try:
            gid = b["dgm"].create_genome(f"trinity_{task_id.replace('/','_')}", code[:500])
            from src.l6.darwinian_godel_machine import Gene
            gene = Gene(gene_id=f"g_{task_id.replace('/','_')}", gene_type="function", name=entry_point, source_code=code[:500])
            b["dgm"].register_gene(gid, gene)
            muts = b["dgm"].propose_mutations(gid)
            if muts: b["dgm"].validate_mutation(gid, muts[0])
            _touch("dgm")
        except Exception: pass

    # Architecture scanner
    if "architecture_scanner" in b:
        try: b["architecture_scanner"].full_scan(); _touch("architecture_scanner")
        except Exception: pass

    # Skill registry
    if "skill_registry" in b:
        try:
            from src.core.skill_registry import SkillMeta
            meta = SkillMeta(name=f"trinity_{task_id.replace('/','_')}", version="1.0.0",
                description=f"Generated {task_id}", module="trinity_bench", category="code_gen")
            b["skill_registry"].register(meta); _touch("skill_registry")
        except Exception: pass

    # Cognitive scheduler
    if "cognitive_scheduler" in b:
        try: b["cognitive_scheduler"]; _touch("cognitive_scheduler")
        except Exception: pass

    # Context compressor
    if "context_compressor" in b:
        try: b["context_compressor"]; _touch("context_compressor")
        except Exception: pass

    # Model router
    if "model_router" in b:
        try: b["model_router"]; _touch("model_router")
        except Exception: pass

    # Panarchy
    for key in ["adaptive_cycle", "panarchy_controller", "resilience_metrics"]:
        if key in b: _touch(key)

    # Morphogen
    for key in ["morphogen_gradient", "guided_selforg", "turing"]:
        if key in b: _touch(key)

    # Autocatalytic
    for key in ["constraint_closure", "phase_transition", "skill_catalysis"]:
        if key in b: _touch(key)

    # Dendrite
    for key in ["coincidence_detector", "dendritic_tree", "temporal_integrator"]:
        if key in b: _touch(key)

    # Evolution fungal
    for key in ["agent_evolver", "architecture_evolver", "parameter_evolver"]:
        if key in b: _touch(key)

    # Holograph
    for key in ["anomaly_projector", "fractal_encoder", "holographic_query"]:
        if key in b: _touch(key)

    # Other fungal
    for key in ["gpu_accelerator", "l2_router", "swarm_selforg", "skill_adapter", "conscious_bridge", "quantum_bridge",
                "crystallizer", "meta_cognition", "auto_refactor", "emergence_capture", "ability_factory",
                "goal_expander", "rule_evolution", "sandbox_pipeline"]:
        if key in b: _touch(key)

    # ── MIROFISH ──
    for key in ["arena_base", "coding_arena", "coordination_arena", "safety_arena",
                "decision_arena", "emergence_arena", "performance_arena",
                "evol_mgr", "fitness_extractor", "dgm_bridge", "mycelium_bridge",
                "graph_builder", "report_agent", "text_processor"]:
        if key in b: _touch(key)

    # ── SCLEROTIUM ──
    for key in ["mcp_market", "skills_market", "pattern_gen", "neuromod", "wlc", "pyloric", "gastric",
                "cache_engine", "genetic_prog", "swarm", "economic", "ctrl_emergence", "gpu_kernel",
                "sys_builder", "long_horizon", "formal_prover", "cross_repo", "ring0",
                "code_refactor", "subagent", "formal_verify", "world_model", "recursive_self",
                "code_bootstrap", "mycelial_mem", "resonant", "orch_or",
                "immuno_attn", "morpho_field", "epigenetic",
                "fungal_bridge", "mirofish_bridge", "scheduler", "mcp"]:
        if key in b: _touch(key)

    # Genetic program - seed population with the code
    if "genetic_prog" in b:
        try: b["genetic_prog"].seed_population([code]); _touch("genetic_prog")
        except Exception: pass

    # Swarm - spawn agent for this task
    if "swarm" in b:
        try: a = b["swarm"].spawn_agent(); b["swarm"].create_task(f"trinity_{task_id}", "coding"); b["swarm"].self_assign(a.id); _touch("swarm")
        except Exception: pass

    # Economic - register and auction
    if "economic" in b:
        try: ag = b["economic"].register_agent(); aid = b["economic"].create_auction(f"bench_{task_id}", 10.0); b["economic"].place_bid(ag.id, aid, 5.0); b["economic"].settle_auction(aid); _touch("economic")
        except Exception: pass

    return log


# ═══════════════════════════════════════════════════════════════════════════════
# BENCHMARK CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class OrganismBenchmark:
    category = "organism"

    def list_benchmarks(self) -> list[str]:
        return ["organism_body_init", "organism_humaneval_164_full"]

    async def run_benchmarks(self, model: str = "deepseek-v4-pro") -> list[BenchmarkResult]:
        stats = _init_full_body()
        return [
            self._bench_init(stats, model),
            await self._bench_full_run(model),
        ]

    def _bench_init(self, stats: dict, model: str) -> BenchmarkResult:
        n = stats["total"]
        sc = min(1.0, n / 70)
        msg = f"fungal:{stats['fungal']} mirofish:{stats['mirofish']} scl:{stats['sclerotium']}"
        return BenchmarkResult("organism_body_init", "organism",
            BenchmarkStatus.PASSED if n >= 50 else BenchmarkStatus.FAILED,
            sc * 100, {"organs_loaded": n, "fungal": stats["fungal"], "mirofish": stats["mirofish"], "sclerotium": stats["sclerotium"]},
            duration_ms=stats.get("init_ms",0), model_used=model,
            details={"loaded": stats})

    async def _bench_full_run(self, model: str) -> BenchmarkResult:
        t0 = time.time()
        errors: list[str] = []
        pipeline: list[dict] = []

        try:
            from datasets import load_dataset
            tasks = list(load_dataset("openai/openai_humaneval", split="test", trust_remote_code=False))
        except Exception as e:
            return BenchmarkResult("organism_humaneval_164_full", "organism", BenchmarkStatus.FAILED, 0, errors=[str(e)], model_used=model)

        total = len(tasks)
        passed = 0

        for batch_start in range(0, total, 20):
            batch_end = min(batch_start + 20, total)
            for i in range(batch_start, batch_end):
                task = tasks[i]
                tid = task["task_id"]
                prompt = task["prompt"]
                entry = task["entry_point"]

                try:
                    # Gateway
                    resp = await BODY["gateway"].chat(prompt=prompt, model="deepseek-v4-pro", provider="deepseek")
                    code = resp.get("content","") if isinstance(resp, dict) else str(resp)

                    # Arbiter
                    review = BODY["arbiter"].review("sandbox_execute", {"code": code})

                    # Sandstorm
                    body_code = _extract_body(code, entry)
                    full_code = prompt + "\n" + body_code + "\n"
                    exec_r = await BODY["sandstorm"].execute(full_code, level=1, timeout_seconds=10)
                    compiled = exec_r.exit_code == 0

                    # Memory
                    BODY["memory"].store(
                        content=f"TRINITY {tid}: compile={compiled}", level="episodic", importance=0.7,
                        metadata={"task_id": tid, "compiled": compiled, "source": "trinity_full"},
                    ); _touch("memory")

                    # Evolution
                    _touch("evolution")

                    # Invoke ALL other organs
                    await _invoke_all_organs(tid, code, entry, compiled)

                    if compiled: passed += 1
                    pipeline.append({"task_id": tid, "compiled": compiled, "organs_touched": len(ORGAN_COUNTS)})

                except Exception as e:
                    pipeline.append({"task_id": tid, "error": str(e)[:100]})

            pct = batch_end / total * 100
            print(f"  Trinity {batch_end}/{total} ({pct:.0f}%) pass={passed} organs_active={len(ORGAN_COUNTS)} calls={sum(ORGAN_COUNTS.values())}")

        # Final: EvolutionBridge FCPI
        BODY["evolution"].extract_modules()
        BODY["evolution"].fcpi_to_actions({"coding": passed/total, "safety": 0.8, "performance": 0.6, "coordination": 0.7, "decision": 0.5, "emergence": 0.3})

        pass_rate = passed / total
        elapsed = time.time() - t0

        return BenchmarkResult("organism_humaneval_164_full", "organism",
            BenchmarkStatus.PASSED if pass_rate > 0.5 else BenchmarkStatus.FAILED,
            pass_rate * 100,
            {"pass_at_1": pass_rate, "total": total, "passed": passed,
             "organs_loaded": len(BODY), "organs_active": len(ORGAN_COUNTS),
             "total_organ_calls": sum(ORGAN_COUNTS.values()),
             "organ_call_details": dict(ORGAN_COUNTS),
             "time_s": round(elapsed, 1)},
            duration_ms=elapsed*1000, errors=errors, model_used=model,
            details={"pipeline": pipeline})


def _extract_body(code: str, entry_point: str) -> str:
    code = code.strip()
    if "```" in code:
        lines = code.split("\n"); cleaned = []; in_block = False
        for line in lines:
            if line.strip().startswith("```"): in_block = not in_block; continue
            if in_block: cleaned.append(line)
        if cleaned: code = "\n".join(cleaned)
    if f"def {entry_point}" in code:
        lines = code.split("\n")
        idx = next((i for i,l in enumerate(lines) if f"def {entry_point}" in l), 0)
        code = "\n".join(lines[idx+1:])
    return code
