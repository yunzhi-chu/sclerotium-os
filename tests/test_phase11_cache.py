"""Phase 11 Cache tests — Universal Prompt Cache Engine."""
import pytest

class TestDeltaEncoder:
    def test_identical(self):
        from kernel.cache.prompt_cache_engine import DeltaEncoder
        de = DeltaEncoder()
        de.register_reference("sys","You are a helpful assistant.")
        r = de.compute_delta("sys","You are a helpful assistant.")
        assert r["type"] == "identical"
    def test_delta_computation(self):
        from kernel.cache.prompt_cache_engine import DeltaEncoder
        de = DeltaEncoder()
        de.register_reference("block1","line1\nline2\nline3")
        r = de.compute_delta("block1","line1\nline2_new\nline3\nline4")
        assert r["type"] == "delta"
        assert len(r["insertions"]) >= 1
    def test_apply_delta(self):
        from kernel.cache.prompt_cache_engine import DeltaEncoder
        de = DeltaEncoder()
        de.register_reference("b1","hello world")
        delta = de.compute_delta("b1","hello beautiful world")
        result = de.apply_delta("b1",delta)
        assert "beautiful" in result

class TestCacheHitTracker:
    def test_record_hit_and_miss(self):
        from kernel.cache.prompt_cache_engine import CacheHitTracker
        cht = CacheHitTracker()
        cht.register_block("sys_abc","You are a helpful assistant.", 25)
        cht.record_hit("sys_abc"); cht.record_hit("sys_abc"); cht.record_miss("sys_abc")
        assert cht.hit_rate > 0
    def test_eviction(self):
        from kernel.cache.prompt_cache_engine import CacheHitTracker
        cht = CacheHitTracker()
        cht.register_block("rare_block","rare content block here", 5)
        cht._blocks["rare_block"].continuation_probability = 0.05
        evicted = cht.evict_low_probability(0.1)
        assert evicted >= 1

class TestPromptCacheEngine:
    def test_warmup(self):
        from kernel.cache.prompt_cache_engine import PromptCacheEngine
        eng = PromptCacheEngine("deepseek")
        r = eng.warmup(system_prompt="You are a helpful coding assistant.",
                       tools=[{"name":"search","description":"Search the web"}],
                       reference_docs={"api_doc":"REST API documentation here"})
        assert r["warmed_blocks"] >= 2
        assert eng._warmed_up is True
    def test_optimize_request(self):
        from kernel.cache.prompt_cache_engine import PromptCacheEngine
        eng = PromptCacheEngine("deepseek")
        eng.warmup(system_prompt="You are a helpful assistant.",
                   tools=[{"name":"code_search","description":"Search codebase"}])
        r = eng.optimize_request(
            system="You are a helpful assistant.",
            messages=[{"role":"user","content":"Find the bug in auth.py"}],
            tools=[{"name":"code_search","description":"Search codebase"}],
            user_input="Find the bug in auth.py",
        )
        assert "estimated_hit_rate" in r
        assert r["estimated_hit_rate"] >= 0.5
        assert r["cost_savings_pct"] > 0
        assert r["hit_blocks"] >= 1
    def test_compare_providers(self):
        from kernel.cache.prompt_cache_engine import PromptCacheEngine
        eng = PromptCacheEngine("deepseek")
        eng.warmup(system_prompt="You are a helpful assistant.")
        results = eng.compare_providers(
            system="You are a helpful assistant.",
            messages=[{"role":"user","content":"test"}],
        )
        assert len(results) >= 4
        # DeepSeek should be best (highest savings)
        assert results[0]["provider"] == "deepseek"
    def test_deepseek_target_hit_rate(self):
        from kernel.cache.prompt_cache_engine import PromptCacheEngine
        eng = PromptCacheEngine("deepseek")
        eng.warmup(system_prompt="You are a helpful assistant.",
                   tools=[{"name":"t1","description":"d1"},{"name":"t2","description":"d2"}])
        r = eng.optimize_request(
            system="You are a helpful assistant.",
            messages=[{"role":"user","content":"test"}],
            tools=[{"name":"t1","description":"d1"},{"name":"t2","description":"d2"}],
            user_input="test",
        )
        # With well-structured prefix, hit rate should approach target
        assert r["estimated_hit_rate"] >= 0.90
    def test_provider_switch(self):
        from kernel.cache.prompt_cache_engine import PromptCacheEngine
        eng = PromptCacheEngine("deepseek")
        eng.warmup(system_prompt="test")
        r = eng.optimize_for_provider("anthropic",system="test",messages=[])
        assert r["cache_strategy"] == "anthropic"
    def test_stats(self):
        from kernel.cache.prompt_cache_engine import PromptCacheEngine
        eng = PromptCacheEngine("deepseek")
        eng.warmup(system_prompt="test")
        eng.optimize_request(system="test",messages=[])
        s = eng.get_stats()
        assert s["warmed_up"] is True
        assert s["target_hit_rate"] == 0.98

class TestCacheMCPTools:
    def test_all_registered(self):
        from mcp.server import SclerotiumMCPServer
        s = SclerotiumMCPServer(); s.register_all_tools()
        for n in ["cache_warmup","cache_optimize","cache_compare","cache_stats"]:
            assert s.tools.get_handler(n) is not None, f"Missing: {n}"
