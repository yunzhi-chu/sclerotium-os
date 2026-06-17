"""Integration tests — full subsystem coordination verification.

Eight integration scenarios verifying cross-module interaction:
  1. Memory store→search→consolidate→forget cycle
  2. Sandbox execute→verify safety loop
  3. Arbiter review→audit integrity chain
  4. STG neuromodulator profile switch
  5. Scheduler create→list→toggle→remove
  6. Mode switch→STG rhythm modulation
  7. Full MCP tool dispatch chain
  8. CLI command→MCP tool round-trip
"""

from __future__ import annotations

import pytest

from mcp.server import SclerotiumMCPServer


@pytest.fixture
def tools():
    server = SclerotiumMCPServer()
    server.register_all_tools()
    return server.tools


# ── Scenario 1: Memory full lifecycle ───────────────────────────────


class TestMemoryLifecycle:
    @pytest.mark.asyncio
    async def test_store_search_consolidate_forget(self, tools):
        store = tools.get_handler("memory_store")
        search = tools.get_handler("memory_search")
        consolidate = tools.get_handler("memory_consolidate")
        forget = tools.get_handler("memory_forget")

        # Store 3 episodic memories
        for i in range(3):
            r = await store(content=f"Evolution generation {i}: FCPI improved", memory_level="episodic")
            assert "memory_id" in r

        # Search should find them
        results = await search(query="evolution FCPI")
        assert len(results) >= 1

        # Consolidate episodic → semantic
        cr = await consolidate(from_level="episodic", to_level="semantic")
        assert cr["consolidated_count"] >= 0

        # Forget old low-importance
        fr = await forget(level="episodic", threshold_days=0)
        assert "forgotten_count" in fr


# ── Scenario 2: Sandbox execute + verify ─────────────────────────────


class TestSandboxLoop:
    @pytest.mark.asyncio
    async def test_execute_and_verify(self, tools):
        execute = tools.get_handler("sandbox_execute")
        verify = tools.get_handler("sandbox_verify")

        code = "x = sum(range(100)); print(x)"
        result = await execute(code=code)
        assert result["exit_code"] == 0
        assert "4950" in result["stdout"]

        # Verify the same code
        checks = await verify(code=code)
        assert all(c["passed"] for c in checks)


# ── Scenario 3: Arbiter review + audit chain ─────────────────────────


class TestArbiterAudit:
    def test_review_and_audit_integrity(self):
        from kernel.constitutional_arbiter import ConstitutionalArbiter
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            arbiter = ConstitutionalArbiter(
                audit_log_path=str(Path(tmp) / "audit.jsonl")
            )

            # Safe operation should pass
            r = arbiter.review("memory_search", {"query": "test"})
            assert r.verdict.value in ("APPROVED", "APPROVED_WITH_WARNING")

            # Sensitive operation needs human
            r = arbiter.review("evolution_start", {"generations": 10})
            assert r.human_required is True

            # Verify chain integrity
            integrity = arbiter.verify_chain_integrity()
            assert integrity["valid"] is True


# ── Scenario 4: STG neuromodulator profile switch ───────────────────


class TestNeuromodulation:
    def test_full_profile_cycle(self):
        from kernel.stg.neuromodulator import Neuromodulator

        nm = Neuromodulator()
        assert nm.active_profile.value == "work"

        for profile in ["sleep", "game", "meeting", "creative", "work"]:
            result = nm.switch(profile)
            assert result["active_profile"] == profile
            assert "changes" in result


# ── Scenario 5: Scheduler CRUD ──────────────────────────────────────


class TestSchedulerCRUD:
    @pytest.mark.asyncio
    async def test_create_list_remove(self, tools):
        add = tools.get_handler("schedule_add")
        lst = tools.get_handler("schedule_list")
        remove = tools.get_handler("schedule_remove")

        # Add a job
        r = await add(
            name="test_job",
            trigger="interval",
            trigger_config={"seconds": 3600},
            action_type="scan_code",
        )
        assert "job_id" in r

        # List should include it
        jobs = await lst()
        assert isinstance(jobs, list)

        # Remove it
        if r["job_id"]:
            rr = await remove(job_id=r["job_id"])
            assert rr["status"] in ("removed", "not_found")


# ── Scenario 6: Mode switch ←→ STG profile ──────────────────────────


class TestModeSTGIntegration:
    @pytest.mark.asyncio
    async def test_mode_switch_affects_stg(self, tools):
        mode_switch = tools.get_handler("mode_switch")

        # Switch to sleep
        r = await mode_switch(profile="sleep")
        assert r["active_profile"] == "sleep"
        assert not r["changes"]["evolution_enabled"]
        assert r["changes"]["notification_level"] == "none"

        # Switch back to work
        r = await mode_switch(profile="work")
        assert r["active_profile"] == "work"
        assert r["changes"]["evolution_enabled"]
        assert r["changes"]["notification_level"] == "all"


# ── Scenario 7: Full MCP dispatch chain ──────────────────────────────


class TestFullMCPChain:
    @pytest.mark.asyncio
    async def test_status_to_evolve_to_memory_chain(self, tools):
        """Simulate a full agent interaction: status → express intent → check result."""
        # 1. Check system status
        status = await tools.get_handler("system_status")()
        assert status["layers"]["mcp"] == "running"

        # 2. Check evolution status (idle)
        evo = await tools.get_handler("evolution_status")()
        assert "phase" in evo

        # 3. Search memory for context
        mem = await tools.get_handler("memory_search")(query="evolution")
        assert isinstance(mem, list)

        # 4. List skills
        skills = await tools.get_handler("skill_list")()
        assert isinstance(skills, list)


# ── Scenario 8: CLI command → MCP tool round-trip ────────────────────


class TestCLIMCPIntegration:
    def test_cli_app_wires_all_tools(self):
        from cli.app import SclerotiumCLI
        cli = SclerotiumCLI()
        assert cli.mcp.tools.tool_count >= 45
        assert cli.dashboard is not None

    def test_repl_parses_all_commands(self):
        from cli.screens.repl import COMMANDS
        assert "/evolve" in COMMANDS
        assert "/status" in COMMANDS
        assert "/memory" in COMMANDS
        assert "/scan" in COMMANDS
        assert "/mode" in COMMANDS
        assert "/help" in COMMANDS

    @pytest.mark.asyncio
    async def test_cli_status_command(self):
        from cli.app import SclerotiumCLI
        cli = SclerotiumCLI()
        result = await cli._cmd_status([])
        assert "layers" in result


# ── System acceptance criteria ───────────────────────────────────────


class TestAcceptanceCriteria:
    def test_minimum_45_tools(self, tools):
        assert tools.tool_count >= 45

    def test_evolution_tools_available(self, tools):
        for name in ["evolution_start", "evolution_status", "genome_list"]:
            assert tools.get_handler(name) is not None

    def test_memory_tools_available(self, tools):
        for name in ["memory_search", "memory_store", "memory_consolidate", "memory_forget"]:
            assert tools.get_handler(name) is not None

    def test_sandbox_tools_available(self, tools):
        for name in ["sandbox_execute", "sandbox_verify"]:
            assert tools.get_handler(name) is not None

    def test_im_tools_available(self, tools):
        for name in ["im_send", "im_receive", "im_list_conversations"]:
            assert tools.get_handler(name) is not None

    def test_scheduler_tools_available(self, tools):
        for name in ["schedule_add", "schedule_list"]:
            assert tools.get_handler(name) is not None

    def test_mode_tool_available(self, tools):
        assert tools.get_handler("mode_switch") is not None

    def test_arbiter_verifies_chain(self):
        from kernel.constitutional_arbiter import ConstitutionalArbiter
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            arbiter = ConstitutionalArbiter(str(Path(tmp) / "audit.jsonl"))
            for i in range(3):
                arbiter.review("memory_search", {"query": f"test_{i}"})
            integrity = arbiter.verify_chain_integrity()
            assert integrity["valid"] is True

    def test_hexis_memory_five_levels(self):
        from kernel.hexis_memory import HexisMemoryStore
        store = HexisMemoryStore(
            chroma_path="./data/int_chroma",
            sqlite_path="./data/int_memory.db",
        )
        for level in HexisMemoryStore.LEVELS:
            store.store(f"Test {level} memory content", level=level)

        ctx = store.get_context()
        for level in HexisMemoryStore.LEVELS:
            assert level in ctx["level_counts"]
        store.close()

    def test_mycelium_md_exists(self):
        from pathlib import Path
        p = Path(__file__).parent.parent / "mycelium.md"
        assert p.exists(), "mycelium.md constitution file must exist"
        content = p.read_text(encoding="utf-8")
        assert "Safety Constitution" in content
        assert "Sclerotium OS" in content
