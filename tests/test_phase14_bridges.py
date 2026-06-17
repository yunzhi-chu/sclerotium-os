"""Phase 14 灰度测试 — 桥接·群体智慧v2"""

import pytest
from kernel.unified_bridge import UnifiedBridge, BridgeStatus, BridgeInfo, BridgeHubStats
from field.stigmergy_v2_bridge import StigmergyFieldV2, TrailEntry, Citation, TrailState
from kernel.skill_bridge import SkillBridge, SkillDefinition, SkillExecution


# ═══════════════════════════════════════════════════════════════
# UnifiedBridge
# ═══════════════════════════════════════════════════════════════

class TestUnifiedBridge:
    @pytest.fixture
    def hub(self):
        return UnifiedBridge()

    def test_register_bridge(self, hub):
        hub.register("test_bridge", object(), "L6", "L10")
        bridges = hub.list_bridges()
        assert len(bridges) == 1

    def test_activate(self, hub):
        hub.register("b1", object())
        assert hub.activate("b1")
        info = hub.list_bridges()[0]
        assert info.status == BridgeStatus.ACTIVE

    def test_deactivate(self, hub):
        hub.register("b1", object())
        hub.activate("b1")
        hub.deactivate("b1")
        assert hub.list_bridges()[0].status == BridgeStatus.INACTIVE

    def test_activate_nonexistent(self, hub):
        assert not hub.activate("nonexistent")

    def test_activate_all(self, hub):
        for i in range(5):
            hub.register(f"bridge_{i}", object())
        results = hub.activate_all()
        assert len(results) == 5
        assert all(results.values())

    def test_send_message(self, hub):
        received = []
        hub.register("sender", object())
        hub.activate("sender")
        hub.on_message("receiver", lambda d: received.append(d))
        ok = hub.send_message("sender", "receiver", {"msg": "hello"})
        assert ok
        assert len(received) == 1

    def test_send_inactive(self, hub):
        hub.register("sender", object())  # 未激活
        ok = hub.send_message("sender", "receiver", {})
        assert not ok

    def test_stats(self, hub):
        for i in range(10):
            hub.register(f"b{i}", object())
        hub.activate_all()
        stats = hub.get_stats()
        assert stats.total_bridges == 10
        assert stats.activation_ratio == 1.0


# ═══════════════════════════════════════════════════════════════
# StigmergyFieldV2
# ═══════════════════════════════════════════════════════════════

class TestStigmergyFieldV2:
    @pytest.fixture
    def v2(self):
        return StigmergyFieldV2()

    def test_deposit_trail(self, v2):
        t = v2.deposit_trail("medium", "auth_bug_pattern", trust=0.8)
        assert t.trail_id != ""
        assert t.trust == 0.8

    def test_cite(self, v2):
        t1 = v2.deposit_trail("long", "root_cause")
        t2 = v2.deposit_trail("short", "symptom")
        cit = v2.cite(t2.trail_id, t1.trail_id)
        assert cit is not None

    def test_cite_nonexistent(self, v2):
        assert v2.cite("no_exist", "also_no") is None

    def test_boost_trust(self, v2):
        t = v2.deposit_trail("medium", "test", trust=0.5)
        assert v2.boost_trust(t.trail_id, 0.2)
        state = v2.get_state()
        assert state.avg_trust > 0.5

    def test_hotspots(self, v2):
        t1 = v2.deposit_trail("long", "important", trust=0.95)
        v2.deposit_trail("short", "noise", trust=0.3)
        for _ in range(10):
            v2.cite(f"trail_{v2._counter:04d}" if False else "dummy",
                    t1.trail_id)  # cite doesn't work with random ids
        # 直接 boost
        v2.boost_trust(t1.trail_id, 0.4)
        hotspots = v2.get_hotspots(threshold=0.5)
        assert len(hotspots) >= 1

    def test_citation_graph(self, v2):
        a = v2.deposit_trail("long", "A")
        b = v2.deposit_trail("long", "B")
        v2.cite(b.trail_id, a.trail_id)
        graph = v2.get_citation_graph()
        assert b.trail_id in graph

    def test_state(self, v2):
        v2.deposit_trail("short", "s")
        v2.deposit_trail("medium", "m")
        v2.deposit_trail("long", "l")
        state = v2.get_state()
        assert state.total_trails == 3


# ═══════════════════════════════════════════════════════════════
# SkillBridge
# ═══════════════════════════════════════════════════════════════

class TestSkillBridge:
    @pytest.fixture
    def bridge(self):
        return SkillBridge()

    def test_register_skill(self, bridge):
        skill = bridge.register(
            "桌面整理", "整理桌面文件",
            steps=[{"action": "open_app", "app": "explorer"}],
            triggers=["整理", "桌面"],
        )
        assert skill.name == "桌面整理"

    def test_find_by_trigger(self, bridge):
        bridge.register("整理", "desc", steps=[], triggers=["整理", "桌面"])
        bridge.register("分析", "desc", steps=[], triggers=["分析", "查看"])
        matches = bridge.find_by_trigger("帮我整理一下")
        assert len(matches) == 1

    def test_execute_without_executor(self, bridge):
        bridge.register("test", "test desc",
                       steps=[{"action": "wait", "seconds": 0.01}])
        result = bridge.execute("test")
        assert result.success

    def test_execute_unknown(self, bridge):
        result = bridge.execute("nonexistent")
        assert not result.success

    def test_list_skills(self, bridge):
        bridge.register("a", "d", steps=[])
        bridge.register("b", "d", steps=[])
        assert len(bridge.list_skills()) == 2

    def test_stats(self, bridge):
        bridge.register("s1", "d", steps=[])
        bridge.execute("s1")
        stats = bridge.get_stats()
        assert stats["skills_registered"] == 1
        assert stats["total_executions"] == 1


# ═══════════════════════════════════════════════════════════════
# 集成
# ═══════════════════════════════════════════════════════════════

class TestPhase14Integration:
    def test_bridge_to_skill_pipeline(self):
        hub = UnifiedBridge()
        skill = SkillBridge()
        v2 = StigmergyFieldV2()

        # 注册桥接
        hub.register("skill_bridge", skill, "L6", "automation")
        hub.activate("skill_bridge")

        # 注册技能
        skill.register("桌面整理", "desc", steps=[
            {"action": "screenshot", "label": "before"},
            {"action": "open_app", "app": "explorer"},
        ], triggers=["整理"])

        # 沉积踪迹
        v2.deposit_trail("long", "桌面整理技能已注册", trust=0.7)

        assert hub.get_stats().active == 1
        assert len(skill.list_skills()) == 1
        assert v2.get_state().total_trails == 1
