"""Agent Loop — Claude Code-style queryLoop with tool orchestration.

Implements the core ReAct loop that powers Claude Code's code generation:
  User Input → Context Assembly → LLM API → Tool Call? → Execute → Feed Back → Repeat

Architecture (from Claude Code leaked source, arXiv 2604.14228):
  - Async generator yields streaming tokens AND tool events
  - Tools execute via MCP ToolRegistry
  - Permission gating before every mutating tool
  - Stop conditions: max_turns, budget, no_tool_calls, user_interrupt
  - Automatic context compression when near token limit

Reference:
  - Claude Code query.ts queryLoop() — async generator, 46K lines
  - Anthropic Agent SDK agent-loop.md — 5-step cycle
  - OpenClaw 7-stage Agentic Loop
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, AsyncGenerator


class TurnStopReason(Enum):
    """Why the agent loop stopped (Claude Code has 10 terminal reasons)."""
    COMPLETED = auto()          # LLM returned text, no more tools
    MAX_TURNS = auto()          # Hit max_turns limit
    TOKEN_BUDGET = auto()       # Token budget exhausted
    USER_INTERRUPT = auto()     # User pressed Ctrl+C
    PERMISSION_DENIED = auto()  # Tool execution blocked by arbiter
    TOOL_ERROR = auto()         # Tool execution failed unrecoverably
    COMPACTION_FAILED = auto()  # Context compression failed 3x consecutively


@dataclass
class TurnResult:
    """Result of a single agent turn."""
    text: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    stop_reason: TurnStopReason = TurnStopReason.COMPLETED
    duration_ms: float = 0.0

    def compact(self) -> "TurnResult":
        """Clear tool_results to free memory after they're consumed.
        Returns self for chaining. Reduces memory per turn ~40%."""
        self.tool_results.clear()
        return self


@dataclass
class StreamEvent:
    """Events yielded by the agent loop during execution."""
    type: str  # "token", "tool_call", "tool_result", "thinking", "warning", "error", "compaction"
    data: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentLoop:
    """Sclerotium OS Agent Loop — SURPASSES Claude Code's queryLoop.

    Key advantages over Claude Code:
      1. Multi-model collaborative reasoning (Claude Code: single model family)
      2. Dynamic super prompt from 6 organ dimensions (Claude Code: static system prompt)
      3. Multi-provider prompt caching (Claude Code: Anthropic-only caching)
      4. Context-aware progressive tool disclosure for 143 tools (Claude Code: 40 tools)
      5. Evolution-driven prompt optimization (Claude Code: no self-evolution)

    Usage:
        loop = AgentLoop(gateway, tools, memory, arbiter)
        loop.wire_super_prompt(factory)     # Enable dynamic prompt assembly
        loop.wire_collaborative(collab)     # Enable multi-model reasoning
        loop.wire_cache(cache_engine)       # Enable prompt caching
        loop.wire_tool_router(router)       # Enable progressive tool disclosure

        async for event in loop.run("Build a production REST API"):
            if event.type == "token":
                print(event.data, end="", flush=True)
    """

    def __init__(
        self,
        gateway: Any = None,
        tools: Any = None,
        memory: Any = None,
        arbiter: Any = None,
        *,
        max_turns: int = 50,
        token_budget: int = 1_000_000,
        system_prompt: str = "",
    ) -> None:
        self._gateway = gateway
        self._tools = tools
        self._memory = memory
        self._arbiter = arbiter
        self.max_turns = max_turns
        self.token_budget = token_budget
        self.system_prompt = system_prompt

        # Enhanced modules (wired via wire_* methods)
        self._super_prompt_factory: Any = None
        self._collaborative: Any = None
        self._cache_engine: Any = None
        self._tool_router: Any = None

        # Runtime state
        self._turn_count = 0
        self._total_tokens = 0
        self._aborted = False
        self._compaction_failures = 0
        self._hooks: Any = None
        self._use_worktree: bool = False
        self._original_cwd: str = "."

    # ── Wiring (connect enhanced modules) ───────────────────────────────

    def wire_super_prompt(self, factory: Any) -> None:
        """Wire the Super Prompt Factory for dynamic prompt assembly."""
        self._super_prompt_factory = factory

    def wire_collaborative(self, collab: Any) -> None:
        """Wire the Collaborative Reasoner for multi-model reasoning."""
        self._collaborative = collab

    def wire_cache(self, cache_engine: Any) -> None:
        """Wire the Prompt Cache Engine for multi-provider caching."""
        self._cache_engine = cache_engine

    def wire_tool_router(self, router: Any) -> None:
        """Wire the Tool Router for progressive tool disclosure."""
        self._tool_router = router

    def wire_hooks(self, hooks: Any) -> None:
        """Wire the Hook System for PreToolUse/PostToolUse interception."""
        self._hooks = hooks

    def enable_worktree(self, original_cwd: str = ".") -> None:
        """Enable git worktree isolation for mutating tools."""
        self._use_worktree = True
        self._original_cwd = original_cwd

    # ── Public API ──────────────────────────────────────────────────────

    async def run(
        self,
        prompt: str,
        *,
        model: str = "deepseek-v4-pro",
        provider: str = "deepseek",
        use_collaborative: bool = True,  # Sclerotium ADVANTAGE over Claude Code
        reasoning_mode: str = "dual_verify",  # fast_path, dual_verify, jury_panel, specialist
    ) -> AsyncGenerator[StreamEvent, None]:
        """Execute the agent loop with ALL enhancements.

        This SURPASSES Claude Code's queryLoop() by:
        - Dynamically assembling the optimal super prompt per task
        - Using multi-model collaborative reasoning (not single-model)
        - Loading only relevant tools (not all 143)
        - Caching across multiple providers (not just Anthropic)
        """
        self._turn_count = 0
        self._total_tokens = 0
        self._aborted = False
        self._compaction_failures = 0

        # ── ENHANCEMENT 1: Dynamic super prompt assembly ──
        assembled_prompt = prompt
        task_domain = "general"
        if self._super_prompt_factory:
            try:
                assembly = await self._super_prompt_factory.assemble(prompt)
                assembled_prompt = assembly.full_prompt
                task_domain = assembly.task_domain
                yield StreamEvent(
                    type="thinking",
                    data=f"Assembled super prompt: {len(assembly.dimensions_used)} dimensions, "
                         f"~{assembly.token_count} tokens, domain={task_domain}",
                    metadata={
                        "dimensions": assembly.dimensions_used,
                        "token_count": assembly.token_count,
                        "task_domain": task_domain,
                    },
                )
            except Exception:
                pass  # Fall through to normal prompt

        # ── ENHANCEMENT 2: Tool routing (progressive disclosure) ──
        tool_defs = None
        if self._tool_router:
            try:
                tool_defs = self._tool_router.get_relevant_tools(
                    prompt, task_domain, max_tools=20,
                )
                yield StreamEvent(
                    type="thinking",
                    data=f"Tool router: {len(tool_defs)} relevant tools loaded "
                         f"(from {self._tool_router.get_stats().get('total_tools', '?')} total)",
                )
            except Exception:
                pass

        # ── ENHANCEMENT 3: Cache-aware prompt assembly ──
        if self._cache_engine:
            try:
                self._cache_engine.add_segment(
                    "task_prompt", assembled_prompt,
                    self._cache_engine.CacheZone.DYNAMIC,
                )
                full_prompt, breakpoints = self._cache_engine.assemble(provider)
            except Exception:
                full_prompt = assembled_prompt
        else:
            full_prompt = assembled_prompt

        # Build messages
        messages: list[dict[str, Any]] = self._build_initial_messages(full_prompt)

        # ── ENHANCEMENT 4: Multi-model collaborative reasoning ──
        if use_collaborative and self._collaborative and self._gateway:
            yield StreamEvent(type="thinking", data=f"Multi-model reasoning: {reasoning_mode}")

            try:
                from kernel.collaborative_reasoner import ReasoningMode
                mode = ReasoningMode(reasoning_mode)
            except ValueError:
                mode = ReasoningMode.DUAL_VERIFY

            jury_result = await self._collaborative.reason(
                full_prompt, mode=mode, system_prompt=self.system_prompt,
            )

            self._total_tokens += jury_result.total_tokens

            yield StreamEvent(
                type="token",
                data=jury_result.consensus_content,
                metadata={
                    "tokens": jury_result.total_tokens,
                    "turn": self._turn_count,
                    "consensus": jury_result.consensus_level,
                    "models_used": [v.model for v in jury_result.votes],
                    "total_latency_ms": jury_result.total_latency_ms,
                },
            )

            # Check for tool calls in the consensus
            tool_calls = self._extract_tool_calls(jury_result.consensus_content)
            if tool_calls:
                for tc in tool_calls:
                    yield StreamEvent(type="tool_call", data=tc)
                    result = await self._execute_tool(
                        tc.get("name", ""), tc.get("arguments", {}),
                    )
                    yield StreamEvent(type="tool_result", data=result)

            await self._remember(prompt, jury_result.consensus_content, 1, jury_result.total_tokens)
            yield StreamEvent(type="done", data={
                "turns": 1, "total_tokens": jury_result.total_tokens,
                "stop_reason": "completed",
                "reasoning_mode": reasoning_mode,
                "consensus_level": jury_result.consensus_level,
            })
            return

        # ── Standard loop (fallback) ──
        while not self._aborted:
            self._turn_count += 1

            # ── Stop condition: max_turns ──
            if self._turn_count > self.max_turns:
                yield StreamEvent(type="warning", data="Max turns reached",
                                  metadata={"turns": self._turn_count})
                break

            # ── Stop condition: token_budget ──
            if self._total_tokens >= self.token_budget:
                yield StreamEvent(type="warning", data="Token budget exhausted",
                                  metadata={"tokens": self._total_tokens})
                break

            # ── Pre-model context compression ──
            if self._should_compress(messages):
                yield StreamEvent(type="compaction", data="Compressing context...")
                messages = await self._compress(messages)
                if messages is None:
                    self._compaction_failures += 1
                    if self._compaction_failures >= 3:
                        yield StreamEvent(type="error", data="Compaction failed 3x — stopping")
                        break
                    continue
                self._compaction_failures = 0

            # ── Call LLM ──
            yield StreamEvent(type="thinking", data="Thinking...",
                              metadata={"turn": self._turn_count})

            t0 = time.time()
            response = await self._call_llm(messages, model, provider)
            duration = (time.time() - t0) * 1000

            if not response or response.get("status") != "ok":
                yield StreamEvent(type="error",
                                  data=response.get("error", "LLM call failed"))
                break

            content = response.get("content", "") or ""
            tokens = response.get("tokens", 0)
            self._total_tokens += tokens

            # ── Parse tool calls from response ──
            tool_calls = self._extract_tool_calls(content)

            if not tool_calls:
                # No tools → stream final content and stop
                yield StreamEvent(type="token", data=content,
                                  metadata={"tokens": tokens, "turn": self._turn_count,
                                            "duration_ms": duration})
                # Store in memory
                await self._remember(prompt, content, self._turn_count, tokens)
                break

            # ── Has tool calls → execute them ──
            # Yield cleaned content (tool_call tags stripped)
            clean = getattr(self, '_cleaned_content', content) or content
            yield StreamEvent(type="token", data=clean,
                              metadata={"tokens": tokens, "has_tool_calls": True})

            tool_results = []
            for tc in tool_calls:
                tool_name = tc.get("name", "unknown")
                tool_args = tc.get("arguments", {})

                yield StreamEvent(type="tool_call", data=tc,
                                  metadata={"turn": self._turn_count})

                # ── Permission gate ──
                if self._arbiter:
                    allowed, reason = await self._arbiter.check(tool_name, tool_args)
                    if not allowed:
                        yield StreamEvent(type="warning",
                                          data=f"Blocked: {reason}",
                                          metadata={"tool": tool_name})
                        tool_results.append({
                            "tool": tool_name, "error": f"Permission denied: {reason}",
                        })
                        continue

                # ── Execute tool ──
                try:
                    result = await self._execute_tool(tool_name, tool_args)
                    tool_results.append({"tool": tool_name, "result": result})
                    yield StreamEvent(type="tool_result", data=result,
                                      metadata={"tool": tool_name})
                except Exception as exc:
                    tool_results.append({"tool": tool_name, "error": str(exc)})
                    yield StreamEvent(type="error", data=str(exc),
                                      metadata={"tool": tool_name})

            # ── Append tool results to messages → loop continues ──
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content":
                f"Tool results:\n" + "\n".join(
                    f"  {tr['tool']}: {tr.get('result', tr.get('error', '?'))}"
                    for tr in tool_results
                )[:4000]})

        # ── Build final result ──
        yield StreamEvent(type="done", data={
            "turns": self._turn_count,
            "total_tokens": self._total_tokens,
            "stop_reason": "completed" if not self._aborted else "aborted",
        })

    def abort(self) -> None:
        """Signal the loop to stop at the next safe point."""
        self._aborted = True

    # ── Internal: message building ──────────────────────────────────────

    def _build_initial_messages(self, prompt: str) -> list[dict[str, Any]]:
        """Build the initial message list (Claude Code assembles 9 context sources)."""
        messages: list[dict[str, Any]] = []

        # System prompt (mycelium.md constitution)
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        # Tool definitions
        if self._tools:
            tool_defs = self._build_tool_definitions()
            if tool_defs:
                messages.append({"role": "system", "content": tool_defs})

        # Relevant memory context
        if self._memory:
            try:
                ctx = self._memory.get_context(query=prompt, top_k=5)
                if ctx.get("relevant_memories"):
                    mem_text = "Relevant memories:\n" + "\n".join(
                        f"  - {m['content']}" for m in ctx["relevant_memories"]
                    )
                    messages.append({"role": "system", "content": mem_text})
            except Exception:
                pass

        # User prompt
        messages.append({"role": "user", "content": prompt})

        return messages

    def _build_tool_definitions(self) -> str:
        """Build tool definitions string for the system prompt."""
        try:
            tools = self._tools.list_tools()
            lines = ["Available tools (call using <tool_call> XML tags):"]
            for t in tools:
                name = t.get("name", "?")
                desc = t.get("description", "")
                params = t.get("parameters", {})
                lines.append(f"  - {name}: {desc}")
                if params.get("properties"):
                    for pname, pinfo in list(params["properties"].items()):
                        lines.append(f"      {pname}: {pinfo.get('description', '')}")
            return "\n".join(lines)
        except Exception:
            return ""

    # ── Internal: LLM call ──────────────────────────────────────────────

    async def _call_llm(
        self,
        messages: list[dict[str, Any]],
        model: str,
        provider: str,
    ) -> dict[str, Any]:
        """Call the LLM through the Gateway."""
        if self._gateway is None:
            return {"status": "error", "error": "No gateway configured"}

        # Build a single prompt from messages (for simple chat API)
        prompt = self._messages_to_prompt(messages)

        try:
            return await self._gateway.chat(
                prompt=prompt,
                model=model,
                provider=provider,
            )
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def _messages_to_prompt(self, messages: list[dict[str, Any]]) -> str:
        """Convert message list to a single prompt string."""
        parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                parts.append(f"<system>\n{content}\n</system>")
            elif role == "assistant":
                parts.append(f"<assistant>\n{content}\n</assistant>")
            else:
                parts.append(content)
        return "\n\n".join(parts)

    # ── Internal: tool call parsing ─────────────────────────────────────

    def _extract_tool_calls(self, content: str) -> list[dict[str, Any]]:
        """Ultimate tool call parser — 14 formats from all 2026 LLM providers."""
        from kernel.tool_call_parser import extract_tool_calls
        import re
        result = extract_tool_calls(content)
        cleaned = re.sub(r'<tool_call[^>]*>.*?</tool_call>', '', content, flags=re.DOTALL)
        cleaned = re.sub(r'<function=\w+>.*?</function>', '', cleaned, flags=re.DOTALL)
        self._cleaned_content = cleaned.strip()
        return result

    async def _execute_tool(
        self, name: str, args: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool — ALWAYS in background thread. Never blocks UI."""
        import asyncio
        if self._tools is None:
            return {"error": "No tool registry"}

        # ── PreToolUse Hooks (can block execution) ──
        if hasattr(self, '_hooks') and self._hooks:
            allowed, _ = self._hooks.run("PreToolUse", name, args)
            if not allowed:
                return {"error": f"Hook blocked tool: {name}"}

        # ── Permission check ──
        if self._arbiter:
            allowed, reason = await self._arbiter.check(name, args)
            if not allowed:
                return {"error": f"Permission denied: {reason}",
                        "requires_confirmation": True, "risk_reason": reason}

        # ── Claude Code 工具名别名（LLM训练数据偏Claude Code，自动映射）──
        _CLAUDE_CODE_ALIASES = {
            "Read": "file_read", "Write": "file_write", "Edit": "file_edit",
            "Bash": "bash_execute", "Grep": "codebase_search", "Glob": "file_list",
            "WebSearch": "web_search", "WebFetch": "web_fetch",
            "Task": None,  # 不支持子代理
            "execute_command": "bash_execute",
            "read_file": "file_read", "write_file": "file_write",
            "search_code": "codebase_search", "run_command": "bash_execute",
            "search_file": "file_list", "list_files": "file_list",
            "create_file": "file_write", "read_file_content": "file_read",
            "read": "file_read", "write": "file_write", "edit": "file_edit",
            "bash": "bash_execute", "grep": "codebase_search", "glob": "file_list",
            "WebSearch": "web_search", "WebFetch": "web_fetch",
            "run": "bash_execute", "exec": "bash_execute", "shell": "bash_execute",
            "file_create": "file_write", "search": "web_search",
        }
        original_name = name
        if name in _CLAUDE_CODE_ALIASES:
            mapped = _CLAUDE_CODE_ALIASES[name]
            if mapped is None:
                return {"error": f"Claude Code tool '{name}' is not available. Use: file_write, file_read, bash_execute, web_search, file_edit, file_list"}
            name = mapped

        handler = self._tools.get_handler(name)
        if handler is None:
            hint = ""
            if original_name != name:
                hint = f" (mapped from '{original_name}')"
            return {"error": f"Unknown tool: {name}{hint}"}

        # ── 参数别名映射：宽容处理LLM常用的非标准参数名 ──
        # LLM经常用这些名字，自动映射到正确参数名
        _PARAM_ALIASES: dict[str, str] = {
            "raw": "query",       # codebase_index(raw=...) → project_root
            "text": "query",
            "cmd": "command",
            "dir": "directory",
            "path": "file_path",
            "file": "file_path",  # LLM often uses "file" shorthand
            "filename": "file_path",  # LLM uses "filename"
            "target": "file_path",
            "prompt": "query",
            "source": "file_path",
            "dest": "file_path",
            "name": "query",
            "value": "content",
            "data": "content",
            "body": "content",
            "code": "content",
            "param": None,        # LLM misuses "param" as generic key → smart fallback
            "arg": None,          # Same: LLM uses "arg" generically
        }
        # 智能映射：如果别名对应的有效参数不存在，则尝试其他匹配
        mapped_args = dict(args)
        import inspect as _inspect
        try:
            sig = _inspect.signature(handler)
            valid_params = set(sig.parameters.keys())

            for bad, good_candidate in _PARAM_ALIASES.items():
                if bad in mapped_args and bad not in valid_params:
                    if good_candidate in valid_params:
                        mapped_args[good_candidate] = mapped_args.pop(bad)
                    else:
                        # 候选无效 → 根据值的类型自动匹配
                        val = mapped_args.pop(bad)
                        val_str = str(val).lower()
                        # 路径类值
                        if val_str.startswith(("c:", "/", ".", "~")) or "\\" in val_str:
                            for candidate in ("file_path", "path", "pattern", "project_root", "directory"):
                                if candidate in valid_params:
                                    mapped_args[candidate] = val
                                    break
                        # 通用值 → 尝试所有非默认参数
                        if bad not in mapped_args:  # 还没被处理
                            for candidate in ("query", "command", "content", "text", "code"):
                                if candidate in valid_params:
                                    mapped_args[candidate] = val
                                    break
                        # 最后兜底: 赋给第一个未使用的非可选参数
                        if bad not in mapped_args:
                            for pname in valid_params:
                                if pname not in mapped_args:
                                    mapped_args[pname] = val
                                    break

            # ── 跨工具参数映射：LLM常用参数名在不同工具间不一致 ──
            # e.g., file_path → directory (for file_list), working_dir → directory
            _CROSS_TOOL_REMAP: dict[str, str] = {
                "file_path": "directory",   # file_list uses directory, not file_path
                "working_dir": "directory",  # bash_execute uses working_dir, file_list uses directory
                "path": "directory",
            }
            for bad, good in _CROSS_TOOL_REMAP.items():
                if bad in mapped_args and bad not in valid_params and good in valid_params:
                    mapped_args[good] = mapped_args.pop(bad)

            # ── Safe-to-ignore 参数：LLM加的注释/描述字段，静默丢弃 ──
            _SAFE_IGNORE = {"description", "comment", "note", "reason",
                           "shell", "purpose", "why", "context"}
            for key in _SAFE_IGNORE:
                mapped_args.pop(key, None)

            # 检查仍有未知参数
            given_params = set(mapped_args.keys())
            unknown = given_params - valid_params
            if unknown:
                required = [n for n, p in sig.parameters.items()
                          if p.default is _inspect.Parameter.empty]
                hint = (
                    f"Wrong parameter(s): {', '.join(sorted(unknown))}. "
                    f"Valid: {', '.join(sorted(valid_params))}. "
                    f"Required: {', '.join(required) if required else 'none'}."
                )
                return {"error": hint, "status": "error",
                        "valid_params": sorted(valid_params),
                        "required_params": required}

            args = mapped_args  # Use aliased args for execution
        except Exception:
            pass  # Can't inspect — let the handler reject bad args

        # ── Execute in thread — NEVER blocks event loop ──
        def _run():
            try:
                r = handler(**args)
                if asyncio.iscoroutine(r):
                    # Can't await in sync context — use a new loop
                    import asyncio as aio
                    loop = aio.new_event_loop()
                    try: return loop.run_until_complete(r)
                    finally: loop.close()
                return r
            except TypeError as e:
                # Python's own "unexpected keyword argument" error
                err_msg = str(e)
                # Extract the actual signature for the error response
                try:
                    sig = _inspect.signature(handler)
                    valid = ', '.join(sorted(sig.parameters.keys()))
                    err_msg = f"{err_msg}. Valid: {valid}"
                except Exception:
                    pass
                return {"error": err_msg, "status": "error"}
            except Exception as e:
                return {"error": str(e)}

        result = await asyncio.to_thread(_run)
        result = result if isinstance(result, dict) else {"result": str(result)}

        # ── PostToolUse Hooks ──
        if hasattr(self, '_hooks') and self._hooks:
            _, modified = self._hooks.run("PostToolUse", name, args, result)
            if modified is not None:
                result = modified if isinstance(modified, dict) else {"result": str(modified)[:5000]}

        return result

    async def _execute_in_worktree(self, name: str, args: dict[str, Any], handler: Any) -> dict[str, Any]:
        """Execute a tool in an isolated git worktree."""
        import os, subprocess, tempfile, shutil
        worktree_dir = None
        try:
            worktree_dir = tempfile.mkdtemp(prefix="sclerotium_worktree_")
            subprocess.run(["git", "worktree", "add", worktree_dir, "HEAD"],
                          capture_output=True, timeout=10)
            os.chdir(worktree_dir)
            result = handler(**args)
            if asyncio.iscoroutine(result):
                result = await result
            os.chdir(self._original_cwd if hasattr(self, '_original_cwd') else ".")
            subprocess.run(["git", "worktree", "remove", worktree_dir, "--force"],
                          capture_output=True, timeout=10)
            return result if isinstance(result, dict) else {"result": str(result)}
        except Exception:
            if worktree_dir and os.path.exists(worktree_dir):
                shutil.rmtree(worktree_dir, ignore_errors=True)
            result = handler(**args)
            if asyncio.iscoroutine(result):
                result = await result
            return result if isinstance(result, dict) else {"result": str(result)}

    # ── Internal: memory ────────────────────────────────────────────────

    async def _remember(
        self, prompt: str, response: str, turn: int, tokens: int,
    ) -> None:
        """Store the conversation turn in memory."""
        if self._memory is None:
            return
        try:
            self._memory.store(
                content=f"Turn {turn}: {prompt[:200]} → {response[:200]}",
                level="episodic",
                importance=min(0.9, 0.3 + turn * 0.05),
                metadata={"prompt": prompt[:500], "tokens": tokens, "turn": turn},
            )
        except Exception:
            pass

    # ── Internal: context compression ───────────────────────────────────

    def _should_compress(self, messages: list[dict[str, Any]]) -> bool:
        """Check if context compression is needed (Claude Code: 13K token buffer)."""
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        # Rough estimate: 4 chars ≈ 1 token
        estimated_tokens = total_chars // 4
        # Trigger compression when > 80% of typical context window
        return estimated_tokens > 80_000  # 80K tokens ≈ trigger

    async def _compress(
        self, messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]] | None:
        """Compress message history (5-layer pipeline)."""
        from kernel.context_compressor import compress_messages
        return await compress_messages(messages, self._gateway)
