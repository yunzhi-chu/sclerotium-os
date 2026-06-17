"""REPL screen — Claude Code-style interactive command REPL.

Provides:
  - Command parsing (slash commands: /evolve, /status, /memory, /scan, ...)
  - Rich markdown rendering for LLM responses
  - Command history
  - Help system
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax


# ── Command definitions ──────────────────────────────────────────────

COMMANDS: dict[str, dict[str, Any]] = {
    "/evolve": {
        "args": "<generations> [--population N]",
        "desc": "Start N-generation evolution run",
        "category": "evolution",
    },
    "/status": {
        "args": "",
        "desc": "Show full system status dashboard",
        "category": "system",
    },
    "/memory": {
        "args": "<query>",
        "desc": "Search system memory across 5 levels",
        "category": "memory",
    },
    "/scan": {
        "args": "[path]",
        "desc": "Run L6 architecture code scan",
        "category": "code",
    },
    "/refactor": {
        "args": "<issue_id>",
        "desc": "View/pending auto-refactor",
        "category": "code",
    },
    "/skills": {
        "args": "",
        "desc": "Browse registered/crystallized skills",
        "category": "skills",
    },
    "/genome": {
        "args": "[genome_id]",
        "desc": "View genome status or list top N",
        "category": "evolution",
    },
    "/sandbox": {
        "args": "<code>",
        "desc": "Execute code in isolated sandbox",
        "category": "sandbox",
    },
    "/audit": {
        "args": "",
        "desc": "View constitutional audit log",
        "category": "safety",
    },
    "/config": {
        "args": "[key] [value]",
        "desc": "View/modify system configuration",
        "category": "system",
    },
    "/digest": {
        "args": "",
        "desc": "Generate daily information digest",
        "category": "info",
    },
    "/mode": {
        "args": "<work|sleep|game|meeting|creative>",
        "desc": "Switch neuromodulation profile",
        "category": "system",
    },
    "/help": {
        "args": "",
        "desc": "Show this help",
        "category": "system",
    },
    "/quit": {
        "args": "",
        "desc": "Exit Sclerotium OS",
        "category": "system",
    },
}


class REPLScreen:
    """Interactive command REPL with Rich rendering."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._history: list[str] = []
        self._command_handlers: dict[str, Callable] = {}
        self._llm_handler: Callable | None = None  # async (prompt: str) -> str

        # Prompt styling
        self._prompt = Text("sclerotium> ", style="bold cyan")

    def register_handler(self, command: str, handler: Callable) -> None:
        """Register a handler for a slash command."""
        self._command_handlers[command] = handler

    def set_llm_handler(self, handler: Callable) -> None:
        """Set the async handler for non-slash LLM messages. handler(prompt: str) -> str"""
        self._llm_handler = handler

    # ── Command parsing ───────────────────────────────────────────────

    def parse_command(self, line: str) -> tuple[str, list[str]]:
        """Parse a command line into (command, args)."""
        parts = line.strip().split()
        if not parts:
            return "", []

        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        return cmd, args

    # ── Rendering ─────────────────────────────────────────────────────

    def render_welcome(self) -> None:
        """Display welcome banner."""
        banner = r"""
╔══════════════════════════════════════════════════════════════╗
║          🧬  SCLEROTIUM OS  v0.2.0                          ║
║          Electronic Lichen Life Form                         ║
║          Octopus × Slime Mold × Lobster × Lichen × Horse     ║
║                                                              ║
║  Type /help for commands    /quit to exit                    ║
╚══════════════════════════════════════════════════════════════╝
"""
        self.console.print(Text(banner, style="bold cyan"))
        self.console.print(
            Text("Self-evolving electronic organism. Symbiotic, not parasitic.", style="dim italic")
        )
        self.console.print(
            Text("Human is the ultimate decision-maker.\n", style="dim")
        )

    def render_help(self) -> None:
        """Render command help."""
        from rich.table import Table

        by_category: dict[str, list[tuple[str, str, str]]] = {}
        for cmd, info in COMMANDS.items():
            cat = info["category"]
            by_category.setdefault(cat, []).append((cmd, info["args"], info["desc"]))

        for cat, cmds in sorted(by_category.items()):
            table = Table(title=f"[{cat}]", border_style="cyan")
            table.add_column("Command", width=16, style="bold cyan")
            table.add_column("Args", width=24, style="dim")
            table.add_column("Description")
            for cmd, args, desc in cmds:
                table.add_row(cmd, args, desc)
            self.console.print(table)
            self.console.print()

    def render_response(self, text: str) -> None:
        """Render an LLM response as markdown."""
        try:
            md = Markdown(text)
            self.console.print(md)
        except Exception:
            self.console.print(text)

    def render_code(self, code: str, language: str = "python") -> None:
        """Render syntax-highlighted code block."""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        self.console.print(syntax)

    def render_error(self, message: str) -> None:
        """Render an error message."""
        self.console.print(Text(f"[ERROR] {message}", style="bold red"))

    def render_info(self, message: str) -> None:
        """Render an info message."""
        self.console.print(Text(f"[INFO] {message}", style="dim"))

    def render_json(self, data: dict[str, Any]) -> None:
        """Render a JSON response nicely."""
        import json
        formatted = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        syntax = Syntax(formatted, "json", theme="monokai")
        self.console.print(syntax)

    # ── REPL loop ────────────────────────────────────────────────────

    async def run_loop(self) -> None:
        """Run the interactive REPL loop."""
        self.render_welcome()

        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.console.input(self._prompt)
                )
            except (EOFError, KeyboardInterrupt):
                self.console.print("\n[INFO] Shutting down...")
                break

            line = line.strip()
            if not line:
                continue

            self._history.append(line)

            # Non-slash: send to LLM through Sclerotium body (Gateway)
            if not line.startswith("/"):
                if self._llm_handler is None:
                    self.render_error("LLM Gateway not connected. Run with --init-all to load bridges.")
                    continue
                self.render_info("Thinking...")
                try:
                    result = self._llm_handler(line)
                    if asyncio.iscoroutine(result):
                        result = await result
                    if result:
                        self.render_response(result)
                    else:
                        self.render_error("LLM returned empty response")
                except Exception as exc:
                    self.render_error(f"Gateway error: {exc}")
                continue

            cmd, args = self.parse_command(line)

            if cmd == "/quit":
                self.console.print("[INFO] Goodbye.", style="dim")
                break
            elif cmd == "/help":
                self.render_help()
            elif cmd in self._command_handlers:
                try:
                    result = self._command_handlers[cmd](args)
                    if asyncio.iscoroutine(result):
                        result = await result
                    if result is not None:
                        if isinstance(result, dict):
                            self.render_json(result)
                        elif isinstance(result, str):
                            self.render_response(result)
                except Exception as exc:
                    self.render_error(str(exc))
            else:
                self.render_error(f"Unknown command: {cmd}. Type /help for available commands.")
