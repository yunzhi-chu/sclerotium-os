"""测试: 全部后台→前台映射"""

import json
import pytest
import urllib.request
import time

from kernel.frontend_bridge import FrontendBridge, SystemSnapshot, OrganCard
from kernel.constitutional_arbiter import ConstitutionalArbiter, ActionRequest
from kernel.immune_gateway import ImmuneGateway
from kernel.consciousness_monitor import ConsciousnessMonitor
from kernel.self_awareness import SelfAwareness
from kernel.event_bus import EventBus
from kernel.hexis_memory import HexisMemoryStore
from kernel.meta_cognition_bridge import MetaCognitionBridge
from evolution.fcpi_tracker import FCPITracker
from evolution.evolution_loop import EvolutionLoop
from evolution.strategy_genome import StrategyGenome
from rhythm.nudge_engine import NudgeEngine
from field.stigmergy_bridge import StigmergyBridge
from world.digital_twin import DigitalTwinEngine
from gateways.custom_provider import CustomProviderGateway


class TestOrganCard:
    def test_create(self):
        c = OrganCard(name="test", layer="L0", category="sense",
                     status="healthy")
        assert c.name == "test"

    def test_frozen(self):
        c = OrganCard(name="x", layer="L0")
        with pytest.raises(Exception):
            c.status = "failing"  # type: ignore


class TestFrontendBridge:
    @pytest.fixture
    def bridge(self):
        return FrontendBridge()

    def test_register(self, bridge):
        card = bridge.register("test_module", object(), "L6", "think")
        assert card.name == "test_module"
        assert card.layer == "L6"

    def test_snapshot_empty(self, bridge):
        snap = bridge.snapshot()
        assert snap.total_organs == 0

    def test_snapshot_with_modules(self, bridge, tmp_path):
        """注册多个真实模块 → 快照包含全部。"""
        bus = EventBus()
        arbiter = ConstitutionalArbiter()
        tracker = FCPITracker()
        monitor = ConsciousnessMonitor()
        field = StigmergyBridge()

        bridge.register("event_bus", bus, "core", "sense")
        bridge.register("constitutional_arbiter", arbiter, "L10", "act")
        bridge.register("fcpi_tracker", tracker, "L6", "evolve")
        bridge.register("consciousness_monitor", monitor, "L10", "think")
        bridge.register("stigmergy_field", field, "L5", "metabolize")

        # 产生一些活动
        tracker.record_coding(test_pass=True)
        arbiter.review(ActionRequest(tool="file_read", target="test"))
        bus.publish("test.topic", {"data": 1})

        snap = bridge.snapshot()
        assert snap.total_organs == 5
        assert len(snap.sense_organs) == 1
        assert len(snap.act_organs) == 1
        assert len(snap.evolve_organs) == 1
        assert len(snap.think_organs) == 1
        assert len(snap.metabolize_organs) == 1

    def test_to_json(self, bridge):
        bridge.register("test", object(), "L1", "sense")
        data = bridge.to_json()
        parsed = json.loads(data)
        assert "symphony" in parsed
        assert "metrics" in parsed
        assert parsed["organs"]["total"] == 1

    def test_system_snapshot_frozen(self):
        snap = SystemSnapshot()
        with pytest.raises(Exception):
            snap.version = "changed"  # type: ignore


class TestFrontendToDashboard:
    """前端桥接→仪表盘 集成测试。"""

    def test_bridge_to_dashboard_data(self):
        bridge = FrontendBridge()
        arbiter = ConstitutionalArbiter()
        tracker = FCPITracker()
        monitor = ConsciousnessMonitor()

        bridge.register("arbiter", arbiter, "L10", "act")
        bridge.register("fcpi", tracker, "L6", "evolve")
        bridge.register("consciousness", monitor, "L10", "think")

        tracker.record_coding(test_pass=True)
        tracker.record_safety(error=False)
        monitor.update_phi(active_topics=10, responding_organs=5, total_events=100)

        snap = bridge.snapshot()
        assert snap.fcpi_score > 0.4
        assert snap.phi_value > 0.4

    def test_full_dashboard_serves(self, tmp_path):
        """完整仪表盘启动→HTTP响应。"""
        bridge = FrontendBridge()
        bridge.register("arbiter", ConstitutionalArbiter(), "L10", "act")
        bridge.register("fcpi", FCPITracker(), "L6", "evolve")

        from ui.dashboard_web import FullDashboardServer
        port = 11992
        server = FullDashboardServer(port=port, bridge=bridge)
        server.start()
        time.sleep(0.3)

        try:
            code, body = _http_get(f"http://127.0.0.1:{port}/")
            assert code == 200
            html = body.decode("utf-8")
            assert "Sclerotium OS v5.0" in html
            assert "SENSE" in html or "THINK" in html or "ACT" in html

            code2, body2 = _http_get(f"http://127.0.0.1:{port}/api/full")
            assert code2 == 200
            data = json.loads(body2)
            assert "symphony" in data
        finally:
            server.stop()

    def test_full_json_api(self, tmp_path):
        """JSON API 返回完整数据。"""
        bridge = FrontendBridge()
        for org_data in [
            ("arbiter", ConstitutionalArbiter(), "L10", "act"),
            ("fcpi", FCPITracker(), "L6", "evolve"),
            ("consciousness", ConsciousnessMonitor(), "L10", "think"),
            ("field", StigmergyBridge(), "L5", "metabolize"),
            ("event_bus", EventBus(), "core", "sense"),
        ]:
            bridge.register(*org_data)

        json_str = bridge.to_json()
        data = json.loads(json_str)

        assert "symphony" in data
        assert len(data["symphony"]["act"]) >= 1
        assert len(data["symphony"]["evolve"]) >= 1
        assert len(data["symphony"]["think"]) >= 1
        assert len(data["symphony"]["metabolize"]) >= 1
        assert len(data["symphony"]["sense"]) >= 1


def _http_get(url, timeout=3):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except Exception as e:
        return 0, str(e).encode()
