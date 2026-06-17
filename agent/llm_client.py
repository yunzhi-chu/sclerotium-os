"""LLM Client — async streaming client with native function calling.

Replaces the old blocking urllib + shell regex approach in sclerotium.py.
Supports OpenAI-compatible APIs (DeepSeek, OpenAI, Groq, Ollama, etc.)
with native tool_use/function calling.

Key improvements over sclerotium.py:
  - Native function calling (not regex parsing ```sh blocks)
  - Async aiohttp streaming (not blocking urllib)
  - Environment variable for API key (not hardcoded)
  - Automatic retry with exponential backoff
  - Multi-turn tool use conversation support
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

logger = logging.getLogger("sclerotium.llm")

# ── Data types ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ProviderConfig:
    """Configuration for a single LLM provider in the fallback chain."""
    name: str
    base_url: str
    api_key: str = ""
    default_model: str = ""
    priority: int = 0  # Lower = higher priority


# Built-in provider registry (extendable via env vars)
_PROVIDER_REGISTRY: dict[str, ProviderConfig] = {
    "deepseek": ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.com/v1",
        default_model="deepseek-v4-flash",
        priority=0,
    ),
    "openai": ProviderConfig(
        name="openai",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o",
        priority=10,
    ),
    "groq": ProviderConfig(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-4-maverick-128k",
        priority=20,
    ),
    "openrouter": ProviderConfig(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        default_model="openrouter/auto",
        priority=30,
    ),
    "ollama": ProviderConfig(
        name="ollama",
        base_url="http://localhost:11434/v1",
        default_model="llama3.3",
        priority=40,
    ),
}

# ── Data types ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ToolCall:
    """A parsed tool call from the LLM response."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMResponse:
    """Structured LLM response with optional tool calls."""
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: str = "stop"
    model: str = ""
    tokens_used: int = 0
    duration_ms: float = 0.0

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


# ── LLM Client ─────────────────────────────────────────────────────────────


class LLMClient:
    """Async LLM client with native function calling support.

    Usage:
        client = LLMClient()
        client.configure_tools(tool_registry)  # Wire MCP tools

        # Non-streaming
        response = await client.chat(messages)
        for tc in response.tool_calls:
            result = await client.execute_tool(tc)

        # Streaming
        async for chunk in client.chat_stream(messages):
            if chunk["type"] == "token":
                print(chunk["data"], end="")
            elif chunk["type"] == "tool_call":
                print(f"\\n[Tool: {chunk['data']['name']}]")
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "deepseek-v4-flash",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        *,
        # Retry + fallback config
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        retry_max_delay: float = 30.0,
        fallback_providers: list[str] | None = None,
    ) -> None:
        # Primary provider
        self.api_key = api_key or os.environ.get(
            "SCLEROTIUM_API_KEY",
            os.environ.get("DEEPSEEK_API_KEY", ""),
        )
        self.base_url = base_url or os.environ.get(
            "SCLEROTIUM_API_BASE",
            "https://api.deepseek.com/v1",
        )
        self.model = model or os.environ.get("SCLEROTIUM_MODEL", "deepseek-v4-flash")
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Retry config
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.retry_max_delay = retry_max_delay

        # Fallback chain: build from arg or env var
        if fallback_providers is None:
            fb_env = os.environ.get("SCLEROTIUM_FALLBACK_PROVIDERS", "")
            fallback_providers = [p.strip() for p in fb_env.split(",") if p.strip()] if fb_env else []
        self._fallback_providers = fallback_providers

        self._tools: list[dict[str, Any]] = []
        self._tool_handlers: dict[str, Any] = {}
        self._session = None  # Lazy aiohttp session
        self._total_retries = 0

    # ── Provider management ──────────────────────────────────────────────

    @property
    def current_provider(self) -> str:
        """Detect current provider from base URL."""
        for name, cfg in _PROVIDER_REGISTRY.items():
            if cfg.base_url in self.base_url:
                return name
        return "custom"

    def get_fallback_chain(self) -> list[tuple[str, str, str]]:
        """Get ordered fallback chain as [(provider_name, base_url, api_key), ...].

        Returns chain starting from current primary, then configured fallbacks.
        """
        chain = [(self.current_provider, self.base_url, self.api_key)]

        for fb_name in self._fallback_providers:
            cfg = _PROVIDER_REGISTRY.get(fb_name)
            if cfg is None:
                continue
            # Try env var for this provider's key
            key_var = f"{fb_name.upper()}_API_KEY"
            fb_key = os.environ.get(key_var, "")
            chain.append((fb_name, cfg.base_url, fb_key))

        return chain

    @property
    def retry_stats(self) -> dict[str, Any]:
        return {"total_retries": self._total_retries}

    # ── Tool configuration ─────────────────────────────────────────────────

    def configure_tools(self, tool_registry: Any) -> None:
        """Wire MCP ToolRegistry tools for native function calling.

        Converts MCP tool definitions to OpenAI function calling format.
        """
        self._tools = []
        self._tool_handlers = {}

        try:
            for tool_def in tool_registry.list_tools():
                name = tool_def["name"]
                desc = tool_def.get("description", "")
                params = tool_def.get("parameters", {})

                # Build OpenAI function definition
                func_def: dict[str, Any] = {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": desc[:1024],  # OpenAI limit
                        "parameters": {
                            "type": params.get("type", "object"),
                            "properties": params.get("properties", {}),
                        },
                    },
                }

                # Add required params if specified
                required = params.get("required", [])
                if required:
                    func_def["function"]["parameters"]["required"] = required

                self._tools.append(func_def)
                self._tool_handlers[name] = tool_registry.get_handler(name)

        except Exception as e:
            logger.warning("Failed to configure tools: %s", e)

    @property
    def tool_count(self) -> int:
        return len(self._tools)

    # ── Chat (non-streaming) ───────────────────────────────────────────────

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        """Send chat completion with native function calling.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts
            model: Override model
            system: System prompt (prepended as system message)

        Returns:
            LLMResponse with content and optional tool_calls
        """
        t0 = time.time()

        # Build full message list with system prompt
        full_messages = list(messages)
        if system:
            # Only prepend system if not already present
            if not full_messages or full_messages[0].get("role") != "system":
                full_messages.insert(0, {"role": "system", "content": system})

        body = {
            "model": model or self.model,
            "messages": full_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }

        # Add tools if configured
        if self._tools:
            body["tools"] = self._tools
            body["tool_choice"] = "auto"

        try:
            data = await self._post_json("/chat/completions", body)
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "") or ""
            finish = choice.get("finish_reason", "stop")

            # Parse tool calls from response
            tool_calls: list[ToolCall] = []
            raw_tool_calls = message.get("tool_calls", [])
            for tc in raw_tool_calls:
                func = tc.get("function", {})
                try:
                    args = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(ToolCall(
                    id=tc.get("id", ""),
                    name=func.get("name", ""),
                    arguments=args,
                ))

            duration = (time.time() - t0) * 1000
            tokens = data.get("usage", {}).get("total_tokens", 0)

            return LLMResponse(
                content=content,
                tool_calls=tuple(tool_calls),
                finish_reason=finish,
                model=data.get("model", model or self.model),
                tokens_used=tokens,
                duration_ms=duration,
            )

        except Exception as e:
            logger.error("LLM chat failed: %s", e)
            return LLMResponse(
                content=f"Error: {e}",
                finish_reason="error",
                duration_ms=(time.time() - t0) * 1000,
            )

    # ── Chat (streaming) ───────────────────────────────────────────────────

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        system: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream chat completion with SSE parsing.

        Yields dicts:
          {"type": "token", "data": "text fragment"}
          {"type": "tool_call_start", "data": {"id": "...", "name": "..."}}
          {"type": "tool_call_args", "data": "json fragment"}
          {"type": "tool_call_end", "data": ToolCall}
          {"type": "done", "data": {"finish_reason": "...", "tokens": N}}
          {"type": "error", "data": "error message"}
        """
        full_messages = list(messages)
        if system and (not full_messages or full_messages[0].get("role") != "system"):
            full_messages.insert(0, {"role": "system", "content": system})

        body = {
            "model": model or self.model,
            "messages": full_messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True,
        }

        if self._tools:
            body["tools"] = self._tools
            body["tool_choice"] = "auto"

        try:
            # Accumulators for streaming tool call parsing
            tool_call_acc: dict[str, dict[str, Any]] = {}
            content_parts: list[str] = []

            async for sse_event in self._post_stream("/chat/completions", body):
                if sse_event.get("type") == "error":
                    yield sse_event
                    return

                data = sse_event.get("data", {})
                choices = data.get("choices", [])
                if not choices:
                    continue

                choice = choices[0]
                delta = choice.get("delta", {})
                finish = choice.get("finish_reason") or ""

                # Text content
                text = delta.get("content", "")
                if text:
                    content_parts.append(text)
                    yield {"type": "token", "data": text}

                # Tool calls in delta
                delta_tcs = delta.get("tool_calls", [])
                for tc_delta in delta_tcs:
                    idx = tc_delta.get("index", 0)
                    tc_id = tc_delta.get("id", "")
                    func = tc_delta.get("function", {})

                    # Initialize accumulator for this tool call
                    if idx not in tool_call_acc:
                        tool_call_acc[idx] = {
                            "id": tc_id,
                            "name": func.get("name", ""),
                            "arguments": "",
                        }
                        yield {
                            "type": "tool_call_start",
                            "data": {
                                "id": tc_id,
                                "name": func.get("name", ""),
                                "index": idx,
                            },
                        }

                    # Accumulate
                    if tc_id:
                        tool_call_acc[idx]["id"] = tc_id
                    if func.get("name"):
                        tool_call_acc[idx]["name"] = func["name"]

                    args_chunk = func.get("arguments", "")
                    if args_chunk:
                        tool_call_acc[idx]["arguments"] += args_chunk
                        yield {"type": "tool_call_args", "data": args_chunk}

                # Finish — finalize accumulated tool calls
                if finish:
                    for idx, acc in tool_call_acc.items():
                        try:
                            parsed_args = json.loads(acc["arguments"]) if acc["arguments"] else {}
                        except json.JSONDecodeError:
                            parsed_args = {}

                        tc = ToolCall(
                            id=acc["id"],
                            name=acc["name"],
                            arguments=parsed_args,
                        )
                        yield {"type": "tool_call_end", "data": tc}

                    tokens = data.get("usage", {}).get("total_tokens", 0)
                    yield {
                        "type": "done",
                        "data": {
                            "finish_reason": finish,
                            "tokens": tokens,
                            "content": "".join(content_parts),
                        },
                    }

        except Exception as e:
            logger.error("LLM stream failed: %s", e)
            yield {"type": "error", "data": str(e)}

    # ── Tool execution ─────────────────────────────────────────────────────

    # Long-running tools that may exceed default timeouts
    LONG_RUNNING_TOOLS: set[str] = {
        "evolution_start", "evolution_cycle", "evolve_cycle", "evolve_detect",
        "refactor_analyze", "refactor_impact", "refactor_callers",
        "system_build", "gp_evolve", "bootstrap_cycle",
        "recursive_improve", "sandbox_execute", "cache_warmup",
        "memory_consolidate", "consolidate_chain", "memory_dream",
        "codebase_scan", "codebase_index", "dependency_scan",
    }

    async def execute_tool(self, tool_call: ToolCall) -> dict[str, Any]:
        """Execute a tool call and return the result in OpenAI tool result format.

        Long-running tools get a 300s timeout (5 min) instead of the default 60s.
        Automatically truncates large results (screenshots, big files) to
        avoid blowing up the LLM context window.
        """
        handler = self._tool_handlers.get(tool_call.name)
        if handler is None:
            return {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps({"error": f"Unknown tool: {tool_call.name}"}),
            }

        # Determine timeout based on tool type
        is_long = tool_call.name in self.LONG_RUNNING_TOOLS
        tool_timeout = 18000 if is_long else 300  # 5h for long tools, 5min for normal

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await asyncio.wait_for(
                    handler(**tool_call.arguments),
                    timeout=tool_timeout,
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, lambda: handler(**tool_call.arguments),
                    ),
                    timeout=tool_timeout,
                )

            # Smart truncation: keep result under ~2000 chars for LLM context
            truncated = self._truncate_tool_result(tool_call.name, result)

            return {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(truncated, ensure_ascii=False, default=str),
            }
        except asyncio.TimeoutError:
            return {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps({
                    "error": f"Tool '{tool_call.name}' timed out after {tool_timeout}s. "
                             f"Try with smaller scope or use sub-tasks.",
                    "timed_out": True,
                }),
            }
        except Exception as e:
            return {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps({"error": str(e)}),
            }

    @staticmethod
    def _truncate_tool_result(tool_name: str, result: Any) -> Any:
        """Intelligently truncate large tool results for LLM context.

        Rules:
          - Screenshots: strip base64, keep resolution + OCR text
          - Large strings: truncate to 3000 chars with summary
          - Dicts: recursively truncate large values
          - Lists: keep first 20 items
        """
        MAX_STR = 3000
        MAX_LIST = 20

        if isinstance(result, dict):
            truncated = {}
            for k, v in result.items():
                # Screenshot/image data — replace with summary
                if k in ("image_base64", "image_data", "audio_data") and isinstance(v, str) and len(v) > 500:
                    truncated[k] = f"[{len(v)} chars binary data truncated]"
                elif k == "content" and isinstance(v, str) and len(v) > MAX_STR:
                    truncated[k] = v[:MAX_STR] + f"\n... [{len(v) - MAX_STR} more chars]"
                    truncated["_truncated"] = True
                elif isinstance(v, str) and len(v) > MAX_STR:
                    truncated[k] = v[:500] + f"... [{len(v)} chars total]"
                elif isinstance(v, dict):
                    truncated[k] = LLMClient._truncate_tool_result(tool_name, v)
                elif isinstance(v, list) and len(v) > MAX_LIST:
                    truncated[k] = v[:MAX_LIST] + [f"... [{len(v) - MAX_LIST} more items]"]
                else:
                    truncated[k] = v
            return truncated

        if isinstance(result, str) and len(result) > MAX_STR:
            return result[:MAX_STR] + f"\n... [{len(result) - MAX_STR} more chars]"

        if isinstance(result, list) and len(result) > MAX_LIST:
            return result[:MAX_LIST] + [f"... [{len(result) - MAX_LIST} more items]"]

        return result

    # ── Multi-turn tool use loop ───────────────────────────────────────────

    async def run_with_tools(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        max_turns: int = 200,
    ) -> AsyncIterator[dict[str, Any]]:
        """Run a multi-turn conversation with automatic tool execution.

        This is a simplified agent loop that:
        1. Calls the LLM with tools
        2. If tool_calls returned, executes them and feeds results back
        3. Repeats until no more tool calls or max_turns reached

        Yields:
          {"type": "token", "data": "text"}
          {"type": "tool_executing", "data": {"name": "...", "args": {...}}}
          {"type": "tool_result", "data": {"name": "...", "result": {...}}}
          {"type": "done", "data": {"turns": N, "content": "..."}}
        """
        current_messages = list(messages)

        for turn in range(max_turns):
            response = await self.chat(current_messages, system=system if turn == 0 else None)

            if response.content:
                yield {"type": "token", "data": response.content}

            if not response.has_tool_calls:
                yield {
                    "type": "done",
                    "data": {
                        "turns": turn + 1,
                        "content": response.content,
                        "tokens": response.tokens_used,
                        "finish_reason": response.finish_reason,
                    },
                }
                return

            # Execute tool calls
            tool_results = []
            for tc in response.tool_calls:
                yield {
                    "type": "tool_executing",
                    "data": {"name": tc.name, "args": tc.arguments},
                }

                result_msg = await self.execute_tool(tc)
                tool_results.append(result_msg)

                # Parse result for display
                try:
                    result_data = json.loads(result_msg["content"])
                except json.JSONDecodeError:
                    result_data = result_msg["content"]
                yield {
                    "type": "tool_result",
                    "data": {"name": tc.name, "result": result_data},
                }

            # Append assistant message with tool calls
            assistant_msg: dict[str, Any] = {"role": "assistant", "content": response.content or ""}
            if response.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                        },
                    }
                    for tc in response.tool_calls
                ]
            current_messages.append(assistant_msg)

            # Append tool results
            current_messages.extend(tool_results)

        yield {
            "type": "done",
            "data": {
                "turns": max_turns,
                "content": "",
                "finish_reason": "max_turns",
            },
        }

    # ── Internal: HTTP ─────────────────────────────────────────────────────

    async def _get_session(self):
        """Lazy aiohttp session creation.

        Timeout config: 5 hours for long-running autonomous tasks.
          - total=18000s: full request lifecycle (5 hours)
          - connect=30s: initial TCP connection
          - sock_read=18000s: idle read timeout for streaming
        """
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=18000, connect=30, sock_read=18000),
                headers={"Content-Type": "application/json"},
            )
        return self._session

    async def _post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """POST JSON to the API endpoint with retry + fallback."""
        return await self._retry_json(path, body)

    async def _post_stream(
        self, path: str, body: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """POST JSON and stream SSE events with retry + fallback."""
        async for event in self._retry_stream(path, body):
            yield event

    async def _retry_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """Retry loop for non-streaming JSON POST."""
        fallback_chain = self.get_fallback_chain()
        last_error = ""

        for attempt in range(self.max_retries + 1):
            if attempt < 2:
                provider_name, base_url, api_key = fallback_chain[0]
            else:
                fb_idx = min(attempt - 2, len(fallback_chain) - 1)
                provider_name, base_url, api_key = fallback_chain[fb_idx]

            try:
                return await self._do_post_json(base_url, api_key, path, body)
            except Exception as e:
                last_error = str(e)[:200]
                self._total_retries += 1
                if attempt < self.max_retries:
                    delay = min(self.retry_base_delay * (2 ** attempt), self.retry_max_delay)
                    logger.warning(
                        "LLM attempt %d/%d failed (provider=%s): %s. Retrying in %.1fs...",
                        attempt + 1, self.max_retries + 1, provider_name, last_error, delay,
                    )
                    await asyncio.sleep(delay)

        raise RuntimeError(f"LLM request failed after {self.max_retries + 1} attempts: {last_error}")

    async def _retry_stream(
        self, path: str, body: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """Retry loop for streaming SSE POST."""
        fallback_chain = self.get_fallback_chain()
        last_error = ""

        for attempt in range(self.max_retries + 1):
            if attempt < 2:
                provider_name, base_url, api_key = fallback_chain[0]
            else:
                fb_idx = min(attempt - 2, len(fallback_chain) - 1)
                provider_name, base_url, api_key = fallback_chain[fb_idx]

            try:
                async for event in self._do_post_stream(base_url, api_key, path, body):
                    yield event
                return  # Success — stop retrying
            except Exception as e:
                last_error = str(e)[:200]
                self._total_retries += 1
                if attempt < self.max_retries:
                    delay = min(self.retry_base_delay * (2 ** attempt), self.retry_max_delay)
                    logger.warning(
                        "LLM stream attempt %d/%d failed (provider=%s): %s. Retrying in %.1fs...",
                        attempt + 1, self.max_retries + 1, provider_name, last_error, delay,
                    )
                    await asyncio.sleep(delay)

        yield {"type": "error", "data": f"All {self.max_retries + 1} attempts failed: {last_error}"}

    async def _do_post_json(
        self, base_url: str, api_key: str, path: str, body: dict[str, Any],
    ) -> dict[str, Any]:
        """Single POST attempt (no retry)."""
        session = await self._get_session()
        url = f"{base_url}{path}"
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with session.post(url, json=body, headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"HTTP {resp.status}: {text[:500]}")
            return await resp.json()

    async def _do_post_stream(
        self, base_url: str, api_key: str, path: str, body: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        """Single streaming POST attempt (no retry)."""
        session = await self._get_session()
        url = f"{base_url}{path}"

        headers = {"Accept": "text/event-stream"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with session.post(url, json=body, headers=headers) as resp:
            if resp.status != 200:
                text = await resp.text()
                yield {"type": "error", "data": f"HTTP {resp.status}: {text[:500]}"}
                return

            buffer = ""
            async for chunk_bytes, _ in resp.content.iter_chunks():
                chunk = chunk_bytes.decode("utf-8", errors="replace")
                buffer += chunk

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()

                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            return
                        try:
                            data = json.loads(data_str)
                            yield {"type": "delta", "data": data}
                        except json.JSONDecodeError:
                            pass

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
