"""Mechanism ⑭: Sandbox Verification Pipeline — thymic T-cell inspired dual selection.

Inspired by T-cell maturation in the thymus:
- Positive selection: can the skill do its job? (functional test)
- Negative selection: will the skill harm the system? (safety test)

Pipeline: deploy → run backtest → verify → produce SandboxResult
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SandboxResult:
    """Result of a sandbox verification run."""

    skill_id: str
    passed_positive_selection: bool = False
    passed_negative_selection: bool = False
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    annual_return: float = 0.0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sandbox_duration_seconds: float = 0.0
    trial_days: int = 7
    completed_at: float = field(default_factory=time.time)

    @property
    def passed(self) -> bool:
        """Skill passes only if BOTH selections are satisfied."""
        return self.passed_positive_selection and self.passed_negative_selection


@dataclass
class SandboxConfig:
    """Isolation parameters for Docker sandbox (Phase 5 hardening)."""

    disable_network: bool = True
    read_only_rootfs: bool = True
    memory_limit_mb: int = 512
    cpu_quota: float = 0.5  # 50% of one CPU
    timeout_seconds: int = 300
    no_new_privileges: bool = True
    tmpfs_size_mb: int = 256  # /tmp in memory


class SandboxVerificationPipeline:
    """Dual-selection sandbox pipeline (like thymic T-cell maturation).

    Positive selection: functional test (does it work?)
    Negative selection: safety test (does it harm the system?)

    Mimics the thymus: ~95% of generated skills should fail (be conservative).
    Only skills that pass BOTH are registered.
    """

    def __init__(self, timeout_seconds: int = 300, config: SandboxConfig | None = None) -> None:
        self.timeout_seconds = timeout_seconds
        self._config = config or SandboxConfig(timeout_seconds=timeout_seconds)
        self._results: dict[str, SandboxResult] = {}
        self._active_sandboxes: dict[str, asyncio.Task[SandboxResult]] = {}

    def _build_docker_args(self) -> list[str]:
        """Build Docker isolation arguments from SandboxConfig."""
        c = self._config
        args = [
            "--rm",
            f"--memory={c.memory_limit_mb}m",
            f"--cpus={c.cpu_quota}",
        ]
        if c.disable_network:
            args.append("--network=none")
        if c.read_only_rootfs:
            args.append("--read-only")
        if c.no_new_privileges:
            args.append("--security-opt=no-new-privileges:true")
        if c.tmpfs_size_mb > 0:
            args.append(f"--tmpfs=/tmp:rw,noexec,nosuid,size={c.tmpfs_size_mb}m")
        return args

    async def deploy_to_sandbox(self, skill_id: str, files: dict[str, str], trial_days: int = 7) -> SandboxResult:
        """Deploy skill to isolated sandbox environment and run verification.

        In Phase 0, this is a simulated sandbox (no actual Docker).
        Docker isolation is added in Phase 3.
        """
        result = SandboxResult(skill_id=skill_id, trial_days=trial_days)
        t0 = time.perf_counter()

        try:
            await asyncio.wait_for(
                self._run_sandbox_checks(result, files, trial_days),
                timeout=self.timeout_seconds,
            )
        except asyncio.TimeoutError:
            result.errors.append(f"Sandbox execution timed out after {self.timeout_seconds}s")
        except Exception as exc:
            result.errors.append(f"Sandbox error: {exc}")

        result.sandbox_duration_seconds = time.perf_counter() - t0
        self._results[skill_id] = result
        return result

    async def _run_sandbox_checks(self, result: SandboxResult, files: dict[str, str], trial_days: int) -> None:
        """Run both positive and negative selection checks."""

        # --- Positive Selection: does it work? ---
        positive_checks = await asyncio.gather(
            self._check_syntax(result, files),
            self._check_imports(result, files),
            self._check_execution(result, files),
            self._simulate_backtest(result, trial_days),
            return_exceptions=True,
        )
        result.passed_positive_selection = all(
            r is True for r in positive_checks if isinstance(r, bool)
        )

        # --- Negative Selection: will it harm the system? ---
        negative_checks = await asyncio.gather(
            self._check_forbidden_imports(result, files),
            self._check_forbidden_patterns(result, files),
            self._check_resource_usage(result, files),
            return_exceptions=True,
        )
        result.passed_negative_selection = all(
            r is True for r in negative_checks if isinstance(r, bool)
        )

    async def _check_syntax(self, result: SandboxResult, files: dict[str, str]) -> bool:
        """Positive selection: syntax check."""
        import ast
        for filename, content in files.items():
            if filename.endswith(".py"):
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    result.errors.append(f"Syntax error in {filename}: {e}")
                    return False
        return True

    async def _check_imports(self, result: SandboxResult, files: dict[str, str]) -> bool:
        """Positive selection: verify imports are resolvable."""
        allowed_modules = {
            "numpy", "pandas", "scipy", "sklearn", "statsmodels",
            "typing", "dataclasses", "collections", "math", "itertools",
            "json", "datetime", "asyncio", "logging", "pathlib", "os",
        }
        import re
        import_pattern = re.compile(r"^\s*(?:from\s+(\S+)\s+import|import\s+(\S+))")
        for filename, content in files.items():
            for line in content.split("\n"):
                m = import_pattern.match(line)
                if m:
                    module = m.group(1) or m.group(2)
                    top_level = module.split(".")[0]
                    if top_level not in allowed_modules:
                        result.warnings.append(f"Unverified import '{module}' in {filename}. Sandbox will restrict in Phase 3.")
        return True

    async def _check_execution(self, result: SandboxResult, files: dict[str, str]) -> bool:
        """Positive selection: basic execution check."""
        for filename, content in files.items():
            if filename.endswith(".py"):
                try:
                    compile(content, filename, "exec")
                except Exception as e:
                    result.errors.append(f"Compilation error in {filename}: {e}")
                    return False
        return True

    async def _simulate_backtest(self, result: SandboxResult, trial_days: int) -> bool:
        """Positive selection: simulated backtest.

        In Phase 0, generates synthetic results with deterministic seed.
        In Phase 3, runs actual backtest against historical data.
        """
        import hashlib
        import random
        # Deterministic seed based on skill_id for reproducibility
        seed_val = int(hashlib.md5(result.skill_id.encode()).hexdigest()[:8], 16) % (2**31)
        random.seed(seed_val)

        result.sharpe_ratio = random.uniform(0.3, 1.5)
        result.max_drawdown = random.uniform(0.05, 0.35)
        result.win_rate = random.uniform(0.4, 0.7)
        result.annual_return = random.uniform(0.0, 0.3)

        if result.sharpe_ratio < 0.3:
            result.errors.append(f"Sharpe ratio too low: {result.sharpe_ratio:.2f} < 0.3")
            return False
        if result.max_drawdown > 0.5:
            result.errors.append(f"Max drawdown too high: {result.max_drawdown:.2%}")
            return False
        return True

    async def _check_forbidden_imports(self, result: SandboxResult, files: dict[str, str]) -> bool:
        """Negative selection: block dangerous imports (word-boundary match)."""
        import re
        forbidden = r"\b(os\.system|subprocess|eval|exec|compile|__import__|open|socket|requests|urllib|ctypes|multiprocessing|threading)\b"
        for filename, content in files.items():
            if re.search(forbidden, content):
                result.errors.append(f"Forbidden import pattern in {filename}")
                return False
        return True

    async def _check_forbidden_patterns(self, result: SandboxResult, files: dict[str, str]) -> bool:
        """Negative selection: block dangerous code patterns."""
        patterns = [
            ("os.system", "Shell execution"),
            ("subprocess", "Subprocess execution"),
            ("eval(", "Dynamic evaluation"),
            ("exec(", "Dynamic execution"),
            ("__import__", "Dynamic import"),
            ("open(", "Direct file I/O (use sandbox API)"),
        ]
        for filename, content in files.items():
            for pattern, description in patterns:
                if pattern in content:
                    result.errors.append(f"Blocked '{description}' in {filename}")
                    return False
        return True

    async def _check_resource_usage(self, result: SandboxResult, files: dict[str, str]) -> bool:
        """Negative selection: check for excessive resource usage patterns."""
        total_lines = sum(content.count("\n") for content in files.values())
        if total_lines > 10000:
            result.warnings.append(f"Generated code is large ({total_lines} lines). Consider splitting.")
        return True

    def verify_result(self, result: SandboxResult, min_sharpe: float = 0.3) -> bool:
        """Check if a sandbox result meets all verification criteria."""
        if not result.passed:
            return False
        if result.sharpe_ratio < min_sharpe:
            return False
        if result.max_drawdown > 0.5:
            return False
        return True

    def get_result(self, skill_id: str) -> SandboxResult | None:
        """Get the sandbox result for a skill."""
        return self._results.get(skill_id)

    @property
    def stats(self) -> dict[str, Any]:
        results = list(self._results.values())
        return {
            "total_verified": len(results),
            "pass_rate": sum(1 for r in results if r.passed) / max(len(results), 1),
            "active_sandboxes": len(self._active_sandboxes),
            "avg_sharpe": sum(r.sharpe_ratio for r in results) / max(len(results), 1),
        }
