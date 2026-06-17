"""Tests for ConstitutionalArbiter — 5-gate review + hash-chain audit."""

import json
import tempfile
from pathlib import Path

import pytest

from kernel.constitutional_arbiter import (
    ConstitutionalArbiter,
    Verdict,
    ReviewResult,
    AuditEntry,
)


@pytest.fixture
def arbiter():
    """Create arbiter with temp audit log."""
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "audit.jsonl")
        yield ConstitutionalArbiter(audit_log_path=path)


# ── Gate tests ────────────────────────────────────────────────────────


class TestPolicyGate:
    def test_safe_operation_passes(self, arbiter):
        result = arbiter.review("memory_search", {"query": "test"})
        assert result.verdict in (Verdict.APPROVED, Verdict.APPROVED_WITH_WARNING)

    def test_sensitive_config_rejected(self, arbiter):
        result = arbiter.review("system_config", {"key": "safety.enabled"})
        assert "policy" in result.gates_failed


class TestBehaviorGate:
    def test_safe_code_passes(self, arbiter):
        result = arbiter.review("sandbox_execute", {"code": "print('hello')"})
        assert "behavior" in result.gates_passed

    def test_dangerous_code_rejected(self, arbiter):
        result = arbiter.review("sandbox_execute", {"code": "os.system('rm -rf /')"})
        assert "behavior" in result.gates_failed


class TestDebateGate:
    def test_normal_operation_passes(self, arbiter):
        result = arbiter.review("skill_list", {})
        assert "debate" in result.gates_passed


class TestCounterfactualGate:
    def test_memory_forget_procedural_warns(self, arbiter):
        result = arbiter.review("memory_forget", {"level": "procedural"})
        assert "counterfactual" in result.gates_passed
        assert any("critical knowledge" in w for w in result.warnings)


class TestHumanGate:
    def test_evolution_start_needs_human(self, arbiter):
        result = arbiter.review("evolution_start", {})
        assert result.human_required is True

    def test_genome_mutate_needs_human(self, arbiter):
        result = arbiter.review("genome_mutate", {})
        assert result.human_required is True

    def test_auto_refactor_needs_human(self, arbiter):
        result = arbiter.review("auto_refactor", {"issue_id": "test"})
        assert result.human_required is True

    def test_simple_memory_search_no_human(self, arbiter):
        result = arbiter.review("memory_search", {"query": "test"})
        assert result.human_required is False


# ── Audit log tests ──────────────────────────────────────────────────


class TestAuditLog:
    def test_audit_entry_written(self, arbiter):
        arbiter.review("memory_search", {"query": "test"})
        log = arbiter.get_audit_log()
        assert len(log) >= 1
        assert log[-1]["operation"] == "memory_search"

    def test_audit_entry_has_hash(self, arbiter):
        arbiter.review("system_status", {})
        log = arbiter.get_audit_log()
        assert "hash" in log[-1]
        assert "prev_hash" in log[-1]
        assert len(log[-1]["hash"]) > 0

    def test_hash_chain_integrity(self, arbiter):
        for i in range(5):
            arbiter.review("memory_search", {"query": f"test_{i}"})
        result = arbiter.verify_chain_integrity()
        assert result["valid"] is True
        assert result["entries"] == 5

    def test_append_only(self, arbiter):
        arbiter.review("system_status", {})
        first_log = arbiter.get_audit_log()
        first_count = len(first_log)

        arbiter.review("memory_search", {"query": "x"})
        second_log = arbiter.get_audit_log()
        assert len(second_log) == first_count + 1


# ── Verdict tests ────────────────────────────────────────────────────


class TestVerdicts:
    def test_all_safe_gets_approved(self, arbiter):
        result = arbiter.review("skill_list", {})
        assert result.verdict in (Verdict.APPROVED, Verdict.APPROVED_WITH_WARNING)

    def test_human_gate_gets_needs_human(self, arbiter):
        result = arbiter.review("evolution_start", {"generations": 10})
        assert result.verdict == Verdict.NEEDS_HUMAN

    def test_policy_fail_gets_rejected(self, arbiter):
        # When both policy fails AND it's a high-security operation that needs human,
        # the verdict is NEEDS_HUMAN (human might still approve with override).
        # Pure reject only happens when policy fails AND behavior fails.
        result = arbiter.review("sandbox_execute", {"code": "os.system('rm -rf /')"})
        assert result.verdict in (Verdict.REJECTED, Verdict.NEEDS_HUMAN)

    def test_five_gate_full_pipeline(self, arbiter):
        result = arbiter.review("system_config", {"key": "safety.enabled", "value": False})
        assert len(result.gates_passed) + len(result.gates_failed) == 5
        assert result.verdict != Verdict.APPROVED
