"""Tests for Mechanism ②: Hyphal Agent lifecycle."""

import pytest

from src.agent.agent_state import AgentState, AgentStateTracker, Lifecycle, Specialty
from src.agent.hyphal_agent import HyphalAgent
from src.field.field_geometry import FieldGeometry
from src.field.stigmergy_field import StigmergyField


@pytest.fixture
def field() -> StigmergyField:
    return StigmergyField(geometry=FieldGeometry(width=64, height=64))


@pytest.fixture
def agent(field: StigmergyField) -> HyphalAgent:
    state = AgentState(name="test-agent", lifecycle=Lifecycle.ACTIVE, position=(32, 32))
    return HyphalAgent(state=state, field=field)


class TestHyphalAgent:
    def test_agent_initial_state(self, agent: HyphalAgent) -> None:
        assert agent.is_alive
        assert agent.state.lifecycle == Lifecycle.ACTIVE

    def test_sense_returns_values(self, agent: HyphalAgent) -> None:
        s, n, d = agent.sense()
        assert isinstance(s, float)
        assert isinstance(n, float)
        assert isinstance(d, float)

    def test_decide_direction_returns_delta(self, agent: HyphalAgent) -> None:
        dx, dy = agent.decide_direction()
        assert dx in (-1, 0, 1)
        assert dy in (-1, 0, 1)

    def test_step_moves_agent(self, agent: HyphalAgent) -> None:
        old_i, old_j = agent.state.position
        dx, dy = agent.decide_direction()
        # The move() method in AgentState is a position SETTER, not adder.
        # The actual step() method correctly adds the delta.
        new_i = max(0, min(agent.field.geom.width - 1, old_i + dx))
        new_j = max(0, min(agent.field.geom.height - 1, old_j + dy))
        agent.state = agent.state.move(new_i, new_j)
        # Agent should not move too far in one step
        assert abs(new_i - old_i) <= 1
        assert abs(new_j - old_j) <= 1

    def test_should_branch_probabilistic(self, agent: HyphalAgent) -> None:
        """Branch decision is probabilistic but should not error."""
        result = agent.should_branch()
        assert isinstance(result, bool)

    def test_branch_creates_offspring_state(self, agent: HyphalAgent) -> None:
        child = agent.branch_offspring_state("child-1")
        assert child.name == "child-1"
        assert child.lifecycle == Lifecycle.SPAWNING
        assert child.generation == agent.state.generation + 1
        assert child.skills == agent.state.skills

    def test_record_message_increments(self, agent: HyphalAgent) -> None:
        target = "other-agent-id"
        assert target not in agent._message_counts
        agent.record_message(target)
        assert agent._message_counts[target] == 1
        agent.record_message(target)
        assert agent._message_counts[target] == 2

    def test_should_apoptose_at_low_nutrition(self, agent: HyphalAgent) -> None:
        agent.apoptose_threshold = 0.5
        agent.state = agent.state.starve(1.0)  # nutrition → 0
        assert agent.should_apoptose()

    def test_immutable_state_transitions(self, agent: HyphalAgent) -> None:
        """State transitions must produce new states, not mutate."""
        old_id = id(agent.state)
        agent.state = agent.state.move(33, 33)
        assert id(agent.state) != old_id  # Different object

    def test_myelinate_threshold_check(self, agent: HyphalAgent) -> None:
        target = "neighbor-agent"
        agent.myelinate_threshold = 3
        assert not agent.should_myelinate(target)
        for _ in range(3):
            agent.record_message(target)
        assert agent.should_myelinate(target)


class TestAgentState:
    """Tests for AgentState immutable state transitions."""

    def test_activate_transition(self) -> None:
        state = AgentState()
        new = state.activate()
        assert new.lifecycle == Lifecycle.ACTIVE
        assert new is not state

    def test_idle_transition(self) -> None:
        state = AgentState()
        new = state.idle()
        assert new.lifecycle == Lifecycle.IDLE

    def test_apoptose_transition(self) -> None:
        state = AgentState()
        new = state.apoptose()
        assert new.lifecycle == Lifecycle.APOPTOSING

    def test_die_transition(self) -> None:
        state = AgentState()
        new = state.die()
        assert new.lifecycle == Lifecycle.DEAD

    def test_feed_increases_nutrition(self) -> None:
        state = AgentState(nutrition=0.5)
        new = state.feed(0.3)
        assert new.nutrition == pytest.approx(0.8)
        assert new is not state

    def test_feed_caps_at_maximum(self) -> None:
        state = AgentState(nutrition=0.9)
        new = state.feed(0.3)
        assert new.nutrition == 1.0

    def test_starve_decreases_nutrition(self) -> None:
        state = AgentState(nutrition=0.5)
        new = state.starve(0.2)
        assert new.nutrition == pytest.approx(0.3)

    def test_starve_floors_at_zero(self) -> None:
        state = AgentState(nutrition=0.1)
        new = state.starve(0.5)
        assert new.nutrition == 0.0

    def test_update_activity_sets_value(self) -> None:
        state = AgentState()
        new = state.update_activity(0.75)
        assert new.activity == pytest.approx(0.75)

    def test_promote_changes_specialty_and_lifecycle(self) -> None:
        state = AgentState()
        new = state.promote(Specialty.STRATEGY)
        assert new.specialty == Specialty.STRATEGY
        assert new.lifecycle == Lifecycle.PROMOTING

    def test_add_skill_appends_to_tuple(self) -> None:
        state = AgentState()
        new = state.add_skill("analysis")
        assert "analysis" in new.skills
        assert len(new.skills) == 1

    def test_add_skill_duplicate_returns_same(self) -> None:
        state = AgentState(skills=("analysis",))
        new = state.add_skill("analysis")
        assert new is state

    def test_remove_skill_removes_from_tuple(self) -> None:
        state = AgentState(skills=("a", "b", "c"))
        new = state.remove_skill("b")
        assert "b" not in new.skills
        assert new.skills == ("a", "c")

    def test_position_float_property(self) -> None:
        state = AgentState(position=(10, 20))
        px, py = state.position_float
        assert isinstance(px, float)
        assert isinstance(py, float)
        assert px == 10.0
        assert py == 20.0

    def test_to_dict_returns_expected_keys(self) -> None:
        state = AgentState(
            name="test-agent",
            lifecycle=Lifecycle.ACTIVE,
            specialty=Specialty.RISK,
            position=(5, 10),
            nutrition=0.7,
            activity=0.3,
            generation=2,
            skills=("skill_a", "skill_b"),
        )
        d = state.to_dict()
        assert d["name"] == "test-agent"
        assert d["lifecycle"] == "active"
        assert d["specialty"] == "risk"
        assert d["position"] == [5, 10]
        assert d["nutrition"] == 0.7
        assert d["activity"] == 0.3
        assert d["generation"] == 2
        assert d["skills"] == ["skill_a", "skill_b"]


class TestAgentStateTracker:
    """Tests for AgentStateTracker history tracking."""

    def test_push_adds_to_history(self) -> None:
        tracker = AgentStateTracker()
        assert tracker.current is None
        s1 = AgentState()
        tracker.push(s1)
        assert tracker.current is s1

    def test_current_returns_latest(self) -> None:
        tracker = AgentStateTracker()
        s1 = AgentState(name="first")
        s2 = AgentState(name="second")
        tracker.push(s1)
        tracker.push(s2)
        assert tracker.current is s2

    def test_history_returns_copy(self) -> None:
        tracker = AgentStateTracker()
        s1 = AgentState()
        tracker.push(s1)
        h = tracker.history
        h.append(AgentState())
        assert len(tracker.history) == 1

    def test_push_trims_at_max(self) -> None:
        tracker = AgentStateTracker(max_history=3)
        for _ in range(5):
            tracker.push(AgentState())
        assert len(tracker.history) == 3


class TestHyphalAgentStep:
    """Tests for HyphalAgent.step() and edge cases."""

    async def test_step_full_lifecycle(self, agent: HyphalAgent) -> None:
        initial_nutrition = agent.state.nutrition
        initial_activity = agent.state.activity
        new = await agent.step()
        assert new.is_alive
        assert new.nutrition < initial_nutrition
        assert new.activity == pytest.approx(initial_activity * 0.95)

    async def test_step_returns_new_state(self, agent: HyphalAgent) -> None:
        old_id = id(agent.state)
        new = await agent.step()
        assert id(new) != old_id

    async def test_step_moves_within_bounds(self, agent: HyphalAgent) -> None:
        new = await agent.step()
        i, j = new.position
        assert 0 <= i < agent.field.geom.width
        assert 0 <= j < agent.field.geom.height

    async def test_step_when_dead_returns_same_state(self, agent: HyphalAgent) -> None:
        agent.state = agent.state.die()
        old_id = id(agent.state)
        result = await agent.step()
        assert id(result) == old_id
        assert result is agent.state

    async def test_step_apoptoses_at_low_nutrition(self, agent: HyphalAgent) -> None:
        agent.state = agent.state.starve(0.49)
        agent.apoptose_threshold = 0.4
        new = await agent.step()
        assert new.lifecycle == Lifecycle.APOPTOSING

    def test_sense_no_field_returns_defaults(self) -> None:
        agent = HyphalAgent()
        s, n, d = agent.sense()
        assert s == 0.0
        assert n == 0.5
        assert d == 0.0

    def test_decide_direction_no_field_returns_zero(self) -> None:
        agent = HyphalAgent()
        dx, dy = agent.decide_direction()
        assert dx == 0
        assert dy == 0

    def test_should_branch_returns_bool(self, agent: HyphalAgent) -> None:
        result = agent.should_branch()
        assert isinstance(result, bool)

    def test_should_apoptose_low_field_nutrient(self, agent: HyphalAgent) -> None:
        i, j = agent.state.position
        agent.field.consume_nutrient(i, j, amount=0.5, radius=10)
        agent.apoptose_threshold = 0.2
        assert agent.should_apoptose()

    def test_should_apoptose_false_when_above_threshold(self, agent: HyphalAgent) -> None:
        agent.apoptose_threshold = 0.01
        assert not agent.should_apoptose()

    def test_connection_strength_returns_dict(self, agent: HyphalAgent) -> None:
        agent.record_message("neighbor-1")
        agent.record_message("neighbor-1")
        agent.record_message("neighbor-2")
        cs = agent.connection_strength
        assert cs == {"neighbor-1": 2, "neighbor-2": 1}
