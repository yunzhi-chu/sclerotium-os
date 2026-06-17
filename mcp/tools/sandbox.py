"""MCP Sandbox Tools — sandbox_execute, sandbox_verify.

Backed by kernel/sandstorm.py: L1 subprocess / L2 Docker / L3 WASM.
"""

from __future__ import annotations

from typing import Any

from mcp.server import ToolRegistry
from kernel.sandstorm import SandstormExecutor

_executor = SandstormExecutor()


async def _sandbox_execute(
    code: str, language: str = "python", isolation_level: int = 1,
    timeout_seconds: int = 30, max_memory_mb: int = 512,
) -> dict[str, Any]:
    result = await _executor.execute(
        code=code, language=language, level=isolation_level,
        timeout_seconds=timeout_seconds, max_memory_mb=max_memory_mb,
    )
    return {
        "stdout": result.stdout, "stderr": result.stderr,
        "exit_code": result.exit_code, "duration_ms": result.duration_ms,
        "isolation_level": result.isolation_level, "was_killed": result.was_killed,
    }


async def _sandbox_verify(
    code: str, checks: list[str] | None = None,
) -> list[dict[str, Any]]:
    return await _executor.verify(code)


def register_sandbox_tools(registry: ToolRegistry) -> None:
    registry.register(
        name="sandbox_execute",
        description="Execute code in isolated sandbox. L1 (subprocess, temp dir), L2 (Docker, --network=none --read-only --cap-drop=ALL), L3 (WASM, planned).",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string", "default": "python"},
                "isolation_level": {"type": "integer", "default": 1},
                "timeout_seconds": {"type": "integer", "default": 30},
                "max_memory_mb": {"type": "integer", "default": 512},
            },
            "required": ["code"],
        },
        handler=_sandbox_execute, category="sandbox",
    )
    registry.register(
        name="sandbox_verify",
        description="Static analysis: CWE-190 overflow, CWE-191 underflow, CWE-195 div-by-zero, dangerous calls.",
        parameters={
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "checks": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["code"],
        },
        handler=_sandbox_verify, category="sandbox",
    )
