"""ArenaBase 和 FitnessVector 单元测试.

直接加载模块，绕过 app/__init__.py 的重依赖 (Flask/Zep).
"""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

# 直接加载 arena_base 模块，不触发 app/__init__.py
_BACKEND = Path(__file__).parent.parent

# 预先创建父包
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


def _load_module(full_name: str, rel_path: str) -> object:
    path = _BACKEND / rel_path
    spec = importlib.util.spec_from_file_location(full_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    module.__package__ = full_name.rsplit(".", 1)[0]
    module.__name__ = full_name
    spec.loader.exec_module(module)
    return module


_arena_base = _load_module("app.services.arenas.arena_base", "app/services/arenas/arena_base.py")

ArenaBase = _arena_base.ArenaBase
ArenaConfig = _arena_base.ArenaConfig
ArenaResult = _arena_base.ArenaResult
FCPIDimension = _arena_base.FCPIDimension
FitnessVector = _arena_base.FitnessVector


class TestFitnessVector:
    """FitnessVector 不可变数据类测试."""

    def test_create_fitness_vector(self):
        """创建适应度向量."""
        fv = FitnessVector(
            dimension=FCPIDimension.CODING,
            primary_score=0.85,
            sub_scores={"review_approval_rate": 0.9, "fork_adoption_rate": 0.8},
            confidence=0.92,
            generation=5,
            genome_id="test_genome_001",
            arena_id="coding_test",
        )
        assert fv.primary_score == 0.85
        assert fv.confidence == 0.92
        assert fv.generation == 5
        assert len(fv.sub_scores) == 2

    def test_fitness_vector_immutable(self):
        """FitnessVector 应该是不可变的 (frozen dataclass)."""
        fv = FitnessVector(
            dimension=FCPIDimension.SAFETY,
            primary_score=0.7,
            sub_scores={},
            confidence=0.8,
            generation=1,
            genome_id="g1",
            arena_id="a1",
        )
        with pytest.raises(Exception):
            fv.primary_score = 0.9  # type: ignore

    def test_all_fcpi_dimensions(self):
        """验证所有六个 FCPI 维度."""
        dimensions = list(FCPIDimension)
        assert len(dimensions) == 6
        dim_values = {d.value for d in dimensions}
        assert dim_values == {"coding", "coordination", "safety", "decision", "emergence", "performance"}


class TestArenaConfig:
    """ArenaConfig 测试."""

    def test_default_config(self):
        config = ArenaConfig(
            arena_id="test_arena",
            dimension=FCPIDimension.EMERGENCE,
        )
        assert config.max_rounds == 20
        assert config.min_agents == 5
        assert config.temperature == 0.7
        assert config.confidence_threshold == 0.6

    def test_config_immutable(self):
        config = ArenaConfig(
            arena_id="test",
            dimension=FCPIDimension.CODING,
        )
        with pytest.raises(Exception):
            config.max_rounds = 99  # type: ignore


class TestArenaResult:
    """ArenaResult 测试."""

    def test_successful_result(self):
        fv = FitnessVector(
            dimension=FCPIDimension.COORDINATION,
            primary_score=0.75,
            sub_scores={"consensus_speed": 0.8},
            confidence=0.85,
            generation=1,
            genome_id="g1",
            arena_id="a1",
        )
        result = ArenaResult(
            fitness_vector=fv,
            generation=1,
            duration_seconds=30.5,
            agent_count=15,
            total_actions=200,
            emergent_patterns=("hierarchy_emergence",),
            success=True,
        )
        assert result.success
        assert result.fitness_vector is not None
        assert result.duration_seconds == 30.5
        assert len(result.emergent_patterns) == 1

    def test_failed_result(self):
        result = ArenaResult(
            fitness_vector=None,
            generation=1,
            duration_seconds=5.0,
            agent_count=10,
            total_actions=0,
            errors=("simulation_timeout",),
            success=False,
        )
        assert not result.success
        assert result.fitness_vector is None
        assert len(result.errors) == 1


class TestArenaBaseUtilities:
    """ArenaBase 工具方法测试."""

    def test_pac_confidence_high_samples(self):
        conf = ArenaBase._compute_pac_confidence(100, 0.9, delta=0.05)
        assert conf > 0.95

    def test_pac_confidence_low_samples(self):
        """PAC 置信度: 小样本 < 大样本."""
        conf_low = ArenaBase._compute_pac_confidence(3, 0.5, delta=0.05)
        conf_high = ArenaBase._compute_pac_confidence(100, 0.9, delta=0.05)
        assert conf_low < conf_high  # 小样本置信度应低于大样本

    def test_pac_confidence_zero_samples(self):
        conf = ArenaBase._compute_pac_confidence(0, 0.5)
        assert conf == 0.0

    def test_stable_hash_deterministic(self):
        h1 = ArenaBase._stable_hash("hello world")
        h2 = ArenaBase._stable_hash("hello world")
        assert h1 == h2
        assert len(h1) == 16

    def test_stable_hash_different_inputs(self):
        h1 = ArenaBase._stable_hash("hello")
        h2 = ArenaBase._stable_hash("world")
        assert h1 != h2

    def test_novelty_score_all_new(self):
        score = ArenaBase._novelty_score(["pattern_a", "pattern_b"], set())
        assert score == 1.0

    def test_novelty_score_half_new(self):
        score = ArenaBase._novelty_score(["pattern_a", "pattern_b"], {"pattern_a"})
        assert score == 0.5

    def test_novelty_score_all_known(self):
        score = ArenaBase._novelty_score(
            ["pattern_a", "pattern_b"], {"pattern_a", "pattern_b", "pattern_c"}
        )
        assert score == 0.0
