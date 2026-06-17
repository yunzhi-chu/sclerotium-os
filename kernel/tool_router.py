"""Tool Router — Context-aware progressive disclosure for 143 tools.

Claude Code uses defer_loading: send lightweight tool stubs, load full schema
only when the model selects a tool. This prevents cache invalidation when
tools are added/removed.

Sclerotium ADVANTAGE: with 143 tools (3.5x Claude Code's 40+), progressive
disclosure is even more critical. This module:
  1. Classifies the task to determine which tool categories are relevant
  2. Returns lightweight stubs for all tools (for cache stability)
  3. Loads full schemas only for the ~15 most relevant tools
  4. Supports dynamic tool discovery (model can request more tools)

Task → Tool category mapping (learned from 50-generation evolution data):
  code_gen     → file_write, file_edit, bash, sandbox, code_scan, test_gen
  code_review  → file_read, code_scan, architecture_scanner, formal_verify
  refactor     → file_read, file_write, auto_refactor, semantic_refactor, code_scan
  debug        → file_read, debugger, sandbox, memory_search, formal_verify
  architecture → file_read, code_scan, architecture_scanner, call_graph, genome
  testing      → file_read, sandbox, test_generator, code_scan, formal_verify
  devops       → bash, sandbox, system_status, scheduler, file_read
  general      → system_status, memory_search, skill_list, file_read, model_list
"""

from __future__ import annotations

from typing import Any


# ── Task → Tool category mapping ────────────────────────────────────────

TASK_TOOL_MAP: dict[str, list[str]] = {
    "code_gen": [
        "file_write", "file_edit", "bash_execute", "sandbox_execute",
        "code_scan", "test_generator", "file_read", "memory_search",
        "auto_refactor", "semantic_refactor", "call_graph",
        "skill_list", "system_status",
    ],
    "code_review": [
        "file_read", "code_scan", "architecture_scanner", "formal_verifier",
        "call_graph", "memory_search", "sandbox_execute", "system_status",
    ],
    "refactor": [
        "file_read", "file_write", "file_edit", "auto_refactor",
        "semantic_refactor", "code_scan", "call_graph", "architecture_scanner",
        "sandbox_execute", "formal_verifier", "test_generator",
    ],
    "debug": [
        "file_read", "debugger_agent", "sandbox_execute", "memory_search",
        "formal_verifier", "bash_execute", "code_scan", "system_status",
    ],
    "architecture": [
        "file_read", "code_scan", "architecture_scanner", "call_graph",
        "genome_list", "genome_get", "memory_search", "system_status",
    ],
    "testing": [
        "file_read", "sandbox_execute", "test_generator", "code_scan",
        "formal_verifier", "bash_execute", "memory_search",
    ],
    "devops": [
        "bash_execute", "sandbox_execute", "system_status", "scheduler_add",
        "scheduler_list", "file_read", "file_write",
    ],
    "general": [
        "system_status", "memory_search", "skill_list", "file_read",
        "model_list", "provider_list", "sandbox_execute",
    ],
    "data_science": [
        "file_read", "file_write", "sandbox_execute", "bash_execute",
        "memory_search", "code_scan",
    ],
}

# Tools that are ALWAYS included (lightweight, essential)
ALWAYS_TOOLS = [
    "system_status", "memory_search", "skill_list", "file_read",
]

# Tool categories and their typical token cost (full schema)
TOOL_CATEGORY_COST: dict[str, int] = {
    "system": 200,
    "evolution": 400,
    "memory": 300,
    "sandbox": 250,
    "skills": 350,
    "code_analysis": 500,
    "im": 600,
    "desktop": 550,
    "scheduler": 400,
    "files": 300,
    "info": 300,
    "mode": 150,
    "gateways": 350,
    "advanced": 800,
    "sovereign": 900,
    "genesis": 700,
    "cosmic": 800,
    "omega": 600,
    "innovation": 700,
    "apotheosis": 650,
    "cache": 300,
    "benchmark": 500,
}


class ToolRouter:
    """Context-aware tool schema loader — progressive disclosure.

    Claude Code equivalent: defer_loading + tool stub pattern.
    Sclerotium ADVANTAGE: 143 tools managed with semantic task routing.
    """

    def __init__(self, tools_registry: Any = None) -> None:
        self._tools = tools_registry
        self._tool_index: dict[str, dict[str, Any]] = {}
        self._category_index: dict[str, list[str]] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Index all tools by name and category for fast lookup."""
        if self._tools is None:
            return
        try:
            all_tools = self._tools.list_tools()
            for t in all_tools:
                name = t.get("name", "")
                cat = t.get("category", "general")
                self._tool_index[name] = t
                self._category_index.setdefault(cat, []).append(name)
        except Exception:
            pass

    # ── Main API ────────────────────────────────────────────────────────

    def get_relevant_tools(
        self,
        task_description: str,
        task_domain: str = "general",
        *,
        max_tools: int = 20,
        include_always: bool = True,
    ) -> list[dict[str, Any]]:
        """Get the most relevant tools for this task.

        Claude Code equivalent: the tool list built per-turn based on
        task context. Only ~15 of 40+ tools are sent with full schemas.

        Args:
            task_description: The user's task (used for semantic matching)
            task_domain: Classified domain (code_gen, debug, etc.)
            max_tools: Maximum tools to return with full schemas
            include_always: Always include essential tools

        Returns:
            List of tool definitions (name, description, parameters)
        """
        if not self._tool_index:
            return []

        selected_names: set[str] = set()

        # Always-include tools
        if include_always:
            for name in ALWAYS_TOOLS:
                if name in self._tool_index:
                    selected_names.add(name)

        # Domain-specific tools (from learned mapping)
        domain_tools = TASK_TOOL_MAP.get(task_domain, TASK_TOOL_MAP["general"])
        for name in domain_tools:
            if name in self._tool_index and len(selected_names) < max_tools:
                selected_names.add(name)

        # Keyword-based semantic matching (cheap, zero-cost)
        task_lower = task_description.lower()
        keyword_map = {
            "memory": ["memory", "remember", "recall", "history", "past"],
            "evolution": ["evolve", "evolution", "generation", "genome", "mutate"],
            "sandbox": ["execute", "run", "sandbox", "test", "code"],
            "im": ["message", "send", "wechat", "feishu", "telegram", "qq"],
            "desktop": ["desktop", "screen", "click", "type", "automation"],
            "scheduler": ["schedule", "cron", "timer", "repeat", "daily"],
            "skills": ["skill", "capability", "ability", "register"],
            "code_analysis": ["scan", "architecture", "refactor", "analyze"],
            "gateways": ["model", "provider", "gateway", "api"],
            "benchmark": ["benchmark", "evaluate", "score", "measure"],
        }

        for category, keywords in keyword_map.items():
            if any(kw in task_lower for kw in keywords):
                cat_tools = self._category_index.get(category, [])
                for name in cat_tools:
                    if name in self._tool_index and len(selected_names) < max_tools:
                        selected_names.add(name)

        # Build result with tool definitions
        result = []
        for name in selected_names:
            tool_def = self._tool_index[name]
            result.append({
                "name": name,
                "description": tool_def.get("description", "")[:120],
                "parameters": tool_def.get("parameters", {}),
                "category": tool_def.get("category", "general"),
            })

        return result

    def get_tool_stubs(self) -> list[dict[str, Any]]:
        """Get lightweight stubs for ALL tools (cache-safe).

        Claude Code equivalent: the defer_loading pattern — send only
        tool names + short descriptions. Full schema loaded on demand.
        This keeps the SEMI_STATIC cache zone stable.
        """
        if not self._tool_index:
            return []

        stubs = []
        for name, tool_def in self._tool_index.items():
            stubs.append({
                "name": name,
                "description": tool_def.get("description", "")[:80],
                "category": tool_def.get("category", "general"),
                # Lightweight — no full parameters schema
                "parameters": {"type": "object", "properties": {}},
            })
        return stubs

    def get_full_schema(self, tool_name: str) -> dict[str, Any] | None:
        """Load the full schema for a specific tool (on-demand).

        Called when the model selects a tool stub for use.
        Claude Code equivalent: loading the full tool schema after selection.
        """
        return self._tool_index.get(tool_name)

    def get_tools_by_category(self, category: str) -> list[dict[str, Any]]:
        """Get all tools in a category."""
        names = self._category_index.get(category, [])
        return [
            self._tool_index[name]
            for name in names
            if name in self._tool_index
        ]

    def estimate_token_cost(self, tool_names: list[str]) -> int:
        """Estimate the token cost of including these tools' full schemas."""
        total = 0
        for name in tool_names:
            tool_def = self._tool_index.get(name, {})
            cat = tool_def.get("category", "general")
            total += TOOL_CATEGORY_COST.get(cat, 300)
        return total

    def get_stats(self) -> dict[str, Any]:
        """Get tool routing statistics."""
        return {
            "total_tools": len(self._tool_index),
            "categories": len(self._category_index),
            "always_tools": len(ALWAYS_TOOLS),
            "domain_mappings": len(TASK_TOOL_MAP),
            "avg_full_schema_cost": sum(TOOL_CATEGORY_COST.values()) // len(TOOL_CATEGORY_COST),
            "estimated_full_load_tokens": sum(
                TOOL_CATEGORY_COST.get(t.get("category", "general"), 300)
                for t in self._tool_index.values()
            ),
            "estimated_routed_tokens": sum(
                TOOL_CATEGORY_COST.get(t.get("category", "general"), 300)
                for name, t in self._tool_index.items()
                if name in TASK_TOOL_MAP.get("code_gen", [])
            ),
        }
