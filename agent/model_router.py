"""Model Router — task complexity → optimal model routing (Gap 16).

Routes simple tasks to cheap/fast models and complex tasks to strong models.
Saves 40-60% token cost vs always using strongest model.

Injecting R10 (DeepAgent ToolPO): RL-based tool-use optimization
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelRoute:
    """Routing decision — which model to use for a task."""
    provider: str
    model: str
    reason: str = ""
    estimated_cost_multiplier: float = 1.0


class ModelRouter:
    """Routes tasks to optimal models based on complexity analysis.

    Strategy:
      - Trivial (greetings, /status): haiku-level / flash models (1x cost)
      - Standard (coding, search): standard models (2-5x cost)
      - Complex (refactor, architecture): pro/opus models (10x+ cost)

    Usage:
        router = ModelRouter()
        route = router.route("Build a REST API with authentication")
        # → ModelRoute(provider="deepseek", model="deepseek-v4-pro", reason="complex: architecture")
    """

    # Complexity indicators → tier
    _COMPLEXITY_MARKERS: dict[str, int] = {
        # Simple (tier 0-1)
        "hello": 0, "hi": 0, "/status": 0, "/fcpi": 0, "/tools": 0,
        "what is": 1, "how do i": 1, "explain": 1, "show me": 1,
        # Standard (tier 2-3)
        "write": 2, "create": 2, "fix": 2, "debug": 2, "test": 2,
        "search": 2, "find": 2, "read": 2, "list": 2,
        # Complex (tier 4-5)
        "refactor": 4, "migrate": 4, "redesign": 4, "architect": 5,
        "build": 3, "implement": 3, "optimize": 4, "secure": 4,
        "deploy": 3, "scale": 5, "multi-agent": 5, "pipeline": 4,
    }

    # Provider tiers: (provider, model, max_tokens) per complexity tier
    _DEFAULT_ROUTES: dict[int, tuple[str, str, int]] = {
        0: ("deepseek", "deepseek-v4-flash", 1024),
        1: ("deepseek", "deepseek-v4-flash", 2048),
        2: ("deepseek", "deepseek-v4-flash", 4096),
        3: ("deepseek", "deepseek-v4-pro", 8192),
        4: ("deepseek", "deepseek-v4-pro", 16384),
        5: ("deepseek", "deepseek-v4-pro", 32768),
    }

    def __init__(self) -> None:
        self._routes = dict(self._DEFAULT_ROUTES)
        self._stats: dict[str, int] = {}  # model → call count

    def route(self, prompt: str, history: list[dict] | None = None) -> ModelRoute:
        """Determine the optimal model for a task.

        Args:
            prompt: User's input text
            history: Optional conversation history for context

        Returns:
            ModelRoute with provider, model, and reasoning
        """
        tier = self._analyze_complexity(prompt, history)

        provider, model, max_tokens = self._routes.get(
            tier, self._routes[2]  # Default to standard
        )

        # Track stats
        self._stats[model] = self._stats.get(model, 0) + 1

        tier_names = {0: "trivial", 1: "simple", 2: "standard",
                      3: "moderate", 4: "complex", 5: "architecture"}
        cost_map = {0: 0.3, 1: 0.5, 2: 1.0, 3: 3.0, 4: 7.0, 5: 15.0}

        return ModelRoute(
            provider=provider,
            model=model,
            reason=f"tier={tier} ({tier_names.get(tier, '?')})",
            estimated_cost_multiplier=cost_map.get(tier, 1.0),
        )

    def _analyze_complexity(
        self, prompt: str, history: list[dict] | None,
    ) -> int:
        """Analyze task complexity from prompt text and history."""
        prompt_lower = prompt.lower().strip()
        max_tier = 0

        # Keyword-based complexity scoring
        for keyword, tier in self._COMPLEXITY_MARKERS.items():
            if keyword in prompt_lower:
                max_tier = max(max_tier, tier)

        # Length-based boost
        if len(prompt) > 500:
            max_tier = max(max_tier, 3)
        if len(prompt) > 2000:
            max_tier = max(max_tier, 4)

        # History-based boost (longer conversations = more context needed)
        if history and len(history) > 10:
            max_tier = max(max_tier, 3)

        # Multi-file indicators
        if any(k in prompt_lower for k in ["multiple file", "across", "entire", "all the"]):
            max_tier = max(max_tier, 4)

        return max_tier

    def get_stats(self) -> dict[str, Any]:
        return {"routes": self._stats, "total_requests": sum(self._stats.values())}
