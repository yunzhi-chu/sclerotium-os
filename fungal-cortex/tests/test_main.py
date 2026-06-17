"""Tests for main.py — FastAPI application entry point and endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture(autouse=True)
def setup_minimal_services():
    """Initialize minimal services for testing without full lifespan."""
    from src.core.event_bus import EventBus
    from src.core.skill_registry import SkillRegistry
    from src.l6.emergence_capture import EmergenceCapture
    from src.l6.security_gateway import CrossEcoSecurityGateway
    from src.l6.rule_evolution import DynamicRuleEvolutionEngine
    from src.l6.goal_expander import GlobalGoalExpander
    from src.l6.auto_refactor import AutoRefactorEngine
    from src.l6.sandbox_pipeline import SandboxVerificationPipeline
    from src.l6.ability_factory import AbilityCreationFactory
    from src.l6.meta_cognition import MetaCognitionEngine
    from src.bridge.strategy_dna_loader import StrategyDNALoader
    from src.bridge.l0_l7_pipeline import L0L7Pipeline
    from src.bridge.final_bench_bridge import FINALBenchBridge
    from src.orchestration.cluster_manager import ClusterManager
    from src.trading.data_pipeline import DataPipeline
    from src.trading.risk_gate import RiskGate
    from src.trading.portfolio_manager import PortfolioManager
    from src.field.stigmergy_field import StigmergyField
    from src.monitoring.prometheus_exporter import PrometheusExporter

    app.state.event_bus = EventBus()
    app.state.skill_registry = SkillRegistry()
    app.state.emergence_capture = EmergenceCapture()
    app.state.security_gateway = CrossEcoSecurityGateway()
    app.state.rule_evolution = DynamicRuleEvolutionEngine()
    app.state.goal_expander = GlobalGoalExpander()
    app.state.auto_refactor = AutoRefactorEngine()
    app.state.sandbox = SandboxVerificationPipeline()
    app.state.ability_factory = AbilityCreationFactory(
        skill_registry=app.state.skill_registry, sandbox=app.state.sandbox
    )
    app.state.meta_cognition = MetaCognitionEngine(
        skill_registry=app.state.skill_registry, event_bus=app.state.event_bus
    )
    app.state.strategy_loader = StrategyDNALoader()
    app.state.strategy_loader.load()
    app.state.pipeline = L0L7Pipeline(event_bus=app.state.event_bus)
    app.state.final_bench = FINALBenchBridge()
    app.state.cluster_manager = ClusterManager(event_bus=app.state.event_bus)
    app.state.data_pipeline = DataPipeline()
    app.state.risk_gate = RiskGate()
    app.state.portfolio_manager = PortfolioManager()
    app.state.stigmergy_field = StigmergyField()
    app.state.prometheus = PrometheusExporter()
    yield
    # Clean up
    for attr in list(app.state.__dict__.keys()):
        if not attr.startswith("_"):
            delattr(app.state, attr)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "health_score" in data["data"]
        assert data["data"]["version"] == "2.0.0"

    def test_health_data_structure(self, client):
        resp = client.get("/api/health")
        data = resp.json()["data"]
        assert "status" in data
        assert "agents" in data
        assert "skills" in data
        assert "pipeline" in data
        assert "phase" in data


class TestSkillsEndpoints:
    def test_list_skills_empty(self, client):
        resp = client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "meta" in data

    def test_list_skills_with_filters(self, client):
        resp = client.get("/api/skills?category=core&search=test&page=1&limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert "meta" in data
        assert data["meta"]["page"] == 1

    def test_get_skill_not_found(self, client):
        resp = client.get("/api/skills/nonexistent")
        assert resp.status_code == 404
        assert resp.json()["success"] is False


class TestStrategiesEndpoint:
    def test_list_strategies(self, client):
        resp = client.get("/api/strategies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_list_strategies_with_filters(self, client):
        resp = client.get("/api/strategies?search=momentum&min_sharpe=1.5&page=1&limit=20")
        assert resp.status_code == 200


class TestBacktestEndpoint:
    def test_run_backtest(self, client):
        resp = client.post("/api/backtest", json={"strategy": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True


class TestAuditEndpoint:
    def test_list_audit_records(self, client):
        resp = client.get("/api/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_list_audit_with_filters(self, client):
        resp = client.get(
            "/api/audit?event_type=error&severity=high&module=l6&from_date=2026-01-01&to_date=2026-06-01&page=1&limit=50"
        )
        assert resp.status_code == 200


class TestL6Endpoints:
    def test_trigger_l6_scan(self, client):
        resp = client.post("/api/l6/scan")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_approve_refactor(self, client):
        resp = client.post("/api/l6/refactor/issue-001/approve")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_create_ability(self, client):
        resp = client.post("/api/l6/create-ability", json={"name": "test-ability"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_list_emergence_events(self, client):
        resp = client.get("/api/l6/emergence")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_crystallize_pattern(self, client):
        resp = client.post("/api/l6/crystallize/pattern-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True


class TestGoalsEndpoints:
    def test_list_goals(self, client):
        resp = client.get("/api/goals")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_deploy_goal(self, client):
        resp = client.post("/api/goals/deploy", json={"name": "test-goal", "domain": "china-finance"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "goal_id" in data["data"]


class TestGatewayEndpoints:
    def test_list_gateway_services(self, client):
        resp = client.get("/api/gateway/services")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_register_service(self, client):
        resp = client.post("/api/gateway/register", json={"name": "test-svc", "type": "data_provider"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True


class TestRulesEndpoints:
    def test_list_rule_tests(self, client):
        resp = client.get("/api/rules/tests")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_generate_rules(self, client):
        resp = client.post("/api/rules/generate", json={"strategy_type": "momentum"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True


class TestWebSocketEndpoints:
    def test_ws_health_connects(self, client):
        with client.websocket_connect("/ws/health") as ws:
            data = ws.receive_json()
            assert data["type"] == "health"
            assert "health_score" in data

    def test_ws_pipeline_connects(self, client):
        with client.websocket_connect("/ws/pipeline") as ws:
            data = ws.receive_json()
            assert data["type"] == "pipeline"
            assert "layers" in data
            assert "L0" in data["layers"]

    def test_ws_agents_connects(self, client):
        with client.websocket_connect("/ws/agents") as ws:
            data = ws.receive_json()
            assert data["type"] == "agents"
            assert "nodes" in data

    def test_ws_field_connects(self, client):
        with client.websocket_connect("/ws/field") as ws:
            data = ws.receive_json()
            assert data["type"] == "field_update"
            assert "signal" in data

    def test_ws_l6_connects(self, client):
        with client.websocket_connect("/ws/l6") as ws:
            data = ws.receive_json()
            assert data["type"] == "l6"
            assert "health" in data
            assert "ma_er" in data

    def test_ws_trading_connects(self, client):
        with client.websocket_connect("/ws/trading") as ws:
            data = ws.receive_json()
            assert data["type"] == "trading"
            assert "positions" in data

    def test_ws_market_connects(self, client):
        with client.websocket_connect("/ws/market") as ws:
            data = ws.receive_json()
            assert data["type"] == "tick"
            assert "symbol" in data
            assert "price" in data


class TestAppStructure:
    def test_cors_middleware(self):
        assert len(app.user_middleware) > 0

    def test_app_title(self):
        assert "Fungal Cortex" in app.title
