"""Tests for model_router module — LLM routing and prompt construction."""

from __future__ import annotations

import pytest

from src.config import LLMConfig
from src.core.model_router import CognitiveDepth, ModelResponse, ModelRouter


class TestCognitiveDepth:
    def test_enum_values(self):
        assert CognitiveDepth.L1_FAST.value == 1
        assert CognitiveDepth.L2_DECIDE.value == 2
        assert CognitiveDepth.L3_DEBATE.value == 3
        assert CognitiveDepth.L4_RESEARCH.value == 4
        assert CognitiveDepth.L5_PLAN.value == 5
        assert CognitiveDepth.L6_META.value == 6

    def test_comparison(self):
        assert CognitiveDepth.L1_FAST.value < CognitiveDepth.L6_META.value


class TestModelResponse:
    def test_creation_defaults(self):
        resp = ModelResponse(content="hello", model="test-model")
        assert resp.content == "hello"
        assert resp.model == "test-model"
        assert resp.tokens_used == 0
        assert resp.latency_ms == 0.0
        assert resp.finish_reason == "stop"
        assert resp.metadata == {}

    def test_creation_full(self):
        resp = ModelResponse(
            content="hi",
            model="m1",
            tokens_used=100,
            latency_ms=250.0,
            finish_reason="length",
            metadata={"source": "cache"},
        )
        assert resp.tokens_used == 100
        assert resp.latency_ms == 250.0
        assert resp.finish_reason == "length"
        assert resp.metadata["source"] == "cache"


@pytest.fixture
def router_config():
    return LLMConfig(
        deep_think_model="deepseek-pro",
        quick_think_model="deepseek-flash",
        fallback_model="deepseek-pro",
        temperature_deep=0.3,
        temperature_quick=0.7,
        max_tokens_deep=4096,
        max_tokens_quick=1024,
    )


@pytest.fixture
def router(router_config):
    return ModelRouter(config=router_config)


class TestModelRouterSelect:
    def test_select_model_fast_depth(self, router):
        assert router.select_model(CognitiveDepth.L1_FAST) == "deepseek-flash"
        assert router.select_model(CognitiveDepth.L2_DECIDE) == "deepseek-flash"

    def test_select_model_deep_depth(self, router):
        assert router.select_model(CognitiveDepth.L3_DEBATE) == "deepseek-pro"
        assert router.select_model(CognitiveDepth.L6_META) == "deepseek-pro"

    def test_select_temperature(self, router):
        assert router.select_temperature(CognitiveDepth.L1_FAST) == 0.7
        assert router.select_temperature(CognitiveDepth.L6_META) == 0.3

    def test_select_max_tokens(self, router):
        assert router.select_max_tokens(CognitiveDepth.L1_FAST) == 1024
        assert router.select_max_tokens(CognitiveDepth.L5_PLAN) == 4096


class TestModelRouterPrompt:
    def test_build_prompt_l1(self, router):
        prompt = router.build_prompt(CognitiveDepth.L1_FAST, "sys", "user")
        assert prompt["model"] == "deepseek-flash"
        assert prompt["temperature"] == 0.7
        assert prompt["max_tokens"] == 1024
        assert prompt["system"] == "sys"
        assert "only the answer" in prompt["user"]

    def test_build_prompt_l6(self, router):
        prompt = router.build_prompt(CognitiveDepth.L6_META, "sys", "query")
        assert prompt["model"] == "deepseek-pro"
        assert "Reflect on your own reasoning" in prompt["user"]

    def test_build_prompt_l3(self, router):
        prompt = router.build_prompt(CognitiveDepth.L3_DEBATE, "sys", "query")
        lwr = prompt["user"].lower()
        assert "multiple perspectives" in lwr or "pros" in lwr

    def test_build_prompt_l4(self, router):
        prompt = router.build_prompt(CognitiveDepth.L4_RESEARCH, "sys", "query")
        assert "step by step" in prompt["user"].lower()

    def test_build_prompt_l5(self, router):
        prompt = router.build_prompt(CognitiveDepth.L5_PLAN, "sys", "query")
        assert "plan" in prompt["user"].lower()

    def test_build_prompt_with_context(self, router):
        prompt = router.build_prompt(CognitiveDepth.L1_FAST, "sys", "user", context={"key": "val"})
        assert prompt["context"] == {"key": "val"}

    def test_build_prompt_context_defaults_to_empty(self, router):
        prompt = router.build_prompt(CognitiveDepth.L1_FAST, "sys", "user")
        assert prompt["context"] == {}


class TestModelRouterTier:
    def test_model_tier_deep(self, router):
        assert router._model_tier("deepseek-pro") == "deep"

    def test_model_tier_quick(self, router):
        assert router._model_tier("deepseek-flash") == "quick"

    def test_model_tier_fallback(self, router):
        assert router._model_tier("unknown-model") == "fallback"


class TestModelRouterStats:
    def test_stats_initial(self, router):
        s = router.stats
        assert "deep" in s
        assert "quick" in s
        assert "fallback" in s
        assert s["deep"]["calls"] == 0
        assert s["deep"]["avg_latency_ms"] == 0
        assert s["deep"]["avg_tokens"] == 0

    def test_router_defaults_to_config(self):
        router = ModelRouter()
        assert router.config.deep_think_model is not None


class TestModelRouterAsync:
    @pytest.mark.asyncio
    async def test_call_raises_not_implemented(self, router):
        with pytest.raises(NotImplementedError):
            await router.call(CognitiveDepth.L1_FAST, "sys", "user")

    @pytest.mark.asyncio
    async def test_execute_call_raises(self, router):
        with pytest.raises(NotImplementedError):
            await router._execute_call(CognitiveDepth.L1_FAST, "sys", "user")

    @pytest.mark.asyncio
    async def test_execute_fallback_raises(self, router):
        with pytest.raises(NotImplementedError):
            await router._execute_fallback(CognitiveDepth.L1_FAST, "sys", "user")


class TestModelRouterEdgeCases:
    def test_model_tier_same_model_both_tiers(self):
        """When quick and deep are the same model, it matches deep first."""
        cfg = LLMConfig(
            deep_think_model="same-model",
            quick_think_model="same-model",
            fallback_model="fb",
            temperature_deep=0.5,
            temperature_quick=0.5,
            max_tokens_deep=100,
            max_tokens_quick=100,
        )
        r = ModelRouter(config=cfg)
        assert r._model_tier("same-model") == "deep"

    def test_model_tier_fallback_priority(self):
        cfg = LLMConfig(
            deep_think_model="d",
            quick_think_model="q",
            fallback_model="f",
            temperature_deep=0.5,
            temperature_quick=0.5,
            max_tokens_deep=100,
            max_tokens_quick=100,
        )
        r = ModelRouter(config=cfg)
        assert r._model_tier("f") == "fallback"


class TestModelRouterAsyncConcrete:
    """Tests that exercise the async call path with concrete implementations."""

    @pytest.fixture
    def router(self):
        cfg = LLMConfig(
            deep_think_model="deep",
            quick_think_model="quick",
            fallback_model="fallback",
            temperature_deep=0.3,
            temperature_quick=0.7,
            max_tokens_deep=100,
            max_tokens_quick=50,
        )
        return ModelRouter(config=cfg)

    @pytest.mark.asyncio
    async def test_call_success_path(self, router):
        """Test call with a working _execute_call override."""
        async def fake_execute(depth, system, user, context=None):
            return ModelResponse(content="fake response", model="deep", tokens_used=10, latency_ms=50.0)

        router._execute_call = fake_execute
        resp = await router.call(CognitiveDepth.L6_META, "sys", "user")
        assert resp.content == "fake response"
        assert resp.model == "deep"
        assert router._stats["deep"]["calls"] == 1

    @pytest.mark.asyncio
    async def test_call_fallback_path(self, router):
        """Test call: _execute_call fails → _execute_fallback succeeds."""
        async def fake_execute_fail(depth, system, user, context=None):
            raise RuntimeError("primary failed")

        async def fake_fallback(depth, system, user, context=None):
            return ModelResponse(content="fallback ok", model="fallback", tokens_used=5, latency_ms=30.0)

        router._execute_call = fake_execute_fail
        router._execute_fallback = fake_fallback
        resp = await router.call(CognitiveDepth.L1_FAST, "sys", "user")
        assert resp.content == "fallback ok"
        assert router._stats["fallback"]["calls"] == 1
        assert router._stats["quick"]["errors"] == 1

    @pytest.mark.asyncio
    async def test_call_both_fail(self, router):
        """Test call: both _execute_call and _execute_fallback fail → should raise."""
        async def always_fail(depth, system, user, context=None):
            raise RuntimeError("always fails")

        router._execute_call = always_fail
        router._execute_fallback = always_fail
        with pytest.raises(RuntimeError):
            await router.call(CognitiveDepth.L1_FAST, "sys", "user")

    @pytest.mark.asyncio
    async def test_call_with_same_fallback_as_primary(self, router):
        """When primary model IS the fallback model, fallback path uses it directly."""
        # If deep == fallback, then fallback isn't triggered separately
        router.config.fallback_model = "deep"
        async def fake_execute(depth, system, user, context=None):
            return ModelResponse(content="ok", model="deep", tokens_used=1)

        router._execute_call = fake_execute
        resp = await router.call(CognitiveDepth.L6_META, "sys", "user")
        assert resp.content == "ok"

    def test_stats_after_call(self, router):
        """Stats include avg_latency and avg_tokens calculations."""
        s = router.stats
        for tier in ("deep", "quick", "fallback"):
            assert "avg_latency_ms" in s[tier]
            assert "avg_tokens" in s[tier]
