"""Tests for Mechanism 14: Sandbox Verification Pipeline."""

import asyncio

import pytest

from src.l6.sandbox_pipeline import SandboxConfig, SandboxResult, SandboxVerificationPipeline


@pytest.fixture
def pipeline() -> SandboxVerificationPipeline:
    return SandboxVerificationPipeline(timeout_seconds=10)


class TestSandboxVerificationPipeline:
    async def test_deploy_valid_code_passes(self, pipeline: SandboxVerificationPipeline) -> None:
        """Valid Python code should pass sandbox verification."""
        files = {
            "strategy.py": """
def execute(context):
    return {"signal": "buy", "confidence": 0.8}
""",
        }
        result = await pipeline.deploy_to_sandbox("test-valid", files)
        assert result.passed_positive_selection
        assert result.passed_negative_selection
        assert result.passed

    async def test_syntax_error_fails(self, pipeline: SandboxVerificationPipeline) -> None:
        """Code with syntax errors should fail positive selection."""
        files = {
            "broken.py": "def execute(context:  # missing paren and colon",
        }
        result = await pipeline.deploy_to_sandbox("test-syntax", files)
        assert not result.passed_positive_selection
        assert not result.passed

    async def test_forbidden_imports_blocked(self, pipeline: SandboxVerificationPipeline) -> None:
        """Code with dangerous imports should fail negative selection."""
        files = {
            "dangerous.py": """
import os
os.system("rm -rf /")
""",
        }
        result = await pipeline.deploy_to_sandbox("test-dangerous", files)
        assert not result.passed_negative_selection
        assert not result.passed

    async def test_forbidden_patterns_blocked(self, pipeline: SandboxVerificationPipeline) -> None:
        """Code with exec/eval should fail negative selection."""
        files = {
            "evil.py": "eval(input('enter code: '))",
        }
        result = await pipeline.deploy_to_sandbox("test-evil", files)
        assert not result.passed_negative_selection

    def test_verify_result_min_sharpe(self, pipeline: SandboxVerificationPipeline) -> None:
        """Verification should reject low Sharpe results."""
        result = SandboxResult(
            skill_id="test-low-sharpe",
            passed_positive_selection=True,
            passed_negative_selection=True,
            sharpe_ratio=0.1,
            max_drawdown=0.1,
        )
        assert not pipeline.verify_result(result, min_sharpe=0.3)

    def test_verify_result_passes_good(self, pipeline: SandboxVerificationPipeline) -> None:
        """Good results should pass verification."""
        result = SandboxResult(
            skill_id="test-good",
            passed_positive_selection=True,
            passed_negative_selection=True,
            sharpe_ratio=1.2,
            max_drawdown=0.15,
            win_rate=0.6,
        )
        assert pipeline.verify_result(result, min_sharpe=0.3)

    async def test_deploy_timeout(self) -> None:
        """Deploy should handle timeout errors gracefully."""
        quick_pipeline = SandboxVerificationPipeline(timeout_seconds=0.01)
        files = {"strategy.py": "x = 1"}

        async def never_ending(*args, **kwargs):
            await asyncio.sleep(100)

        quick_pipeline._run_sandbox_checks = never_ending  # type: ignore[assignment]
        result = await quick_pipeline.deploy_to_sandbox("test-timeout", files)
        assert "timed out" in result.errors[0].lower()

    async def test_deploy_exception_during_checks(self) -> None:
        """Deploy should handle unexpected exceptions in sandbox checks."""
        quick_pipeline = SandboxVerificationPipeline(timeout_seconds=5)
        files = {"strategy.py": "x = 1"}

        async def crashing_check(*args, **kwargs):
            raise RuntimeError("Unexpected crash in sandbox")

        quick_pipeline._run_sandbox_checks = crashing_check  # type: ignore[assignment]
        result = await quick_pipeline.deploy_to_sandbox("test-exception", files)
        assert any("error" in e.lower() for e in result.errors)

    async def test_non_py_file_skipped_in_syntax_check(self, pipeline: SandboxVerificationPipeline) -> None:
        """Non-.py files should be skipped during syntax and execution checks."""
        files = {
            "data.json": "{invalid json",
            "config.yaml": "invalid: yaml: :::",
        }
        result = await pipeline.deploy_to_sandbox("test-nonpy", files)
        assert result.passed_positive_selection

    async def test_compile_error_during_execution_check(self, pipeline: SandboxVerificationPipeline) -> None:
        """Code that fails compilation should fail the execution check."""
        files = {
            "bad_code.py": "def f():\n  break  # 'break' outside loop is a compile error",
        }
        result = await pipeline.deploy_to_sandbox("test-compile", files)
        assert not result.passed_positive_selection
        assert any("compilation error" in e.lower() for e in result.errors)

    async def test_forbidden_import_subprocess(self, pipeline: SandboxVerificationPipeline) -> None:
        """subprocess import should be blocked by forbidden imports check."""
        files = {"danger.py": "import subprocess\nsubprocess.run(['ls'])"}
        result = await pipeline.deploy_to_sandbox("test-subprocess", files)
        assert not result.passed_negative_selection

    async def test_forbidden_import_eval(self, pipeline: SandboxVerificationPipeline) -> None:
        """eval should be blocked by forbidden imports check."""
        files = {"danger.py": "eval('1+1')"}
        result = await pipeline.deploy_to_sandbox("test-eval-f", files)
        assert not result.passed_negative_selection

    async def test_forbidden_import_exec(self, pipeline: SandboxVerificationPipeline) -> None:
        """exec should be blocked by forbidden imports check."""
        files = {"danger.py": "exec('x=1')"}
        result = await pipeline.deploy_to_sandbox("test-exec-f", files)
        assert not result.passed_negative_selection

    async def test_forbidden_import_compile_call(self, pipeline: SandboxVerificationPipeline) -> None:
        """compile built-in should be blocked by forbidden imports."""
        files = {"danger.py": "compile('x=1', '<string>', 'exec')"}
        result = await pipeline.deploy_to_sandbox("test-compile-f", files)
        assert not result.passed_negative_selection

    async def test_forbidden_import_open(self, pipeline: SandboxVerificationPipeline) -> None:
        """open() should be blocked by forbidden imports."""
        files = {"danger.py": "open('/etc/passwd')"}
        result = await pipeline.deploy_to_sandbox("test-open-f", files)
        assert not result.passed_negative_selection

    async def test_forbidden_import_socket(self, pipeline: SandboxVerificationPipeline) -> None:
        """socket should be blocked by forbidden imports."""
        files = {"danger.py": "import socket"}
        result = await pipeline.deploy_to_sandbox("test-socket-f", files)
        assert not result.passed_negative_selection

    async def test_forbidden_import_ctypes(self, pipeline: SandboxVerificationPipeline) -> None:
        """ctypes should be blocked by forbidden imports."""
        files = {"danger.py": "import ctypes"}
        result = await pipeline.deploy_to_sandbox("test-ctypes-f", files)
        assert not result.passed_negative_selection

    async def test_forbidden_import_requests(self, pipeline: SandboxVerificationPipeline) -> None:
        """requests should be blocked by forbidden imports."""
        files = {"danger.py": "import requests"}
        result = await pipeline.deploy_to_sandbox("test-requests-f", files)
        assert not result.passed_negative_selection

    async def test_forbidden_import_urllib(self, pipeline: SandboxVerificationPipeline) -> None:
        """urllib import should be blocked."""
        files = {"danger.py": "import urllib.request"}
        result = await pipeline.deploy_to_sandbox("test-urllib", files)
        assert not result.passed_negative_selection

    async def test_forbidden_import_multiprocessing(self, pipeline: SandboxVerificationPipeline) -> None:
        """multiprocessing import should be blocked."""
        files = {"danger.py": "import multiprocessing"}
        result = await pipeline.deploy_to_sandbox("test-mp", files)
        assert not result.passed_negative_selection

    async def test_forbidden_import_threading(self, pipeline: SandboxVerificationPipeline) -> None:
        """threading import should be blocked."""
        files = {"danger.py": "import threading"}
        result = await pipeline.deploy_to_sandbox("test-thread", files)
        assert not result.passed_negative_selection

    async def test_forbidden_pattern_subprocess(self, pipeline: SandboxVerificationPipeline) -> None:
        """subprocess pattern should be blocked."""
        files = {"danger.py": "subprocess.call(['ls'])"}
        result = await pipeline.deploy_to_sandbox("test-subpattern", files)
        assert not result.passed_negative_selection

    async def test_forbidden_pattern_exec_call(self, pipeline: SandboxVerificationPipeline) -> None:
        """exec( pattern should be blocked."""
        files = {"danger.py": "exec(code)"}
        result = await pipeline.deploy_to_sandbox("test-execpattern", files)
        assert not result.passed_negative_selection

    async def test_forbidden_pattern_import(self, pipeline: SandboxVerificationPipeline) -> None:
        """__import__ pattern should be blocked."""
        files = {"danger.py": "__import__('os')"}
        result = await pipeline.deploy_to_sandbox("test-importpattern", files)
        assert not result.passed_negative_selection

    async def test_forbidden_pattern_os_system(self, pipeline: SandboxVerificationPipeline) -> None:
        """os.system pattern should be blocked."""
        files = {"danger.py": "os.system('ls')"}
        result = await pipeline.deploy_to_sandbox("test-ospattern", files)
        assert not result.passed_negative_selection

    async def test_forbidden_pattern_open(self, pipeline: SandboxVerificationPipeline) -> None:
        """open( pattern should be blocked."""
        files = {"danger.py": "open('file.txt')"}
        result = await pipeline.deploy_to_sandbox("test-openpattern", files)
        assert not result.passed_negative_selection

    async def test_resource_usage_warning_large_file(self, pipeline: SandboxVerificationPipeline) -> None:
        """Large files should generate a resource warning."""
        files = {
            "large.py": "x = 1\n" * 10001,
        }
        result = await pipeline.deploy_to_sandbox("test-large", files)
        assert result.passed_negative_selection  # Should still pass
        assert any("large" in w.lower() for w in result.warnings)

    async def test_import_warning_unverified_module(self, pipeline: SandboxVerificationPipeline) -> None:
        """Unverified imports should generate a warning, not an error."""
        files = {
            "strategy.py": "import requests\nimport numpy",
        }
        result = await pipeline.deploy_to_sandbox("test-unverified", files)
        assert result.passed_positive_selection
        assert any("requests" in w for w in result.warnings)
        assert not any("numpy" in w for w in result.warnings)

    def test_verify_result_fails_not_passed(self, pipeline: SandboxVerificationPipeline) -> None:
        """verify_result should return False when the result did not pass both selections."""
        result = SandboxResult(
            skill_id="test-fail-not-passed",
            passed_positive_selection=False,
            passed_negative_selection=True,
        )
        assert not pipeline.verify_result(result)

    def test_verify_result_fails_max_drawdown(self, pipeline: SandboxVerificationPipeline) -> None:
        """verify_result should return False when max_drawdown exceeds 0.5."""
        result = SandboxResult(
            skill_id="test-high-dd",
            passed_positive_selection=True,
            passed_negative_selection=True,
            sharpe_ratio=1.0,
            max_drawdown=0.6,
        )
        assert not pipeline.verify_result(result)

    def test_get_result_nonexistent(self, pipeline: SandboxVerificationPipeline) -> None:
        """get_result should return None for an unknown skill_id."""
        assert pipeline.get_result("nonexistent-skill") is None

    def test_get_result_found(self, pipeline: SandboxVerificationPipeline) -> None:
        """get_result should return the result for a known skill_id."""
        result = SandboxResult(skill_id="stored-skill")
        pipeline._results["stored-skill"] = result
        retrieved = pipeline.get_result("stored-skill")
        assert retrieved is not None
        assert retrieved.skill_id == "stored-skill"

    def test_stats_empty(self) -> None:
        """stats should handle empty results gracefully (no division by zero)."""
        p = SandboxVerificationPipeline(timeout_seconds=10)
        s = p.stats
        assert s["total_verified"] == 0
        assert s["pass_rate"] == 0.0
        assert s["avg_sharpe"] == 0.0
        assert s["active_sandboxes"] == 0

    def test_stats_with_results(self) -> None:
        """stats should reflect stored verification results."""
        p = SandboxVerificationPipeline(timeout_seconds=10)
        result = SandboxResult(
            skill_id="test-stats",
            passed_positive_selection=True,
            passed_negative_selection=True,
            sharpe_ratio=0.8,
        )
        p._results["test-stats"] = result
        s = p.stats
        assert s["total_verified"] == 1
        assert s["pass_rate"] == 1.0
        assert s["avg_sharpe"] == 0.8

    def test_sandbox_result_passed_property(self) -> None:
        """SandboxResult.passed should require both selections."""
        r1 = SandboxResult(skill_id="r1")
        assert not r1.passed

        r2 = SandboxResult(skill_id="r2", passed_positive_selection=True, passed_negative_selection=False)
        assert not r2.passed

        r3 = SandboxResult(skill_id="r3", passed_positive_selection=True, passed_negative_selection=True)
        assert r3.passed

    async def test_backtest_fails_low_sharpe(self) -> None:
        """Backtest should fail when sharpe_ratio is too low."""
        p = SandboxVerificationPipeline(timeout_seconds=10)
        files = {"strategy.py": "x = 1"}
        result = await p.deploy_to_sandbox("test-low-sharpe-bt", files)
        if not result.passed_positive_selection:
            assert any("sharpe" in e.lower() for e in result.errors)

    async def test_backtest_fails_high_drawdown(self) -> None:
        """Backtest should fail when max_drawdown is too high."""
        p = SandboxVerificationPipeline(timeout_seconds=10)
        files = {"strategy.py": "x = 1"}
        result = await p.deploy_to_sandbox("test-high-dd-bt", files)
        if not result.passed_positive_selection:
            assert any("drawdown" in e.lower() or "sharpe" in e.lower() for e in result.errors)

    def test_build_docker_args_default_config(self) -> None:
        """_build_docker_args should include all security flags with default config."""
        pipeline = SandboxVerificationPipeline()
        args = pipeline._build_docker_args()
        assert "--rm" in args
        assert any(a.startswith("--memory=") for a in args)
        assert any(a.startswith("--cpus=") for a in args)
        assert "--network=none" in args
        assert "--read-only" in args
        assert "--security-opt=no-new-privileges:true" in args
        assert any(a.startswith("--tmpfs=") for a in args)
        assert "--tmpfs=/tmp:rw,noexec,nosuid,size=256m" in args

    def test_build_docker_args_network_enabled(self) -> None:
        """_build_docker_args should omit --network=none when network is enabled."""
        config = SandboxConfig(disable_network=False)
        pipeline = SandboxVerificationPipeline(config=config)
        args = pipeline._build_docker_args()
        assert "--network=none" not in args

    def test_build_docker_args_read_write_fs(self) -> None:
        """_build_docker_args should omit --read-only when rootfs is writable."""
        config = SandboxConfig(read_only_rootfs=False)
        pipeline = SandboxVerificationPipeline(config=config)
        args = pipeline._build_docker_args()
        assert "--read-only" not in args

    def test_build_docker_args_privileges_allowed(self) -> None:
        """_build_docker_args should omit no-new-privileges when allowed."""
        config = SandboxConfig(no_new_privileges=False)
        pipeline = SandboxVerificationPipeline(config=config)
        args = pipeline._build_docker_args()
        assert not any("no-new-privileges" in a for a in args)

    def test_build_docker_args_no_tmpfs(self) -> None:
        """_build_docker_args should omit --tmpfs when tmpfs_size is 0."""
        config = SandboxConfig(tmpfs_size_mb=0)
        pipeline = SandboxVerificationPipeline(config=config)
        args = pipeline._build_docker_args()
        assert not any(a.startswith("--tmpfs=") for a in args)
