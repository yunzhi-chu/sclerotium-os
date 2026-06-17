"""Tests for L6 M2: AbilityCreationFactory."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.event_bus import EventBus
from src.core.skill_registry import SkillMeta, SkillRegistry
from src.l6.ability_factory import AbilityCreationFactory, CreationSpec, CreationStatus, CreationTask
from src.l6.architecture_scanner import ArchitectureIssue, IssueSeverity
from src.l6.sandbox_pipeline import SandboxResult, SandboxVerificationPipeline


@pytest.fixture
def factory() -> AbilityCreationFactory:
    registry = SkillRegistry()
    sandbox = SandboxVerificationPipeline()
    return AbilityCreationFactory(
        skill_registry=registry,
        sandbox=sandbox,
        max_retries=2,
    )


@pytest.fixture
def registry() -> SkillRegistry:
    return SkillRegistry()


@pytest.fixture
def mock_sandbox() -> MagicMock:
    """Sandbox mock with deploy_to_sandbox as AsyncMock and verify_result as sync MagicMock."""
    sandbox = MagicMock(spec=SandboxVerificationPipeline)
    result = SandboxResult(
        skill_id="test",
        passed_positive_selection=True,
        passed_negative_selection=True,
        sharpe_ratio=0.5,
        max_drawdown=0.1,
    )
    sandbox.deploy_to_sandbox = AsyncMock(return_value=result)
    sandbox.verify_result.return_value = True
    return sandbox


def _make_gap(dimension: str = "skill_gap", gap_id: str = "test-1234") -> ArchitectureIssue:
    return ArchitectureIssue(
        id=gap_id,
        dimension=dimension,
        severity=IssueSeverity.HIGH,
        title=f"Test {dimension}",
        description=f"A test gap of dimension {dimension}",
        evidence={"missing_capabilities": [f"cap_{dimension}"]},
    )


class TestAbilityCreationFactory:
    # --- existing tests (preserved as-is) ---

    async def test_create_strategy(self, factory: AbilityCreationFactory) -> None:
        """Creating a strategy should generate valid Python code."""
        task = await factory.create_strategy(
            name="test-momentum-strategy",
            description="A simple momentum strategy for testing",
            keywords=["momentum", "test"],
        )
        assert task.status == CreationStatus.COMPLETE
        assert len(task.generated_files) > 0
        assert task.syntax_valid

    async def test_create_indicator(self, factory: AbilityCreationFactory) -> None:
        """Creating an indicator should generate valid Python code."""
        task = await factory.create_indicator(
            name="test-rsi-indicator",
            description="RSI indicator for testing",
            keywords=["rsi", "momentum", "indicator"],
        )
        assert task.status == CreationStatus.COMPLETE
        assert task.syntax_valid

    async def test_create_from_spec(self, factory: AbilityCreationFactory) -> None:
        """Creating from a CreationSpec should work."""
        spec = CreationSpec(
            name="test-custom-skill",
            category="utility",
            description="Custom skill from spec",
            keywords=["custom"],
        )
        task = await factory.create(spec)
        assert task.status == CreationStatus.COMPLETE

    async def test_generated_code_is_valid_python(self, factory: AbilityCreationFactory) -> None:
        """Generated code must be syntactically valid Python."""
        task = await factory.create_strategy("test-valid-python", "Testing syntax validation", ["test"])
        for filename, content in task.generated_files.items():
            if filename.endswith(".py"):
                import ast
                try:
                    ast.parse(content)
                except SyntaxError:
                    pytest.fail(f"Generated code failed syntax check: {filename}")

    async def test_task_tracking(self, factory: AbilityCreationFactory) -> None:
        """Tasks should be retrievable by ID."""
        task = await factory.create_strategy("test-tracking", "Task tracking test", [])
        retrieved = factory.get_task(task.id)
        assert retrieved is not None
        assert retrieved.id == task.id

    def test_stats(self, factory: AbilityCreationFactory) -> None:
        """Stats should report factory state."""
        stats = factory.stats
        assert "total_tasks" in stats
        assert "completed" in stats
        assert "failed" in stats

    # --- create_from_gap and _infer_category ---

    @pytest.mark.parametrize("dimension,expected_category", [
        ("skill_gap", "core"),
        ("algorithm_gap", "strategy"),
        ("latency", "utility"),
        ("bottleneck", "utility"),
        ("redundancy", "refactor"),
        ("error_pattern", "risk"),
        ("unknown_dim", "utility"),
        ("", "utility"),
    ])
    async def test_create_from_gap_dimensions(self, factory: AbilityCreationFactory, dimension: str, expected_category: str) -> None:
        """create_from_gap should infer category from gap dimension."""
        gap = _make_gap(dimension)
        task = await factory.create_from_gap(gap)
        assert task.status == CreationStatus.COMPLETE
        assert task.spec.category == expected_category
        assert gap.id in task.spec.gap_source

    async def test_create_from_gap_with_evidence_keywords(self, factory: AbilityCreationFactory) -> None:
        """create_from_gap should pass evidence keywords to the spec."""
        gap = _make_gap("skill_gap")
        task = await factory.create_from_gap(gap)
        assert task.spec.keywords == ["cap_skill_gap"]

    async def test_create_from_gap_missing_evidence_key(self, factory: AbilityCreationFactory) -> None:
        """create_from_gap should default to empty keywords when evidence key is missing."""
        gap = ArchitectureIssue(
            id="test-no-evidence",
            dimension="skill_gap",
            severity=IssueSeverity.HIGH,
            title="No evidence",
            description="Gap without evidence",
            evidence={},
        )
        task = await factory.create_from_gap(gap)
        assert task.spec.keywords == []

    async def test_create_from_gap_short_id(self, factory: AbilityCreationFactory) -> None:
        """create_from_gap should handle short gap IDs ([:8] slicing)."""
        gap = _make_gap(dimension="latency", gap_id="ab")
        task = await factory.create_from_gap(gap)
        assert task.status == CreationStatus.COMPLETE
        assert "ab" in task.spec.name

    # --- _infer_category static method ---

    @pytest.mark.parametrize("dimension,expected", [
        ("skill_gap", "core"),
        ("algorithm_gap", "strategy"),
        ("latency", "utility"),
        ("bottleneck", "utility"),
        ("redundancy", "refactor"),
        ("error_pattern", "risk"),
        ("unknown", "utility"),
        ("", "utility"),
    ])
    def test_infer_category(self, dimension: str, expected: str) -> None:
        """_infer_category should map dimension to correct category."""
        gap = _make_gap(dimension)
        assert AbilityCreationFactory._infer_category(gap) == expected

    # --- _to_class_name ---

    @pytest.mark.parametrize("input_name,expected", [
        ("snake_case_name", "SnakeCaseName"),
        ("kebab-case-name", "KebabCaseName"),
        ("alreadyPascal", "Alreadypascal"),
        ("single", "Single"),
        ("mixed-case_name", "MixedCaseName"),
        ("", ""),
        ("hello_world_test", "HelloWorldTest"),
    ])
    def test_to_class_name(self, input_name: str, expected: str) -> None:
        """_to_class_name should convert various naming conventions to PascalCase."""
        assert AbilityCreationFactory._to_class_name(input_name) == expected

    # --- code generation failure ---

    async def test_create_code_generation_failure(self, factory: AbilityCreationFactory) -> None:
        """When _generate_code returns False, task should be FAILED."""
        spec = CreationSpec(name="fail-gen", category="strategy", description="Generation failure")
        with patch.object(factory, '_generate_code', AsyncMock(return_value=False)):
            task = await factory.create(spec)
        assert task.status == CreationStatus.FAILED
        assert "Code generation failed" in task.error_message

    # --- syntax validation and retry ---

    async def test_create_syntax_retry_success(self, factory: AbilityCreationFactory) -> None:
        """When first syntax validation fails but retry succeeds, task should complete."""
        spec = CreationSpec(name="retry-ok", category="strategy", description="Retry then success")
        with patch.object(factory, '_validate_syntax') as mock_validate:
            mock_validate.side_effect = [False, True]
            task = await factory.create(spec)
        assert task.status == CreationStatus.COMPLETE
        assert task.retry_count == 1

    async def test_create_syntax_retry_exhausted(self, factory: AbilityCreationFactory) -> None:
        """When syntax validation fails and retry also fails, task should FAILED."""
        spec = CreationSpec(name="retry-fail", category="strategy", description="Retry failure")
        with patch.object(factory, '_validate_syntax', return_value=False):
            task = await factory.create(spec)
        assert task.status == CreationStatus.FAILED
        assert "Syntax validation failed" in task.error_message
        assert task.retry_count == 1

    # --- sandbox verification failure ---

    async def test_create_sandbox_verification_failure(self, registry: SkillRegistry, mock_sandbox: MagicMock) -> None:
        """When sandbox verify_result returns False, task should FAILED."""
        mock_sandbox.verify_result.return_value = False
        factory = AbilityCreationFactory(
            skill_registry=registry,
            sandbox=mock_sandbox,
            max_retries=2,
        )
        spec = CreationSpec(name="sandbox-fail", category="strategy", description="Sandbox failure")
        task = await factory.create(spec)
        assert task.status == CreationStatus.FAILED
        assert "Sandbox verification failed" in task.error_message

    # --- registration conflict ---

    async def test_create_registration_conflict(self, factory: AbilityCreationFactory) -> None:
        """When skill name already exists, task should FAILED at registration."""
        task1 = await factory.create_strategy("duplicate-skill", "First registration", [])
        assert task1.status == CreationStatus.COMPLETE

        task2 = await factory.create_strategy("duplicate-skill", "Duplicate registration", [])
        assert task2.status == CreationStatus.FAILED
        assert "registration failed" in task2.error_message

    # --- event bus integration ---

    async def test_create_with_event_bus_publishes_event(self) -> None:
        """When event_bus is provided, skill_created event should be published."""
        registry = SkillRegistry()
        sandbox = SandboxVerificationPipeline()
        event_bus = AsyncMock(spec=EventBus)
        event_bus.publish_nowait = AsyncMock(return_value=True)

        factory = AbilityCreationFactory(
            skill_registry=registry,
            sandbox=sandbox,
            event_bus=event_bus,
            max_retries=2,
        )
        task = await factory.create_strategy("event-test-skill", "Testing event bus", ["test"])
        assert task.status == CreationStatus.COMPLETE
        event_bus.publish_nowait.assert_awaited_once()

    async def test_create_with_event_bus_verify_payload(self) -> None:
        """Event bus should receive correct payload on skill creation."""
        registry = SkillRegistry()
        sandbox = SandboxVerificationPipeline()
        event_bus = AsyncMock(spec=EventBus)
        event_bus.publish_nowait = AsyncMock(return_value=True)

        factory = AbilityCreationFactory(
            skill_registry=registry,
            sandbox=sandbox,
            event_bus=event_bus,
            max_retries=2,
        )
        task = await factory.create_strategy("payload-test", "Payload test", ["kw1"])
        event_bus.publish_nowait.assert_awaited_once_with(
            "l6.skill_created",
            {
                "task_id": task.id,
                "skill_name": task.registered_skill_name,
                "category": task.spec.category,
                "gap_source": task.spec.gap_source,
            },
        )

    async def test_create_without_event_bus_no_crash(self, factory: AbilityCreationFactory) -> None:
        """When event_bus is None, creation should still succeed."""
        assert factory._event_bus is None
        task = await factory.create_strategy("no-event-bus", "No event bus", [])
        assert task.status == CreationStatus.COMPLETE

    # --- exception handling ---

    async def test_create_exception_during_generate(self, factory: AbilityCreationFactory) -> None:
        """When an exception occurs in _generate_code, task should FAILED."""
        spec = CreationSpec(name="except-gen", category="strategy", description="Exception during generate")
        with patch.object(factory, '_generate_code', AsyncMock(side_effect=RuntimeError("Gen crash"))):
            task = await factory.create(spec)
        assert task.status == CreationStatus.FAILED
        assert "Gen crash" in task.error_message

    async def test_create_exception_during_sandbox(self, registry: SkillRegistry) -> None:
        """When an exception occurs during sandbox deploy, task should FAILED."""
        sandbox = MagicMock(spec=SandboxVerificationPipeline)
        sandbox.deploy_to_sandbox = AsyncMock(side_effect=ValueError("Sandbox crash"))
        sandbox.verify_result = MagicMock(return_value=True)

        factory = AbilityCreationFactory(
            skill_registry=registry,
            sandbox=sandbox,
            max_retries=2,
        )
        task = await factory.create_strategy("except-sandbox", "Exception in sandbox", [])
        assert task.status == CreationStatus.FAILED
        assert "Sandbox crash" in task.error_message

    # --- _validate_syntax edge cases ---

    def test_validate_syntax_invalid_python(self, factory: AbilityCreationFactory) -> None:
        """_validate_syntax should return False for invalid Python."""
        assert not factory._validate_syntax({"bad.py": "this is not valid python {{}"})

    def test_validate_syntax_valid_python(self, factory: AbilityCreationFactory) -> None:
        """_validate_syntax should return True for valid Python."""
        assert factory._validate_syntax({"good.py": "x = 1\ndef f(): pass\n"})

    def test_validate_syntax_empty_content(self, factory: AbilityCreationFactory) -> None:
        """_validate_syntax should accept empty Python files."""
        assert factory._validate_syntax({"empty.py": ""})

    def test_validate_syntax_skips_non_py_files(self, factory: AbilityCreationFactory) -> None:
        """_validate_syntax should skip non-.py files."""
        assert factory._validate_syntax({
            "data.json": "{invalid json",
            "config.yaml": "invalid: yaml: :::",
        })

    def test_validate_syntax_empty_dict(self, factory: AbilityCreationFactory) -> None:
        """_validate_syntax with empty dict should return True."""
        assert factory._validate_syntax({})

    def test_validate_syntax_mixed_files_one_invalid(self, factory: AbilityCreationFactory) -> None:
        """_validate_syntax should return False if any .py file is invalid."""
        assert not factory._validate_syntax({
            "good.py": "x = 1",
            "bad.py": "def broken(:",
            "readme.md": "## docs",
        })

    # --- _generate_code edge cases ---

    async def test_generate_code_none_spec(self, factory: AbilityCreationFactory) -> None:
        """_generate_code should return False when task.spec is None."""
        task = CreationTask(spec=None)
        result = await factory._generate_code(task)
        assert result is False

    # --- get_recent_completions ---

    async def test_get_recent_completions_empty(self, factory: AbilityCreationFactory) -> None:
        """get_recent_completions should return empty list when no completions."""
        assert factory.get_recent_completions() == []

    async def test_get_recent_completions_returns_completed(self, factory: AbilityCreationFactory) -> None:
        """get_recent_completions should return completed tasks."""
        task1 = await factory.create_strategy("complete-a", "First completion", [])
        task2 = await factory.create_strategy("complete-b", "Second completion", [])
        completions = factory.get_recent_completions()
        assert len(completions) == 2
        # Both completed tasks should be present
        ids = {t.id for t in completions}
        assert task1.id in ids
        assert task2.id in ids

    async def test_get_recent_completions_respects_limit(self, factory: AbilityCreationFactory) -> None:
        """get_recent_completions should respect the limit parameter."""
        for i in range(5):
            await factory.create_strategy(f"bulk-{i}", f"Bulk completion {i}", [])
        completions = factory.get_recent_completions(limit=3)
        assert len(completions) == 3

    async def test_get_recent_completions_excludes_failed(self, factory: AbilityCreationFactory) -> None:
        """get_recent_completions should not include FAILED tasks."""
        await factory.create_strategy("good-one", "Good skill", [])
        spec = CreationSpec(name="bad-one", category="strategy", description="Bad skill")
        with patch.object(factory, '_generate_code', AsyncMock(return_value=False)):
            await factory.create(spec)
        completions = factory.get_recent_completions()
        assert len(completions) == 1
        assert completions[0].spec.name == "good-one"

    # --- get_task edge cases ---

    def test_get_task_not_found(self, factory: AbilityCreationFactory) -> None:
        """get_task should return None for non-existent ID."""
        assert factory.get_task("non-existent-id") is None

    # --- stats ---

    async def test_stats_after_completed_creation(self, factory: AbilityCreationFactory) -> None:
        """Stats should reflect completed tasks."""
        await factory.create_strategy("stats-test", "Stats test", [])
        stats = factory.stats
        assert stats["total_tasks"] == 1
        assert stats["completed"] == 1
        assert stats["failed"] == 0
        assert stats["in_progress"] == 0

    async def test_stats_with_failure(self, factory: AbilityCreationFactory) -> None:
        """Stats should reflect failed tasks."""
        spec = CreationSpec(name="stats-fail", category="strategy", description="Stats failure")
        with patch.object(factory, '_generate_code', AsyncMock(return_value=False)):
            await factory.create(spec)
        stats = factory.stats
        assert stats["total_tasks"] == 1
        assert stats["completed"] == 0
        assert stats["failed"] == 1
        assert stats["in_progress"] == 0

    async def test_stats_with_mixed_results(self, factory: AbilityCreationFactory) -> None:
        """Stats should track multiple tasks with mixed outcomes."""
        await factory.create_strategy("good-a", "Good", [])
        spec = CreationSpec(name="bad-b", category="strategy", description="Bad")
        with patch.object(factory, '_generate_code', AsyncMock(return_value=False)):
            await factory.create(spec)
        await factory.create_strategy("good-c", "Good", [])
        stats = factory.stats
        assert stats["total_tasks"] == 3
        assert stats["completed"] == 2
        assert stats["failed"] == 1
        assert stats["in_progress"] == 0

    # --- max_retries configuration ---

    async def test_max_retries_zero_disables_retry(self) -> None:
        """With max_retries=0, syntax failure should immediately fail without retry."""
        registry = SkillRegistry()
        sandbox = SandboxVerificationPipeline()
        factory = AbilityCreationFactory(
            skill_registry=registry,
            sandbox=sandbox,
            max_retries=0,
        )
        spec = CreationSpec(name="no-retry", category="strategy", description="No retry")
        with patch.object(factory, '_validate_syntax', return_value=False):
            task = await factory.create(spec)
        assert task.status == CreationStatus.FAILED
        assert task.retry_count == 0

    async def test_max_retries_high_configuration(self) -> None:
        """Factory should accept high max_retries values."""
        registry = SkillRegistry()
        sandbox = SandboxVerificationPipeline()
        factory = AbilityCreationFactory(
            skill_registry=registry,
            sandbox=sandbox,
            max_retries=10,
        )
        assert factory.max_retries == 10

    # --- create_strategy edge cases ---

    async def test_create_strategy_empty_keywords(self, factory: AbilityCreationFactory) -> None:
        """Creating a strategy with empty keywords should work."""
        task = await factory.create_strategy("no-keywords", "No keywords", keywords=[])
        assert task.status == CreationStatus.COMPLETE
        assert task.spec.keywords == []

    async def test_create_strategy_none_keywords(self, factory: AbilityCreationFactory) -> None:
        """Creating a strategy with None keywords should default to empty list."""
        task = await factory.create_strategy("none-keywords", "None keywords", keywords=None)
        assert task.status == CreationStatus.COMPLETE
        assert task.spec.keywords == []

    async def test_create_strategy_empty_description(self, factory: AbilityCreationFactory) -> None:
        """Creating a strategy with empty description should work."""
        task = await factory.create_strategy("empty-desc", "", [])
        assert task.status == CreationStatus.COMPLETE

    # --- create_indicator edge cases ---

    async def test_create_indicator_none_keywords(self, factory: AbilityCreationFactory) -> None:
        """Creating an indicator with None keywords should default to empty list."""
        task = await factory.create_indicator("none-kw-indicator", "None keywords", keywords=None)
        assert task.status == CreationStatus.COMPLETE
        assert task.spec.keywords == []

    async def test_create_indicator_empty_keywords(self, factory: AbilityCreationFactory) -> None:
        """Creating an indicator with empty keywords should work."""
        task = await factory.create_indicator("empty-kw-indicator", "Empty keywords", keywords=[])
        assert task.status == CreationStatus.COMPLETE

    # --- _fail_task ---

    def test_fail_task_sets_status(self, factory: AbilityCreationFactory) -> None:
        """_fail_task should set FAILED status and error message."""
        task = CreationTask(spec=CreationSpec(name="fail", category="test", description="test"))
        result = factory._fail_task(task, "Something went wrong")
        assert result.status == CreationStatus.FAILED
        assert result.error_message == "Something went wrong"
        assert result.completed_at is not None
        assert result is task  # Returns the same task

    # --- min_backtest_sharpe ---

    def test_default_min_backtest_sharpe(self) -> None:
        """Default min_backtest_sharpe should be 0.3."""
        factory = AbilityCreationFactory(skill_registry=SkillRegistry())
        assert factory.min_backtest_sharpe == 0.3

    def test_custom_min_backtest_sharpe(self) -> None:
        """Factory should accept custom min_backtest_sharpe."""
        factory = AbilityCreationFactory(
            skill_registry=SkillRegistry(),
            min_backtest_sharpe=0.5,
        )
        assert factory.min_backtest_sharpe == 0.5
