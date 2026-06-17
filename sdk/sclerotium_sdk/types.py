"""Sclerotium SDK — type definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChatResponse:
    content: str
    tool_calls: tuple[dict[str, Any], ...] = ()
    finish_reason: str = "stop"
    model: str = ""
    tokens_used: int = 0


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    category: str = "general"


@dataclass(frozen=True)
class SessionInfo:
    session_id: str
    title: str = ""
    model: str = ""
    message_count: int = 0
    token_count: int = 0


@dataclass(frozen=True)
class StreamEvent:
    type: str
    data: Any = None


@dataclass(frozen=True)
class ToolCallResult:
    tool_name: str
    result: dict[str, Any]
    success: bool = True
    error: str = ""


@dataclass(frozen=True)
class SclerotiumConfig:
    api_key: str = ""
    base_url: str = "http://localhost:18789"
    model: str = "deepseek-v4-flash"
    timeout: float = 120.0
