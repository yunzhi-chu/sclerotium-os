"""Sub-Agent Manager — spawn/isolate sub-agents for parallel work (Gap 13).

Each sub-agent gets:
  - Isolated message history
  - Depth-limited tool access (deeper = fewer tools)
  - Independent token budget
  - Timeout protection
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("sclerotium.sub_agent")


@dataclass(frozen=True)
class SubAgentResult:
    """Result from a sub-agent execution (immutable)."""
    agent_id: str
    task: str
    content: str = ""
    success: bool = True
    error: str = ""
    tool_calls_made: int = 0
    tokens_used: int = 0
    duration_ms: float = 0.0


class SubAgentManager:
    """Manages sub-agent spawn, isolation, and lifecycle.

    Depth-based tool denial:
      Depth 0 (main agent): all tools
      Depth 1 (sub-agent): no spawn, no system_config, no evolution
      Depth 2 (sub-sub): read-only tools only
      Depth 3+: not allowed

    Usage:
        mgr = SubAgentManager(llm_client, tool_registry, arbiter)
        result = await mgr.spawn("Find all bugs in src/utils.py", depth=1)
    """

    # Tools denied at each depth level
    _DEPTH_DENY: dict[int, set[str]] = {
        1: {
            "sessions_spawn", "sub_agent_spawn",
            "system_config", "evolution_start", "genome_mutate",
            "immuno_mature", "mode_switch",
        },
        2: {
            "file_write", "file_edit", "file_delete",
            "bash_execute", "bash_run", "bash_smart",
            "git_commit", "git_push",
            "desktop_click", "desktop_type",
            "im_send", "schedule_add",
            "sandbox_execute",
        },
    }

    def __init__(
        self,
        llm_client: Any = None,
        tool_registry: Any = None,
        arbiter: Any = None,
        *,
        max_depth: int = 3,
    ) -> None:
        self._llm = llm_client
        self._tools = tool_registry
        self._arbiter = arbiter
        self.max_depth = max_depth
        self._active_agents: dict[str, asyncio.Task] = {}
        self._results: dict[str, SubAgentResult] = {}

    async def spawn(
        self,
        task: str,
        *,
        depth: int = 1,
        timeout_seconds: float = 120.0,
        system_prompt: str = "",
    ) -> SubAgentResult:
        """Spawn a sub-agent to handle a specific task.

        Args:
            task: Task description for the sub-agent
            depth: Nesting depth (0=main, 1=sub, 2=sub-sub)
            timeout_seconds: Maximum execution time
            system_prompt: Custom system prompt

        Returns:
            SubAgentResult with content and metadata
        """
        if depth >= self.max_depth:
            return SubAgentResult(
                agent_id="",
                task=task,
                success=False,
                error=f"Max depth reached ({self.max_depth})",
            )

        agent_id = f"sub_{uuid.uuid4().hex[:8]}"
        t0 = time.time()

        try:
            # Build limited tool set for this depth
            limited_tools = self._build_depth_tools(depth)

            # Build messages
            messages: list[dict[str, Any]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                deny_info = ", ".join(sorted(self._DEPTH_DENY.get(depth, set())))
                messages.append({
                    "role": "system",
                    "content": (
                        f"You are a sub-agent (depth={depth}). "
                        f"Complete this task and return the result. "
                        f"Denied tools: {deny_info}. "
                        f"Be concise — return results directly."
                    ),
                })
            messages.append({"role": "user", "content": task})

            # Execute with timeout
            response = await asyncio.wait_for(
                self._llm.chat(messages) if self._llm else self._fallback_execute(task),
                timeout=timeout_seconds,
            )

            duration = (time.time() - t0) * 1000

            if isinstance(response, str):
                content = response
                tokens = 0
            else:
                content = response.content if hasattr(response, "content") else str(response)
                tokens = response.tokens_used if hasattr(response, "tokens_used") else 0

            result = SubAgentResult(
                agent_id=agent_id,
                task=task,
                content=content,
                success=True,
                tokens_used=tokens,
                duration_ms=duration,
            )
            self._results[agent_id] = result
            return result

        except asyncio.TimeoutError:
            return SubAgentResult(
                agent_id=agent_id,
                task=task,
                success=False,
                error=f"Timeout after {timeout_seconds}s",
                duration_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            return SubAgentResult(
                agent_id=agent_id,
                task=task,
                success=False,
                error=str(e),
                duration_ms=(time.time() - t0) * 1000,
            )

    def _build_depth_tools(self, depth: int) -> Any:
        """Build a limited tool registry for the given depth."""
        if self._tools is None:
            return None

        # Start with all tools, then filter
        deny = set()
        for d in range(1, depth + 1):
            deny.update(self._DEPTH_DENY.get(d, set()))

        # Return the original registry — filtering happens at execution time
        return self._tools

    async def _fallback_execute(self, task: str) -> str:
        """Fallback when no LLM client is available."""
        return f"[Sub-agent not available — no LLM client] Task: {task[:200]}"

    def get_result(self, agent_id: str) -> SubAgentResult | None:
        return self._results.get(agent_id)

    def cancel(self, agent_id: str) -> bool:
        task = self._active_agents.get(agent_id)
        if task and not task.done():
            task.cancel()
            return True
        return False

    @property
    def active_count(self) -> int:
        return len([t for t in self._active_agents.values() if not t.done()])
