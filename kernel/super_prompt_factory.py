"""Super Prompt Factory — Dynamic organ-aware prompt assembly.

Assembles the most powerful code-generation prompt by dynamically pulling
context from ALL Sclerotium organs WITHOUT modifying them.

Claude Code: static system prompt + CLAUDE.md injection
Sclerotium OS: DYNAMIC prompt assembled from 6 organ dimensions per task

Six prompt dimensions (each pulls from different organs at runtime):
  D1: IDENTITY       — mycelium.md constitution + STG rhythm phase
  D2: MEMORY         — Hexis 5-layer context + relevant past sessions
  D3: TOOLS          — context-aware tool subset (via ToolRouter)
  D4: EVOLUTION      — FCPI state + best genome patterns + emergent skills
  D5: SAFETY         — ConstitutionalArbiter rules + recent audit findings
  D6: ARCHITECTURE   — codebase structure + recent scan results

Sclerotium ADVANTAGE over Claude Code:
  - Task-adaptive prompt (not one-size-fits-all)
  - Self-improving via evolution feedback loop
  - 5-layer memory provides richer context than CLAUDE.md alone
  - Safety rules dynamically injected based on risk assessment
  - Tool list adapts to task complexity (not all 143 every time)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskDomain(Enum):
    """Task classification for prompt adaptation."""
    CODE_GENERATION = "code_gen"
    CODE_REVIEW = "code_review"
    REFACTORING = "refactor"
    DEBUGGING = "debug"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    DEVOPS = "devops"
    DATA_SCIENCE = "data_science"
    GENERAL = "general"


@dataclass
class PromptAssembly:
    """The assembled super prompt with metadata."""
    full_prompt: str
    dimensions_used: list[str] = field(default_factory=list)
    token_count: int = 0
    task_domain: str = "general"
    cache_zone_breakpoints: list[int] = field(default_factory=list)


class SuperPromptFactory:
    """Dynamic prompt assembler — builds the optimal prompt per task.

    Reads from ALL organs through their public APIs — never modifies them.
    """

    # ── Dimension weights by task domain ──────────────────────────────

    DOMAIN_WEIGHTS: dict[TaskDomain, dict[str, float]] = {
        TaskDomain.CODE_GENERATION: {
            "identity": 1.0, "tools": 1.0, "architecture": 0.9,
            "memory": 0.7, "evolution": 0.6, "safety": 0.5,
        },
        TaskDomain.CODE_REVIEW: {
            "safety": 1.0, "architecture": 0.9, "tools": 0.8,
            "memory": 0.7, "evolution": 0.5, "identity": 0.3,
        },
        TaskDomain.REFACTORING: {
            "architecture": 1.0, "tools": 0.9, "safety": 0.8,
            "memory": 0.7, "evolution": 0.6, "identity": 0.3,
        },
        TaskDomain.DEBUGGING: {
            "memory": 1.0, "tools": 0.9, "architecture": 0.8,
            "safety": 0.5, "evolution": 0.3, "identity": 0.2,
        },
        TaskDomain.ARCHITECTURE: {
            "architecture": 1.0, "evolution": 0.8, "memory": 0.7,
            "tools": 0.6, "safety": 0.5, "identity": 0.4,
        },
        TaskDomain.TESTING: {
            "tools": 1.0, "memory": 0.8, "safety": 0.7,
            "architecture": 0.6, "evolution": 0.4, "identity": 0.2,
        },
        TaskDomain.GENERAL: {
            "identity": 0.8, "tools": 0.8, "memory": 0.7,
            "architecture": 0.5, "safety": 0.5, "evolution": 0.3,
        },
    }

    def __init__(self) -> None:
        self._gateway: Any = None
        self._tools: Any = None
        self._memory: Any = None
        self._arbiter: Any = None
        self._agent_loop: Any = None
        self._cache: Any = None
        self._tool_router: Any = None

    # ── Wiring (uses existing organs, no modification) ──────────────────

    def wire(
        self,
        *,
        gateway: Any = None,
        tools: Any = None,
        memory: Any = None,
        arbiter: Any = None,
        agent_loop: Any = None,
        cache_engine: Any = None,
        tool_router: Any = None,
    ) -> None:
        """Connect to all Sclerotium organs through their public APIs."""
        self._gateway = gateway
        self._tools = tools
        self._memory = memory
        self._arbiter = arbiter
        self._agent_loop = agent_loop
        self._cache = cache_engine
        self._tool_router = tool_router

    # ── Main API ────────────────────────────────────────────────────────

    def classify_task(self, prompt: str) -> TaskDomain:
        """Classify the user's task to optimize prompt dimensions.

        Uses keyword matching (fast, zero-cost).
        Upgrade path: use a local MiniCPM classifier for higher accuracy.
        """
        prompt_lower = prompt.lower()

        code_gen_keywords = [
            "write", "create", "build", "implement", "generate", "code",
            "function", "class", "module", "api", "endpoint", "component",
        ]
        review_keywords = [
            "review", "check", "audit", "inspect", "analyze", "assess",
        ]
        refactor_keywords = [
            "refactor", "restructure", "reorganize", "clean", "simplify",
            "extract", "split", "rename",
        ]
        debug_keywords = [
            "fix", "debug", "bug", "error", "broken", "issue", "crash",
            "wrong", "fails", "not working",
        ]
        test_keywords = [
            "test", "spec", "coverage", "mock", "assert", "pytest",
            "unit test", "integration test",
        ]
        arch_keywords = [
            "architecture", "design", "pattern", "structure", "system",
            "plan", "approach", "strategy",
        ]

        scores = {
            TaskDomain.CODE_GENERATION: sum(
                1 for kw in code_gen_keywords if kw in prompt_lower
            ),
            TaskDomain.CODE_REVIEW: sum(
                1 for kw in review_keywords if kw in prompt_lower
            ),
            TaskDomain.REFACTORING: sum(
                1 for kw in refactor_keywords if kw in prompt_lower
            ),
            TaskDomain.DEBUGGING: sum(
                1 for kw in debug_keywords if kw in prompt_lower
            ),
            TaskDomain.TESTING: sum(
                1 for kw in test_keywords if kw in prompt_lower
            ),
            TaskDomain.ARCHITECTURE: sum(
                1 for kw in arch_keywords if kw in prompt_lower
            ),
        }

        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else TaskDomain.GENERAL

    async def assemble(
        self,
        user_prompt: str,
        *,
        task_domain: TaskDomain | None = None,
        max_tokens: int = 128_000,  # Full context — model decides what matters
    ) -> PromptAssembly:
        """Assemble the optimal super prompt for this specific task.

        This is THE key advantage over Claude Code: instead of one static
        system prompt, Sclerotium builds a task-adaptive prompt from all
        organs in real-time.
        """
        if task_domain is None:
            task_domain = self.classify_task(user_prompt)

        weights = self.DOMAIN_WEIGHTS.get(
            task_domain,
            self.DOMAIN_WEIGHTS[TaskDomain.GENERAL],
        )

        dimensions_used: list[str] = []
        prompt_parts: list[str] = []

        # ── D1: IDENTITY (always included) ──
        identity = self._build_identity(task_domain)
        if identity:
            prompt_parts.append(identity)
            dimensions_used.append("identity")

        # ── D2: MEMORY (load relevant context from 5-layer Hexis) ──
        if weights.get("memory", 0) > 0.3:
            memory_ctx = await self._build_memory_context(user_prompt)
            if memory_ctx:
                prompt_parts.append(memory_ctx)
                dimensions_used.append("memory")

        # ── D3: TOOLS (context-aware subset via ToolRouter) ──
        if weights.get("tools", 0) > 0.3 and self._tool_router:
            tool_defs = self._tool_router.get_relevant_tools(
                user_prompt, task_domain.value, max_tools=20,
            )
            if tool_defs:
                prompt_parts.append(self._format_tools(tool_defs))
                dimensions_used.append("tools")
        elif weights.get("tools", 0) > 0.3 and self._tools:
            # Fallback: include all tools but truncated
            all_tools = self._tools.list_tools()
            prompt_parts.append(self._format_tools(all_tools[:30]))
            dimensions_used.append("tools")

        # ── D4: EVOLUTION (FCPI state + best patterns) ──
        if weights.get("evolution", 0) > 0.3:
            evo_ctx = self._build_evolution_context()
            if evo_ctx:
                prompt_parts.append(evo_ctx)
                dimensions_used.append("evolution")

        # ── D5: SAFETY (Arbiter rules + risk context) ──
        if weights.get("safety", 0) > 0.3 and self._arbiter:
            safety_ctx = self._build_safety_context(task_domain)
            if safety_ctx:
                prompt_parts.append(safety_ctx)
                dimensions_used.append("safety")

        # ── D6: ARCHITECTURE (codebase context) ──
        if weights.get("architecture", 0) > 0.3:
            arch_ctx = self._build_architecture_context()
            if arch_ctx:
                prompt_parts.append(arch_ctx)
                dimensions_used.append("architecture")

        # ── User prompt (always last — cache boundary) ──
        prompt_parts.append(f"<user_request>\n{user_prompt}\n</user_request>")

        full_prompt = "\n\n".join(prompt_parts)
        token_count = len(full_prompt) // 4

        # Truncate if needed (keep user prompt intact)
        if token_count > max_tokens:
            # Trim from middle dimensions, preserving identity + user request
            full_prompt = self._trim_to_budget(
                prompt_parts, max_tokens, keep_first=1, keep_last=1,
            )
            token_count = len(full_prompt) // 4

        return PromptAssembly(
            full_prompt=full_prompt,
            dimensions_used=dimensions_used,
            token_count=token_count,
            task_domain=task_domain.value,
        )

    # ── Dimension builders (read organs, never modify) ──────────────────

    def _build_identity(self, domain: TaskDomain) -> str:
        """D1: Build identity + constitution section."""
        identity = f"""<system identity="sclerotium-os">
You are Sclerotium OS, an electronic lichen life form.
Architecture: Octopus (federal neural) × Slime Mold (least-action) × Lobster (STG rhythm) × Lichen (3-layer symbiosis) × Horse (self-evolving memory).

Current task domain: {domain.value}
Code generation mode: MAXIMUM QUALITY — prefer correctness over brevity.
Write complete, production-ready code with error handling, type hints, and tests.
</system>"""

        # Append mycelium.md constitution if available
        if self._gateway:
            try:
                constitution = self._gateway.load_super_prompt()
                if constitution:
                    identity += f"\n\n<constitution>\n{constitution[:3000]}\n</constitution>"
            except Exception:
                pass

        return identity

    async def _build_memory_context(self, query: str) -> str:
        """D2: Pull relevant memories from 5-layer Hexis store."""
        if not self._memory:
            return ""

        try:
            ctx = self._memory.get_context(query=query, top_k=8)
            memories = ctx.get("relevant_memories", [])
            if not memories:
                return ""

            lines = ["<memory_context source=\"hexis-5layer\">"]
            lines.append("Relevant knowledge from Sclerotium's 5-layer memory:")
            for m in memories[:8]:
                level = m.get("level", "?")
                content = str(m.get("content", ""))[:200]
                lines.append(f"  [{level}] {content}")
            lines.append("</memory_context>")
            return "\n".join(lines)
        except Exception:
            return ""

    def _build_evolution_context(self) -> str:
        """D4: Pull FCPI state and best genome patterns."""
        try:
            # Try to access MiroFish bridge for FCPI state
            import mcp.tools.evolution as evo
            bridge = getattr(evo, '_mirofish_bridge', None) or getattr(evo, '_fungal_bridge', None)
            # Placeholder — full integration reads from active evolution state
            return "<evolution_context>\nFCPI evolution active. Best patterns available via /genome.\n</evolution_context>"
        except Exception:
            return ""

    def _build_safety_context(self, domain: TaskDomain) -> str:
        """D5: Build safety rules based on task risk."""
        if not self._arbiter:
            return ""

        safety = """<safety_rules>
IMMUTABLE RULES (ConstitutionalArbiter 7-layer gate):
1. NEVER modify Windows system files
2. NEVER delete code without human confirmation
3. NEVER access sensitive directories
4. ALL code execution in Sandstorm isolation
5. ALL critical operations go through ConstitutionalArbiter
6. HUMAN is the ultimate decision-maker — you are a symbiote, not a master
</safety_rules>"""

        # Add domain-specific safety emphasis
        if domain == TaskDomain.CODE_GENERATION:
            safety += "\n<!-- Code generation safety: validate all inputs, don't generate security vulnerabilities, use parameterized queries, never hardcode secrets -->"
        elif domain == TaskDomain.REFACTORING:
            safety += "\n<!-- Refactoring safety: preserve existing behavior, don't change public APIs without explicit request, keep backward compatibility -->"

        return safety

    def _build_architecture_context(self) -> str:
        """D6: Build architecture/codebase context."""
        return """<codebase_context>
Sclerotium OS architecture (3-layer lichen):
  ALGAE LAYER (energy/intelligence): DeepSeek V4 Pro, Ollama MiniCPM, Claude Opus
  MEDULLA LAYER (skeleton/transport): MCP Server, EventBus, Hexis 5-layer Memory, ConstitutionalArbiter, Sandstorm
  CONTACT LAYER (senses/movement): CLI TUI, IM Platforms, Desktop Automation, File Watcher

143 MCP tools across 22 categories.
Write code that integrates with this architecture through MCP tools.
</codebase_context>"""

    # ── Tool formatting ──────────────────────────────────────────────────

    def _format_tools(self, tools: list[dict[str, Any]]) -> str:
        """Format tool definitions for the prompt.

        Claude Code equivalent: tool definitions in system prompt,
        with progressive disclosure via defer_loading.
        """
        lines = ["<available_tools>"]
        lines.append("Use these tools to interact with Sclerotium OS organs:")
        for t in tools[:30]:
            name = t.get("name", "?")
            desc = t.get("description", "")[:100]
            params = t.get("parameters", {})
            lines.append(f"\n  {name}: {desc}")
            props = params.get("properties", {})
            for pname, pinfo in list(props.items())[:3]:
                pdesc = pinfo.get("description", "") if isinstance(pinfo, dict) else str(pinfo)
                lines.append(f"    - {pname}: {pdesc[:60]}")
        lines.append("</available_tools>")
        return "\n".join(lines)

    # ── Budget management ───────────────────────────────────────────────

    def _trim_to_budget(
        self,
        parts: list[str],
        max_tokens: int,
        keep_first: int = 1,
        keep_last: int = 1,
    ) -> str:
        """Trim prompt parts to fit within token budget.

        Keeps first N and last N parts intact, trims middle parts.
        """
        if len(parts) <= keep_first + keep_last:
            return "\n\n".join(parts)

        first = parts[:keep_first]
        last = parts[-keep_last:]
        middle = parts[keep_first:-keep_last]

        budget_chars = max_tokens * 4
        first_chars = sum(len(p) for p in first)
        last_chars = sum(len(p) for p in last)
        middle_budget = budget_chars - first_chars - last_chars

        trimmed_middle = []
        used = 0
        for p in middle:
            if used + len(p) <= middle_budget:
                trimmed_middle.append(p)
                used += len(p)
            else:
                remaining = middle_budget - used
                if remaining > 100:
                    trimmed_middle.append(p[:remaining] + "\n... [trimmed]")
                break

        return "\n\n".join(first + trimmed_middle + last)
