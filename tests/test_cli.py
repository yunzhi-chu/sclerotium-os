"""Tests for CLI/TUI layer — screens, widgets, app wiring."""

from __future__ import annotations

import pytest

from cli.widgets.fcpi_gauges import FCPIGauges
from cli.widgets.event_log import EventLog
from cli.widgets.genome_tree import GenomeTree
from cli.screens.dashboard import DashboardScreen
from cli.screens.evolution import EvolutionScreen
from cli.screens.memory import MemoryScreen
from cli.screens.repl import REPLScreen, COMMANDS


# ── FCPI Gauges ──────────────────────────────────────────────────────


class TestFCPIGauges:
    def test_init_all_zero(self):
        gauges = FCPIGauges()
        assert gauges._fcpi_total == 0.0
        for dim, _, _ in FCPIGauges.DIMENSIONS:
            assert gauges._scores[dim] == 0.0

    def test_update_scores(self):
        gauges = FCPIGauges()
        gauges.update({
            "coding": 0.82, "coordination": 0.71, "safety": 0.85,
            "decision": 0.56, "emergence": 0.48, "performance": 0.62,
        })
        assert 0.60 < gauges._fcpi_total < 0.80  # weighted sum
        assert gauges._scores["coding"] == 0.82

    def test_render_returns_panel(self):
        gauges = FCPIGauges()
        panel = gauges.render()
        assert panel is not None
        assert "FCPI" in str(panel.title)

    def test_score_clamped(self):
        gauges = FCPIGauges()
        gauges.update({"coding": 1.5, "safety": -0.3})
        assert gauges._scores["coding"] == 1.0
        assert gauges._scores["safety"] == 0.0


# ── Event Log ────────────────────────────────────────────────────────


class TestEventLog:
    def test_push_and_render(self):
        log = EventLog(max_entries=10)
        log.push("evolution.tick", "Gen 1 complete, FCPI 0.52")
        log.push("memory.stored", "Stored episodic memory")
        panel = log.render(max_rows=5)
        assert "Event Stream" in str(panel.title)

    def test_max_entries(self):
        log = EventLog(max_entries=3)
        for i in range(10):
            log.push("system.warning", f"Warning {i}")
        # Should not exceed max_entries
        assert len(log._entries) <= 3


# ── Genome Tree ──────────────────────────────────────────────────────


class TestGenomeTree:
    def test_empty_render(self):
        tree = GenomeTree()
        panel = tree.render()
        assert "No genomes" in str(panel.renderable)

    def test_update_and_render(self):
        tree = GenomeTree()
        tree.update([
            {"genome_id": "abc123", "fcpi_total": 0.85, "generation": 5, "skills": ["skill_a"]},
            {"genome_id": "def456", "fcpi_total": 0.42, "generation": 3, "skills": []},
        ])
        panel = tree.render()
        assert panel is not None
        assert "Lineage" in str(panel.title)


# ── Dashboard Screen ─────────────────────────────────────────────────


class TestDashboardScreen:
    def test_init(self):
        screen = DashboardScreen()
        assert screen.gauges is not None
        assert screen.event_log is not None

    def test_update_fcpi(self):
        screen = DashboardScreen()
        screen.update_fcpi({"coding": 0.5, "coordination": 0.6})
        assert screen.gauges._scores["coding"] == 0.5

    def test_push_event(self):
        screen = DashboardScreen()
        screen.push_event("evolution.tick", "Test event")
        assert len(screen.event_log._entries) == 1

    def test_render_compact(self):
        screen = DashboardScreen()
        status = screen.render_compact()
        assert "FCPI" in status
        assert "MCP" in status


# ── Evolution Screen ─────────────────────────────────────────────────


class TestEvolutionScreen:
    def test_init(self):
        screen = EvolutionScreen()
        assert screen._phase == "IDLE"

    def test_update(self):
        screen = EvolutionScreen()
        screen.update({
            "current_generation": 5,
            "total_generations": 10,
            "phase": "RUNNING_ARENAS",
            "fcpi_total": 0.72,
            "fcpi_vector": {"coding": 0.8, "safety": 0.7},
            "panarchy_phase": "r",
        })
        assert screen._gen_current == 5
        assert screen._phase == "RUNNING_ARENAS"
        assert len(screen._history) == 1


# ── Memory Screen ───────────────────────────────────────────────────


class TestMemoryScreen:
    def test_render_empty_results(self):
        screen = MemoryScreen()
        # Just verify no crash
        screen.render_search_results("test", [])

    def test_render_search_results(self):
        screen = MemoryScreen()
        screen.render_search_results("test", [
            {"content": "test memory", "memory_level": "episodic", "score": 0.95, "id": "mem_001"},
        ])


# ── REPL Screen ──────────────────────────────────────────────────────


class TestREPLScreen:
    def test_parse_command_simple(self):
        repl = REPLScreen()
        cmd, args = repl.parse_command("/evolve 10")
        assert cmd == "/evolve"
        assert args == ["10"]

    def test_parse_command_no_args(self):
        repl = REPLScreen()
        cmd, args = repl.parse_command("/status")
        assert cmd == "/status"
        assert args == []

    def test_parse_command_empty(self):
        repl = REPLScreen()
        cmd, args = repl.parse_command("")
        assert cmd == ""

    def test_commands_defined(self):
        assert "/help" in COMMANDS
        assert "/evolve" in COMMANDS
        assert "/status" in COMMANDS
        assert "/memory" in COMMANDS
        assert "/quit" in COMMANDS
        assert len(COMMANDS) >= 13


# ── CLI App ──────────────────────────────────────────────────────────


class TestCLIApp:
    def test_instantiation(self):
        from cli.app import SclerotiumCLI
        cli = SclerotiumCLI()
        assert cli.mcp.tools.tool_count >= 20
        assert cli.dashboard is not None
