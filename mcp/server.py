"""Sclerotium MCP Server — Model Context Protocol implementation.

Exposes all Sclerotium OS capabilities as MCP tools consumable by LLMs.
Follows the MCP Protocol (Anthropic 2025, Linux Foundation) specification
with stdio JSON-RPC transport.

Architecture:
  ToolRegistry → registers all tools from mcp/tools/
  MCP loop → reads JSON-RPC from stdin → dispatches → writes to stdout
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

# ── Tool type ─────────────────────────────────────────────────────────

ToolHandler = Callable[..., Awaitable[dict[str, Any]]]


@dataclass
class ToolDef:
    """Metadata for a registered MCP tool."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for inputs
    handler: ToolHandler
    category: str = "general"


# ── Tool Registry ─────────────────────────────────────────────────────


class ToolRegistry:
    """Central registry for MCP tools. Supports register / list / invoke."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: ToolHandler,
        category: str = "general",
    ) -> None:
        self._tools[name] = ToolDef(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            category=category,
        )

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "category": t.category,
            }
            for t in self._tools.values()
        ]

    def get_handler(self, name: str) -> ToolHandler | None:
        tool = self._tools.get(name)
        return tool.handler if tool else None

    def get_tool(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    @property
    def tool_count(self) -> int:
        return len(self._tools)


# ── MCP Server ────────────────────────────────────────────────────────


class SclerotiumMCPServer:
    """Stdio MCP server — bridges LLM to Sclerotium OS execution body.

    Usage:
        server = SclerotiumMCPServer()
        server.register_all_tools()   # load all tools from mcp/tools/
        await server.run()            # start stdio JSON-RPC loop
    """

    def __init__(self) -> None:
        self.tools = ToolRegistry()
        self._start_time = time.time()
        self._request_count = 0
        self._error_count = 0

    # ── Tool registration ─────────────────────────────────────────────

    def register_all_tools(self) -> None:
        """Import and register all MCP tools from mcp/tools/."""
        from mcp.tools.system import register_system_tools
        from mcp.tools.evolution import register_evolution_tools
        from mcp.tools.memory import register_memory_tools
        from mcp.tools.sandbox import register_sandbox_tools
        from mcp.tools.skills import register_skills_tools
        from mcp.tools.code_analysis import register_code_analysis_tools
        from mcp.tools.im import register_im_tools
        from mcp.tools.desktop import register_desktop_tools
        from mcp.tools.scheduler_mcp import register_scheduler_mcp_tools
        from mcp.tools.files import register_files_tools
        from mcp.tools.info import register_info_tools
        from mcp.tools.mode import register_mode_tools
        from mcp.tools.gateways import register_gateway_tools
        from mcp.tools.advanced import register_advanced_tools
        from mcp.tools.sovereign import register_sovereign_tools
        from mcp.tools.genesis import register_genesis_tools
        from mcp.tools.cosmic import register_cosmic_tools
        from mcp.tools.omega import register_omega_tools
        from mcp.tools.innovation import register_innovation_tools
        from mcp.tools.apotheosis import register_apotheosis_tools
        from mcp.tools.cache_engine import register_cache_tools
        from mcp.tools.evolution_bridge import register_evolution_bridge_tools
        from mcp.tools.benchmark import register_benchmark_tools
        from mcp.tools.web_search import register_web_tools
        from mcp.tools.codebase_search import register_codebase_tools
        from mcp.tools.git_tools import register_git_tools
        from mcp.tools.bash_tool import register_bash_tools
        from mcp.tools.file_ops import register_file_ops
        from mcp.tools.os_commands import register_os_commands
        from mcp.tools.installer import register_installer_tools

        register_system_tools(self.tools)
        register_evolution_tools(self.tools)
        register_memory_tools(self.tools)
        register_sandbox_tools(self.tools)
        register_skills_tools(self.tools)
        register_code_analysis_tools(self.tools)
        register_im_tools(self.tools)
        register_desktop_tools(self.tools)
        register_scheduler_mcp_tools(self.tools)
        register_files_tools(self.tools)
        register_info_tools(self.tools)
        register_mode_tools(self.tools)
        register_gateway_tools(self.tools)
        register_advanced_tools(self.tools)
        register_sovereign_tools(self.tools)
        register_genesis_tools(self.tools)
        register_cosmic_tools(self.tools)
        register_omega_tools(self.tools)
        register_innovation_tools(self.tools)
        register_apotheosis_tools(self.tools)
        register_cache_tools(self.tools)
        register_evolution_bridge_tools(self.tools)
        register_benchmark_tools(self.tools)
        register_web_tools(self.tools)
        register_codebase_tools(self.tools)
        register_git_tools(self.tools)
        register_bash_tools(self.tools)
        register_file_ops(self.tools)
        register_os_commands(self.tools)
        register_installer_tools(self.tools)

    # ── JSON-RPC loop ─────────────────────────────────────────────────

    async def run(self) -> None:
        """Run the MCP JSON-RPC loop on stdio.

        Reads JSON-RPC messages from stdin line by line,
        dispatches to the appropriate handler, and writes
        responses to stdout.
        """
        loop = asyncio.get_event_loop()

        while True:
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line:
                    break  # stdin closed

                line = line.strip()
                if not line:
                    continue

                request = json.loads(line)
                response = await self._dispatch(request)
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()

            except json.JSONDecodeError:
                error_resp = self._error(
                    None, -32700, "Parse error: invalid JSON"
                )
                sys.stdout.write(json.dumps(error_resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            except Exception:
                # Don't crash the server on unexpected errors
                continue

    async def _dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        """Route a single JSON-RPC request."""
        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        self._request_count += 1

        try:
            if method == "initialize":
                return self._ok(req_id, {
                    "protocolVersion": "1.0",
                    "serverInfo": {
                        "name": "Sclerotium OS MCP",
                        "version": "0.1.0",
                    },
                    "capabilities": {"tools": {}},
                })

            if method == "tools/list":
                return self._ok(req_id, {"tools": self.tools.list_tools()})

            if method == "tools/call":
                tool_name = params.get("name", "")
                tool_args = params.get("arguments", {})
                return await self._call_tool(req_id, tool_name, tool_args)

            if method == "ping":
                return self._ok(req_id, {})

            # Unknown method
            return self._error(req_id, -32601, f"Method not found: {method}")

        except Exception as exc:
            self._error_count += 1
            return self._error(req_id, -32603, str(exc))

    async def _call_tool(
        self, req_id: Any, tool_name: str, tool_args: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a tool call. Handles both sync and async handlers transparently."""
        handler = self.tools.get_handler(tool_name)
        if handler is None:
            return self._error(
                req_id, -32602, f"Unknown tool: {tool_name}"
            )

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**tool_args)
            else:
                # Run sync handler in thread pool to avoid blocking the event loop
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: handler(**tool_args)
                )
            return self._ok(req_id, {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}]})
        except Exception as exc:
            self._error_count += 1
            return self._ok(req_id, {"content": [{"type": "text", "text": json.dumps({"error": str(exc)}, ensure_ascii=False)}]})

    # ── Response helpers ───────────────────────────────────────────────

    @staticmethod
    def _ok(req_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    @staticmethod
    def _error(req_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        }

    # ── Status ─────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        return {
            "uptime_seconds": time.time() - self._start_time,
            "request_count": self._request_count,
            "error_count": self._error_count,
            "tool_count": self.tools.tool_count,
        }

    # ── Live Backend Injection ─────────────────────────────────────────

    def wire_live_backends(
        self, *,
        genome: Any = None, arbiter: Any = None,
        agent_profiles: Any = None, token_tracker: Any = None,
        memory_store: Any = None, skill_loader: Any = None,
        external_bridge: Any = None, event_bus: Any = None,
        fcpi_tracker: Any = None,
        session_manager: Any = None,
    ) -> None:
        """Inject live backend references for the API bridge."""
        self._live_backends = {
            'genome': genome, 'arbiter': arbiter,
            'agent_profiles': agent_profiles, 'token_tracker': token_tracker,
            'memory_store': memory_store, 'skill_loader': skill_loader,
            'external_bridge': external_bridge, 'event_bus': event_bus,
            'fcpi_tracker': fcpi_tracker,
            'session_manager': session_manager,
        }

        # Inject backends into system tools so system_status returns LIVE data
        try:
            from mcp.tools.system import set_backends
            set_backends(self._live_backends)
        except Exception:
            pass

    # ── SSE HTTP Transport ─────────────────────────────────────────────

    async def run_http(self, host: str = "127.0.0.1", port: int = 18789) -> None:
        """Run MCP server with SSE HTTP transport.

        Endpoints:
          POST /chat          — Non-streaming chat with tool execution
          POST /chat/stream   — SSE streaming chat (AG-UI protocol)
          GET  /tools         — List all registered tools
          GET  /health        — Health check

        The SSE stream follows the AG-UI protocol:
          event: token        — Text token
          event: tool_call    — Tool call initiated
          event: tool_result  — Tool execution result
          event: done         — Completion
        """
        from aiohttp import web

        async def handle_health(request: web.Request) -> web.Response:
            return web.json_response({"status": "ok", "tool_count": self.tools.tool_count})

        async def handle_tools(request: web.Request) -> web.Response:
            return web.json_response({"tools": self.tools.list_tools()})

        async def handle_chat(request: web.Request) -> web.Response:
            """Non-streaming chat: POST {"message": "...", "history": [...]}

            Uses the LLMClient with native function calling if API key is configured,
            otherwise falls back to bash_smart tool execution.
            """
            try:
                body = await request.json()
            except Exception:
                return web.json_response({"error": "Invalid JSON"}, status=400)

            message = body.get("message", "")
            history = body.get("history", [])
            session_id = body.get("session_id", body.get("sender", ""))

            # ── Server-side session management (OpenClaw resolveSession pattern) ──
            session_msgs = []
            if session_id:
                try:
                    be = getattr(self, '_live_backends', {})
                    session_mgr = be.get('session_manager')
                    if session_mgr:
                        raw = session_mgr.get_history(session_id)
                        # COMPACTION: compress old tool_calls into summaries (OpenClaw step 10)
                        # Keep last 4 messages as-is (recent context), summarize older ones
                        if len(raw) > 8:
                            recent = raw[-4:]  # Last 2 exchanges
                            older = raw[:-4]
                            # Build a summary of older conversation
                            summary_parts = []
                            for m in older:
                                role = m.get("role", "")
                                content = str(m.get("content", ""))[:100]
                                if role == "user":
                                    summary_parts.append(f"用户曾问: {content}")
                                elif role == "assistant":
                                    if content and content not in ("Done.", "已完成", ""):
                                        summary_parts.append(f"菌核曾回复: {content}")
                            if summary_parts:
                                summary = "【历史对话摘要 - 已完成，无需重复执行】\n" + "\n".join(summary_parts[-6:])
                                session_msgs = [{"role": "system", "content": summary}] + recent
                            else:
                                session_msgs = recent
                        else:
                            session_msgs = raw
                except Exception:
                    pass

            # Try LLMClient with function calling (if API key configured)
            import os
            api_key = os.environ.get("SCLEROTIUM_API_KEY", os.environ.get("DEEPSEEK_API_KEY", ""))
            if api_key:
                llm = None
                try:
                    from agent.llm_client import LLMClient
                    llm = LLMClient()
                    llm.configure_tools(self.tools)

                    # Merge client history + server session history
                    msgs = list(history) if history else []
                    if session_msgs and not msgs:
                        msgs = list(session_msgs)
                    elif session_msgs:
                        # Deduplicate: client history takes priority, append server-only messages
                        seen = set()
                        for m in msgs:
                            seen.add(m.get("content", "")[:80])
                        for m in session_msgs:
                            if m.get("content", "")[:80] not in seen:
                                msgs.append(m)

                    try:
                        from kernel.prompt_factory_v2 import build_ultimate_prompt
                        be = getattr(self, '_live_backends', {})
                        system_prompt = build_ultimate_prompt(
                            tool_registry=self.tools,
                            user_message=message,
                            arbiter=be.get('arbiter'),
                            memory=be.get('memory_store'),
                            genome=be.get('genome'),
                            skill_loader=be.get('skill_loader'),
                            agent_profiles=be.get('agent_profiles'),
                            workspace_dir=os.path.expanduser("~"),
                        )
                    except Exception:
                        system_prompt = "你是Sclerotium OS。直接调用工具，用中文简短回复。"
                    msgs.insert(0, {"role": "system", "content": system_prompt})
                    msgs.append({"role": "user", "content": message})

                    # Multi-turn automation loop (max 8 turns)
                    all_tool_calls = []
                    all_tool_results = []
                    final_content = ""
                    total_tokens = 0
                    final_model = ""
                    turns = 0

                    for turns in range(100):
                        response = await llm.chat(msgs)
                        final_content = response.content or ""
                        final_model = response.model
                        total_tokens += response.tokens_used

                        if not response.has_tool_calls:
                            break

                        # Build assistant message with tool_calls FIRST (required by API)
                        assistant_msg = {
                            "role": "assistant",
                            "content": response.content or "",
                            "tool_calls": [
                                {
                                    "id": tc.id, "type": "function",
                                    "function": {"name": tc.name, "arguments": json.dumps(tc.arguments, ensure_ascii=False)},
                                }
                                for tc in response.tool_calls
                            ],
                        }
                        msgs.append(assistant_msg)

                        # Execute tools and build tool response messages
                        be = getattr(self, '_live_backends', {})
                        genome = be.get('genome')
                        t_start = __import__('time').time()
                        for tc in response.tool_calls:
                            tr = await llm.execute_tool(tc)
                            data_str = tr.get("content", str(tr))
                            try: data = json.loads(data_str)
                            except: data = data_str
                            # ═══ 8D Natural selection: record real tool usage (用进废退) ═══
                            if genome:
                                is_ok = not isinstance(data, dict) or data.get("status") != "error"
                                try:
                                    genome.record_tool_usage(tc.name, success=is_ok)
                                except Exception:
                                    pass

                            all_tool_calls.append({"name": tc.name, "arguments": tc.arguments})
                            all_tool_results.append({"tool": tc.name, "result": data})
                            msgs.append({
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": json.dumps(data, ensure_ascii=False, default=str),
                            })

                    await llm.close()
                    llm = None

                    # ── Persist session (OpenClaw persistSession pattern) ──
                    if session_id:
                        try:
                            be = getattr(self, '_live_backends', {})
                            session_mgr = be.get('session_manager')
                            if session_mgr:
                                # Ensure session exists
                                if not session_mgr.get(session_id):
                                    session_mgr.create(title=message[:50], model=final_model)
                                # Append this exchange
                                session_mgr.append_messages(session_id, [
                                    {"role": "user", "content": message},
                                    {"role": "assistant", "content": final_content},
                                ])
                        except Exception:
                            pass

                    return web.json_response({
                        "content": final_content,
                        "tool_calls": all_tool_calls,
                        "tool_results": all_tool_results,
                        "tokens": total_tokens,
                        "model": final_model,
                        "turns": turns + 1,
                        "session_id": session_id or "",
                    })
                except Exception:
                    if llm:
                        try: await llm.close()
                        except: pass
                    pass  # Fall through to tool dispatch

            # Fallback: delegate to bash_smart
            resp = await self._dispatch({
                "id": 1, "method": "tools/call",
                "params": {"name": "bash_smart", "arguments": {"action": message}},
            })
            return web.json_response(resp)

        async def handle_chat_stream(request: web.Request) -> web.StreamResponse:
            """SSE streaming chat: POST {"message": "...", "history": [...]}

            Follows AG-UI protocol with SSE events.
            """
            try:
                body = await request.json()
            except Exception:
                resp = web.StreamResponse()
                await resp.prepare(request)
                await resp.write(b"event: error\ndata: Invalid JSON\n\n")
                return resp

            message = body.get("message", "")
            history = body.get("history", [])

            resp = web.StreamResponse(
                status=200,
                reason="OK",
                headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
            await resp.prepare(request)

            try:
                # Build context messages for the LLM
                messages = list(history) if history else []
                messages.append({"role": "user", "content": message})

                # Use bash_smart as fallback for HTTP mode
                result = await self._dispatch({
                    "id": 1, "method": "tools/call",
                    "params": {"name": "bash_smart", "arguments": {"action": message}},
                })

                result_text = json.dumps(
                    result.get("result", {}).get("content", [{}])[0].get("text", "{}"),
                    ensure_ascii=False,
                )

                # Stream the result as SSE
                for i in range(0, len(result_text), 50):
                    chunk = result_text[i:i+50]
                    await resp.write(
                        f"event: token\ndata: {json.dumps({'token': chunk})}\n\n".encode()
                    )
                    await asyncio.sleep(0.01)  # Simulate streaming

                await resp.write(b"event: done\ndata: {}\n\n")

            except Exception as e:
                await resp.write(
                    f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n".encode()
                )

            return resp

        app = web.Application()
        app.router.add_get("/health", handle_health)
        app.router.add_get("/tools", handle_tools)
        app.router.add_post("/chat", handle_chat)
        app.router.add_post("/chat/stream", handle_chat_stream)

        # ── Desktop Pet Dashboard (Arc Reactor core + 4 panels) ──
        try:
            from ui.dashboard_pet import PET_DASHBOARD
            async def handle_root(request: web.Request) -> web.Response:
                return web.Response(text=PET_DASHBOARD, content_type="text/html", charset="utf-8")
            app.router.add_get("/", handle_root)
        except ImportError:
            pass

        # ── Sci-Fi Dashboard (fallback at /scifi) ──
        try:
            from ui.dashboard_scifi import ScifiDashboard
            from ui.api_bridge import APIBridge

            # Create API bridge — backends injected via _live_backends if set
            backends = getattr(self, '_live_backends', {})
            api = APIBridge(
                mcp_server=self,
                genome=backends.get('genome'),
                arbiter=backends.get('arbiter'),
                agent_profiles=backends.get('agent_profiles'),
                token_tracker=backends.get('token_tracker'),
                memory_store=backends.get('memory_store'),
                skill_loader=backends.get('skill_loader'),
                external_bridge=backends.get('external_bridge'),
                event_bus=backends.get('event_bus'),
                fcpi_tracker=backends.get('fcpi_tracker'),
                session_manager=backends.get('session_manager'),
            )
            api.mount(app)
            print(f"  API Bridge: {len([1 for v in backends.values() if v])} live backends wired")

            scifi = ScifiDashboard()
            scifi.mount(app)
        except ImportError:
            pass

        # ── Dashboard v2.0 (fallback at /classic) ──
        try:
            from ui.dashboard_v2 import DashboardV2, DASHBOARD_HTML
            dashboard = DashboardV2()
            app.router.add_get("/classic", dashboard.handle_dashboard)
            app.router.add_get("/api/status", dashboard.handle_api_status)
        except ImportError:
            pass

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()

        print(f"  MCP HTTP Server: http://{host}:{port}")
        print(f"  Endpoints: /health /tools /chat /chat/stream")

        # Keep running
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        finally:
            await runner.cleanup()
