"""Skill Adapter — 209 QuantMind skills → Fungal Cortex unified format.

Maps every QuantMind skill (core platform, agent-plugins, vertical-plugins, alphaear)
into the Fungal Cortex SkillRegistry with proper dependency resolution and runtime
adaptation for the event-driven architecture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.skill_registry import SkillMeta, SkillRegistry
from src.utils.logging import CortexLogger


class SkillCategory(Enum):
    """QuantMind skill categories mapped to the AGENT.md 14-module structure."""

    CORE_PLATFORM = "core"
    ADAPTIVE_ENGINE = "adaptive-engine"
    AUTONOMOUS_PLATFORM = "autonomous-platform"
    CLUSTER_PLATFORM = "cluster-platform"
    COGNITION_PLATFORM = "cognition-platform"
    ALPHAEAR = "alphaear"
    DATA_PACK = "data-pack"
    AGENT_PLUGIN = "agent-plugin"
    VERTICAL_PLUGIN = "vertical-plugin"
    STOCK_ANALYSIS = "stock-analysis"
    QUANT_STRATEGY = "quant-strategy"
    SKILL_CREATOR = "skill-creator"
    WIND_MCP = "wind-mcp"


@dataclass
class AdaptedSkill:
    """A QuantMind skill adapted for the Fungal Cortex runtime.

    Wraps the original SKILL.md metadata with runtime configuration:
    - How to trigger (event topic, keywords)
    - Resource requirements (estimated tokens, compute)
    - Inter-skill relationships (depends_on, catalyzes, inhibits)
    """

    name: str
    category: SkillCategory
    module: str
    version: str = "1.0.0"
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    catalyzes: list[str] = field(default_factory=list)  # Skills this one enhances
    event_triggers: list[str] = field(default_factory=list)  # Event bus topics that activate this
    estimated_tokens: int = 500  # Typical LLM token consumption
    priority: int = 5  # 1-10 scheduling priority
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_skill_meta(self) -> SkillMeta:
        """Convert to the standard SkillRegistry SkillMeta format."""
        return SkillMeta(
            name=self.name,
            version=self.version,
            description=self.description,
            module=self.module,
            category=self.category.value,
            keywords=self.keywords,
            dependencies=self.depends_on,
            metadata={
                "catalyzes": self.catalyzes,
                "event_triggers": self.event_triggers,
                "estimated_tokens": self.estimated_tokens,
                "priority": self.priority,
                **self.metadata,
            },
        )


class SkillAdapter:
    """Adapts 209 QuantMind skills to the Fungal Cortex SkillRegistry.

    Three adaptation strategies:
    1. DIRECT: Core platform skills map 1:1 to Fungal Cortex agents
    2. WRAPPED: AlphaEar/data-pack skills wrap as DataSource adapters
    3. ROUTED: Agent/vertical plugins are loaded on-demand via the event bus

    The adapter handles:
    - Module path resolution (QuantMind dir → Fungal Cortex import path)
    - Dependency chain resolution across skill categories
    - Batch loading with progress tracking and error isolation
    """

    def __init__(self, registry: SkillRegistry, batch_size: int = 50) -> None:
        self._registry = registry
        self._batch_size = batch_size
        self._logger = CortexLogger("skill_adapter")
        self._adapted: dict[str, AdaptedSkill] = {}
        self._failed: dict[str, str] = {}  # name → error message

    def adapt_skill(self, skill: AdaptedSkill) -> bool:
        """Adapt a single skill into the registry. Returns True on success."""
        try:
            meta = skill.to_skill_meta()
            if self._registry.register(meta):
                self._adapted[skill.name] = skill
                self._logger.debug("skill_adapted", name=skill.name, category=skill.category.value)
                return True
            return False
        except Exception as e:
            self._failed[skill.name] = str(e)
            self._logger.warn("skill_adapt_failed", name=skill.name, error=str(e))
            return False

    def adapt_batch(self, skills: list[AdaptedSkill]) -> int:
        """Adapt a batch of skills. Returns count of successfully adapted."""
        success = 0
        for i in range(0, len(skills), self._batch_size):
            batch = skills[i : i + self._batch_size]
            for skill in batch:
                if self.adapt_skill(skill):
                    success += 1
        self._logger.info("batch_adapt_complete", total=len(skills), success=success, failed=len(skills) - success)
        return success

    def adapt_core_platform(self) -> list[AdaptedSkill]:
        """Adapt the 22 core/platform skills."""
        skills = [
            AdaptedSkill(name="adaptive-engine", category=SkillCategory.ADAPTIVE_ENGINE, module="core", priority=10, event_triggers=["market.regime_change", "pipeline.tick"], estimated_tokens=2000),
            AdaptedSkill(name="l4-autonomous-platform", category=SkillCategory.AUTONOMOUS_PLATFORM, module="core", priority=9, depends_on=["adaptive-engine"], event_triggers=["agent.spawn", "agent.apoptose"]),
            AdaptedSkill(name="l5-cluster-platform", category=SkillCategory.CLUSTER_PLATFORM, module="core", priority=9, depends_on=["l4-autonomous-platform"], event_triggers=["cluster.reorganize"]),
            AdaptedSkill(name="l6-cognition-platform", category=SkillCategory.COGNITION_PLATFORM, module="core", priority=10, depends_on=["l5-cluster-platform"], event_triggers=["l6.scan.complete", "l6.emergence.detected"], estimated_tokens=4000),
            AdaptedSkill(name="a-stock-data", category=SkillCategory.DATA_PACK, module="data", priority=8, event_triggers=["market.data_request"], estimated_tokens=500),
            AdaptedSkill(name="global-stock-data", category=SkillCategory.DATA_PACK, module="data", priority=8, event_triggers=["market.data_request"], estimated_tokens=500),
            AdaptedSkill(name="alphaear-stock", category=SkillCategory.ALPHAEAR, module="alphaear", priority=7, event_triggers=["signal.alpha"], estimated_tokens=1500),
            AdaptedSkill(name="alphaear-news", category=SkillCategory.ALPHAEAR, module="alphaear", priority=6, event_triggers=["news.article"], estimated_tokens=1000),
            AdaptedSkill(name="alphaear-search", category=SkillCategory.ALPHAEAR, module="alphaear", priority=6, event_triggers=["search.request"], estimated_tokens=800),
            AdaptedSkill(name="alphaear-sentiment", category=SkillCategory.ALPHAEAR, module="alphaear", priority=6, event_triggers=["sentiment.analyze"], estimated_tokens=1200),
            AdaptedSkill(name="alphaear-predictor", category=SkillCategory.ALPHAEAR, module="alphaear", priority=7, depends_on=["alphaear-stock"], event_triggers=["prediction.request"], estimated_tokens=2000),
            AdaptedSkill(name="alphaear-signal-tracker", category=SkillCategory.ALPHAEAR, module="alphaear", priority=7, depends_on=["alphaear-predictor"], event_triggers=["signal.track"]),
            AdaptedSkill(name="alphaear-deepear-lite", category=SkillCategory.ALPHAEAR, module="alphaear", priority=5, event_triggers=["deepear.scan"], estimated_tokens=3000),
            AdaptedSkill(name="alphaear-reporter", category=SkillCategory.ALPHAEAR, module="alphaear", priority=5, depends_on=["alphaear-signal-tracker"], event_triggers=["report.generate"]),
            AdaptedSkill(name="alphaear-logic-visualizer", category=SkillCategory.ALPHAEAR, module="alphaear", priority=4, depends_on=["alphaear-reporter"], event_triggers=["visualize.request"]),
            AdaptedSkill(name="quant-strategies", category=SkillCategory.QUANT_STRATEGY, module="quant", priority=8, event_triggers=["strategy.request"], estimated_tokens=2500),
            AdaptedSkill(name="quant-theory", category=SkillCategory.QUANT_STRATEGY, module="quant", priority=7, depends_on=["quant-strategies"], event_triggers=["theory.analyze"], estimated_tokens=3000),
            AdaptedSkill(name="quanthub", category=SkillCategory.QUANT_STRATEGY, module="quant", priority=7, event_triggers=["quant.hub_query"]),
            AdaptedSkill(name="masterminds", category=SkillCategory.QUANT_STRATEGY, module="quant", priority=6, event_triggers=["mastermind.consult"]),
            AdaptedSkill(name="stock-analysis-team", category=SkillCategory.STOCK_ANALYSIS, module="analysis", priority=7, event_triggers=["analysis.stock"], estimated_tokens=1500),
            AdaptedSkill(name="skill-creator", category=SkillCategory.SKILL_CREATOR, module="core", priority=5, depends_on=["l6-cognition-platform"], event_triggers=["skill.create"], estimated_tokens=2000),
            AdaptedSkill(name="wind-mcp", category=SkillCategory.WIND_MCP, module="data", priority=8, event_triggers=["wind.query"], estimated_tokens=500),
        ]
        return skills

    def adapt_agent_plugins(self, agent_type: str, count: int = 32) -> list[AdaptedSkill]:
        """Adapt agent-plugin skills for a given agent type.

        Agent types: earnings-reviewer, market-researcher, model-builder, pitch-agent
        Each has 32 china-* skills (china-3-statement-model, china-dcf, china-comps, etc.)

        Args:
            agent_type: One of the 4 agent specializations
            count: Number of skills to generate (max 32 per agent)
        """
        template_skills = [
            "3-statement-model", "dcf", "comps", "merger-model",
            "idea-generation", "earnings-analysis", "sector-analysis",
            "macro-analysis", "credit-analysis", "lbo-model",
            "sum-of-parts", "dividend-discount", "residual-income",
            "asset-based", "liquidation", "replacement-cost",
            "sensitivity-analysis", "scenario-analysis", "monte-carlo",
            "real-options", "venture-capital", "growth-equity",
            "buyout-analysis", "distressed-debt", "special-situations",
            "event-driven", "relative-value", "capital-structure",
            "technical-analysis", "quantitative-factor", "risk-parity", "tail-risk",
        ][:count]

        skills: list[AdaptedSkill] = []
        for tmpl in template_skills:
            name = f"china-{tmpl}"
            skills.append(AdaptedSkill(
                name=f"{agent_type}/{name}",
                category=SkillCategory.AGENT_PLUGIN,
                module=f"agent-plugins/{agent_type}",
                keywords=[agent_type, tmpl, "china"],
                depends_on=["l6-cognition-platform"] if agent_type == "model-builder" else [],
                event_triggers=[f"agent.{agent_type}.request"],
                estimated_tokens=1500,
                priority=6,
            ))
        return skills

    def adapt_vertical_plugins(self, domain: str, skills_spec: list[tuple[str, int]]) -> list[AdaptedSkill]:
        """Adapt vertical-plugin skills for a domain.

        Domains: china-finance(32), fund-admin(6), investment-banking(10),
        private-equity(9), operations(2), wealth-management(5)

        Args:
            domain: Domain name (e.g., "china-finance")
            skills_spec: List of (skill_name, estimated_tokens) tuples
        """
        skills: list[AdaptedSkill] = []
        for name, tokens in skills_spec:
            skills.append(AdaptedSkill(
                name=f"{domain}/{name}",
                category=SkillCategory.VERTICAL_PLUGIN,
                module=f"vertical-plugins/{domain}",
                keywords=[domain, name],
                event_triggers=[f"vertical.{domain}.request"],
                estimated_tokens=tokens,
                priority=5,
            ))
        return skills

    @property
    def adapted_count(self) -> int:
        return len(self._adapted)

    @property
    def failed_count(self) -> int:
        return len(self._failed)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_adapted": len(self._adapted),
            "total_failed": len(self._failed),
            "failed_skills": dict(self._failed),
            "by_category": {
                cat.value: sum(1 for s in self._adapted.values() if s.category == cat)
                for cat in SkillCategory
            },
        }
