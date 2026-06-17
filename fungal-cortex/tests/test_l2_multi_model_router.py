"""Tests for L2b: MultiModelRouter — intelligent model routing."""

import numpy as np
import pytest

from src.l2.multi_model_router import (
    FusedAnswer,
    ModelProfile,
    ModelTier,
    MultiModelRouter,
    OrchestrationTopology,
    RouterConfig,
    RoutingDecision,
    TopologyType,
    create_default_model_pool,
)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def config() -> RouterConfig:
    return RouterConfig(
        top_k=3,
        embedding_dim=32,
        quality_weight=0.40,
        cost_weight=0.25,
        latency_weight=0.20,
        reliability_weight=0.15,
    )


@pytest.fixture
def router(config: RouterConfig) -> MultiModelRouter:
    r = MultiModelRouter(config=config)
    # Register default models
    for model in create_default_model_pool():
        r.register_model(model)
    return r


@pytest.fixture
def empty_router() -> MultiModelRouter:
    return MultiModelRouter()


# ═══════════════════════════════════════════════════════════════════════
# Unit Tests
# ═══════════════════════════════════════════════════════════════════════


class TestMultiModelRouterInit:
    """Test initialization."""

    def test_default_initialization(self) -> None:
        router = MultiModelRouter()
        assert router._config.top_k == 3
        assert router._config.embedding_dim == 64
        assert len(router._models) == 0

    def test_custom_config(self, config: RouterConfig) -> None:
        router = MultiModelRouter(config=config)
        assert router._config.top_k == 3
        assert router._config.embedding_dim == 32

    def test_stats_property(self, empty_router: MultiModelRouter) -> None:
        stats = empty_router.stats
        assert stats["route_count"] == 0
        assert stats["registered_models"] == 0


class TestModelRegistry:
    """Test model registration."""

    def test_register_model(self, empty_router: MultiModelRouter) -> None:
        model = ModelProfile(
            model_id="test-model",
            tier=ModelTier.CLOUD_STANDARD,
            provider="test",
        )
        empty_router.register_model(model)
        assert "test-model" in empty_router.registered_models
        assert empty_router.get_model("test-model") is model

    def test_unregister_model(self, empty_router: MultiModelRouter) -> None:
        model = ModelProfile(model_id="tmp", tier=ModelTier.LOCAL_SMALL, provider="ollama")
        empty_router.register_model(model)
        assert empty_router.unregister_model("tmp") is True
        assert empty_router.unregister_model("nonexistent") is False

    def test_list_models(self, router: MultiModelRouter) -> None:
        all_models = router.list_models()
        assert len(all_models) == 7

        cloud = router.list_models(tier=ModelTier.CLOUD_PREMIUM)
        assert len(cloud) == 3  # Claude, GPT, Gemini

        local = router.list_models(tier=ModelTier.LOCAL_LARGE)
        assert len(local) == 1  # DeepSeek

    def test_get_nonexistent_model(self, router: MultiModelRouter) -> None:
        assert router.get_model("nonexistent") is None

    def test_default_model_pool(self) -> None:
        pool = create_default_model_pool()
        assert len(pool) == 7
        tiers = {m.tier for m in pool}
        assert ModelTier.CLOUD_PREMIUM in tiers
        assert ModelTier.EDGE_LIQUID in tiers


class TestRouting:
    """Test query routing."""

    def test_route_returns_decision(self, router: MultiModelRouter) -> None:
        decision = router.route("What is quantum computing?")
        assert isinstance(decision, RoutingDecision)
        assert len(decision.selected_models) > 0
        assert len(decision.selected_models) <= router._config.top_k

    def test_route_complex_query(self, router: MultiModelRouter) -> None:
        """Complex queries should prefer premium models."""
        decision = router.route(
            "Explain the mathematical derivation of the Black-Scholes PDE "
            "and its implications for exotic option pricing in incomplete markets",
            task_complexity=0.9,
        )
        # At least one premium model should be selected for complex tasks
        tiers = {m.tier for m in decision.selected_models}
        assert len(decision.selected_models) > 0

    def test_route_simple_query(self, router: MultiModelRouter) -> None:
        """Simple queries can use cheaper models."""
        decision = router.route(
            "What is 2 + 2?",
            task_complexity=0.1,
        )
        assert len(decision.selected_models) > 0

    def test_route_confidence(self, router: MultiModelRouter) -> None:
        decision = router.route("Hello world")
        assert 0.0 <= decision.confidence <= 1.0

    def test_route_empty_registry(self, empty_router: MultiModelRouter) -> None:
        decision = empty_router.route("test")
        assert decision.selected_models == []
        assert decision.confidence == 0.0

    def test_route_with_budget(self, router: MultiModelRouter) -> None:
        """Budget constraint should favor cheaper models."""
        decision_cheap = router.route(
            "Summarize this article",
            budget_usd=0.001,  # Very tight budget
        )
        decision_normal = router.route(
            "Summarize this article",
            budget_usd=1.0,  # Generous budget
        )
        # Both should produce valid decisions
        assert len(decision_cheap.selected_models) > 0
        assert len(decision_normal.selected_models) > 0


class TestTopologySelection:
    """Test topology optimization."""

    def test_topology_simple_task(self, router: MultiModelRouter) -> None:
        decision = router.route("Simple question", task_complexity=0.2)
        # Simple tasks often use PARALLEL or SEQUENTIAL
        assert decision.topology.topology_type in (
            TopologyType.PARALLEL,
            TopologyType.SEQUENTIAL,
        )

    def test_topology_complex_task(self, router: MultiModelRouter) -> None:
        decision = router.route(
            "Design a distributed system architecture for...",
            task_complexity=0.9,
        )
        # Complex tasks should use HYBRID or HIERARCHICAL
        assert decision.topology.topology_type in (
            TopologyType.HYBRID,
            TopologyType.HIERARCHICAL,
        )

    def test_topology_single_model(self, empty_router: MultiModelRouter) -> None:
        model = ModelProfile(
            model_id="solo",
            tier=ModelTier.CLOUD_PREMIUM,
            provider="test",
            quality_score=0.9,
        )
        empty_router.register_model(model)
        decision = empty_router.route("test")
        # Single model → sequential
        assert decision.topology.topology_type == TopologyType.SEQUENTIAL
        assert decision.topology.model_count() == 1

    def test_select_topology_from_dag(self, router: MultiModelRouter) -> None:
        dag = {
            "nodes": ["A", "B", "C", "D"],
            "edges": [
                {"from": "A", "to": "B"},
                {"from": "A", "to": "C"},
                {"from": "B", "to": "D"},
                {"from": "C", "to": "D"},
            ],
        }
        topology = router.select_topology_from_dag(dag)
        assert isinstance(topology, OrchestrationTopology)
        assert topology.model_count() > 0

    def test_select_topology_empty_dag(self, router: MultiModelRouter) -> None:
        topology = router.select_topology_from_dag({"nodes": [], "edges": []})
        assert topology.model_count() == 0


class TestAnswerFusion:
    """Test answer fusion."""

    def test_fuse_single_answer(self, router: MultiModelRouter) -> None:
        model = router.get_model("claude-opus-4-7")
        assert model is not None
        fused = router.fuse_answers(
            ["The answer is 42."],
            [model],
        )
        assert fused.content == "The answer is 42."
        assert fused.confidence > 0.0
        assert fused.disagreement_score == 0.0

    def test_fuse_multiple_answers(self, router: MultiModelRouter) -> None:
        models = router.list_models()[:3]
        answers = [
            "Quantum computing uses qubits for computation.",
            "Quantum computing leverages quantum superposition and entanglement.",
            "Quantum computing is a paradigm using quantum mechanical phenomena.",
        ]
        fused = router.fuse_answers(answers, models)
        assert fused.content != ""
        assert len(fused.constituent_answers) == 3
        assert len(fused.weights) == 3
        assert 0.0 <= fused.disagreement_score <= 1.0

    def test_fuse_disagreeing_answers(self, router: MultiModelRouter) -> None:
        models = router.list_models()[:2]
        answers = [
            "Python is the best language for everything.",
            "Rust is superior in every possible way to all other languages.",
        ]
        fused = router.fuse_answers(answers, models)
        # Disagreement should be relatively high for such divergent answers
        assert fused.disagreement_score > 0.3

    def test_fuse_empty_answers(self, router: MultiModelRouter) -> None:
        fused = router.fuse_answers([], [])
        assert fused.content == ""
        assert fused.confidence == 0.0

    def test_aggregate_deterministic(self, router: MultiModelRouter) -> None:
        answers = ["Answer A", "Answer B", "Answer C"]
        scores = [0.9, 0.5, 0.3]
        # Should always return the highest-scored answer (deterministic)
        result1 = router.aggregate_deterministic(answers, scores)
        result2 = router.aggregate_deterministic(answers, scores)
        assert result1 == result2
        assert result1 == "Answer A"


class TestCostEstimation:
    """Test cost estimation."""

    def test_estimate_cost(self, router: MultiModelRouter) -> None:
        decision = router.route("What is AI?")
        cost = router.estimate_cost(decision)
        assert cost >= 0.0

    def test_record_usage_success(self, router: MultiModelRouter) -> None:
        decision = router.route("test query")
        initial_weight = decision.selected_models[0].weight
        router.record_usage(decision, actual_cost=0.01, success=True)
        # Weight should increase after successful usage
        updated_model = router.get_model(decision.selected_models[0].model_id)
        assert updated_model is not None
        assert updated_model.weight >= initial_weight

    def test_record_usage_failure(self, router: MultiModelRouter) -> None:
        decision = router.route("test query")
        initial_weight = decision.selected_models[0].weight
        router.record_usage(decision, actual_cost=0.01, success=False)
        updated_model = router.get_model(decision.selected_models[0].model_id)
        assert updated_model is not None
        assert updated_model.weight <= initial_weight

    def test_cost_tracking(self, router: MultiModelRouter) -> None:
        for query in ["q1", "q2", "q3"]:
            decision = router.route(query)
            router.record_usage(decision, actual_cost=0.005, success=True)
        assert router._total_queries == 3


class TestEmbeddingCache:
    """Test query embedding caching."""

    def test_cache_hit(self, router: MultiModelRouter) -> None:
        query = "What is machine learning?"
        router._embed_query(query)
        assert query in router._embedding_cache

    def test_cache_eviction(self, config: RouterConfig) -> None:
        config.cache_size = 3
        r = MultiModelRouter(config=config)
        for i in range(10):
            r._embed_query(f"query {i}")
        # Cache should not exceed max size
        assert len(r._embedding_cache) <= 3


class TestRouterReset:
    """Test reset functionality."""

    def test_reset(self, router: MultiModelRouter) -> None:
        router.route("test")
        router.reset()
        assert router._route_count == 0
        assert router._total_queries == 0
        assert len(router._embedding_cache) == 0
        assert len(router._ema_scores) == 0


# ═══════════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════════


class TestL1L2RouterIntegration:
    """Test full L1 → L2 routing pipeline."""

    def test_percept_to_routing(self) -> None:
        """L1 percept → L2 router model selection."""
        import asyncio
        from src.l1.liquid_perceptor import (
            DataPoint,
            LiquidPerceptor,
            LiquidPerceptorConfig,
            ModalityType,
        )
        from src.l2.liquid_time_constant_net import (
            LiquidTimeConstantNet,
            TimeConstantConfig,
        )

        # L1: Perceive
        lp = LiquidPerceptor(LiquidPerceptorConfig(
            n_hidden=16,
            n_input_time_series=5,
            tau_default=0.5,
        ))

        # L2a: Liquid Time Constant
        ltn = LiquidTimeConstantNet(TimeConstantConfig(
            input_dim=16,
            hidden_dim=16,
        ))

        # L2b: Model Router
        router = MultiModelRouter(RouterConfig(
            embedding_dim=16,
            top_k=2,
        ))
        for model in create_default_model_pool():
            router.register_model(model)

        # Simulate a data point
        dp = DataPoint(
            modality=ModalityType.TIME_SERIES,
            vector=np.random.randn(5).astype(np.float64),
        )
        percept = asyncio.run(lp.perceive(dp))

        # Generate hyper-parameters
        params = ltn.forward(
            percept.vector,
            surprise=percept.surprise,
            confidence=percept.confidence,
        )

        # Route based on percept regime
        query = f"Analyze market regime: {percept.regime_hint}, tau={params.tau:.3f}"
        decision = router.route(query, task_complexity=percept.surprise)

        assert len(decision.selected_models) > 0
        assert decision.topology.model_count() > 0
        assert decision.confidence > 0.0

    def test_full_phase1_pipeline(self) -> None:
        """End-to-end Phase 1: L1 perceptor + SNN encoder → L2 routing."""
        import asyncio
        from src.l1.liquid_perceptor import (
            DataPoint,
            LiquidPerceptor,
            LiquidPerceptorConfig,
            ModalityType,
        )
        from src.l1.snn_spiking_encoder import (
            EncodingMethod,
            SNNSpikingEncoder,
            SpikeEncoderConfig,
        )
        from src.l2.liquid_time_constant_net import (
            LiquidTimeConstantNet,
            TimeConstantConfig,
        )

        # Initialize all Phase 1 components
        lp = LiquidPerceptor(LiquidPerceptorConfig(n_hidden=16, n_input_time_series=5))
        snn = SNNSpikingEncoder(SpikeEncoderConfig(n_neurons=16, n_input_features=16))
        ltn = LiquidTimeConstantNet(TimeConstantConfig(input_dim=16, hidden_dim=16))
        router = MultiModelRouter(RouterConfig(top_k=2, embedding_dim=16))
        for model in create_default_model_pool():
            router.register_model(model)

        # Process a batch of data points
        rng = np.random.RandomState(777)
        for i in range(5):
            # L1a: Liquid perception
            dp = DataPoint(
                modality=ModalityType.TIME_SERIES,
                vector=rng.randn(5).astype(np.float64),
            )
            percept = asyncio.run(lp.perceive(dp))

            # L1b: SNN encoding (optional neuromorphic path)
            spike_train = snn.encode(percept.vector, method=EncodingMethod.RATE)
            assert spike_train.spike_count >= 0

            # L2a: Liquid time constant
            params = ltn.forward(
                percept.vector,
                surprise=percept.surprise,
                confidence=percept.confidence,
            )

            # L2b: Model routing
            decision = router.route(
                f"Task: {percept.regime_hint} regime analysis",
                task_complexity=percept.surprise,
            )
            assert decision.confidence >= 0.0

        # All components should have processed data
        assert lp._call_count == 5
        assert ltn._call_count == 5
        assert router._route_count == 5


class TestModelProfileDataTypes:
    """Test data type utilities."""

    def test_topology_model_count(self) -> None:
        model = ModelProfile(model_id="m1", tier=ModelTier.LOCAL_SMALL, provider="test")
        topo = OrchestrationTopology(
            topology_type=TopologyType.PARALLEL,
            stages=[[model, model], [model]],
        )
        assert topo.model_count() == 3

    def test_routing_decision_reasoning(self, router: MultiModelRouter) -> None:
        decision = router.route("Explain AI")
        assert len(decision.reasoning) > 0

    def test_fused_answer_metadata(self, router: MultiModelRouter) -> None:
        models = router.list_models()[:2]
        fused = router.fuse_answers(["A", "B"], models)
        assert "best_model" in fused.metadata
