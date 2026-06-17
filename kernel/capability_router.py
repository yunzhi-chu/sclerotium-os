"""Capability Router — Semantic intent → automatic capability activation.

The system that makes Sclerotium OS "just know" what you need.

ARCHITECTURE:
  1. Capability Registry — unified index of ALL capabilities
  2. Auto-Discovery — file watchers + marketplace + GitHub scanners
  3. Semantic Index — keyword/phrase → capability mapping
  4. Intent Router — natural language → active capabilities
  5. Context Injector — auto-adds relevant context to prompts

USER EXPERIENCE:
  User: "build me a FastAPI endpoint with JWT auth"
  System: [auto-detects: fastapi skill, jwt-auth plugin, file_write MCP,
           sandbox MCP, security-audit skill]
  System: [injects all relevant context into prompt]
  System: [generates code using ALL relevant capabilities]
  → NO / needed. Just type naturally.

CAPABILITY SOURCES (auto-discovered):
  1. Skills — SKILL.md files in ~/.sclerotium/skills/, project/.claude/skills/
  2. MCP Tools — local MCP server + MCP market gateway
  3. GitHub Plugins — AI productivity tools from GitHub topics
  4. Built-in Commands — the /-command system
  5. Hexis Memory — past session patterns
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Capability:
    """A single discoverable capability."""
    id: str                          # unique ID
    name: str                        # human-readable name
    type: str                        # "skill", "mcp_tool", "plugin", "command", "memory"
    description: str = ""
    source: str = ""                 # file path, URL, marketplace origin
    keywords: list[str] = field(default_factory=list)       # trigger keywords
    trigger_phrases: list[str] = field(default_factory=list) # multi-word triggers
    auto_activate: bool = True       # auto-activate on keyword match?
    priority: int = 50               # higher = more important
    handler: Any = None              # callable for MCP tools
    skill_content: str = ""          # full SKILL.md content
    usage_count: int = 0             # how many times activated
    last_used: float = 0.0           # timestamp of last use
    confidence: float = 0.5          # how well this matches typical requests

    def match_score(self, user_input: str) -> float:
        """Calculate how well this capability matches user input. Returns 0-1."""
        text = user_input.lower()
        score = 0.0

        # Keyword matching (highest weight)
        for kw in self.keywords:
            if kw.lower() in text:
                score += 0.25
                # Exact word boundary match = stronger signal
                if re.search(rf'\b{re.escape(kw.lower())}\b', text):
                    score += 0.15

        # Phrase matching
        for phrase in self.trigger_phrases:
            if phrase.lower() in text:
                score += 0.4

        # Description matching (weaker signal)
        desc_words = set(self.description.lower().split())
        input_words = set(text.split())
        overlap = desc_words & input_words
        if overlap:
            score += min(0.2, len(overlap) * 0.02)

        # Usage boost — frequently used capabilities get priority
        if self.usage_count > 0:
            score += min(0.1, self.usage_count * 0.01)

        # Recency boost — recently used capabilities get priority
        if self.last_used > 0:
            hours_ago = (time.time() - self.last_used) / 3600
            if hours_ago < 1:
                score += 0.1
            elif hours_ago < 24:
                score += 0.05

        return min(1.0, score)


class CapabilityRouter:
    """Auto-discovers and activates capabilities from natural language.

    The brain that makes Sclerotium OS "just work" without / commands.
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._keyword_index: dict[str, list[str]] = {}  # keyword → capability IDs
        self._activation_log: list[dict[str, Any]] = []
        self._watch_paths: list[Path] = []

    # ═══════════════════════════════════════════════════════════
    # AUTO-DISCOVERY
    # ═══════════════════════════════════════════════════════════

    def discover_all(self) -> dict[str, int]:
        """Scan ALL sources and register every capability found.

        Returns counts by source type.
        """
        counts: dict[str, int] = {}

        # 1. Built-in commands
        counts["commands"] = self._discover_commands()

        # 2. Skills from filesystem
        counts["skills"] = self._discover_skills()

        # 3. MCP tools (if connected)
        counts["mcp_tools"] = self._discover_mcp_tools()

        # 4. GitHub plugins
        counts["plugins"] = self._discover_plugins()

        # 5. Hexis memory patterns
        counts["memory"] = self._discover_memory_patterns()

        return counts

    def _discover_commands(self) -> int:
        """Register all /-commands as capabilities."""
        commands = {
            "help": {"kw": ["help", "commands", "what can you do", "how to"],
                     "desc": "Show available commands and help"},
            "status": {"kw": ["status", "health", "system info", "how are you"],
                      "desc": "Show full system vitals"},
            "model": {"kw": ["model", "switch model", "change model", "which model",
                            "provider", "gpt", "claude", "llama"],
                     "desc": "Switch or configure LLM model"},
            "permission": {"kw": ["permission", "security mode", "auto approve",
                                  "plan mode", "bypass", "ask first"],
                          "desc": "Switch permission/security mode"},
            "generate": {"kw": ["generate", "build", "create project", "scaffold",
                               "full pipeline", "tdd"],
                        "desc": "Full Nine-Laws code generation pipeline"},
            "files": {"kw": ["files", "directory", "folder", "project structure",
                            "list files", "show files", "browse"],
                     "desc": "Browse project files"},
            "open": {"kw": ["open file", "open in editor", "edit file"],
                    "desc": "Open file in default editor"},
            "reason": {"kw": ["reasoning mode", "jury", "dual verify", "fast mode"],
                      "desc": "Switch multi-model reasoning mode"},
            "mode": {"kw": ["work mode", "sleep mode", "creative mode", "game mode"],
                    "desc": "Switch lifeform mode"},
            "memory": {"kw": ["remember", "recall", "memory search", "what did I",
                             "find in memory", "past session"],
                      "desc": "Search 5-layer Hexis memory"},
            "scan": {"kw": ["scan code", "architecture check", "code quality",
                           "analyze codebase"],
                    "desc": "Run L6 architecture code scan"},
            "evolve": {"kw": ["evolve", "evolution", "generation", "mutate code",
                             "self improve"],
                      "desc": "Start FCPI evolution"},
            "sandbox": {"kw": ["sandbox", "execute safely", "run in isolation",
                              "test this code"],
                       "desc": "Execute code in isolated sandbox"},
            "search": {"kw": ["search", "find online", "look up", "google", "web search",
                             "latest", "current", "recent", "news", "what is",
                             "how to", "documentation for", "docs for", "API for",
                             "who is", "when did", "where is", "why is",
                             "2026", "2025", "update on"],
                       "desc": "Search the web for current information"},
            "fetch": {"kw": ["fetch", "read url", "open link", "get page",
                            "download page", "check website"],
                     "desc": "Fetch and read a web page"},
        }

        count = 0
        for name, info in commands.items():
            cap = Capability(
                id=f"cmd:{name}",
                name=f"/{name}",
                type="command",
                description=info["desc"],
                source="builtin",
                keywords=info["kw"],
                trigger_phrases=info.get("phrases", []),
                auto_activate=info.get("auto", True),
                priority=40,
            )
            self._register(cap)
            count += 1
        return count

    def _discover_skills(self) -> int:
        """Auto-discover skills from filesystem SKILL.md files."""
        count = 0
        search_paths = [
            Path.home() / ".sclerotium" / "skills",
            Path.home() / ".claude" / "skills",
            Path("./skills"),
            Path("./.claude/skills"),
            Path("C:/Users/34442/Desktop/porject/Quantitative model/fungal-cortex/skills"),
        ]

        for base in search_paths:
            if not base.exists():
                continue
            self._watch_paths.append(base)
            for skill_file in base.rglob("SKILL.md"):
                try:
                    meta = self._parse_skill_frontmatter(skill_file)
                    name = meta.get("name", skill_file.parent.name)
                    desc = meta.get("description", f"Skill: {name}")
                    keywords = meta.get("keywords", [])
                    # Auto-extract keywords from description
                    if not keywords:
                        keywords = self._extract_keywords(desc)
                    # Add filename words as keywords
                    keywords.extend(name.lower().replace("-", " ").replace("_", " ").split())

                    cap = Capability(
                        id=f"skill:{name}",
                        name=name,
                        type="skill",
                        description=desc,
                        source=str(skill_file),
                        keywords=keywords,
                        trigger_phrases=meta.get("triggers", []),
                        auto_activate=True,
                        priority=60,
                        skill_content=skill_file.read_text(encoding="utf-8", errors="replace"),
                    )
                    self._register(cap)
                    count += 1
                except Exception:
                    pass
        return count

    def _discover_mcp_tools(self) -> int:
        """Register MCP tools as auto-activatable capabilities."""
        count = 0
        try:
            from mcp.server import SclerotiumMCPServer
            mcp = SclerotiumMCPServer()
            mcp.register_all_tools()
            for tool in mcp.tools.list_tools():
                name = tool.get("name", "")
                desc = tool.get("description", "")
                cat = tool.get("category", "general")
                keywords = self._extract_keywords(f"{name} {desc} {cat}")
                keywords.append(name)

                cap = Capability(
                    id=f"mcp:{name}",
                    name=name,
                    type="mcp_tool",
                    description=desc,
                    source=f"mcp://{cat}",
                    keywords=keywords,
                    auto_activate=True,
                    priority=55,
                    handler=mcp.tools.get_handler(name),
                )
                self._register(cap)
                count += 1
        except Exception:
            pass
        return count

    def _discover_plugins(self) -> int:
        """Register known AI productivity plugins as capabilities."""
        # Well-known plugins with their trigger keywords
        plugins = [
            ("plugin:git", "Git Workflow", ["git", "commit", "push", "pull", "branch", "merge", "pr", "pull request"],
             "Git integration for Sclerotium OS"),
            ("plugin:docker", "Docker Integration", ["docker", "container", "image", "compose", "kubernetes", "k8s"],
             "Docker container management"),
            ("plugin:database", "Database Tools", ["database", "sql", "migration", "schema", "postgres", "mysql", "sqlite"],
             "Database schema and migration tools"),
            ("plugin:testing", "Testing Suite", ["test", "testing", "pytest", "jest", "coverage", "mock", "assert"],
             "Comprehensive testing framework integration"),
            ("plugin:linting", "Code Quality", ["lint", "format", "prettier", "eslint", "ruff", "black", "style"],
             "Code quality and linting tools"),
            ("plugin:ci_cd", "CI/CD Pipeline", ["ci", "cd", "deploy", "pipeline", "github actions", "jenkins"],
             "CI/CD pipeline integration"),
            ("plugin:docs", "Documentation", ["docs", "documentation", "readme", "api docs", "swagger", "openapi"],
             "Documentation generation tools"),
            ("plugin:debug", "Debugging Tools", ["debug", "breakpoint", "trace", "profile", "inspect", "log"],
             "Debugging and profiling tools"),
            ("plugin:api", "API Development", ["api", "rest", "graphql", "endpoint", "fastapi", "flask", "express", "route"],
             "API development and testing tools"),
            ("plugin:frontend", "Frontend Tools", ["react", "vue", "component", "ui", "css", "tailwind", "html", " frontend"],
             "Frontend development tools"),
            ("plugin:auth", "Authentication", ["auth", "login", "jwt", "oauth", "session", "token", "password", "2fa"],
             "Authentication and authorization tools"),
            ("plugin:data", "Data Science", ["data", "pandas", "numpy", "ml", "machine learning", "ai model", "train"],
             "Data science and ML tools"),
        ]

        count = 0
        for pid, name, keywords, desc in plugins:
            cap = Capability(
                id=pid,
                name=name,
                type="plugin",
                description=desc,
                source="plugin_registry",
                keywords=keywords,
                auto_activate=True,
                priority=45,
            )
            self._register(cap)
            count += 1
        return count

    def _discover_memory_patterns(self) -> int:
        """Register frequently-used patterns from Hexis memory as capabilities."""
        # Placeholder — in production, scans semantic memory for patterns
        return 0

    # ═══════════════════════════════════════════════════════════
    # SEMANTIC INTENT ROUTING
    # ═══════════════════════════════════════════════════════════

    def route(self, user_input: str, max_capabilities: int = 10) -> list[Capability]:
        """Given natural language input, return the most relevant capabilities.

        This is THE magic — user types naturally, system auto-activates
        the right skills, tools, and plugins.
        """
        # Don't route slash commands through semantic matching
        if user_input.strip().startswith("/"):
            return []

        scored = []
        for cap in self._capabilities.values():
            score = cap.match_score(user_input)
            if score > 0.15:  # Minimum relevance threshold
                scored.append((score, cap))

        # Sort by score descending, take top N
        scored.sort(key=lambda x: -x[0])
        activated = [cap for _, cap in scored[:max_capabilities]]

        # Update usage stats
        for cap in activated:
            cap.usage_count += 1
            cap.last_used = time.time()

        # Log activation
        if activated:
            self._activation_log.append({
                "input": user_input[:200],
                "activated": [c.id for c in activated],
                "timestamp": time.time(),
            })

        return activated

    def build_context_injection(
        self, user_input: str, max_capabilities: int = 8,
    ) -> str:
        """Build the context injection string for auto-activated capabilities.

        This is what gets injected into the system prompt so the LLM
        knows what capabilities are available for this specific request.
        """
        caps = self.route(user_input, max_capabilities)
        if not caps:
            return ""

        lines = ["<auto_activated_capabilities>"]
        lines.append("The following capabilities are available for this request "
                     "(auto-detected from your message):")

        by_type: dict[str, list[Capability]] = {}
        for c in caps:
            by_type.setdefault(c.type, []).append(c)

        for ctype in ["skill", "plugin", "mcp_tool", "command", "memory"]:
            items = by_type.get(ctype, [])
            if items:
                type_label = {"skill": "Skills", "plugin": "Plugins",
                             "mcp_tool": "MCP Tools", "command": "Commands",
                             "memory": "Relevant Memories"}.get(ctype, ctype)
                lines.append(f"\n{type_label}:")
                for item in items[:5]:
                    lines.append(f"  • {item.name}: {item.description[:100]}")

                    # For skills, include brief content preview
                    if item.type == "skill" and item.skill_content:
                        preview = item.skill_content[:300].replace("\n", " ")
                        lines.append(f"    {preview}")

        lines.append("\nUse these capabilities automatically. No need for / commands.")
        lines.append("</auto_activated_capabilities>")

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════
    # REGISTRY MANAGEMENT
    # ═══════════════════════════════════════════════════════════

    def _register(self, cap: Capability) -> None:
        """Register a capability and index its keywords."""
        self._capabilities[cap.id] = cap
        for kw in cap.keywords:
            kw_lower = kw.lower()
            self._keyword_index.setdefault(kw_lower, []).append(cap.id)

    def register_external(self, cap: Capability) -> None:
        """Public API: register an externally-discovered capability."""
        self._register(cap)

    def unregister(self, cap_id: str) -> None:
        """Remove a capability."""
        if cap_id in self._capabilities:
            cap = self._capabilities.pop(cap_id)
            for kw in cap.keywords:
                kw_lower = kw.lower()
                if kw_lower in self._keyword_index:
                    self._keyword_index[kw_lower] = [
                        cid for cid in self._keyword_index[kw_lower]
                        if cid != cap_id
                    ]

    def get(self, cap_id: str) -> Capability | None:
        return self._capabilities.get(cap_id)

    def list_all(self, cap_type: str = "all") -> list[Capability]:
        """List all capabilities, optionally filtered by type."""
        if cap_type == "all":
            return list(self._capabilities.values())
        return [c for c in self._capabilities.values() if c.type == cap_type]

    def search(self, query: str, limit: int = 20) -> list[Capability]:
        """Search capabilities by name or description."""
        q = query.lower()
        results = []
        for cap in self._capabilities.values():
            if q in cap.name.lower() or q in cap.description.lower():
                results.append(cap)
            elif any(q in kw.lower() for kw in cap.keywords):
                results.append(cap)
        return results[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Get capability ecosystem statistics."""
        by_type: dict[str, int] = {}
        for c in self._capabilities.values():
            by_type[c.type] = by_type.get(c.type, 0) + 1

        return {
            "total_capabilities": len(self._capabilities),
            "by_type": by_type,
            "keyword_index_size": len(self._keyword_index),
            "activation_log_entries": len(self._activation_log),
            "watch_paths": len(self._watch_paths),
        }

    # ═══════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════

    def _parse_skill_frontmatter(self, path: Path) -> dict[str, Any]:
        """Extract metadata from SKILL.md frontmatter."""
        try:
            content = path.read_text(encoding="utf-8", errors="replace")[:3000]
            meta: dict[str, Any] = {}
            in_fm = False
            for line in content.split("\n"):
                line = line.strip()
                if line == "---":
                    if not in_fm:
                        in_fm = True
                        continue
                    else:
                        break
                if in_fm and ":" in line:
                    key, _, val = line.partition(":")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key == "keywords" or key == "triggers":
                        meta[key] = [v.strip() for v in val.split(",") if v.strip()]
                    else:
                        meta[key] = val
            return meta
        except Exception:
            return {}

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text."""
        # Remove common words, keep technical terms
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                      "has", "have", "had", "do", "does", "did", "will", "would",
                      "can", "could", "should", "may", "might", "shall", "to",
                      "of", "in", "for", "on", "with", "at", "by", "from", "as",
                      "it", "its", "or", "and", "not", "no", "this", "that",
                      "these", "those", "use", "using", "used", "provide"}

        words = re.findall(r'[a-zA-Z][a-zA-Z0-9_+#.-]*', text.lower())
        keywords = []
        for w in words:
            if w not in stop_words and len(w) > 2:
                keywords.append(w)

        # Also extract multi-word technical terms
        technical_patterns = [
            r'fastapi', r'react\s*(js|native)?', r'vue\.?js', r'next\.?js',
            r'django', r'flask', r'express\.?js', r'spring\s*boot',
            r'postgres(ql)?', r'mysql', r'mongodb', r'redis',
            r'docker', r'kubernetes', r'k8s', r'aws', r'azure', r'gcp',
            r'jwt', r'oauth2?', r'openid', r'sso',
            r'graphql', r'rest\s*api', r'grpc', r'websocket',
            r'pytest', r'jest', r'mocha', r'cypress',
            r'css', r'scss', r'tailwind', r'bootstrap',
            r'git', r'github', r'gitlab', r'bitbucket',
            r'ci/cd', r'devops', r'mlops',
            r'typescript', r'javascript', r'python', r'rust', r'go(lang)?',
            r'tdd', r'bdd', r'ddd',
            r'linux', r'windows', r'mac\s*os',
        ]
        for pattern in technical_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                keywords.append(match.group(0).lower().replace(" ", ""))

        return list(set(keywords))[:30]  # Deduplicate, limit
