"""完整集成测试 — Arena → OASIS → FCPI → Mycelium → DGM 全链路.

验证:
    1. OasisBridge 将 Arena Profile/Config 写入 OASIS 格式
    2. MyceliumBridge 将 FCPI 向量映射为 Mycelium 格式
    3. DGMBridge 将 FCPI 映射为失败信号 + 基因适应度更新
    4. 完整闭环: 6 竞技场 → 6 适应度 → FCPI 向量 → Mycelium + DGM
"""

import importlib.util
import json
import sys
import tempfile
import time
from pathlib import Path

import pytest

# ── 模块加载 ──────────────────────────────────────────────────────────
_BACKEND = Path(__file__).parent.parent


def _setup_packages():
    import types
    for pkg_path, pkg_name in [
        ("app", "app"),
        ("app/services", "app.services"),
        ("app/services/arenas", "app.services.arenas"),
    ]:
        if pkg_name not in sys.modules:
            pkg = types.ModuleType(pkg_name)
            pkg.__path__ = [str(_BACKEND / pkg_path)]
            pkg.__package__ = pkg_name
            sys.modules[pkg_name] = pkg


def _load_module(full_name: str, rel_path: str):
    path = _BACKEND / rel_path
    spec = importlib.util.spec_from_file_location(full_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    module.__package__ = full_name.rsplit(".", 1)[0]
    module.__name__ = full_name
    spec.loader.exec_module(module)
    return module


_setup_packages()

_m_arena_base = _load_module("app.services.arenas.arena_base", "app/services/arenas/arena_base.py")
_m_fitext = _load_module("app.services.fitness_extractor", "app/services/fitness_extractor.py")
_m_oasis = _load_module("app.services.oasis_bridge", "app/services/oasis_bridge.py")
_m_mycelium = _load_module("app.services.mycelium_bridge", "app/services/mycelium_bridge.py")
_m_dgm = _load_module("app.services.dgm_bridge", "app/services/dgm_bridge.py")

# 加载竞技场模块
for arena_name in ["coding_arena", "coordination_arena", "safety_arena", "decision_arena", "emergence_arena", "performance_arena"]:
    _load_module(f"app.services.arenas.{arena_name}", f"app/services/arenas/{arena_name}.py")

_evomgr = _load_module("app.services.evolution_generation_manager", "app/services/evolution_generation_manager.py")

from app.services.arenas.arena_base import FCPIDimension, FitnessVector  # noqa: E402
from app.services.arenas.coding_arena import CodingArena  # noqa: E402
from app.services.arenas.coordination_arena import CoordinationArena  # noqa: E402
from app.services.arenas.safety_arena import SafetyArena  # noqa: E402
from app.services.arenas.decision_arena import DecisionArena  # noqa: E402
from app.services.arenas.emergence_arena import EmergenceArena  # noqa: E402
from app.services.arenas.performance_arena import PerformanceArena  # noqa: E402
from app.services.fitness_extractor import EmergentFitnessExtractor  # noqa: E402
from app.services.oasis_bridge import OasisBridge  # noqa: E402
from app.services.mycelium_bridge import MyceliumBridge  # noqa: E402
from app.services.dgm_bridge import DGMBridge  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def genome_context():
    return {
        "genome_id": "test_genome_integration",
        "generation": 1,
        "code_snippets": [
            {
                "id": "snipp_1", "name": "router", "language": "python",
                "source": "def route(x): return handlers.get(x, 'default')",
                "context": "Request router for multi-agent dispatch",
            },
        ],
        "decision_tasks": [
            {
                "name": "Resource Challenge", "description": "Allocate resources optimally",
                "subgoals": ["audit", "plan", "execute"], "difficulty": 0.6,
            },
        ],
        "performance_data": {
            "routing_latency_ms": 150, "event_throughput": 8000,
            "field_update_cells_per_ms": 500, "token_efficiency": 0.68,
            "memory_compression_ratio": 0.52, "scalability_factor": 0.65,
        },
        "agent_count": 10,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Test: OasisBridge
# ═══════════════════════════════════════════════════════════════════════════

class TestOasisBridge:
    def test_write_agent_profiles_csv(self, temp_dir, genome_context):
        """OasisBridge 写入 Twitter CSV Profile."""
        bridge = OasisBridge(uploads_dir=str(temp_dir))
        arena = CodingArena(work_dir=temp_dir / "coding")
        profiles = arena.build_agent_profiles(genome_context)
        bridge._write_twitter_profiles(profiles, temp_dir)
        csv_path = temp_dir / "twitter_profiles.csv"
        assert csv_path.exists()
        with open(csv_path) as f:
            lines = f.readlines()
            assert len(lines) > 1  # header + data rows

    def test_write_agent_profiles_json(self, temp_dir, genome_context):
        """OasisBridge 写入 Reddit JSON Profile."""
        bridge = OasisBridge(uploads_dir=str(temp_dir))
        arena = SafetyArena(work_dir=temp_dir / "safety")
        profiles = arena.build_agent_profiles(genome_context)
        bridge._write_reddit_profiles(profiles, temp_dir)
        json_path = temp_dir / "reddit_profiles.json"
        assert json_path.exists()
        with open(json_path) as f:
            data = json.load(f)
            assert len(data) > 0
            assert "user_id" in data[0]

    def test_write_simulation_config(self, temp_dir, genome_context):
        """OasisBridge 写入仿真配置."""
        bridge = OasisBridge(uploads_dir=str(temp_dir))
        arena = CoordinationArena(work_dir=temp_dir / "coord")
        profiles = arena.build_agent_profiles(genome_context)
        sim_config = arena.build_simulation_config(profiles, genome_context)
        sim_dir = bridge._prepare_simulation_dir("test_sim_001")
        config_path = sim_dir / "simulation_config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(sim_config, f, ensure_ascii=False)
        assert config_path.exists()
        with open(config_path) as f:
            loaded = json.load(f)
            assert "arena_type" in loaded


# ═══════════════════════════════════════════════════════════════════════════
# Test: MyceliumBridge
# ═══════════════════════════════════════════════════════════════════════════

class TestMyceliumBridge:
    def test_single_gene_mapping(self):
        """单个 FCPI 向量 → Mycelium 格式."""
        bridge = MyceliumBridge()
        extractor = EmergentFitnessExtractor()
        arena_results = {
            dim: FitnessVector(dimension=dim, primary_score=0.75, sub_scores={},
                               confidence=0.85, generation=1, genome_id="g1", arena_id="a")
            for dim in FCPIDimension
        }
        extraction = extractor.extract(arena_results, {"genome_id": "g1"})
        result = bridge.to_mycelium_format(extraction.fcpi_vector)
        assert "g1" in result
        assert "sharpe" in result["g1"]
        assert "consistency" in result["g1"]
        assert "diversity_contrib" in result["g1"]
        assert "_fcpi_vector" in result["g1"]
        assert 0.0 <= result["g1"]["sharpe"] <= 1.0

    def test_batch_mapping(self):
        """批量 FCPI 向量映射."""
        bridge = MyceliumBridge()
        extractor = EmergentFitnessExtractor()

        fcpi_vectors = {}
        for i in range(5):
            arena_results = {
                dim: FitnessVector(dimension=dim, primary_score=0.5 + i * 0.1,
                                   sub_scores={}, confidence=0.7 + i * 0.05,
                                   generation=1, genome_id=f"g{i}", arena_id="a")
                for dim in FCPIDimension
            }
            extraction = extractor.extract(arena_results, {"genome_id": f"g{i}"})
            fcpi_vectors[f"g{i}"] = extraction.fcpi_vector

        result = bridge.batch_to_mycelium(fcpi_vectors)
        assert result.genes_processed == 5
        assert result.mapping_quality > 0.9
        assert len(result.performance_data) == 5

    def test_from_extraction_result(self):
        """从 ExtractionResult 直接映射."""
        bridge = MyceliumBridge()
        extractor = EmergentFitnessExtractor()
        arena_results = {
            dim: FitnessVector(dimension=dim, primary_score=0.8, sub_scores={},
                               confidence=0.9, generation=1, genome_id="g_direct", arena_id="a")
            for dim in FCPIDimension
        }
        extraction = extractor.extract(arena_results, {"genome_id": "g_direct"})
        result = bridge.from_extraction_result(extraction, gene_id="custom_id")
        assert "custom_id" in result

    def test_goodharting_mapping(self):
        """Goodharting 标记的映射."""
        bridge = MyceliumBridge()
        extractor = EmergentFitnessExtractor()
        # 安全分数异常低 → 触发 Goodharting
        arena_results = {
            FCPIDimension.CODING: FitnessVector(
                dimension=FCPIDimension.CODING, primary_score=0.9,
                sub_scores={}, confidence=0.9, generation=1, genome_id="g_cheat", arena_id="a"),
            FCPIDimension.COORDINATION: FitnessVector(
                dimension=FCPIDimension.COORDINATION, primary_score=0.85,
                sub_scores={}, confidence=0.9, generation=1, genome_id="g_cheat", arena_id="a"),
            FCPIDimension.SAFETY: FitnessVector(
                dimension=FCPIDimension.SAFETY, primary_score=0.1,
                sub_scores={}, confidence=0.5, generation=1, genome_id="g_cheat", arena_id="a"),
            FCPIDimension.DECISION: FitnessVector(
                dimension=FCPIDimension.DECISION, primary_score=0.85,
                sub_scores={}, confidence=0.8, generation=1, genome_id="g_cheat", arena_id="a"),
            FCPIDimension.EMERGENCE: FitnessVector(
                dimension=FCPIDimension.EMERGENCE, primary_score=0.6,
                sub_scores={}, confidence=0.7, generation=1, genome_id="g_cheat", arena_id="a"),
            FCPIDimension.PERFORMANCE: FitnessVector(
                dimension=FCPIDimension.PERFORMANCE, primary_score=0.88,
                sub_scores={}, confidence=0.95, generation=1, genome_id="g_cheat", arena_id="a"),
        }
        extraction = extractor.extract(arena_results, {"genome_id": "g_cheat"})
        result = bridge.from_extraction_result(extraction)
        assert "g_cheat" in result
        assert result["g_cheat"].get("_goodharting_flag") == 1.0


# ═══════════════════════════════════════════════════════════════════════════
# Test: DGMBridge
# ═══════════════════════════════════════════════════════════════════════════

class TestDGMBridge:
    def test_failure_signals_low_safety(self):
        """低安全分数 → failure_signals."""
        bridge = DGMBridge()
        extractor = EmergentFitnessExtractor()
        arena_results = {
            dim: FitnessVector(dimension=dim, primary_score=0.5, sub_scores={},
                               confidence=0.8, generation=1, genome_id="g_low", arena_id="a")
            for dim in FCPIDimension
        }
        # 覆盖安全为低分
        arena_results[FCPIDimension.SAFETY] = FitnessVector(
            dimension=FCPIDimension.SAFETY, primary_score=0.15,
            sub_scores={}, confidence=0.7, generation=1, genome_id="g_low", arena_id="a")
        extraction = extractor.extract(arena_results, {"genome_id": "g_low"})
        signals = bridge.fcpi_to_failure_signals(extraction.fcpi_vector, "g_low")
        assert len(signals) >= 1
        assert any(s.signature == "safety_threshold_violation" for s in signals)

    def test_failure_signals_healthy(self):
        """健康分数 → 无失败信号."""
        bridge = DGMBridge()
        extractor = EmergentFitnessExtractor()
        arena_results = {
            dim: FitnessVector(dimension=dim, primary_score=0.85, sub_scores={},
                               confidence=0.9, generation=1, genome_id="g_healthy", arena_id="a")
            for dim in FCPIDimension
        }
        extraction = extractor.extract(arena_results, {"genome_id": "g_healthy"})
        signals = bridge.fcpi_to_failure_signals(extraction.fcpi_vector, "g_healthy")
        assert len(signals) == 0

    def test_gene_fitness_updates(self):
        """FCPI 驱动基因适应度更新."""
        bridge = DGMBridge()
        extractor = EmergentFitnessExtractor()
        arena_results = {
            dim: FitnessVector(dimension=dim, primary_score=0.85, sub_scores={},
                               confidence=0.9, generation=1, genome_id="g_update", arena_id="a")
            for dim in FCPIDimension
        }
        extraction = extractor.extract(arena_results, {"genome_id": "g_update"})
        gene_map = {
            "func_001": {"type": "function", "fitness_score": 0.5},
            "func_002": {"type": "class", "fitness_score": 0.6},
            "bridge_001": {"type": "bridge", "fitness_score": 0.4},
            "skill_001": {"type": "skill", "fitness_score": 0.55},
            "hyper_001": {"type": "hyperparam", "fitness_score": 0.65},
        }
        updates = bridge.fcpi_to_gene_fitness_updates(extraction.fcpi_vector, gene_map)
        assert len(updates) > 0
        # 所有更新应该是正向的 (高分 FCPI → 提升基因适应度)
        for u in updates:
            assert u.new_fitness > u.old_fitness or abs(u.new_fitness - u.old_fitness) < 0.01

    def test_genome_health_report(self):
        """基因组健康报告."""
        bridge = DGMBridge()
        extractor = EmergentFitnessExtractor()
        arena_results = {
            dim: FitnessVector(dimension=dim, primary_score=0.85 if dim != FCPIDimension.SAFETY else 0.15,
                               sub_scores={}, confidence=0.8, generation=1, genome_id="g_health", arena_id="a")
            for dim in FCPIDimension
        }
        extraction = extractor.extract(arena_results, {"genome_id": "g_health"})
        health = DGMBridge.compute_genome_health(extraction.fcpi_vector)
        assert not health["healthy"]
        assert "safety" in health["critical_dimensions"]

    def test_suggest_mutation_strategy(self):
        """建议变异策略."""
        history = [
            {"coding": 0.7, "coordination": 0.7, "safety": 0.8, "decision": 0.6, "emergence": 0.5, "performance": 0.7},
            {"coding": 0.65, "coordination": 0.68, "safety": 0.75, "decision": 0.62, "emergence": 0.5, "performance": 0.71},
            {"coding": 0.55, "coordination": 0.65, "safety": 0.6, "decision": 0.63, "emergence": 0.5, "performance": 0.72},
        ]
        suggestions = DGMBridge.suggest_mutation_strategy(history)
        assert suggestions["INSERT"] == "increase"  # coding 退化 → 多 INSERT
        assert suggestions["SUBSTITUTE"] == "increase"  # safety 退化 → 多 SUBSTITUTE


# ═══════════════════════════════════════════════════════════════════════════
# Test: 完整闭环
# ═══════════════════════════════════════════════════════════════════════════

class TestFullIntegration:
    def test_complete_closed_loop(self, temp_dir):
        """完整闭环: Arena → FCPI → Mycelium → DGM 信号."""
        extractor = EmergentFitnessExtractor()
        mycelium_bridge = MyceliumBridge()
        dgm_bridge = DGMBridge()

        arenas = {
            FCPIDimension.CODING: CodingArena(work_dir=temp_dir / "coding"),
            FCPIDimension.COORDINATION: CoordinationArena(work_dir=temp_dir / "coord"),
            FCPIDimension.SAFETY: SafetyArena(work_dir=temp_dir / "safety"),
            FCPIDimension.DECISION: DecisionArena(work_dir=temp_dir / "decision"),
            FCPIDimension.EMERGENCE: EmergenceArena(work_dir=temp_dir / "emergence"),
            FCPIDimension.PERFORMANCE: PerformanceArena(work_dir=temp_dir / "perf"),
        }

        ctx = {
            "genome_id": "closed_loop_test",
            "generation": 1,
            "code_snippets": [
                {"id": "1", "name": "test", "language": "python",
                 "source": "def test(): pass", "context": "test"},
            ],
            "decision_tasks": [
                {"name": "Test Task", "description": "Test", "subgoals": ["do"], "difficulty": 0.5},
            ],
            "performance_data": {
                "routing_latency_ms": 200, "event_throughput": 7000,
                "field_update_cells_per_ms": 450, "token_efficiency": 0.60,
                "memory_compression_ratio": 0.50, "scalability_factor": 0.60,
            },
            "agent_count": 8,
        }

        # Step 1: 每个竞技场运行一代
        arena_results: dict[FCPIDimension, FitnessVector] = {}
        for dim, arena in arenas.items():
            result = arena.run_generation(ctx, action_logs=[])
            if result.success and result.fitness_vector:
                arena_results[dim] = result.fitness_vector

        assert len(arena_results) == 6, "All 6 arenas must produce fitness vectors"

        # Step 2: 提取 FCPI 向量
        extraction = extractor.extract(arena_results, ctx)
        fcpi = extraction.fcpi_vector
        print(f"\n  FCPI: C={fcpi.coding:.3f} R={fcpi.coordination:.3f} "
              f"S={fcpi.safety:.3f} D={fcpi.decision:.3f} "
              f"E={fcpi.emergence:.3f} P={fcpi.performance:.3f} "
              f"| Total={fcpi.to_legacy_fitness():.4f}")

        # Step 3: Mycelium 格式映射
        mycelium_data = mycelium_bridge.from_extraction_result(
            extraction, gene_id=ctx["genome_id"]
        )
        assert ctx["genome_id"] in mycelium_data
        assert "sharpe" in mycelium_data[ctx["genome_id"]]
        print(f"  Mycelium: sharpe={mycelium_data[ctx['genome_id']]['sharpe']:.4f} "
              f"consistency={mycelium_data[ctx['genome_id']]['consistency']:.4f} "
              f"diversity={mycelium_data[ctx['genome_id']]['diversity_contrib']:.4f}")

        # Step 4: DGM 失败信号
        signals = dgm_bridge.fcpi_to_failure_signals(fcpi, ctx["genome_id"])
        print(f"  DGM failures: {len(signals)} signals")
        for s in signals:
            print(f"    - {s.signature} (severity={s.severity:.2f})")

        # Step 5: DGM 基因适应度更新
        gene_map = {
            "func_001": {"type": "function", "fitness_score": 0.5},
            "func_002": {"type": "class", "fitness_score": 0.5},
            "bridge_001": {"type": "bridge", "fitness_score": 0.5},
            "skill_001": {"type": "skill", "fitness_score": 0.5},
        }
        updates = dgm_bridge.fcpi_to_gene_fitness_updates(fcpi, gene_map)
        print(f"  Gene updates: {len(updates)} fitness adjustments")

        # Step 6: 基因组健康报告
        health = DGMBridge.compute_genome_health(fcpi)
        print(f"  Health: healthy={health['healthy']} "
              f"critical={health['critical_dimensions']} "
              f"warning={health['warning_dimensions']}")

        # 验证闭环成功
        assert extraction is not None
        assert len(mycelium_data) > 0
        assert _isinstance(extraction.fcpi_vector, _m_fitext.FCPIVector)

    def test_multi_genome_batch(self, temp_dir):
        """多基因组批量处理: Arena → FCPI → Mycelium batch."""
        extractor = EmergentFitnessExtractor()
        mycelium_bridge = MyceliumBridge()
        arenas = {
            dim: PerformanceArena(work_dir=temp_dir / dim.value)
            for dim in FCPIDimension
        }

        fcpi_vectors = {}
        for i in range(5):
            ctx = {
                "genome_id": f"batch_genome_{i}",
                "generation": 1,
                "performance_data": {
                    "routing_latency_ms": 100 + i * 20,
                    "event_throughput": 7000 + i * 500,
                    "field_update_cells_per_ms": 400 + i * 100,
                    "token_efficiency": 0.55 + i * 0.05,
                    "memory_compression_ratio": 0.45 + i * 0.05,
                    "scalability_factor": 0.55 + i * 0.05,
                },
                "agent_count": 10,
                "code_snippets": [],
                "decision_tasks": [],
            }
            arena_results = {}
            for dim, arena in arenas.items():
                result = arena.run_generation(ctx, action_logs=[])
                if result.success and result.fitness_vector:
                    arena_results[dim] = result.fitness_vector
            extraction = extractor.extract(arena_results, ctx)
            fcpi_vectors[ctx["genome_id"]] = extraction.fcpi_vector

        # 批量映射
        result = mycelium_bridge.batch_to_mycelium(fcpi_vectors)
        assert result.genes_processed == 5
        assert result.mapping_quality > 0.8

        # 验证适应度随性能数据增长
        scores = [
            result.performance_data[f"batch_genome_{i}"]["sharpe"]
            for i in range(5)
        ]
        print(f"\n  Batch FCPI scores: {[f'{s:.4f}' for s in scores]}")
        # 性能数据逐代改善 → FCPI 应逐代提升
        assert scores[-1] >= scores[0], "FCPI should improve with better performance data"


def _isinstance(obj, cls):
    """类型检查 (模块可能不同)."""
    return type(obj).__name__ == cls.__name__
