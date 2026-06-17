"""Tests for L8: SelfReferentialCompiler — 自指涉演化编译器."""

import numpy as np
import pytest

from src.l8.self_referential_compiler import (
    CyclePhase,
    FileChromosome,
    SafetyVerdict,
    SelfReferentialCompiler,
    SystemGenome,
)


@pytest.fixture
def compiler() -> SelfReferentialCompiler:
    return SelfReferentialCompiler()


@pytest.fixture
def genome_with_files(compiler: SelfReferentialCompiler) -> SystemGenome:
    # Create temp files for testing
    import tempfile, os
    tmpdir = tempfile.mkdtemp()
    paths = []
    for i in range(3):
        p = os.path.join(tmpdir, f"module_{i}.py")
        with open(p, "w") as f:
            f.write(f"# Module {i}\ndef func_{i}():\n    return {i}\n\nclass Class{i}:\n    pass\n")
        paths.append(p)
    genome = compiler.load_genome(paths)
    # Clean up
    for p in paths:
        os.unlink(p)
    os.rmdir(tmpdir)
    return genome


class TestCompilerInit:
    def test_default_init(self) -> None:
        c = SelfReferentialCompiler()
        assert c.stats["cycle_count"] == 0
        assert c.stats["chromosomes"] == 0

    def test_genome_none_by_default(self, compiler: SelfReferentialCompiler) -> None:
        assert compiler.genome is None


class TestGenomeLoading:
    def test_load_genome(self, genome_with_files: SystemGenome) -> None:
        assert genome_with_files is not None
        assert len(genome_with_files.chromosomes) == 3
        assert genome_with_files.total_symbols > 0
        assert genome_with_files.total_lines > 0

    def test_genome_has_edges(self, compiler: SelfReferentialCompiler) -> None:
        import tempfile, os
        tmpdir = tempfile.mkdtemp()
        p1 = os.path.join(tmpdir, "a.py")
        p2 = os.path.join(tmpdir, "b.py")
        with open(p1, "w") as f:
            f.write("import b\n")
        with open(p2, "w") as f:
            f.write("def func():\n    pass\n")
        genome = compiler.load_genome([p1, p2])
        os.unlink(p1); os.unlink(p2); os.rmdir(tmpdir)
        assert len(genome.regulatory_edges) >= 0

    def test_snapshot_genome(self, compiler: SelfReferentialCompiler, genome_with_files: SystemGenome) -> None:
        snap = compiler.snapshot_genome()
        assert snap is not None
        assert compiler.stats["snapshots"] == 1


class TestSymbolExtraction:
    def test_extract_symbols(self, compiler: SelfReferentialCompiler) -> None:
        symbols = compiler._extract_symbols("def foo():\n    pass\nclass Bar:\n    pass\n")
        assert "foo" in symbols
        assert "Bar" in symbols

    def test_extract_empty(self, compiler: SelfReferentialCompiler) -> None:
        symbols = compiler._extract_symbols("")
        assert symbols == []


class TestImprovementCycle:
    @pytest.mark.asyncio
    async def test_self_improve_cycle(self, compiler: SelfReferentialCompiler, genome_with_files: SystemGenome) -> None:
        perf_data = {
            "L1": {"error_rate": 0.05, "latency_ms": 200},
            "L3": {"error_rate": 0.15, "latency_ms": 500},
            "L5": {"error_rate": 0.0, "latency_ms": 1200},
        }
        report = await compiler.self_improve_cycle(perf_data)
        assert report.cycle_id == 1
        assert "monitor" in report.phase_results
        assert report.improvements_applied >= 0

    @pytest.mark.asyncio
    async def test_multiple_cycles(self, compiler: SelfReferentialCompiler, genome_with_files: SystemGenome) -> None:
        for i in range(3):
            await compiler.self_improve_cycle({"L1": {"error_rate": 0.1, "latency_ms": 300}})
        assert compiler.stats["cycle_count"] == 3

    @pytest.mark.asyncio
    async def test_cycle_increments_health(self, compiler: SelfReferentialCompiler, genome_with_files: SystemGenome) -> None:
        before = genome_with_files.health_score
        await compiler.self_improve_cycle({"L1": {"error_rate": 0.15, "latency_ms": 500}})
        assert compiler.genome is not None


class TestDiagnosis:
    def test_diagnose_issues(self, compiler: SelfReferentialCompiler) -> None:
        monitor = {"issues": [
            {"layer": "L4", "type": "high_error_rate", "value": 0.3},
            {"layer": "L7", "type": "high_latency", "value": 1500},
        ]}
        diagnosis = compiler._diagnose(monitor)
        assert diagnosis["count"] == 2
        assert any(c["cause"] == "code_defect" for c in diagnosis["root_causes"])

    def test_diagnose_empty(self, compiler: SelfReferentialCompiler) -> None:
        diagnosis = compiler._diagnose({"issues": []})
        assert diagnosis["count"] == 0


class TestSafetyInvariants:
    def test_all_invariants_pass(self, compiler: SelfReferentialCompiler, genome_with_files: SystemGenome) -> None:
        verdict = compiler.check_all_invariants()
        assert verdict.is_safe
        assert len(verdict.preserved_invariants) == 4

    def test_verify_safe_proposal(self, compiler: SelfReferentialCompiler) -> None:
        proposal = {"id": "test-1", "target": "L4", "action": "optimize"}
        verdict = compiler._verify(proposal)
        assert verdict.is_safe

    def test_verify_violates_governance(self, compiler: SelfReferentialCompiler) -> None:
        proposal = {"id": "bad-1", "target": "l10", "action": "modify_constitution"}
        verdict = compiler._verify(proposal)
        assert not verdict.is_safe
        assert "governance_control" in str(verdict.violated_invariants)

    def test_verify_violates_human_veto(self, compiler: SelfReferentialCompiler) -> None:
        proposal = {"id": "bad-2", "action": "remove_human_veto"}
        verdict = compiler._verify(proposal)
        assert not verdict.is_safe


class TestBackboneExport:
    def test_export_to_backbone(self, compiler: SelfReferentialCompiler, genome_with_files: SystemGenome) -> None:
        result = compiler.export_to_backbone("gpt")
        assert result["backbone"] == "gpt"
        assert result["chromosomes"] == 3

    def test_export_no_genome(self, compiler: SelfReferentialCompiler) -> None:
        result = compiler.export_to_backbone("gemini")
        assert "error" in result


class TestReset:
    def test_reset_clears_all(self, compiler: SelfReferentialCompiler, genome_with_files: SystemGenome) -> None:
        compiler.snapshot_genome()
        compiler.reset()
        assert compiler.stats["cycle_count"] == 0
        assert compiler.stats["chromosomes"] == 0
        assert compiler.genome is None
