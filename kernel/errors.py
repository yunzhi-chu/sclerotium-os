"""Structured Error Hierarchy — 替代 except:pass (Gap 23).

Every error type has: error code, user-friendly message, HTTP status, recovery hint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class SclerotiumError(Exception):
    """Base error for all Sclerotium OS exceptions."""
    code: str = "E0000"
    status: int = 500
    hint: str = ""

    def __init__(self, message: str = "", *, detail: str = "", **kwargs: Any) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail
        self.context: dict[str, Any] = kwargs

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "detail": self.detail,
            "hint": self.hint,
        }


# ── Tool errors (E1xxx) ───────────────────────────────────────────────────

class ToolNotFoundError(SclerotiumError):
    code = "E1001"; status = 404
    hint = "Use /tools to list available tools"

class ToolExecutionError(SclerotiumError):
    code = "E1002"; status = 500
    hint = "Check tool arguments and try again"

class ToolPermissionError(SclerotiumError):
    code = "E1003"; status = 403
    hint = "This tool requires higher permission level"

class ToolTimeoutError(SclerotiumError):
    code = "E1004"; status = 504
    hint = "Tool took too long. Try with a smaller scope."


# ── LLM errors (E2xxx) ────────────────────────────────────────────────────

class LLMConnectionError(SclerotiumError):
    code = "E2001"; status = 502
    hint = "Check API key and network. Provider may be down."

class LLMRateLimitError(SclerotiumError):
    code = "E2002"; status = 429
    hint = "Rate limited. Wait and retry, or switch provider."

class LLMTokenLimitError(SclerotiumError):
    code = "E2003"; status = 400
    hint = "Context too long. Use /compact or reduce history."

class LLMResponseError(SclerotiumError):
    code = "E2004"; status = 502
    hint = "LLM returned malformed response. Retry or switch model."


# ── Session errors (E3xxx) ────────────────────────────────────────────────

class SessionNotFoundError(SclerotiumError):
    code = "E3001"; status = 404
    hint = "Session not found. Use /sessions to list."

class SessionCorruptedError(SclerotiumError):
    code = "E3002"; status = 500
    hint = "Session data is corrupted. Start a new session."


# ── Memory errors (E4xxx) ─────────────────────────────────────────────────

class MemoryStoreError(SclerotiumError):
    code = "E4001"; status = 500
    hint = "Memory store unavailable. Memories will not be persisted."


# ── System errors (E5xxx) ─────────────────────────────────────────────────

class ConfigError(SclerotiumError):
    code = "E5001"; status = 500
    hint = "Configuration error. Check environment variables."

class PlatformNotSupportedError(SclerotiumError):
    code = "E5002"; status = 501
    hint = "This feature is not available on your platform."

class OrganHealthError(SclerotiumError):
    code = "E5003"; status = 500
    hint = "An organ is unhealthy. Check /status for details."


# ── Safe execution helper ─────────────────────────────────────────────────

@dataclass(frozen=True)
class SafeResult:
    """Result of safe_execute — always returns, never raises."""
    success: bool
    value: Any = None
    error: SclerotiumError | None = None

    @property
    def ok(self) -> bool:
        return self.success


def safe_execute(fn, *args, error_code: str = "E0000", **kwargs) -> SafeResult:
    """Execute a function safely — NEVER raises. Replaces except:pass patterns.

    Usage:
        result = safe_execute(memory.store, content="...", level="episodic")
        if not result.ok:
            logger.warning("Memory store failed: %s", result.error.message)
    """
    try:
        return SafeResult(success=True, value=fn(*args, **kwargs))
    except SclerotiumError as e:
        return SafeResult(success=False, error=e)
    except Exception as e:
        return SafeResult(
            success=False,
            error=SclerotiumError(str(e), code=error_code),
        )
