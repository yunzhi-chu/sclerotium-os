"""Phase 11 灰度测试 — 信息素场·世界模型·数字孪生 (L5+L7)。

测试覆盖:
  - StigmergyBridge: 沉积/扩散/蒸发/热点/场状态
  - DigitalTwinEngine: 器官更新/快照/预测
  - ActiveInferenceAgent: 行动选择/EFE/自然停止
"""

from __future__ import annotations

import pytest

from field.stigmergy_bridge import StigmergyBridge, FieldPoint, FieldState
from world.digital_twin import (
    DigitalTwinEngine, SystemSnapshot, OrganMirror, Prediction,
)
from world.active_inference_agent import (
    ActiveInferenceAgent, ActionPolicy, ActionOption, AIState,
)


# ═══════════════════════════════════════════════════════════════
# StigmergyBridge
# ═══════════════════════════════════════════════════════════════

class TestFieldPoint:
    def test_create(self):
        p = FieldPoint(x=10, y=20, intensity=0.7, category="perception")
        assert p.intensity == 0.7

    def test_frozen(self):
        p = FieldPoint(x=0, y=0, intensity=0.5)
        with pytest.raises(Exception):
            p.intensity = 1.0  # type: ignore


class TestStigmergyBridge:
    @pytest.fixture
    def field(self):
        return StigmergyBridge(grid_size=32)

    def test_deposit(self, field):
        field.deposit("perception", x=15, y=15, intensity=0.8)
        p = field.query_point(15, 15)
        assert p.intensity > 0.7

    def test_deposit_random(self, field):
        field.deposit("memory")
        # 应该有强度在某个位置
        state = field.get_state()
        assert state.total_intensity > 0

    def test_diffuse(self, field):
        field.deposit("test", x=16, y=16, intensity=1.0)
        field.diffuse()
        # 扩散后中心点强度降低, 邻域增加
        center = field.query_point(16, 16)
        neighbor = field.query_point(15, 16)
        assert center.intensity < 1.0  # 扩散了
        assert neighbor.intensity > 0.0  # 邻域收到

    def test_evaporation(self, field):
        field.deposit("test", x=10, y=10, intensity=0.5)
        for _ in range(20):
            field.diffuse()
        p = field.query_point(10, 10)
        assert p.intensity < 0.1  # 几乎蒸发完了

    def test_hotspots(self, field):
        field.deposit("perception", x=5, y=5, intensity=0.9)
        field.deposit("memory", x=20, y=20, intensity=0.9)
        hotspots = field.get_hotspots(threshold=0.7)
        assert len(hotspots) >= 2

    def test_hotspots_empty(self, field):
        hotspots = field.get_hotspots(threshold=0.5)
        assert hotspots == []

    def test_multi_deposit_accumulate(self, field):
        for _ in range(5):
            field.deposit("test", x=10, y=10, intensity=0.3)
        p = field.query_point(10, 10)
        assert p.intensity > 0.5  # 积累

    def test_state(self, field):
        field.deposit("perception", x=5, y=5, intensity=0.8)
        field.deposit("perception", x=6, y=6, intensity=0.8)
        state = field.get_state()
        assert state.dominant_category == "perception"

    def test_clamping(self, field):
        field.deposit("test", x=10, y=10, intensity=3.0)
        p = field.query_point(10, 10)
        assert p.intensity <= 1.0  # 钳制

    def test_out_of_bounds(self, field):
        field.deposit("test", x=-10, y=100, intensity=0.5)
        # 不应崩溃, 钳制到有效范围
        state = field.get_state()
        assert isinstance(state, FieldState)


# ═══════════════════════════════════════════════════════════════
# DigitalTwinEngine
# ═══════════════════════════════════════════════════════════════

class TestDigitalTwinEngine:
    @pytest.fixture
    def twin(self):
        return DigitalTwinEngine()

    def test_update_organ(self, twin):
        twin.update_organ("perception/window_watcher",
                         {"status": "healthy", "uptime": 3600})
        snap = twin.get_snapshot()
        assert snap.total_organs == 1
        assert snap.healthy_organs == 1

    def test_multiple_organs(self, twin):
        for i in range(5):
            twin.update_organ(f"organ_{i}", {"status": "healthy"})
        snap = twin.get_snapshot()
        assert snap.total_organs == 5

    def test_degraded_detection(self, twin):
        twin.update_organ("good", {"status": "healthy"})
        twin.update_organ("bad", {"status": "failing"})
        snap = twin.get_snapshot()
        assert snap.healthy_organs == 1
        assert snap.degraded_organs == 1

    def test_health_ratio(self, twin):
        twin.update_organ("a", {"status": "healthy"})
        twin.update_organ("b", {"status": "healthy"})
        twin.update_organ("c", {"status": "failing"})
        snap = twin.get_snapshot()
        assert snap.health_ratio == pytest.approx(2/3)

    def test_predict_safe(self, twin):
        twin.update_organ("window_watcher", {"status": "healthy"})
        pred = twin.predict("check window_watcher")
        assert pred.confidence > 0.5
        assert pred.risk_level < 0.5

    def test_predict_risky(self, twin):
        twin.update_organ("critical_service", {"status": "failing"})
        pred = twin.predict("restart critical_service")
        assert pred.risk_level > 0.3

    def test_history(self, twin):
        twin.update_organ("test", {"status": "healthy"})
        twin.get_snapshot()
        twin.get_snapshot()
        assert len(twin.get_history()) == 2


# ═══════════════════════════════════════════════════════════════
# ActiveInferenceAgent
# ═══════════════════════════════════════════════════════════════

class TestActiveInferenceAgent:
    @pytest.fixture
    def agent(self):
        return ActiveInferenceAgent(stop_threshold=0.15)

    def test_no_actions_stop(self, agent):
        policy = agent.select_action()
        assert policy.should_stop

    def test_select_best_action(self, agent):
        agent.add_action("read", pragmatic=0.9, epistemic=0.1, risk=0.0)
        agent.add_action("write", pragmatic=0.3, epistemic=0.2, risk=0.3)
        policy = agent.select_action()
        assert policy.action == "read"

    def test_stop_when_efe_high(self, agent):
        # EFE = -(0.1+0.05)+0+0.2 = -0.15+0.2 = 0.05 > -0.15 → stop
        agent.add_action("low_value", pragmatic=0.1, epistemic=0.05,
                        risk=0.0, cost=0.2)
        policy = agent.select_action()
        assert policy.should_stop

    def test_proceed_when_efe_low(self, agent):
        agent.add_action("high_value", pragmatic=0.95, epistemic=0.05,
                        risk=0.0, cost=0.0)
        policy = agent.select_action()
        assert not policy.should_stop

    def test_risk_increases_efe(self, agent):
        # EFE = -(0.8+0.1)+0.9+0 = 0.0
        agent.add_action("risky", pragmatic=0.8, epistemic=0.1,
                        risk=0.9, cost=0.0)
        policy = agent.select_action()
        assert policy.efe >= 0.0  # risk cancels out the benefit

    def test_efe_calculation(self, agent):
        # EFE = -(pragmatic + epistemic) + risk + cost
        # EFE = -(0.5 + 0.3) + 0 + 0.1 = -0.7
        agent.add_action("test", pragmatic=0.5, epistemic=0.3,
                        risk=0.0, cost=0.1)
        policy = agent.select_action()
        assert policy.efe == pytest.approx(-0.7)

    def test_state_tracking(self, agent):
        for _ in range(5):
            agent.add_action("step", pragmatic=0.7, epistemic=0.2)
            agent.select_action()
            agent.clear_actions()
        state = agent.get_state()
        assert state.total_actions == 5

    def test_frozen_policy(self):
        p = ActionPolicy(action="test", efe=-0.5, should_stop=False)
        with pytest.raises(Exception):
            p.action = "changed"  # type: ignore


# ═══════════════════════════════════════════════════════════════
# 集成
# ═══════════════════════════════════════════════════════════════

class TestPhase11Integration:
    def test_field_to_twin_integration(self):
        """信息素场检测到热点 → 孪生更新器官状态。"""
        field = StigmergyBridge()
        twin = DigitalTwinEngine()

        # 模拟活动 → 信息素
        for i in range(10):
            field.deposit("perception", x=20+i, y=15, intensity=0.8)
        hotspots = field.get_hotspots(threshold=0.5)
        twin.update_organ("perception/hotspot_zone",
                         {"status": "active" if hotspots else "idle"})

        snap = twin.get_snapshot()
        assert snap.total_organs == 1

    def test_field_diffusion_cycle(self):
        """完整扩散周期：沉积→扩散→蒸发→热点检测。"""
        field = StigmergyBridge(grid_size=16)

        # 模拟10个事件沉积
        for i in range(10):
            field.deposit(f"cat_{i%3}", x=8+i, y=8, intensity=0.5)

        # 执行20次扩散 (模拟时间流逝)
        for _ in range(20):
            field.diffuse()

        # 旧事件大部分蒸发 (初始~5.0, 20次蒸发后衰减)
        state = field.get_state()
        assert state.total_intensity < 3.0
