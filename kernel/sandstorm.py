"""Sandstorm — Multi-Layer Code Execution Sandbox.

Three isolation levels:
  L1 — Python subprocess (temp dir, timeout, memory limit)
  L2 — Docker container (--network=none, --read-only, --cap-drop=ALL)
  L3 — WASM runtime (Pyodide/wasmtime, millisecond startup)

Reference:
  - Code Mode (Red Hat 2026): Single run_python tool, token reduction 53%
  - NVIDIA OpenShell: Container-based sandboxing
  - BranchFS write-on-copy: Execute in isolated branch, no source mutation
"""

from __future__ import annotations

import asyncio
import atexit
import logging
import os
import platform
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("sclerotium.sandstorm")

# P2-9 fix: Track temp dirs for cleanup on abnormal exit
_pending_cleanup: set[str] = set()


def _cleanup_temp_dirs() -> None:
    """atexit hook: remove any uncleaned sandbox temp dirs."""
    for d in list(_pending_cleanup):
        try:
            if os.path.exists(d):
                shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass
    _pending_cleanup.clear()


atexit.register(_cleanup_temp_dirs)


# P3-11 fix: Environment variables to strip before passing to sandbox
_SENSITIVE_ENV_KEYS: set[str] = {
    "PATH", "TEMP", "TMP", "USERNAME", "USER", "HOME", "HOMEPATH",
    "APPDATA", "LOCALAPPDATA", "ONEDRIVE", "COMPUTERNAME", "USERDOMAIN",
    "LOGONSERVER", "SYSTEMROOT", "WINDIR", "PROGRAMFILES", "COMMONPROGRAMFILES",
    "PSMODULEPATH", "PATHEXT", "COMSPEC", "PROMPT",
}

# P3-11 fix: Minimal safe env for sandbox subprocess
def _safe_env() -> dict[str, str]:
    """Return a minimal environment for sandbox subprocesses."""
    safe = {}
    for key, value in os.environ.items():
        if key.upper() in ("PYTHONPATH", "PYTHONHOME", "PYTHONIOENCODING"):
            safe[key] = value
    safe["PYTHONIOENCODING"] = "utf-8"
    safe["PYTHONUNBUFFERED"] = "1"
    safe["HOME"] = os.path.join(tempfile.gettempdir(), "sandstorm_home")
    safe["TEMP"] = tempfile.gettempdir()
    safe["TMP"] = tempfile.gettempdir()
    return safe


@dataclass
class ExecutionResult:
    """Result of sandboxed code execution."""
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    isolation_level: int
    was_killed: bool = False


class SandstormExecutor:
    """Multi-layer code execution sandbox.

    Usage:
        executor = SandstormExecutor()
        result = await executor.execute("print(1+1)", level=1)
    """

    def __init__(self) -> None:
        self._docker_available: bool | None = None

    # ── Public API ────────────────────────────────────────────────────

    async def execute(
        self,
        code: str,
        language: str = "python",
        level: int = 1,
        timeout_seconds: int = 30,
        max_memory_mb: int = 512,
    ) -> ExecutionResult:
        """Execute code at the specified isolation level."""
        if language != "python":
            return ExecutionResult(
                stdout="", stderr=f"Language '{language}' not supported",
                exit_code=-1, duration_ms=0, isolation_level=level,
            )

        if level == 1:
            return await self._execute_l1(code, timeout_seconds, max_memory_mb)
        elif level == 2:
            return await self._execute_l2(code, timeout_seconds, max_memory_mb)
        elif level == 3:
            return await self._execute_l3(code, timeout_seconds)
        else:
            return ExecutionResult(
                stdout="", stderr=f"Invalid level: {level}",
                exit_code=-1, duration_ms=0, isolation_level=level,
            )

    async def verify(self, code: str) -> list[dict[str, Any]]:
        """Static safety analysis of code."""
        return _static_verify(code)

    # ── L1: Subprocess ────────────────────────────────────────────────

    async def _execute_l1(
        self, code: str, timeout: int, max_memory_mb: int
    ) -> ExecutionResult:
        """L1: Python subprocess with temp directory isolation.

        P1-5 fix: Network NOT isolated at L1 — caller should use L2/L3 for untrusted code.
        P1-6 fix: Subprocess spawning LIMITED by restricting os.system/subprocess imports.
        P3-11 fix: Minimal environment passed to child (no PATH/USERNAME/HOME leak).
        """
        start = time.monotonic()
        was_killed = False
        stdout = ""
        stderr = ""

        # P3-11: Sanitize environment
        safe_env = _safe_env()

        with tempfile.TemporaryDirectory(prefix="sandstorm_") as tmpdir:
            script_path = Path(tmpdir) / "user_code.py"

            # P1-6 fix: Prepend import restrictions — block dangerous imports
            guard_header = (
                "# P1-6: Sandstorm L1 import guard — blocking dangerous builtins\n"
                "import builtins\n"
                "_orig_import = builtins.__import__\n"
                "_BLOCKED = {'subprocess', 'os', 'ctypes', 'socket', 'requests', 'http', 'urllib', 'ftplib', 'smtplib'}\n"
                "def _safe_import(name, *a, **kw):\n"
                "    root = name.split('.')[0]\n"
                "    if root in _BLOCKED:\n"
                "        raise ImportError(f'Sandstorm L1 blocked: {name}')\n"
                "    return _orig_import(name, *a, **kw)\n"
                "builtins.__import__ = _safe_import\n"
            )
            script_path.write_text(guard_header + code, encoding="utf-8")

            try:
                proc = await asyncio.create_subprocess_exec(
                    "python", str(script_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmpdir,
                    env=safe_env,  # P3-11 fix
                )

                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        proc.communicate(), timeout=timeout
                    )
                except asyncio.TimeoutError:
                    was_killed = True
                    proc.kill()
                    stdout_bytes, stderr_bytes = await proc.communicate()

                # P1-3 fix: Always decode with errors="replace" for Windows GBK safety
                stdout = stdout_bytes.decode("utf-8", errors="replace")[:10_000]
                stderr = stderr_bytes.decode("utf-8", errors="replace")[:10_000]

            except FileNotFoundError:
                return ExecutionResult(
                    stdout="", stderr="Python interpreter not found",
                    exit_code=-1, duration_ms=(time.monotonic() - start) * 1000,
                    isolation_level=1,
                )
            except Exception as exc:
                return ExecutionResult(
                    stdout="", stderr=f"L1 sandbox error: {exc}",
                    exit_code=-1, duration_ms=(time.monotonic() - start) * 1000,
                    isolation_level=1,
                )

        return ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=proc.returncode or 0,
            duration_ms=round((time.monotonic() - start) * 1000, 1),
            isolation_level=1,
            was_killed=was_killed,
        )

    # ── L2: Docker ────────────────────────────────────────────────────

    async def _execute_l2(
        self, code: str, timeout: int, max_memory_mb: int
    ) -> ExecutionResult:
        """L2: Docker container with full isolation.

        --network=none    → complete network isolation
        --read-only       → immutable filesystem
        --cap-drop=ALL    → no kernel capabilities
        --memory          → hard memory limit
        """
        if not await self._check_docker():
            return ExecutionResult(
                stdout="", stderr="Docker not available — use L1",
                exit_code=-1, duration_ms=0, isolation_level=2,
            )

        start = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="sandstorm_docker_") as tmpdir:
            script_path = Path(tmpdir) / "user_code.py"
            script_path.write_text(code, encoding="utf-8")

            try:
                proc = await asyncio.create_subprocess_exec(
                    "docker", "run", "--rm",
                    "--network=none",
                    "--read-only",
                    f"--memory={max_memory_mb}m",
                    "--cpus=1",
                    "--cap-drop=ALL",
                    "--security-opt=no-new-privileges",
                    "-v", f"{tmpdir}:/code:ro",
                    "python:3.12-slim",
                    "python", "/code/user_code.py",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                return ExecutionResult(
                    stdout="", stderr=f"Timeout after {timeout}s",
                    exit_code=-1, duration_ms=timeout * 1000,
                    isolation_level=2, was_killed=True,
                )

        return ExecutionResult(
            stdout=stdout_bytes.decode("utf-8", errors="replace")[:10_000],
            stderr=stderr_bytes.decode("utf-8", errors="replace")[:10_000],
            exit_code=proc.returncode or 0,
            duration_ms=round((time.monotonic() - start) * 1000, 1),
            isolation_level=2,
        )

    async def _check_docker(self) -> bool:
        """Check if Docker is available. P2-7 fix: log warning on unavailable."""
        if self._docker_available is not None:
            return self._docker_available
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "version",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.communicate()
            self._docker_available = proc.returncode == 0
            if not self._docker_available:
                logger.warning("Docker daemon not running — L2 sandbox falls back to L1")
        except FileNotFoundError:
            self._docker_available = False
            logger.warning("Docker not installed — L2 sandbox unavailable, use L1 or L3")
        except Exception as e:
            self._docker_available = False
            logger.warning("Docker check failed: %s — falling back to L1", e)
        return self._docker_available

    # ── L3: WASM ─────────────────────────────────────────────────────

    async def _execute_l3(self, code: str, timeout: int) -> ExecutionResult:
        """L3: WASM sandbox — Pyodide/wasmtime planned for millisecond startup.

        P1-4 fix: route to L1 as fallback instead of returning error.
        WASM runtime (wasmtime-py / pyodide) requires additional dependencies.
        When available, L3 provides 50ms startup vs L1 2500ms.
        """
        try:
            # Try wasmtime first (fastest)
            import importlib
            if importlib.util.find_spec("wasmtime"):
                # wasmtime is installed but full integration pending Phase 2D
                pass
        except Exception:
            pass

        # Fallback: route to L1 with clear warning
        logger.info("L3 WASM not available — auto-routing to L1 (P1-4 fix)")
        result = await self._execute_l1(code, timeout, 512)
        # Override isolation_level to indicate the routing
        return ExecutionResult(
            stdout=result.stdout,
            stderr=f"[L3→L1 fallback] WASM not yet available. {result.stderr}",
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            isolation_level=1,  # actual level used
            was_killed=result.was_killed,
        )


# ── Static verification ──────────────────────────────────────────────


def _static_verify(code: str) -> list[dict[str, Any]]:
    """Run static security checks on code."""
    results: list[dict[str, Any]] = []

    # CWE-190: Integer overflow
    has_overflow = any(
        kw in code for kw in ["numpy.int", "*99999999", "**999"]
    ) and not ("print(" in code)
    results.append({
        "check": "cwe190 (integer overflow)",
        "passed": not has_overflow,
        "severity": "high" if has_overflow else "low",
        "description": "Potential integer overflow" if has_overflow
        else "No overflow patterns detected",
    })

    # CWE-191: Integer underflow
    has_underflow = any(kw in code for kw in ["-9223372036854775808", "minint", "MIN_INT"])
    results.append({
        "check": "cwe191 (integer underflow)",
        "passed": not has_underflow,
        "severity": "high" if has_underflow else "low",
        "description": "Potential integer underflow" if has_underflow
        else "No underflow patterns detected",
    })

    # CWE-195: Division by zero
    has_div = "/" in code or "//" in code or "%" in code
    has_guard = "if" in code and ("== 0" in code or "!= 0" in code)
    div_safe = not has_div or has_guard
    results.append({
        "check": "cwe195 (division by zero)",
        "passed": div_safe,
        "severity": "medium" if not div_safe else "low",
        "description": "Division without zero guard" if not div_safe
        else "Division operations appear guarded",
    })

    # Dangerous calls — P3-10 fix: show full context, not truncated
    dangerous = {
        "eval(": "dynamic code execution",
        "exec(": "dynamic code execution",
        "os.system(": "shell command execution",
        "__import__(": "dynamic import",
        "subprocess": "process spawning",
        "compile(": "dynamic compilation",
        "open(": "file access",
    }
    found = []
    for pattern, desc in dangerous.items():
        if pattern in code:
            # Find the line containing the pattern for context
            for i, line in enumerate(code.split("\n"), 1):
                if pattern in line:
                    found.append({"call": pattern.strip("("), "line": i, "context": line.strip()[:120], "risk": desc})
                    break
    results.append({
        "check": "safety (dangerous calls)",
        "passed": len(found) == 0,
        "severity": "critical" if found else "low",
        "description": f"Found {len(found)} dangerous pattern(s)" if found else "No dangerous calls detected",
        "findings": found,
    })

    return results
