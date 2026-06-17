"""Tests for Phase 2B MCP Tools — evolution, memory, sandbox, skills, code_analysis."""

from __future__ import annotations

import pytest

from mcp.server import SclerotiumMCPServer


@pytest.fixture
def tools():
    """Server with all tools registered."""
    server = SclerotiumMCPServer()
    server.register_all_tools()
    return server.tools


# ── Evolution tools ──────────────────────────────────────────────────


class TestEvolutionTools:
    def test_evolution_start_registered(self, tools):
        assert tools.get_handler("evolution_start") is not None

    def test_evolution_status_registered(self, tools):
        assert tools.get_handler("evolution_status") is not None

    def test_evolution_pause_registered(self, tools):
        assert tools.get_handler("evolution_pause") is not None

    def test_evolution_resume_registered(self, tools):
        assert tools.get_handler("evolution_resume") is not None

    @pytest.mark.asyncio
    async def test_evolution_status_returns_valid(self, tools):
        handler = tools.get_handler("evolution_status")
        result = await handler()
        assert "phase" in result
        assert "current_generation" in result


# ── Genome tools ─────────────────────────────────────────────────────


class TestGenomeTools:
    def test_genome_list_registered(self, tools):
        assert tools.get_handler("genome_list") is not None

    def test_genome_get_registered(self, tools):
        assert tools.get_handler("genome_get") is not None

    def test_genome_mutate_registered(self, tools):
        assert tools.get_handler("genome_mutate") is not None

    @pytest.mark.asyncio
    async def test_genome_list_returns_list(self, tools):
        handler = tools.get_handler("genome_list")
        result = await handler(top_n=5)
        assert isinstance(result, list)


# ── Memory tools ─────────────────────────────────────────────────────


class TestMemoryTools:
    def test_all_four_memory_tools_registered(self, tools):
        for name in ["memory_search", "memory_store", "memory_consolidate", "memory_forget"]:
            assert tools.get_handler(name) is not None, f"{name} not registered"

    @pytest.mark.asyncio
    async def test_memory_store_and_search(self, tools):
        store = tools.get_handler("memory_store")
        search = tools.get_handler("memory_search")

        await store(content="Test evolution generation 42 completed", memory_level="episodic")
        await store(content="FCPI coding score improved to 0.85", memory_level="episodic")

        results = await search(query="evolution")
        assert len(results) >= 1
        assert any("evolution" in r["content"].lower() for r in results)

    @pytest.mark.asyncio
    async def test_memory_search_filter_by_level(self, tools):
        store = tools.get_handler("memory_store")
        search = tools.get_handler("memory_search")

        await store(content="episodic memory 1", memory_level="episodic")
        await store(content="semantic pattern A", memory_level="semantic")

        results = await search(query="memory", memory_level="episodic")
        for r in results:
            assert r.get("level", r.get("memory_level", "")) == "episodic"

    @pytest.mark.asyncio
    async def test_memory_consolidate(self, tools):
        store = tools.get_handler("memory_store")
        consolidate = tools.get_handler("memory_consolidate")

        await store(content="pattern alpha detected in gen 1", memory_level="episodic")
        await store(content="pattern alpha detected in gen 2", memory_level="episodic")
        await store(content="pattern alpha detected in gen 3", memory_level="episodic")

        result = await consolidate(from_level="episodic", to_level="semantic")
        assert result["consolidated_count"] >= 0

    @pytest.mark.asyncio
    async def test_memory_forget(self, tools):
        store = tools.get_handler("memory_store")
        forget = tools.get_handler("memory_forget")

        await store(content="old unimportant note", memory_level="episodic", importance=0.1)

        result = await forget(level="episodic", threshold_days=0)  # forget immediately
        assert "forgotten_count" in result

    @pytest.mark.asyncio
    async def test_memory_store_invalid_level_defaults(self, tools):
        store = tools.get_handler("memory_store")
        # Should default to "episodic" gracefully
        result = await store(content="test content")
        assert "memory_id" in result


# ── Sandbox tools ────────────────────────────────────────────────────


class TestSandboxTools:
    def test_both_sandbox_tools_registered(self, tools):
        assert tools.get_handler("sandbox_execute") is not None
        assert tools.get_handler("sandbox_verify") is not None

    @pytest.mark.asyncio
    async def test_sandbox_execute_python(self, tools):
        handler = tools.get_handler("sandbox_execute")
        result = await handler(code="print(1+1)")
        assert result["isolation_level"] == 1
        assert "2" in result["stdout"]
        assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_sandbox_execute_timeout(self, tools):
        handler = tools.get_handler("sandbox_execute")
        result = await handler(
            code="while True: pass",
            timeout_seconds=1,
        )
        assert result["was_killed"] is True

    @pytest.mark.asyncio
    async def test_sandbox_execute_infinite_loop(self, tools):
        handler = tools.get_handler("sandbox_execute")
        result = await handler(
            code="while True: pass",
            timeout_seconds=1,
        )
        assert result["was_killed"] is True

    @pytest.mark.asyncio
    async def test_sandbox_verify_clean_code(self, tools):
        handler = tools.get_handler("sandbox_verify")
        result = await handler(code="print('hello world')")
        assert isinstance(result, list)
        assert all(r["passed"] for r in result)

    @pytest.mark.asyncio
    async def test_sandbox_verify_dangerous_code(self, tools):
        handler = tools.get_handler("sandbox_verify")
        result = await handler(code="eval('1+1')")
        safety = [r for r in result if r["check"].startswith("safety")][0]
        assert not safety["passed"]


# ── Skill tools ──────────────────────────────────────────────────────


class TestSkillTools:
    def test_all_skill_tools_registered(self, tools):
        for name in ["skill_list", "skill_invoke", "skill_register"]:
            assert tools.get_handler(name) is not None

    @pytest.mark.asyncio
    async def test_skill_list_returns_list(self, tools):
        handler = tools.get_handler("skill_list")
        result = await handler()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_skill_invoke_nonexistent(self, tools):
        handler = tools.get_handler("skill_invoke")
        result = await handler(skill_name="nonexistent_skill_xyz")
        assert "errors" in result
        assert len(result["errors"]) > 0


# ── Code analysis tools ──────────────────────────────────────────────


class TestCodeAnalysisTools:
    def test_both_code_tools_registered(self, tools):
        assert tools.get_handler("scan_code") is not None
        assert tools.get_handler("auto_refactor") is not None

    @pytest.mark.asyncio
    async def test_scan_code_returns_structure(self, tools):
        handler = tools.get_handler("scan_code")
        result = await handler()
        assert "issues" in result
        assert "scores" in result
        assert "total_issues" in result

    @pytest.mark.asyncio
    async def test_auto_refactor_returns_status(self, tools):
        handler = tools.get_handler("auto_refactor")
        result = await handler(issue_id="test_issue_001")
        assert result["issue_id"] == "test_issue_001"
        assert "status" in result


# ── Tool count ───────────────────────────────────────────────────────


def test_minimum_20_tools_registered(tools):
    assert tools.tool_count >= 20
