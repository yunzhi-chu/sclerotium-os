"""Phase 1 集成测试 — 六维进化引擎端到端验证.

直接加载模块，绕过 app/__init__.py 的 Flask/Zep 重依赖。
"""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pytest

# ── 直接加载所有需要的模块 ──────────────────────────────────────────────
_BACKEND = Path(__file__).parent.parent

# 预先创建所有需要的父包
for pkg_path, pkg_name in [
    ("app", "app"),
    ("app/services", "app.services"),
    ("app/services/arenas", "app.services.arenas"),
]:
    if pkg_name not in sys.modules:
        import types
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [str(_BACKEND / pkg_path)]
        pkg.__package__ = pkg_name
        sys.modules[pkg_name] = pkg


def _load_module(full_name: str, rel_path: str) -> object:
    """加载模块到 sys.modules."""
    path = _BACKEND / rel_path
    spec = importlib.util.spec_from_file_location(full_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    # 从 complete 名称推断 __package__
    module.__package__ = full_name.rsplit(".", 1)[0]
    module.__name__ = full_name
    spec.loader.exec_module(module)
    return module


# 重要: 先注册所有 arena 模块名到 sys.modules 别名 (解决 evolution_manager 的内部导入)
# 按依赖顺序加载
_arena_base = _load_module("app.services.arenas.arena_base", "app/services/arenas/arena_base.py")
_coding = _load_module("app.services.arenas.coding_arena", "app/services/arenas/coding_arena.py")
_coord = _load_module("app.services.arenas.coordination_arena", "app/services/arenas/coordination_arena.py")
_safety = _load_module("app.services.arenas.safety_arena", "app/services/arenas/safety_arena.py")
_decision = _load_module("app.services.arenas.decision_arena", "app/services/arenas/decision_arena.py")
_emergence = _load_module("app.services.arenas.emergence_arena", "app/services/arenas/emergence_arena.py")
_perf = _load_module("app.services.arenas.performance_arena", "app/services/arenas/performance_arena.py")
_evomgr = _load_module("app.services.evolution_generation_manager", "app/services/evolution_generation_manager.py")
_fitext = _load_module("app.services.fitness_extractor", "app/services/fitness_extractor.py")

# 提取所有需要的类型
FCPIDimension = _arena_base.FCPIDimension
FitnessVector = _arena_base.FitnessVector
ArenaConfig = _arena_base.ArenaConfig
ArenaResult = _arena_base.ArenaResult
CodingArena = _coding.CodingArena
CoordinationArena = _coord.CoordinationArena
SafetyArena = _safety.SafetyArena
DecisionArena = _decision.DecisionArena
EmergenceArena = _emergence.EmergenceArena
PerformanceArena = _perf.PerformanceArena
EvolutionGenerationManager = _evomgr.EvolutionGenerationManager
EvolutionConfig = _evomgr.EvolutionConfig
EvolutionPhase = _evomgr.EvolutionPhase
PanarchyPhase = _evomgr.PanarchyPhase
EmergentFitnessExtractor = _fitext.EmergentFitnessExtractor
FCPIVector = _fitext.FCPIVector
ExtractionResult = _fitext.ExtractionResult


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def temp_work_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_genome_context():
    return {
        "genome_id": "test_genome_001",
        "generation": 1,
        "code_snippets": [
            {
                "id": "snippet_1",
                "name": "adaptive_router",
                "language": "python",
                "source": (
                    "def route_request(input_data: dict) -> str:\n"
                    '    """Route request to appropriate handler."""\n'
                    "    if not isinstance(input_data, dict):\n"
                    "        raise ValueError('input_data must be dict')\n"
                    "    task_type = input_data.get('type', 'default')\n"
                    "    handlers = {\n"
                    "        'analysis': '_handle_analysis',\n"
                    "        'trading': '_handle_trading',\n"
                    "        'query': '_handle_query',\n"
                    "    }\n"
                    "    return handlers.get(task_type, '_handle_default')\n"
                ),
                "context": "Adaptive request router for multi-agent task dispatch",
            },
        ],
        "decision_tasks": [
            {
                "name": "Resource Optimization Challenge",
                "description": "Optimize resource allocation across 5 projects over 72 hours",
                "subgoals": ["audit", "assess", "allocate", "rebalance", "optimize"],
                "success_criteria": "80% utilization, no deadline missed",
                "difficulty": 0.7,
            },
        ],
        "performance_data": {
            "routing_latency_ms": 120,
            "event_throughput": 8500,
            "field_update_cells_per_ms": 600,
            "token_efficiency": 0.72,
            "memory_compression_ratio": 0.55,
            "scalability_factor": 0.68,
        },
        "agent_count": 15,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Test: 竞技场创建和配置
# ═══════════════════════════════════════════════════════════════════════════

class TestArenaCreation:
    ARENA_CLASSES = [
        (CodingArena, FCPIDimension.CODING),
        (CoordinationArena, FCPIDimension.COORDINATION),
        (SafetyArena, FCPIDimension.SAFETY),
        (DecisionArena, FCPIDimension.DECISION),
        (EmergenceArena, FCPIDimension.EMERGENCE),
        (PerformanceArena, FCPIDimension.PERFORMANCE),
    ]

    @pytest.mark.parametrize("arena_cls,dimension", ARENA_CLASSES)
    def test_arena_creation_default(self, arena_cls, dimension, temp_work_dir):
        arena = arena_cls(work_dir=temp_work_dir)
        assert arena.config.dimension == dimension
        assert arena.generation == 0
        assert not arena.is_running
        assert len(arena.history) == 0

    @pytest.mark.parametrize("arena_cls,dimension", ARENA_CLASSES)
    def test_arena_creation_custom_config(self, arena_cls, dimension, temp_work_dir):
        config = ArenaConfig(
            arena_id=f"test_{dimension.value}",
            dimension=dimension,
            max_rounds=10,
            min_agents=3,
            max_agents=10,
        )
        arena = arena_cls(config=config, work_dir=temp_work_dir)
        assert arena.config.max_rounds == 10
        assert arena.config.min_agents == 3

    @pytest.mark.parametrize("arena_cls,dimension", ARENA_CLASSES)
    def test_arena_build_profiles(self, arena_cls, dimension, temp_work_dir, sample_genome_context):
        arena = arena_cls(work_dir=temp_work_dir)
        profiles = arena.build_agent_profiles(sample_genome_context)
        if dimension != FCPIDimension.PERFORMANCE:
            assert len(profiles) > 0
            for p in profiles:
                assert "user_id" in p
                assert "user_name" in p
                assert "persona" in p
                assert "role_type" in p

    @pytest.mark.parametrize("arena_cls,dimension", ARENA_CLASSES)
    def test_arena_build_simulation_config(self, arena_cls, dimension, temp_work_dir, sample_genome_context):
        arena = arena_cls(work_dir=temp_work_dir)
        profiles = arena.build_agent_profiles(sample_genome_context)
        config = arena.build_simulation_config(profiles, sample_genome_context)
        assert isinstance(config, dict)
        assert "arena_type" in config
        assert "time_config" in config


# ═══════════════════════════════════════════════════════════════════════════
# Test: 适应度提取
# ═══════════════════════════════════════════════════════════════════════════

class TestFitnessExtraction:
    @pytest.mark.parametrize("arena_cls,dimension", TestArenaCreation.ARENA_CLASSES)
    def test_arena_extract_fitness_empty(self, arena_cls, dimension, temp_work_dir, sample_genome_context):
        arena = arena_cls(work_dir=temp_work_dir)
        profiles = arena.build_agent_profiles(sample_genome_context)
        fitness = arena.extract_fitness([], profiles, sample_genome_context)
        assert isinstance(fitness, FitnessVector)
        assert fitness.dimension == dimension
        assert 0.0 <= fitness.primary_score <= 1.0

    @pytest.mark.parametrize("arena_cls,dimension", TestArenaCreation.ARENA_CLASSES)
    def test_arena_run_generation(self, arena_cls, dimension, temp_work_dir, sample_genome_context):
        arena = arena_cls(work_dir=temp_work_dir)
        result = arena.run_generation(sample_genome_context, action_logs=[])
        assert isinstance(result, ArenaResult)
        assert result.generation == 1

    def test_coding_arena_with_mock_reviews(self, temp_work_dir):
        arena = CodingArena(work_dir=temp_work_dir)
        mock_logs = [
            {"round_num": 1, "action_type": "REVIEW", "agent_id": 1001,
             "role_type": "senior_engineer",
             "content": "Good architecture, approve", "tags": ["code-review"]},
            {"round_num": 1, "action_type": "REVIEW", "agent_id": 1002,
             "role_type": "security_expert",
             "content": "Potential injection vulnerability at line 3", "tags": ["security"]},
            {"round_num": 2, "action_type": "FORK", "agent_id": 1005,
             "role_type": "junior_dev", "content": "Fixed the vulnerability"},
            {"round_num": 3, "action_type": "MERGE", "agent_id": 1001,
             "role_type": "senior_engineer", "content": "Merged security fix"},
            {"round_num": 4, "action_type": "APPROVE", "agent_id": 1002,
             "role_type": "security_expert", "content": "Confirmed fix"},
        ]
        profiles = arena.build_agent_profiles({
            "genome_id": "test",
            "code_snippets": [{"id": "1", "language": "python", "source": "def foo(): pass"}],
        })
        fitness = arena.extract_fitness(mock_logs, profiles, {"genome_id": "test"})
        assert fitness.primary_score > 0.0
        assert fitness.sub_scores["review_approval_rate"] > 0.0

    def test_safety_arena_has_overseer(self, temp_work_dir):
        arena = SafetyArena(work_dir=temp_work_dir)
        profiles = arena.build_agent_profiles({"genome_id": "test"})
        red = [p for p in profiles if p["role_type"] == "red_attacker"]
        blue = [p for p in profiles if p["role_type"] == "blue_defender"]
        overseer = [p for p in profiles if p["role_type"] == "external_overseer"]
        assert len(red) >= 1
        assert len(blue) >= 1
        assert len(overseer) >= 1, "External overseer required by Moltbook theorem"


# ═══════════════════════════════════════════════════════════════════════════
# Test: EvolutionGenerationManager
# ═══════════════════════════════════════════════════════════════════════════

class TestEvolutionManager:
    def test_initialization(self, temp_work_dir):
        config = EvolutionConfig(max_generations=10, population_size=20)
        manager = EvolutionGenerationManager(config=config, work_dir=temp_work_dir)
        assert manager.phase == EvolutionPhase.PENDING
        assert manager.generation == 0

    def test_initialize_population(self, temp_work_dir):
        manager = EvolutionGenerationManager(work_dir=temp_work_dir)
        manager.initialize()
        assert manager.population_size == 50

    def test_run_single_generation(self, temp_work_dir, sample_genome_context):
        manager = EvolutionGenerationManager(
            config=EvolutionConfig(max_generations=5, population_size=5),
            work_dir=temp_work_dir,
        )
        manager.initialize()
        contexts = {
            genome["genome_id"]: sample_genome_context
            for genome in manager._population[:3]
        }
        report = manager.run_generation(contexts)
        assert report["generation"] == 1
        assert "fcpi_scores" in report
        assert report["population_size"] > 0

    def test_multi_generation(self, temp_work_dir, sample_genome_context):
        manager = EvolutionGenerationManager(
            config=EvolutionConfig(max_generations=5, population_size=10, elitism_count=2),
            work_dir=temp_work_dir,
        )
        manager.initialize()
        for gen in range(3):
            contexts = {
                g["genome_id"]: sample_genome_context
                for g in manager._population[:5]
            }
            report = manager.run_generation(contexts)
            assert report["generation"] == gen + 1
        assert len(manager.snapshots) == 3

    def test_snapshot_persistence(self, temp_work_dir, sample_genome_context):
        manager = EvolutionGenerationManager(
            config=EvolutionConfig(max_generations=3, population_size=5),
            work_dir=temp_work_dir,
        )
        manager.initialize()
        contexts = {
            g["genome_id"]: sample_genome_context
            for g in manager._population[:3]
        }
        manager.run_generation(contexts)
        snap_files = list(temp_work_dir.glob("snapshot_gen_*.json"))
        assert len(snap_files) == 1
        with open(snap_files[0]) as f:
            data = json.load(f)
        assert data["generation"] == 1


# ═══════════════════════════════════════════════════════════════════════════
# Test: EmergentFitnessExtractor
# ═══════════════════════════════════════════════════════════════════════════

def _make_fitness(dim, score):
    return FitnessVector(
        dimension=dim, primary_score=score, sub_scores={},
        confidence=0.85, generation=1, genome_id="g1", arena_id="a",
    )


class TestFitnessExtractor:
    def test_extract_from_all_arenas(self):
        extractor = EmergentFitnessExtractor()
        arena_results = {
            FCPIDimension.CODING: _make_fitness(FCPIDimension.CODING, 0.85),
            FCPIDimension.COORDINATION: _make_fitness(FCPIDimension.COORDINATION, 0.72),
            FCPIDimension.SAFETY: _make_fitness(FCPIDimension.SAFETY, 0.88),
            FCPIDimension.DECISION: _make_fitness(FCPIDimension.DECISION, 0.65),
            FCPIDimension.EMERGENCE: _make_fitness(FCPIDimension.EMERGENCE, 0.55),
            FCPIDimension.PERFORMANCE: _make_fitness(FCPIDimension.PERFORMANCE, 0.78),
        }
        result = extractor.extract(arena_results, {"genome_id": "g1", "generation": 1})
        assert isinstance(result, ExtractionResult)
        fcpi = result.fcpi_vector
        assert 0.0 <= fcpi.coding <= 1.0
        assert 0.0 <= fcpi.coordination <= 1.0
        assert 0.0 <= fcpi.safety <= 1.0
        assert 0.0 <= fcpi.decision <= 1.0
        assert 0.0 <= fcpi.emergence <= 1.0
        assert 0.0 <= fcpi.performance <= 1.0

    def test_to_legacy_fitness(self):
        extractor = EmergentFitnessExtractor()
        arena_results = {
            dim: _make_fitness(dim, 0.8 if dim != FCPIDimension.EMERGENCE else 0.4)
            for dim in FCPIDimension
        }
        result = extractor.extract(arena_results, {"genome_id": "g1"})
        legacy = result.fcpi_vector.to_legacy_fitness()
        assert 0.0 <= legacy <= 1.0

    def test_extract_for_mycelium_format(self):
        extractor = EmergentFitnessExtractor()
        arena_results = {
            dim: _make_fitness(dim, 0.75) for dim in FCPIDimension
        }
        mycelium_format = extractor.extract_for_mycelium(
            arena_results, genome_id="g_test", generation=3,
        )
        assert "g_test" in mycelium_format
        assert "sharpe" in mycelium_format["g_test"]
        assert "consistency" in mycelium_format["g_test"]
        assert "diversity_contrib" in mycelium_format["g_test"]
        assert "_fcpi_vector" in mycelium_format["g_test"]

    def test_goodharting_safety_sacrifice(self):
        extractor = EmergentFitnessExtractor()
        arena_results = {
            FCPIDimension.CODING: _make_fitness(FCPIDimension.CODING, 0.9),
            FCPIDimension.COORDINATION: _make_fitness(FCPIDimension.COORDINATION, 0.85),
            FCPIDimension.SAFETY: _make_fitness(FCPIDimension.SAFETY, 0.15),
            FCPIDimension.DECISION: _make_fitness(FCPIDimension.DECISION, 0.8),
            FCPIDimension.EMERGENCE: _make_fitness(FCPIDimension.EMERGENCE, 0.6),
            FCPIDimension.PERFORMANCE: _make_fitness(FCPIDimension.PERFORMANCE, 0.85),
        }
        result = extractor.extract(arena_results, {"genome_id": "g1"})
        assert result.fcpi_vector.goodharting_flag
        assert len(result.goodharting_warnings) > 0

    def test_goodharting_single_spike(self):
        extractor = EmergentFitnessExtractor()
        arena_results = {
            dim: _make_fitness(dim, 0.5 if dim != FCPIDimension.CODING else 0.95)
            for dim in FCPIDimension
        }
        result = extractor.extract(arena_results, {"genome_id": "g1"})
        assert result.fcpi_vector.goodharting_flag


# ═══════════════════════════════════════════════════════════════════════════
# Test: FCPIVector
# ═══════════════════════════════════════════════════════════════════════════

class TestFCPIVector:
    def test_dominates(self):
        v1 = FCPIVector(0.9, 0.9, 0.9, 0.9, 0.9, 0.9)
        v2 = FCPIVector(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
        assert v1.dominance_compare(v2)["dominates"]

    def test_non_dominated(self):
        v1 = FCPIVector(0.9, 0.3, 0.5, 0.5, 0.5, 0.5)
        v2 = FCPIVector(0.3, 0.9, 0.5, 0.5, 0.5, 0.5)
        c = v1.dominance_compare(v2)
        assert not c["dominates"]
        assert not c["dominated_by"]

    def test_pareto_front(self):
        # v1 支配 v2 (所有维度都更高)
        # v3 和 v4 互不支配 (各有一个维度更高)
        vectors = [
            FCPIVector(0.5, 0.5, 0.5, 0.5, 0.5, 0.5),  # 基线
            FCPIVector(0.9, 0.3, 0.5, 0.5, 0.5, 0.5),  # coding 高, coord 低
            FCPIVector(0.3, 0.9, 0.5, 0.5, 0.5, 0.5),  # coord 高, coding 低
            FCPIVector(0.1, 0.1, 0.1, 0.1, 0.1, 0.1),  # 被 v1 支配
        ]
        front = EmergentFitnessExtractor.compute_pareto_front(vectors)
        assert len(front) == 3  # 基线、v2、v3 互不支配; v4 被基线支配

    def test_diversity_score(self):
        vectors = [
            FCPIVector(0.9, 0.8, 0.7, 0.6, 0.5, 0.4),
            FCPIVector(0.1, 0.2, 0.3, 0.4, 0.5, 0.6),
            FCPIVector(0.5, 0.5, 0.5, 0.5, 0.5, 0.5),
        ]
        diversity = EmergentFitnessExtractor.diversity_score(vectors)
        assert 0.0 <= diversity <= 1.0
        assert diversity > 0.1

    def test_serialization(self):
        v = FCPIVector(
            coding=0.85, coordination=0.72, safety=0.88,
            decision=0.65, emergence=0.55, performance=0.78,
            coding_subs={"approval_rate": 0.9},
            generation=3, genome_id="g_test", confidence=0.85,
        )
        d = v.to_dict()
        assert d["coding"] == 0.85
        assert d["genome_id"] == "g_test"
        assert d["generation"] == 3


# ═══════════════════════════════════════════════════════════════════════════
# Test: 端到端进化流程
# ═══════════════════════════════════════════════════════════════════════════

class TestEndToEndEvolution:
    def test_full_single_generation_cycle(self, temp_work_dir, sample_genome_context):
        arenas = {
            FCPIDimension.CODING: CodingArena(work_dir=temp_work_dir / "coding"),
            FCPIDimension.COORDINATION: CoordinationArena(work_dir=temp_work_dir / "coordination"),
            FCPIDimension.SAFETY: SafetyArena(work_dir=temp_work_dir / "safety"),
            FCPIDimension.DECISION: DecisionArena(work_dir=temp_work_dir / "decision"),
            FCPIDimension.EMERGENCE: EmergenceArena(work_dir=temp_work_dir / "emergence"),
            FCPIDimension.PERFORMANCE: PerformanceArena(work_dir=temp_work_dir / "performance"),
        }

        arena_results = {}
        for dim, arena in arenas.items():
            result = arena.run_generation(sample_genome_context, action_logs=[])
            if result.success and result.fitness_vector:
                arena_results[dim] = result.fitness_vector
            else:
                arena_results[dim] = FitnessVector(
                    dimension=dim, primary_score=0.5, sub_scores={},
                    confidence=0.5, generation=1,
                    genome_id=sample_genome_context["genome_id"],
                    arena_id=arena.config.arena_id,
                )

        assert len(arena_results) == 6

        extractor = EmergentFitnessExtractor()
        extraction = extractor.extract(arena_results, sample_genome_context)
        fcpi = extraction.fcpi_vector
        assert fcpi.genome_id == sample_genome_context["genome_id"]

        mycelium_data = extractor.extract_for_mycelium(
            arena_results,
            genome_id=sample_genome_context["genome_id"],
            generation=1,
        )
        assert sample_genome_context["genome_id"] in mycelium_data
