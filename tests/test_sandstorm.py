"""Tests for Sandstorm multi-layer sandbox."""

import pytest

from kernel.sandstorm import SandstormExecutor, ExecutionResult


@pytest.fixture
def executor():
    return SandstormExecutor()


class TestSandstormL1:
    @pytest.mark.asyncio
    async def test_execute_python(self, executor):
        result = await executor.execute("print(42)", level=1)
        assert result.isolation_level == 1
        assert "42" in result.stdout
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_execute_stderr(self, executor):
        result = await executor.execute(
            "import sys; sys.stderr.write('error!')", level=1
        )
        assert "error!" in result.stderr

    @pytest.mark.asyncio
    async def test_execute_timeout(self, executor):
        result = await executor.execute(
            "while True: pass",
            level=1,
            timeout_seconds=1,
        )
        assert result.was_killed is True

    @pytest.mark.asyncio
    async def test_execute_memory_safe(self, executor):
        result = await executor.execute("x = [1]*1000; print(len(x))", level=1)
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_cleanup_after_execution(self, executor):
        import tempfile
        import os

        result = await executor.execute(
            f"import os; print(os.getcwd())", level=1
        )
        cwd = result.stdout.strip()
        # Temp dir should be cleaned up
        assert not os.path.exists(cwd) if cwd else True


# ── Verification tests ───────────────────────────────────────────────


class TestSandstormVerify:
    @pytest.mark.asyncio
    async def test_verify_clean_code(self, executor):
        results = await executor.verify("print('hello')")
        assert all(r["passed"] for r in results)

    @pytest.mark.asyncio
    async def test_verify_dangerous_eval(self, executor):
        results = await executor.verify("eval('1+1')")
        safety = [r for r in results if "safety" in r["check"]][0]
        assert not safety["passed"]

    @pytest.mark.asyncio
    async def test_verify_division_without_guard(self, executor):
        results = await executor.verify("x = a / b")
        div_check = [r for r in results if "cwe195" in r["check"]][0]
        assert not div_check["passed"]

    @pytest.mark.asyncio
    async def test_verify_division_with_guard(self, executor):
        results = await executor.verify("if b != 0: x = a / b")
        div_check = [r for r in results if "cwe195" in r["check"]][0]
        assert div_check["passed"]

    @pytest.mark.asyncio
    async def test_verify_all_four_checks(self, executor):
        results = await executor.verify("x = 1 + 1")
        assert len(results) == 4


# ── L2/L3 tests ──────────────────────────────────────────────────────


class TestSandstormL2:
    @pytest.mark.asyncio
    async def test_l2_fallback_when_no_docker(self, executor):
        result = await executor.execute("print('test')", level=2)
        # Should either work (docker available) or report unavailable
        assert result.isolation_level == 2


class TestSandstormL3:
    @pytest.mark.asyncio
    async def test_l3_not_yet_implemented(self, executor):
        result = await executor.execute("print('test')", level=3)
        assert result.isolation_level == 3
        assert "not yet implemented" in result.stderr
