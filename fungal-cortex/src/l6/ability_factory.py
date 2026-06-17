"""L6 M2: AbilityCreationFactory — LLM-guided capability creation with sandbox verification.

Creates new skills from detected gaps:
1. Gap analysis → requirements specification
2. LLM code generation (with retry up to max_retries)
3. Syntax validation (ast.parse)
4. Sandbox verification (Docker → backtest)
5. Registration in skill registry
"""

from __future__ import annotations

import ast
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.event_bus import EventBus
from src.core.skill_registry import SkillMeta, SkillRegistry
from src.l6.architecture_scanner import ArchitectureIssue
from src.l6.sandbox_pipeline import SandboxResult, SandboxVerificationPipeline
from src.utils.logging import CortexLogger


class CreationStatus(Enum):
    ANALYZING = "analyzing"
    GENERATING = "generating"
    VALIDATING = "validating"
    SANDBOX_TESTING = "sandbox_testing"
    REGISTERING = "registering"
    COMPLETE = "complete"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class CreationSpec:
    """Specification for a new skill to be created."""

    name: str
    category: str  # "strategy", "indicator", "analysis", "utility"
    description: str
    gap_source: str = ""  # The ArchitectureIssue.id that triggered this
    language: str = "python"
    dependencies: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


@dataclass
class CreationTask:
    """State tracking for an ongoing creation task."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    spec: CreationSpec | None = None
    status: CreationStatus = CreationStatus.ANALYZING
    generated_files: dict[str, str] = field(default_factory=dict)  # filename → content
    syntax_valid: bool = False
    sandbox_result: SandboxResult | None = None
    retry_count: int = 0
    error_message: str = ""
    registered_skill_name: str = ""
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None


class AbilityCreationFactory:
    """M2: LLM-guided ability creation with full verification pipeline.

    Flow: gap → spec → generate → syntax check → sandbox → register
    """

    def __init__(
        self,
        skill_registry: SkillRegistry,
        sandbox: SandboxVerificationPipeline | None = None,
        event_bus: EventBus | None = None,
        max_retries: int = 3,
        min_backtest_sharpe: float = 0.3,
    ) -> None:
        self._registry = skill_registry
        self._sandbox = sandbox or SandboxVerificationPipeline()
        self._event_bus = event_bus
        self.max_retries = max_retries
        self.min_backtest_sharpe = min_backtest_sharpe
        self._logger = CortexLogger("ability_factory")
        self._tasks: dict[str, CreationTask] = {}
        self._completed: list[CreationTask] = []

    async def create_from_gap(self, gap: ArchitectureIssue) -> CreationTask:
        """Create a new skill to fill a detected architecture gap."""
        spec = CreationSpec(
            name=f"auto-skill-{gap.dimension}-{gap.id[:8]}",
            category=self._infer_category(gap),
            description=gap.description,
            gap_source=gap.id,
            keywords=gap.evidence.get("missing_capabilities", []),
        )
        return await self.create(spec)

    async def create_strategy(self, name: str, description: str, keywords: list[str] | None = None) -> CreationTask:
        """Create a new strategy skill."""
        spec = CreationSpec(name=name, category="strategy", description=description, keywords=keywords or [])
        return await self.create(spec)

    async def create_indicator(self, name: str, description: str, keywords: list[str] | None = None) -> CreationTask:
        """Create a new indicator skill."""
        spec = CreationSpec(name=name, category="indicator", description=description, keywords=keywords or [])
        return await self.create(spec)

    async def create(self, spec: CreationSpec) -> CreationTask:
        """Execute the full creation pipeline for a specification."""
        task = CreationTask(spec=spec)
        self._tasks[task.id] = task

        try:
            # Phase 1: Generate code
            task.status = CreationStatus.GENERATING
            success = await self._generate_code(task)
            if not success:
                return self._fail_task(task, "Code generation failed")

            # Phase 2: Syntax validation
            task.status = CreationStatus.VALIDATING
            task.syntax_valid = self._validate_syntax(task.generated_files)
            if not task.syntax_valid:
                if task.retry_count < self.max_retries:
                    task.status = CreationStatus.RETRYING
                    task.retry_count += 1
                    task.generated_files.clear()
                    success = await self._generate_code(task)
                    if success:
                        task.syntax_valid = self._validate_syntax(task.generated_files)
                if not task.syntax_valid:
                    return self._fail_task(task, "Syntax validation failed after retries")

            # Phase 3: Sandbox test
            task.status = CreationStatus.SANDBOX_TESTING
            task.sandbox_result = await self._sandbox.deploy_to_sandbox(
                f"create-{task.id[:8]}",
                task.generated_files,
                trial_days=7,
            )
            if not self._sandbox.verify_result(task.sandbox_result, self.min_backtest_sharpe):
                return self._fail_task(task, f"Sandbox verification failed (sharpe={task.sandbox_result.sharpe_ratio:.2f})")

            # Phase 4: Register
            task.status = CreationStatus.REGISTERING
            skill_meta = SkillMeta(
                name=task.spec.name,
                description=task.spec.description,
                keywords=task.spec.keywords,
                category=task.spec.category,
                entry_point=f"generated.{task.spec.name}",
            )
            if not self._registry.register(skill_meta):
                return self._fail_task(task, "Skill registration failed (name conflict)")

            task.registered_skill_name = skill_meta.name
            task.status = CreationStatus.COMPLETE
            task.completed_at = time.time()
            self._completed.append(task)

            # Emit event
            if self._event_bus:
                await self._event_bus.publish_nowait("l6.skill_created", {
                    "task_id": task.id,
                    "skill_name": skill_meta.name,
                    "category": task.spec.category,
                    "gap_source": task.spec.gap_source,
                })

            self._logger.info("skill_created", name=task.spec.name, task_id=task.id[:8])
            return task

        except Exception as exc:
            return self._fail_task(task, str(exc))

    def _validate_syntax(self, files: dict[str, str]) -> bool:
        """Validate Python syntax using ast.parse for all generated files."""
        for filename, content in files.items():
            if filename.endswith(".py"):
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    self._logger.warn("syntax_validation_failed", file=filename, error=str(e))
                    return False
        return True

    async def _generate_code(self, task: CreationTask) -> bool:
        """Generate code using LLM (template-based for now).

        In production, this calls the ModelRouter with deep_think model.
        For Phase 0, generates a minimal working skeleton.
        """
        spec = task.spec
        if spec is None:
            return False

        # Template-based generation (LLM integration in Phase 1+)
        code = self._generate_template(spec)
        task.generated_files[f"{spec.name}.py"] = code
        return True

    def _generate_template(self, spec: CreationSpec) -> str:
        """Generate a minimal working Python module from a template."""
        return f'''"""Auto-generated skill: {spec.name}

Category: {spec.category}
Description: {spec.description}
Generated by: M2 AbilityCreationFactory
"""

from __future__ import annotations

from typing import Any


class {self._to_class_name(spec.name)}:
    """{spec.description}"""

    def __init__(self) -> None:
        self.name = "{spec.name}"
        self.category = "{spec.category}"

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Main execution entry point."""
        return {{"status": "ok", "skill": self.name, "result": {{}}}}

    def health_check(self) -> dict[str, Any]:
        """Return skill health status."""
        return {{"name": self.name, "healthy": True, "category": self.category}}
'''

    @staticmethod
    def _to_class_name(name: str) -> str:
        """Convert kebab-case or snake_case to PascalCase."""
        return "".join(word.capitalize() for word in name.replace("-", "_").split("_"))

    @staticmethod
    def _infer_category(gap: ArchitectureIssue) -> str:
        """Infer the skill category from the gap dimension."""
        mapping = {
            "skill_gap": "core",
            "algorithm_gap": "strategy",
            "latency": "utility",
            "bottleneck": "utility",
            "redundancy": "refactor",
            "error_pattern": "risk",
        }
        return mapping.get(gap.dimension, "utility")

    def _fail_task(self, task: CreationTask, error: str) -> CreationTask:
        task.status = CreationStatus.FAILED
        task.error_message = error
        task.completed_at = time.time()
        self._logger.error("creation_failed", task_id=task.id[:8], error=error)
        return task

    def get_task(self, task_id: str) -> CreationTask | None:
        """Get a creation task by ID."""
        return self._tasks.get(task_id)

    def get_recent_completions(self, limit: int = 20) -> list[CreationTask]:
        """Get recently completed creation tasks."""
        completed = [t for t in self._tasks.values() if t.status == CreationStatus.COMPLETE]
        return sorted(completed, key=lambda t: t.completed_at or 0, reverse=True)[:limit]

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_tasks": len(self._tasks),
            "completed": sum(1 for t in self._tasks.values() if t.status == CreationStatus.COMPLETE),
            "failed": sum(1 for t in self._tasks.values() if t.status == CreationStatus.FAILED),
            "in_progress": sum(1 for t in self._tasks.values() if t.status not in (CreationStatus.COMPLETE, CreationStatus.FAILED)),
        }
