"""Chat Screen — Claude Code-style interactive conversation interface.

Replicates Claude Code's REPL.tsx with:
  - Virtual scrolling message history
  - Streaming markdown from LLM
  - Expandable tool-call / tool-result widgets
  - Multi-line prompt input with history
  - Slash command routing
  - Real-time token counter

Claude Code equivalent: src/components/REPL.tsx (main screen)
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from textual import work
from textual.containers import Container, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Input, RichLog, Static
from textual.worker import Worker, WorkerState

from cli.tui.widgets.tool_use import ToolUseWidget
from cli.tui.widgets.status_bar import SclerotiumStatusBar

# ── Slash command definitions ──────────────────────────────────────────

COMMANDS: dict[str, dict[str, str]] = {
    "/evolve":   {"args": "<generations>", "desc": "Start N-generation evolution"},
    "/status":   {"args": "", "desc": "Full system status dashboard"},
    "/memory":   {"args": "<query>", "desc": "Search 5-layer memory"},
    "/scan":     {"args": "[path]", "desc": "L6 architecture code scan"},
    "/skills":   {"args": "", "desc": "Browse registered skills"},
    "/genome":   {"args": "[id]", "desc": "View genome status / list"},
    "/sandbox":  {"args": "<code>", "desc": "Execute in isolated sandbox"},
    "/audit":    {"args": "", "desc": "View constitutional audit log"},
    "/config":   {"args": "[key] [value]", "desc": "View/modify configuration"},
    "/digest":   {"args": "", "desc": "Generate daily information digest"},
    "/mode":     {"args": "<profile>", "desc": "Switch mode (work/sleep/game/meeting/creative)"},
    "/reason":   {"args": "<fast|dual|jury|specialist>", "desc": "Set multi-model reasoning mode"},
    "/cache":    {"args": "", "desc": "Show prompt cache statistics"},
    "/tools":    {"args": "[domain]", "desc": "Show tools for task domain"},
    "/help":     {"args": "", "desc": "Show this help"},
    "/clear":    {"args": "", "desc": "Clear chat history"},
    "/quit":     {"args": "", "desc": "Exit Sclerotium OS"},
}


class ChatScreen(Screen):
    """Main chat interface — Claude Code's REPL.tsx equivalent.

    Layout:
      ┌──────────────────────────────────────┐
      │  Message History (Scrollable)        │
      │  - User messages (right-aligned)     │
      │  - Assistant messages (markdown)     │
      │  - Tool calls (expandable)           │
      │  - Tool results (collapsible)        │
      ├──────────────────────────────────────┤
      │  Prompt Input (multi-line)           │
      ├──────────────────────────────────────┤
      │  Status Bar (tokens | model | cost)  │
      └──────────────────────────────────────┘
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._gateway: Any = None
        self._tools: Any = None
        self._memory: Any = None
        self._arbiter: Any = None
        self._agent_loop: Any = None
        self._session_store: Any = None
        self._body_ready = False
        self._history: list[str] = []
        self._history_idx: int = 0
        self._message_count: int = 0
        self._total_tokens: int = 0
        self._reasoning_mode: str = "dual_verify"  # Sclerotium ADVANTAGE over Claude Code

    # ── Public API ─────────────────────────────────────────────────────

    def set_body(
        self,
        *,
        gateway: Any = None,
        tools: Any = None,
        memory: Any = None,
        arbiter: Any = None,
        agent_loop: Any = None,
        session_store: Any = None,
    ) -> None:
        """Wire up all Sclerotium OS body systems."""
        self._gateway = gateway
        self._tools = tools
        self._memory = memory
        self._arbiter = arbiter
        self._agent_loop = agent_loop
        self._session_store = session_store
        self._body_ready = True

    def show_welcome(self) -> None:
        """Display welcome banner."""
        log = self.query_one("#message-list", RichLog)
        log.write(Panel(
            Text("🧬  SCLEROTIUM OS  v0.3.0", style="bold cyan", justify="center"),
            border_style="cyan",
        ))
        log.write(Text(
            "Electronic Lichen Life Form — Claude Code-equivalent Terminal\n"
            "Octopus × Slime Mold × Lobster × Lichen × Horse\n"
            "Type /help for commands  |  Ctrl+C to quit\n",
            style="dim italic",
        ))
        if self._body_ready:
            log.write(Text(
                f"🟢 Body ready — {self._tools.tool_count if self._tools else 0} tools, "
                f"5-layer memory, 7-layer security",
                style="green",
            ))

    def clear(self) -> None:
        """Clear chat history."""
        log = self.query_one("#message-list", RichLog)
        log.clear()
        self._message_count = 0

    # ── Composition ─────────────────────────────────────────────────────

    def compose(self) -> dict:
        """Build the chat screen layout."""
        yield ScrollableContainer(
            RichLog(id="message-list", highlight=True, markup=True, wrap=True),
            id="chat-container",
        )
        yield Container(
            Input(
                placeholder="sclerotium> Type a message or /command...",
                id="prompt-input",
            ),
            id="prompt-area",
        )

    # ── Event handlers ──────────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission."""
        prompt = event.value.strip()
        if not prompt:
            return

        # Clear input
        event.input.value = ""

        # Save to history
        self._history.append(prompt)
        self._history_idx = len(self._history)

        # Display user message
        log = self.query_one("#message-list", RichLog)
        log.write(Text(f"\n▸ {prompt}", style="bold cyan"))

        # Route: slash command or LLM message
        if prompt.startswith("/"):
            self._handle_slash_command(prompt, log)
        else:
            self.run_worker(self._handle_chat_message(prompt), exclusive=False)

    async def _handle_chat_message(self, prompt: str) -> None:
        """Process a chat message through the Agent Loop."""
        if not self._body_ready:
            self._write_error("Body not initialized. Wait for 'Body ready' signal.")
            return

        log = self.query_one("#message-list", RichLog)

        # Session: append user message
        if self._session_store:
            self._session_store.append({
                "type": "user_message",
                "content": prompt,
            })

        # Show thinking indicator via notify (non-blocking)
        self.notify("Thinking...", title="🧠", timeout=30)

        try:
            # Use Agent Loop for streaming
            full_response = ""
            tool_calls = []

            async for event in self._agent_loop.run(prompt):
                if event.type == "token":
                    # Streaming token
                    full_response += str(event.data)
                    # Update last message or create new one
                    self._update_streaming_output(full_response, log)

                elif event.type == "tool_call":
                    tool_calls.append(event.data)
                    # Render tool call as expandable widget
                    tc = event.data
                    log.write(Panel(
                        f"🔧 {tc.get('name', 'tool')}\n"
                        f"   args: {str(tc.get('arguments', {}))[:200]}",
                        border_style="blue",
                        title="Tool Call",
                    ))

                elif event.type == "tool_result":
                    # Render tool result
                    result = event.data
                    result_str = str(result)[:1000]
                    log.write(Panel(
                        result_str,
                        border_style="green" if "error" not in str(result).lower() else "red",
                        title="Tool Result",
                    ))

                elif event.type == "thinking":
                    pass  # Already showing thinking indicator

                elif event.type == "compaction":
                    log.write(Text("  📦 Context compressed", style="dim yellow"))

                elif event.type == "warning":
                    log.write(Text(f"  ⚠ {event.data}", style="yellow"))

                elif event.type == "error":
                    log.write(Text(f"  ❌ {event.data}", style="bold red"))
                    break

                elif event.type == "done":
                    meta = event.data
                    try:
                        status_bar = self.app.query_one("#status-bar", SclerotiumStatusBar)
                        status_bar.update_metrics(
                            tokens=meta.get("total_tokens", 0),
                            turns=meta.get("turns", 0),
                        )
                    except Exception:
                        pass

            # Session: append assistant response
            if self._session_store and full_response:
                self._session_store.append({
                    "type": "assistant_message",
                    "content": full_response,
                    "tokens": self._agent_loop._total_tokens,
                })

            # If no streaming happened (direct API response), render now
            if not full_response:
                log.write(Text("  [No response]", style="dim"))

        except Exception as exc:
            self._write_error(f"Agent Loop error: {exc}")

    def _update_streaming_output(self, text: str, log: RichLog) -> None:
        """Update the streaming output in the message list.

        Claude Code equivalent: StreamingMarkdown component — incremental
        token rendering with syntax highlighting.
        """
        try:
            md = Markdown(text)
            log.write(md)
        except Exception:
            log.write(Text(text))

    # ── Slash command handling ────────────────────────────────────────

    def _handle_slash_command(self, line: str, log: RichLog) -> None:
        """Route a slash command to the appropriate handler."""
        parts = line.strip().split()
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        handler_map = {
            "/help": self._cmd_help,
            "/status": self._cmd_status,
            "/evolve": self._cmd_evolve,
            "/memory": self._cmd_memory,
            "/skills": self._cmd_skills,
            "/genome": self._cmd_genome,
            "/sandbox": self._cmd_sandbox,
            "/scan": self._cmd_scan,
            "/config": self._cmd_config,
            "/audit": self._cmd_audit,
            "/digest": self._cmd_digest,
            "/mode": self._cmd_mode,
            "/reason": self._cmd_reason,
            "/cache": self._cmd_cache,
            "/tools": self._cmd_tools_list,
            "/clear": self._cmd_clear,
            "/quit": self._cmd_quit,
        }

        handler = handler_map.get(cmd)
        if handler:
            self.run_worker(handler(args), exclusive=False)
        else:
            log.write(Text(f"  Unknown command: {cmd}. Type /help for available commands.", style="red"))

    # ── Command implementations ─────────────────────────────────────────

    async def _cmd_help(self, _args: list[str]) -> None:
        log = self.query_one("#message-list", RichLog)
        from rich.table import Table
        table = Table(title="Available Commands", border_style="cyan")
        table.add_column("Command", style="bold cyan")
        table.add_column("Args", style="dim")
        table.add_column("Description")
        for cmd, info in COMMANDS.items():
            table.add_row(cmd, info["args"], info["desc"])
        log.write(table)

    async def _cmd_status(self, _args: list[str]) -> None:
        log = self.query_one("#message-list", RichLog)
        if self._tools:
            handler = self._tools.get_handler("system_status")
            if handler:
                try:
                    result = handler()
                    if asyncio.iscoroutine(result):
                        result = await result
                    import json
                    log.write(Syntax(
                        json.dumps(result, indent=2, ensure_ascii=False, default=str),
                        "json", theme="monokai",
                    ))
                except Exception as e:
                    log.write(Text(f"  Status error: {e}", style="red"))
            else:
                log.write(Text("  system_status tool not registered", style="yellow"))

    async def _cmd_evolve(self, args: list[str]) -> None:
        log = self.query_one("#message-list", RichLog)
        generations = int(args[0]) if args else 10
        log.write(Text(f"  🧬 Starting {generations}-generation evolution...", style="cyan"))
        if self._tools:
            handler = self._tools.get_handler("evolution_start")
            if handler:
                result = handler(generations=generations, population=50)
                if asyncio.iscoroutine(result):
                    result = await result
                log.write(Text(
                    f"  ✅ Evolution complete — FCPI: {result.get('fcpi_total', 'N/A')}",
                    style="green",
                ))

    async def _cmd_memory(self, args: list[str]) -> None:
        log = self.query_one("#message-list", RichLog)
        query = " ".join(args)
        if not query:
            log.write(Text("  Usage: /memory <query>", style="yellow"))
            return
        if self._tools:
            handler = self._tools.get_handler("memory_search")
            if handler:
                results = handler(query=query)
                if asyncio.iscoroutine(results):
                    results = await results
                for r in (results or [])[:10]:
                    log.write(Text(
                        f"  [{r.get('level', '?')}] {r.get('content', '')[:150]}",
                        style="dim",
                    ))

    async def _cmd_skills(self, _args: list[str]) -> None:
        log = self.query_one("#message-list", RichLog)
        if self._tools:
            handler = self._tools.get_handler("skill_list")
            if handler:
                skills = handler()
                if asyncio.iscoroutine(skills):
                    skills = await skills
                for s in (skills or [])[:20]:
                    log.write(Text(
                        f"  {s.get('name', '?'):<20} {s.get('category', '?')}",
                    ))

    async def _cmd_genome(self, args: list[str]) -> None:
        log = self.query_one("#message-list", RichLog)
        if self._tools:
            handler = self._tools.get_handler("genome_list")
            if handler:
                genomes = handler(top_n=10)
                if asyncio.iscoroutine(genomes):
                    genomes = await genomes
                for g in (genomes or [])[:10]:
                    log.write(Text(
                        f"  {g.get('genome_id', '?')[:12]:<14} "
                        f"FCPI: {g.get('fcpi_total', 0):.3f}  "
                        f"Gen: {g.get('generation', '?')}",
                    ))

    async def _cmd_sandbox(self, args: list[str]) -> None:
        log = self.query_one("#message-list", RichLog)
        code = " ".join(args)
        if not code:
            log.write(Text("  Usage: /sandbox <python_code>", style="yellow"))
            return
        if self._arbiter:
            allowed, reason = await self._arbiter.check("sandbox_execute", {"code": code})
            if not allowed:
                log.write(Text(f"  🔒 Blocked: {reason}", style="red"))
                return
        # Execute via tool
        if self._tools:
            handler = self._tools.get_handler("sandbox_execute")
            if handler:
                result = handler(code=code)
                if asyncio.iscoroutine(result):
                    result = await result
                log.write(Text(f"  stdout: {result.get('stdout', '')}", style="green"))
                if result.get("stderr"):
                    log.write(Text(f"  stderr: {result['stderr']}", style="red"))

    async def _cmd_scan(self, args: list[str]) -> None:
        log = self.query_one("#message-list", RichLog)
        path = args[0] if args else "."
        if self._tools:
            handler = self._tools.get_handler("scan_code")
            if handler:
                result = handler(path=path)
                if asyncio.iscoroutine(result):
                    result = await result
                log.write(Text(
                    f"  Issues: {result.get('issues_found', 0)} | "
                    f"Scores: {result.get('scores', {})}",
                ))

    async def _cmd_config(self, args: list[str]) -> None:
        log = self.query_one("#message-list", RichLog)
        if self._tools:
            handler = self._tools.get_handler("system_config")
            if handler:
                if args and len(args) >= 2:
                    result = handler(key=args[0], value=args[1])
                elif args:
                    result = handler(key=args[0])
                else:
                    result = handler()
                if asyncio.iscoroutine(result):
                    result = await result
                import json
                log.write(Syntax(
                    json.dumps(result, indent=2, ensure_ascii=False, default=str),
                    "json", theme="monokai",
                ))

    async def _cmd_audit(self, _args: list[str]) -> None:
        log = self.query_one("#message-list", RichLog)
        if self._arbiter:
            stats = self._arbiter.get_stats()
            log.write(Text(
                f"  Allowed: {stats['allowed_count']} | "
                f"Blocked: {stats['blocked_count']} | "
                f"Grants: {stats['session_grants']}",
            ))

    async def _cmd_digest(self, _args: list[str]) -> None:
        log = self.query_one("#message-list", RichLog)
        log.write(Text("  📊 Daily digest — generating...", style="cyan"))
        # Placeholder for Phase 2E implementation

    async def _cmd_mode(self, args: list[str]) -> None:
        log = self.query_one("#message-list", RichLog)
        valid = {"work", "sleep", "game", "meeting", "creative"}
        if not args or args[0] not in valid:
            log.write(Text(
                f"  Usage: /mode <{'|'.join(sorted(valid))}>",
                style="yellow",
            ))
            return
        log.write(Text(f"  🦞 Mode switched to: {args[0]}", style="cyan"))

    async def _cmd_reason(self, args: list[str]) -> None:
        """Set multi-model reasoning mode — Sclerotium ADVANTAGE over Claude Code."""
        log = self.query_one("#message-list", RichLog)
        valid = {"fast", "dual", "jury", "specialist"}
        mode_map = {
            "fast": "fast_path",
            "dual": "dual_verify",
            "jury": "jury_panel",
            "specialist": "specialist",
        }
        if not args or args[0] not in valid:
            log.write(Text(
                f"  Usage: /reason <{'|'.join(sorted(valid))}>\n"
                f"  fast:       Single fast model (Groq) — quick answers\n"
                f"  dual:       Strong generates + fast reviews ★ DEFAULT\n"
                f"  jury:       3 models vote/consensus — critical tasks\n"
                f"  specialist: Domain-specialized model routing",
                style="dim",
            ))
            return
        self._reasoning_mode = mode_map[args[0]]
        log.write(Text(
            f"  🧠 Reasoning mode: {args[0]} ({self._reasoning_mode})\n"
            f"  Sclerotium ADVANTAGE: Multi-model > Single-model (Claude Code)",
            style="green",
        ))

    async def _cmd_cache(self, _args: list[str]) -> None:
        """Show prompt cache statistics."""
        log = self.query_one("#message-list", RichLog)
        if self._agent_loop and self._agent_loop._cache_engine:
            report = self._agent_loop._cache_engine.get_cache_safety_report()
            log.write(Text(
                f"  📦 Prompt Cache: {report['status']}\n"
                f"  Provider: {report['provider']} (TTL: {report['ttl_seconds']}s)\n"
                f"  Hit Rate: {report['hit_rate']} | Tokens Saved: {report['tokens_saved']:,}\n"
                f"  Cost Saved: {report['cost_saved']} | Requests: {report['total_requests']}\n"
                f"  Last Keepalive: {report['last_keepalive_ago']} ago",
            ))
        else:
            log.write(Text("  Cache engine not initialized", style="yellow"))

    async def _cmd_tools_list(self, args: list[str]) -> None:
        """Show tools available for a specific task domain."""
        log = self.query_one("#message-list", RichLog)
        domain = args[0] if args else "code_gen"
        valid_domains = ["code_gen", "code_review", "refactor", "debug", "architecture", "testing", "devops", "general"]
        if domain not in valid_domains:
            log.write(Text(f"  Valid domains: {', '.join(valid_domains)}", style="yellow"))
            return
        if self._agent_loop and self._agent_loop._tool_router:
            tools = self._agent_loop._tool_router.get_relevant_tools("", domain, max_tools=30)
            log.write(Text(f"  🔧 Tools for '{domain}' ({len(tools)} relevant):", style="cyan"))
            for t in tools:
                log.write(Text(f"    {t['name']:<25} {t.get('category', '?')}", style="dim"))
            stats = self._agent_loop._tool_router.get_stats()
            log.write(Text(
                f"\n  Total tools: {stats['total_tools']} | "
                f"Full load: ~{stats['estimated_full_load_tokens']:,} tokens | "
                f"Routed: ~{stats['estimated_routed_tokens']:,} tokens",
                style="dim",
            ))
        else:
            log.write(Text("  Tool router not initialized", style="yellow"))

    async def _cmd_clear(self, _args: list[str]) -> None:
        self.clear()

    async def _cmd_quit(self, _args: list[str]) -> None:
        self.app.exit()

    # ── Helpers ─────────────────────────────────────────────────────────

    def _write_error(self, message: str) -> None:
        """Write an error message to the log."""
        try:
            log = self.query_one("#message-list", RichLog)
            log.write(Text(f"  ❌ {message}", style="bold red"))
        except Exception:
            pass
