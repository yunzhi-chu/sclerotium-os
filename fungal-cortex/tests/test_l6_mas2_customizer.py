"""Tests for L6: MAS2ArchitectureCustomizer — MAS²架构定制器."""

import numpy as np
import pytest

from src.l6.mas2_architecture_customizer import (
    AgentRole,
    ArchitectureBenchmark,
    CustomArchitecture,
    MAS2ArchitectureCustomizer,
    MAS2Config,
    TaskProfile,
)


@pytest.fixture
def config() -> MAS2Config:
    return MAS2Config(min_agents_per_arch=2, max_agents_per_arch=6, rectifier_max_iterations=3)


@pytest.fixture
def customizer(config: MAS2Config) -> MAS2ArchitectureCustomizer:
    return MAS2ArchitectureCustomizer(config=config)


@pytest.fixture
def populated_customizer(customizer: MAS2ArchitectureCustomizer) -> MAS2ArchitectureCustomizer:
    for i in range(8):
        customizer.register_gene(f"gene-{i}", {"type": "function", "skill": f"skill_{i}", "quality": 0.7 + i * 0.03})
    return customizer


class TestCustomizerInit:
    def test_default_init(self) -> None:
        c = MAS2ArchitectureCustomizer()
        assert c.stats["architecture_count"] == 0
        assert c.stats["gene_pool_size"] == 0

    def test_custom_config(self, config: MAS2Config) -> None:
        c = MAS2ArchitectureCustomizer(config=config)
        assert c._config.max_agents_per_arch == 6
        assert c._config.rectifier_max_iterations == 3


class TestTaskAnalysis:
    def test_analyze_simple_task(self, customizer: MAS2ArchitectureCustomizer) -> None:
        profile = customizer.analyze_task("Summarize this article")
        assert isinstance(profile, TaskProfile)
        assert 0.0 <= profile.reasoning_depth <= 1.0
        assert 0.0 <= profile.tool_dependency <= 1.0
        assert 0.0 <= profile.complexity_score <= 1.0

    def test_analyze_complex_task(self, customizer: MAS2ArchitectureCustomizer) -> None:
        profile = customizer.analyze_task(
            "Analyze the security vulnerabilities in this distributed system and "
            "propose a comprehensive remediation plan with encryption, authentication, "
            "and audit logging across all components within the next 60 minutes"
        )
        assert profile.security_requirement >= 0.3
        assert profile.time_sensitivity >= 0.1
        assert profile.reasoning_depth >= 0.3

    def test_analyze_collaborative_task(self, customizer: MAS2ArchitectureCustomizer) -> None:
        profile = customizer.analyze_task(
            "Coordinate multiple teams to build a consensus on the architecture "
            "of the new microservices platform with parallel development streams"
        )
        assert profile.collaboration_need > 0.3

    def test_analyze_tool_heavy_task(self, customizer: MAS2ArchitectureCustomizer) -> None:
        profile = customizer.analyze_task(
            "Use the Kubernetes API to deploy Docker containers, configure the database, "
            "set up HTTP endpoints, and install monitoring tools across the cluster"
        )
        assert profile.tool_dependency > 0.2

    def test_analyze_empty_task(self, customizer: MAS2ArchitectureCustomizer) -> None:
        profile = customizer.analyze_task("")
        assert isinstance(profile, TaskProfile)
        # All dimensions should have minimal values
        assert profile.complexity_score >= 0.0

    def test_task_profile_vector(self) -> None:
        profile = TaskProfile(
            reasoning_depth=0.8, tool_dependency=0.3,
            time_sensitivity=0.5, collaboration_need=0.7, security_requirement=0.2,
        )
        vec = profile.vector
        assert vec.shape == (5,)
        assert vec[0] == 0.8


class TestArchitectureGeneration:
    def test_generate_architecture(self, populated_customizer: MAS2ArchitectureCustomizer) -> None:
        arch = populated_customizer.generate_architecture("Analyze stock market trends")
        assert isinstance(arch, CustomArchitecture)
        assert arch.architecture_id
        assert arch.role_count >= 2
        assert arch.topology in ("sequential", "parallel", "hierarchical", "hybrid")
        assert arch.estimated_quality > 0.0
        assert arch.estimated_cost_usd > 0.0
        assert arch.estimated_latency_ms > 0.0

    def test_generate_with_explicit_profile(self, populated_customizer: MAS2ArchitectureCustomizer) -> None:
        profile = TaskProfile(
            reasoning_depth=0.9, tool_dependency=0.1,
            time_sensitivity=0.3, collaboration_need=0.8, security_requirement=0.6,
        )
        arch = populated_customizer.generate_architecture("Deep research task", profile=profile)
        assert arch.task_profile == profile

    def test_generate_without_gene_pool(self, customizer: MAS2ArchitectureCustomizer) -> None:
        arch = customizer.generate_architecture("Simple task")
        assert isinstance(arch, CustomArchitecture)
        assert arch.role_count >= 2  # Should generate synthetic genes

    def test_generate_increments_count(self, populated_customizer: MAS2ArchitectureCustomizer) -> None:
        before = populated_customizer.stats["architecture_count"]
        populated_customizer.generate_architecture("Task")
        assert populated_customizer.stats["architecture_count"] == before + 1

    def test_generate_high_collaboration_task(self, populated_customizer: MAS2ArchitectureCustomizer) -> None:
        profile = TaskProfile(collaboration_need=0.9)
        arch = populated_customizer.generate_architecture("Distributed task", profile=profile)
        # High collaboration → likely hierarchical topology
        assert isinstance(arch, CustomArchitecture)

    def test_generate_high_time_sensitivity(self, populated_customizer: MAS2ArchitectureCustomizer) -> None:
        profile = TaskProfile(time_sensitivity=0.9)
        arch = populated_customizer.generate_architecture("Urgent task", profile=profile)
        assert isinstance(arch, CustomArchitecture)


class TestArchitectureRoles:
    def test_roles_have_specializations(self, populated_customizer: MAS2ArchitectureCustomizer) -> None:
        arch = populated_customizer.generate_architecture("Complex system design")
        specs = {r.specialization for r in arch.roles}
        assert len(specs) >= 1

    def test_roles_have_gene_assignments(self, populated_customizer: MAS2ArchitectureCustomizer) -> None:
        arch = populated_customizer.generate_architecture("Build API endpoint")
        for role in arch.roles:
            assert isinstance(role.capability_score, float)
            assert 0.0 <= role.capability_score <= 1.0

    def test_orchestrator_role_present(self, populated_customizer: MAS2ArchitectureCustomizer) -> None:
        arch = populated_customizer.generate_architecture("Any task")
        orchestrators = [r for r in arch.roles if r.specialization == "orchestrator"]
        assert len(orchestrators) >= 1


class TestGenePool:
    def test_register_gene(self, customizer: MAS2ArchitectureCustomizer) -> None:
        customizer.register_gene("g1", {"type": "function", "domain": "finance"})
        assert customizer.stats["gene_pool_size"] == 1

    def test_remove_gene(self, customizer: MAS2ArchitectureCustomizer) -> None:
        customizer.register_gene("g1", {})
        assert customizer.remove_gene("g1")
        assert not customizer.remove_gene("g1")

    def test_get_architecture(self, populated_customizer: MAS2ArchitectureCustomizer) -> None:
        arch = populated_customizer.generate_architecture("Test")
        retrieved = populated_customizer.get_architecture(arch.architecture_id)
        assert retrieved is not None
        assert retrieved.architecture_id == arch.architecture_id


class TestBenchmark:
    def test_benchmark_vs_baseline(self, populated_customizer: MAS2ArchitectureCustomizer) -> None:
        arch = populated_customizer.generate_architecture("Benchmark task")
        benchmark = populated_customizer.benchmark_vs_baseline(arch)
        assert isinstance(benchmark, ArchitectureBenchmark)
        assert benchmark.custom_architecture_id == arch.architecture_id
        assert benchmark.samples_evaluated > 0
        # Custom should outperform baseline
        assert benchmark.quality_improvement_pct >= 0

    def test_benchmark_with_custom_samples(self, populated_customizer: MAS2ArchitectureCustomizer) -> None:
        arch = populated_customizer.generate_architecture("Test")
        benchmark = populated_customizer.benchmark_vs_baseline(arch, samples=25)
        assert benchmark.samples_evaluated == 25


class TestRectification:
    def test_rectifier_improves_quality(self, populated_customizer: MAS2ArchitectureCustomizer) -> None:
        # Generate architectures with different rectifier settings
        populated_customizer._config.rectifier_max_iterations = 0
        arch_no_rectify = populated_customizer.generate_architecture("Test rectification")
        q_no = arch_no_rectify.estimated_quality

        populated_customizer._config.rectifier_max_iterations = 5
        populated_customizer._config.rectifier_quality_threshold = 0.0  # Always rectify
        arch_rectified = populated_customizer.generate_architecture("Test rectification")
        q_yes = arch_rectified.estimated_quality

        # Rectification should not decrease quality
        assert q_yes >= q_no * 0.9


class TestReset:
    def test_reset_clears_all(self, populated_customizer: MAS2ArchitectureCustomizer) -> None:
        populated_customizer.generate_architecture("Test")
        populated_customizer.reset()
        assert populated_customizer.stats["architecture_count"] == 0
        assert populated_customizer.stats["gene_pool_size"] == 0
        assert populated_customizer.stats["benchmark_count"] == 0
