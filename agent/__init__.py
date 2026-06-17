"""Agent — AI brain module with native function calling + Code-as-Action.

Replaces the old shell-blind-guess approach (sclerotium.py) with:
  - LLMClient: async SSE streaming with native tool_use/function calling + retry + multi-provider
  - SessionManager: JSONL + SQLite persistent sessions with checkpoint/resume
  - CodeActionRuntime: Code-as-Action for unified reasoning+execution
"""

from agent.llm_client import LLMClient, ProviderConfig, ToolCall, LLMResponse
from agent.code_action import CodeActionRuntime, ExecutionResult
from agent.session import SessionManager, SessionInfo

__all__ = [
    "LLMClient", "ProviderConfig", "ToolCall", "LLMResponse",
    "CodeActionRuntime", "ExecutionResult",
    "SessionManager", "SessionInfo",
]
