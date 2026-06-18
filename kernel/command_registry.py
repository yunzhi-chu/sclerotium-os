"""Unified Command Registry — aggregates ALL commands from every ecosystem source.

Claude Code has Skills, MCP tools, Hooks, Plugins, and Slash Commands all
discoverable through the `/` menu. This module does the same for Sclerotium:

Sources:
  1. Built-in commands (/help, /status, /clear, etc.)
  2. MCP tools (143 tools across 22 categories)
  3. fungal-cortex Skills (~6,067 SKILL.md files)
  4. Connected MCP market tools
  5. User-defined custom commands

Every command has:
  - name: unique identifier (e.g., "tool.file_read", "skill.python-testing")
  - slug: short alias for /-invocation (e.g., "/file_read", "/python-testing")
  - description: one-line help text
  - source: where it came from (builtin/mcp/skill/market/custom)
  - category: grouping label
  - handler: optional callable, or None if it's an LLM-prompt skill
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kernel.project_paths import SKILLS_DIR, Callable


@dataclass
class Command:
    """A single discoverable command."""
    name: str
    slug: str
    description: str = ""
    source: str = "builtin"      # builtin, mcp, skill, market, custom
    category: str = "general"
    handler: Callable | None = None
    args_hint: str = ""
    skill_path: str = ""          # Path to SKILL.md for skills
    skill_content: str = ""       # Cached skill content


class CommandRegistry:
    """Unified registry of ALL commands from ALL sources.

    Usage:
        reg = CommandRegistry()
        reg.load_builtins()
        reg.load_mcp_tools(tool_registry)
        reg.load_skills(skills_dir)
        reg.load_market_tools(market_gateway)

        matches = reg.search("/file")  # → [Command("tool.file_read", ...), ...]
    """

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}
        self._by_source: dict[str, list[str]] = {}
        self._by_category: dict[str, list[str]] = {}

    # ── Loading ───────────────────────────────────────────────────────

    def register(self, cmd: Command) -> None:
        self._commands[cmd.name] = cmd
        self._by_source.setdefault(cmd.source, []).append(cmd.name)
        self._by_category.setdefault(cmd.category, []).append(cmd.name)

    def load_builtins(self) -> int:
        """Register all built-in slash commands."""
        builtins = [
            ("builtin.help", "/help", "Show help and available commands", "general"),
            ("builtin.status", "/status", "Full system vitals and organism status", "system"),
            ("builtin.dashboard", "/dashboard", "Open full-screen organism dashboard", "system"),
            ("builtin.clear", "/clear", "Clear chat history", "general"),
            ("builtin.quit", "/quit", "Exit Sclerotium OS", "general"),
            ("builtin.files", "/files", "Browse project files with icons and sizes", "files"),
            ("builtin.open", "/open", "Open file in default editor", "files"),
            ("builtin.cat", "/cat", "View file with syntax highlighting", "files"),
            ("builtin.scan", "/scan", "Run L6 architecture code scan", "code"),
            ("builtin.reason", "/reason", "Set multi-model reasoning mode (fast/dual/jury)", "model"),
            ("builtin.mode", "/mode", "Switch lifeform mode (work/sleep/game/meeting/creative)", "system"),
            ("builtin.compact", "/compact", "Compress conversation context (Claude Code-style 5-layer pipeline)", "system"),
            ("builtin.selftest", "/selftest", "Run full terminal self-test — test all tool categories and report status", "system"),
            ("builtin.memory", "/memory", "Search 5-layer Hexis memory", "memory"),
            ("builtin.genome", "/genome", "View evolution genomes and FCPI scores", "evolution"),
            ("builtin.evolve", "/evolve", "Start N-generation FCPI evolution run", "evolution"),
            ("builtin.sandbox", "/sandbox", "Execute code in isolated Sandstorm sandbox", "code"),
            ("builtin.audit", "/audit", "View Constitutional Arbiter audit log", "security"),
            ("builtin.digest", "/digest", "Generate daily information digest", "info"),
            ("builtin.cache", "/cache", "Show prompt cache statistics", "system"),
            ("builtin.permission", "/permission", "Switch permission mode (plan/default/accept-edits/auto/dont-ask/bypass)", "security"),
            ("builtin.model", "/model", "Switch LLM model or configure parameters", "model"),
            ("builtin.generate", "/generate", "Full 7-stage TDD pipeline: spec-tests-code-verify-review-learn", "code"),
            ("builtin.skills", "/skills", "List all loaded skills", "skills"),
            ("builtin.search", "/search", "Search the web (Claude Code WebSearch equivalent)", "web"),
            ("builtin.fetch", "/fetch", "Fetch URL content as markdown (Claude Code WebFetch equivalent)", "web"),
            ("builtin.git", "/git", "Show git working tree status", "git"),
            ("builtin.diff", "/diff", "Show git diff with +/- highlighting", "git"),
            ("builtin.log", "/log", "Show git commit history", "git"),
            ("builtin.blame", "/blame", "Show git blame for a file", "git"),
            ("builtin.sessions", "/sessions", "List/resume/fork saved sessions", "system"),
            ("builtin.doctor", "/doctor", "Run environment diagnostic (Claude Code Doctor equivalent)", "system"),
            ("builtin.mcp", "/mcp", "Manage MCP server connections (list/connect/disconnect)", "system"),
            ("builtin.ide", "/ide", "Open project in IDE (code/cursor/windsurf/idea)", "system"),
            ("builtin.daemon", "/daemon", "Start/stop background autonomous daemon", "system"),
            ("builtin.bash", "/bash", "Execute shell command (Claude Code Bash equivalent)", "shell"),
            ("builtin.run", "/run", "Smart run — auto-detects project and executes", "shell"),
            ("builtin.update", "/update", "Check for or apply Sclerotium OS updates", "system"),
            ("builtin.vim", "/vim", "Toggle vim keybindings in input", "system"),
            ("builtin.organs", "/organs", "Explore all 170+ organ symphony (sense/think/act/evolve/metabolize)", "system"),
            ("builtin.tools", "/tools", "List all loaded MCP tools", "tools"),
            ("builtin.reasoning", "/reasoning", "Show current multi-model reasoning config", "model"),
        ]
        for name, slug, desc, cat in builtins:
            self.register(Command(name=name, slug=slug, description=desc, source="builtin", category=cat))
        return len(builtins)

    def load_mcp_tools(self, tool_registry: Any) -> int:
        """Register all MCP tools as /-commands."""
        if tool_registry is None:
            return 0
        count = 0
        try:
            for tool in tool_registry.list_tools():
                tname = tool.get("name", "")
                tdesc = tool.get("description", "")[:100]
                tcat = tool.get("category", "general")
                slug = f"/tool.{tname}" if not tname.startswith("/") else tname
                self.register(Command(
                    name=f"mcp.{tname}",
                    slug=slug,
                    description=f"[MCP] {tdesc}",
                    source="mcp",
                    category=tcat,
                ))
                count += 1
        except Exception:
            pass
        return count

    def load_skills(self, skills_dir: str | Path = "") -> int:
        """Scan a skills directory for SKILL.md files and register them.

        Scans these locations:
          1. fungal-cortex/skills/
          2. sclerotium-os/skills/
          3. User ~/.sclerotium/skills/
        """
        count = 0
        search_dirs = []

        if skills_dir:
            search_dirs.append(Path(skills_dir))
        else:
            # Default search paths
            candidates = [
                SKILLS_DIR,
                Path("./skills"),
                Path.home() / ".sclerotium" / "skills",
            ]
            for d in candidates:
                if d.exists():
                    search_dirs.append(d)

        for base_dir in search_dirs:
            try:
                for skill_file in base_dir.rglob("SKILL.md"):
                    skill_name = skill_file.parent.name if skill_file.parent.name != "skills" else skill_file.stem
                    desc, category = self._parse_skill_frontmatter(skill_file)

                    self.register(Command(
                        name=f"skill.{skill_name}",
                        slug=f"/{skill_name}",
                        description=f"[Skill] {desc}",
                        source="skill",
                        category=category,
                        skill_path=str(skill_file),
                    ))
                    count += 1
            except Exception:
                pass

        return count

    def _parse_skill_frontmatter(self, path: Path) -> tuple[str, str]:
        """Extract name + description from SKILL.md frontmatter."""
        try:
            content = path.read_text(encoding="utf-8", errors="replace")[:2000]
            desc = ""
            category = "skills"
            in_frontmatter = False
            for line in content.split("\n"):
                line = line.strip()
                if line == "---":
                    if not in_frontmatter:
                        in_frontmatter = True
                        continue
                    else:
                        break
                if in_frontmatter:
                    if line.startswith("description:"):
                        desc = line.split(":", 1)[1].strip().strip('"')
                    elif line.startswith("category:"):
                        category = line.split(":", 1)[1].strip().strip('"')
                    elif line.startswith("name:"):
                        name = line.split(":", 1)[1].strip().strip('"')
                        if not desc:
                            desc = name
            return desc or path.stem, category
        except Exception:
            return path.stem, "skills"

    # ── Search / Autocomplete ─────────────────────────────────────────

    def search(self, query: str, limit: int = 15) -> list[Command]:
        """Find commands matching a partial query.

        Used for the `/` autocomplete dropdown. Matches against
        slug, name, description, and category.
        """
        q = query.lower().lstrip("/")
        if not q:
            # Show all commands grouped by source
            return sorted(self._commands.values(), key=lambda c: (c.source, c.name))[:limit]

        results = []
        for cmd in self._commands.values():
            score = 0
            if q in cmd.slug.lower():
                score = 100
            elif q in cmd.name.lower():
                score = 80
            elif q in cmd.description.lower():
                score = 50
            elif q in cmd.category.lower():
                score = 30
            if score > 0:
                results.append((score, cmd))

        results.sort(key=lambda x: -x[0])
        return [cmd for _, cmd in results[:limit]]

    def get(self, slug: str) -> Command | None:
        """Find a command by its slug (e.g., '/file_read')."""
        slug_clean = slug.lower().strip()
        for cmd in self._commands.values():
            if cmd.slug.lower() == slug_clean:
                return cmd
        return None

    def get_by_name(self, name: str) -> Command | None:
        return self._commands.get(name)

    # ── Stats ─────────────────────────────────────────────────────────

    @property
    def total_commands(self) -> int:
        return len(self._commands)

    def stats(self) -> dict[str, Any]:
        return {
            "total": len(self._commands),
            "by_source": {s: len(names) for s, names in self._by_source.items()},
            "by_category": {c: len(names) for c, names in sorted(self._by_category.items())},
            "skills_loaded": len(self._by_source.get("skill", [])),
            "mcp_tools_loaded": len(self._by_source.get("mcp", [])),
        }

    def all_commands(self) -> list[Command]:
        return sorted(self._commands.values(), key=lambda c: (c.source, c.category, c.name))
