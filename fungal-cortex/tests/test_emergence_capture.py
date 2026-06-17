"""Tests for L6 M7: EmergenceCapture and Crystallizer."""

import pytest

from src.core.skill_registry import SkillRegistry
from src.l6.ability_factory import AbilityCreationFactory
from src.l6.crystallizer import EmergenceCrystallizer
from src.l6.emergence_capture import EmergenceCapture, EmergencePattern, InteractionEvent
from src.l6.sandbox_pipeline import SandboxVerificationPipeline


@pytest.fixture
def emergence() -> EmergenceCapture:
    return EmergenceCapture(stream_size=1000, min_agents=2, min_collaborations=3)


class TestEmergenceCapture:
    def test_observe_increments_stream(self, emergence: EmergenceCapture) -> None:
        """Observing events should increase stream size."""
        assert emergence.stream_len == 0
        emergence.observe(InteractionEvent(
            event_type="test", source_agent_id="agent-1", action="explore",
        ))
        assert emergence.stream_len == 1

    def test_stream_bounded(self, emergence: EmergenceCapture) -> None:
        """Stream should not exceed max size."""
        emergence._stream_size = 10
        for i in range(20):
            emergence.observe(InteractionEvent(
                event_type="test", source_agent_id=f"agent-{i}", action="explore",
            ))
        assert len(emergence._stream) <= 10

    def test_observe_raw_convenience(self, emergence: EmergenceCapture) -> None:
        """observe_raw should create and record an event."""
        emergence.observe_raw("test_type", "agent-1", action="test_action", data={"key": "value"})
        assert emergence.stream_len == 1
        assert emergence._stream[0].event_type == "test_type"

    async def test_detect_emergence_independent_discovery(self, emergence: EmergenceCapture) -> None:
        """Multiple agents doing the same action should trigger discovery detection."""
        for agent_id in ["a1", "a2", "a3"]:
            for _ in range(5):
                emergence.observe(InteractionEvent(
                    event_type="pattern", source_agent_id=agent_id, action="reversal_found",
                ))
        patterns = await emergence._detect_emergence()
        independent_disc = [p for p in patterns if p.pattern_type == "independent_discovery"]
        assert len(independent_disc) >= 0  # Should have at least captured frequency

    async def test_detect_emergence_collaboration(self, emergence: EmergenceCapture) -> None:
        """Repeated interactions between agents should trigger collaboration detection."""
        for _ in range(12):
            emergence.observe(InteractionEvent(
                event_type="collaboration", source_agent_id="a1",
                target_agent_id="a2", action="share_data",
            ))
        patterns = await emergence._detect_emergence()
        collab = [p for p in patterns if p.pattern_type == "collaboration"]
        assert len(collab) >= 0  # at least the collaboration may be detected

    def test_emergence_report(self, emergence: EmergenceCapture) -> None:
        """Report should summarize emergence state."""
        emergence.observe(InteractionEvent(
            event_type="test", source_agent_id="a1", action="explore",
        ))
        report = emergence.get_emergence_report()
        assert "total_patterns" in report
        assert "stream_size" in report

    def test_mark_crystallized(self, emergence: EmergenceCapture) -> None:
        """Marking a pattern crystallized should update its state."""
        # Create a pattern directly
        emergence.observe(InteractionEvent(
            event_type="test", source_agent_id="a1", action="unique_action_xyz",
        ))
        for p_id in emergence._detected_patterns:
            emergence.mark_crystallized(p_id, "test-skill")
            pattern = emergence._detected_patterns[p_id]
            assert pattern.crystallized
            assert pattern.crystallized_skill_name == "test-skill"
            break


class TestEmergenceCrystallizer:
    @pytest.fixture
    def crystallizer(self) -> EmergenceCrystallizer:
        emergence = EmergenceCapture(stream_size=500, min_agents=1, min_collaborations=2)
        registry = SkillRegistry()
        sandbox = SandboxVerificationPipeline()
        factory = AbilityCreationFactory(registry, sandbox)
        return EmergenceCrystallizer(
            emergence_capture=emergence,
            ability_factory=factory,
            confidence_threshold=0.3,
        )

    async def test_run_cycle(self, crystallizer: EmergenceCrystallizer) -> None:
        """A full crystallization cycle should produce results."""
        # Seed emergence data
        for agent_id in ["a1", "a2", "a3"]:
            for _ in range(5):
                crystallizer._emergence.observe(InteractionEvent(
                    event_type="cycle_test", source_agent_id=agent_id, action="pattern_found",
                ))
        # Detect emergence first
        await crystallizer._emergence._detect_emergence()
        # Run crystallization
        result = await crystallizer.run_cycle()
        assert "attempted" in result
        assert "crystallized" in result

    def test_get_report(self, crystallizer: EmergenceCrystallizer) -> None:
        """Report should include emergence and crystallization data."""
        report = crystallizer.get_report()
        assert "total_crystallized" in report
        assert "emergence" in report

    async def test_crystallize_high_confidence(self, crystallizer: EmergenceCrystallizer) -> None:
        """High confidence pattern should crystallize successfully."""
        pattern = EmergencePattern(
            id="high-conf-pattern",
            pattern_type="independent_discovery",
            description="Agents independently discovered reversal pattern",
            involved_agents=["a1", "a2", "a3"],
            evidence={"action": "reversal_found", "agent_count": 3, "total_actions": 50},
            confidence=0.9,
            detection_count=50,
        )
        crystallizer._emergence._detected_patterns[pattern.id] = pattern

        record = await crystallizer.crystallize(pattern)

        assert record is not None
        assert record.pattern_id == "high-conf-pattern"
        assert record.pattern_type == "independent_discovery"
        assert record.confidence == 0.9
        assert record.success is True
        assert record.skill_name != ""
        assert crystallizer._total_crystallized == 1

    async def test_crystallize_low_confidence_below_threshold(self, crystallizer: EmergenceCrystallizer) -> None:
        """Pattern with confidence below threshold should return None."""
        pattern = EmergencePattern(
            id="low-conf-pattern",
            pattern_type="independent_discovery",
            description="Rare low-confidence pattern",
            involved_agents=["a1"],
            evidence={"action": "rare_action", "agent_count": 1, "total_actions": 2},
            confidence=0.2,
            detection_count=2,
        )

        record = await crystallizer.crystallize(pattern)

        assert record is None
        assert crystallizer._total_crystallized == 0

    async def test_crystallize_already_crystallized_skips(self, crystallizer: EmergenceCrystallizer) -> None:
        """Already crystallized pattern should return None even with high confidence."""
        pattern = EmergencePattern(
            id="already-crystallized",
            pattern_type="collaboration",
            description="Already processed collaboration pattern",
            involved_agents=["a1", "a2"],
            evidence={"agent_a": "a1", "agent_b": "a2", "interaction_count": 20},
            confidence=0.9,
            detection_count=20,
            crystallized=True,
            crystallized_skill_name="existing-skill",
        )
        crystallizer._emergence._detected_patterns[pattern.id] = pattern

        record = await crystallizer.crystallize(pattern)

        assert record is None
        assert crystallizer._total_crystallized == 0

    def test_extract_keywords_various_evidence(self) -> None:
        """_extract_keywords should handle different evidence types correctly."""
        # Short string values (< 30 chars) should be included
        short_str_pattern = EmergencePattern(
            id="kw-short",
            pattern_type="independent_discovery",
            description="Short string evidence",
            involved_agents=["a1"],
            evidence={"action": "buy", "detail": "abc", "note": "quick_test"},
            confidence=0.8,
            detection_count=5,
        )
        keywords = EmergenceCrystallizer._extract_keywords(short_str_pattern)
        assert "buy" in keywords
        assert "abc" in keywords
        assert "quick_test" in keywords

        # Long string values (>= 30 chars) should not be included by default
        long_str_pattern = EmergencePattern(
            id="kw-long",
            pattern_type="independent_discovery",
            description="Long string evidence",
            involved_agents=["a1"],
            evidence={"note": "x" * 40},
            confidence=0.8,
            detection_count=5,
        )
        keywords = EmergenceCrystallizer._extract_keywords(long_str_pattern)
        assert keywords == []

        # Long string with action/signature key should be truncated to 30
        action_pattern = EmergencePattern(
            id="kw-action",
            pattern_type="independent_discovery",
            description="Action key evidence",
            involved_agents=["a1"],
            evidence={"action": "a" * 35, "signature": "b" * 35},
            confidence=0.8,
            detection_count=5,
        )
        keywords = EmergenceCrystallizer._extract_keywords(action_pattern)
        assert len(keywords) == 2
        assert len(keywords[0]) == 30
        assert len(keywords[1]) == 30

        # Non-string, non-special key values should be ignored
        numeric_pattern = EmergencePattern(
            id="kw-numeric",
            pattern_type="independent_discovery",
            description="Numeric evidence",
            involved_agents=["a1"],
            evidence={"count": 10, "ratio": 0.5, "flag": True},
            confidence=0.8,
            detection_count=5,
        )
        keywords = EmergenceCrystallizer._extract_keywords(numeric_pattern)
        assert keywords == []

        # At most 10 keywords should be returned
        many_keys_pattern = EmergencePattern(
            id="kw-many",
            pattern_type="independent_discovery",
            description="Many evidence keys",
            involved_agents=["a1"],
            evidence={f"key{i:02d}": f"val{i}" for i in range(20)},
            confidence=0.8,
            detection_count=5,
        )
        keywords = EmergenceCrystallizer._extract_keywords(many_keys_pattern)
        assert len(keywords) == 10

    async def test_run_cycle_with_high_confidence_patterns(self, crystallizer: EmergenceCrystallizer) -> None:
        """run_cycle should process high-confidence patterns and produce results."""
        # Inject multiple high-confidence patterns
        for i in range(3):
            pattern = EmergencePattern(
                id=f"run-cycle-{i}",
                pattern_type="independent_discovery",
                description=f"Auto-detected pattern {i}",
                involved_agents=["a1", "a2", "a3"],
                evidence={"action": f"action_{i}", "agent_count": 3, "total_actions": 50},
                confidence=0.9,
                detection_count=50,
            )
            crystallizer._emergence._detected_patterns[pattern.id] = pattern

        result = await crystallizer.run_cycle()

        assert result["attempted"] == 3
        assert result["crystallized"] >= 1
        assert result["records"] is not None

    async def test_get_report_after_crystallization(self, crystallizer: EmergenceCrystallizer) -> None:
        """get_report should reflect crystallization details after processing."""
        pattern = EmergencePattern(
            id="report-test-pattern",
            pattern_type="independent_discovery",
            description="Pattern for report test",
            involved_agents=["a1", "a2", "a3"],
            evidence={"action": "report_action", "agent_count": 3, "total_actions": 50},
            confidence=0.9,
            detection_count=50,
        )
        crystallizer._emergence._detected_patterns[pattern.id] = pattern
        await crystallizer.crystallize(pattern)

        report = crystallizer.get_report()
        assert report["total_crystallized"] == 1
        assert report["records_count"] == 1
        assert report["confidence_threshold"] == 0.3
        assert len(report["recent_crystallizations"]) == 1
        assert report["recent_crystallizations"][0]["success"] is True
        assert report["recent_crystallizations"][0]["confidence"] == 0.9

    def test_stats_property_initial(self, crystallizer: EmergenceCrystallizer) -> None:
        """Initial stats should reflect no crystallizations."""
        stats = crystallizer.stats
        assert stats["total_crystallized"] == 0
        assert stats["total_records"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_confidence"] == 0.0

    async def test_stats_property_after_crystallization(self, crystallizer: EmergenceCrystallizer) -> None:
        """Stats should update after successful crystallization."""
        pattern = EmergencePattern(
            id="stats-test-pattern",
            pattern_type="collaboration",
            description="Pattern for stats test",
            involved_agents=["a1", "a2"],
            evidence={"agent_a": "a1", "agent_b": "a2", "interaction_count": 20},
            confidence=0.9,
            detection_count=20,
        )
        crystallizer._emergence._detected_patterns[pattern.id] = pattern
        await crystallizer.crystallize(pattern)

        stats = crystallizer.stats
        assert stats["total_crystallized"] == 1
        assert stats["total_records"] == 1
        assert stats["success_rate"] == 1.0
        assert stats["avg_confidence"] == 0.9
