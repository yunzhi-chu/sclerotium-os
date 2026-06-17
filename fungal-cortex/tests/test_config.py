"""Tests for config module — YAML + Pydantic configuration system."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from src.config import (
    AgentConfig,
    AppConfig,
    AutocatalyticConfig,
    BridgeConfig,
    CoreConfig,
    FieldConfig,
    L6Config,
    LLMConfig,
    MonitoringConfig,
    PipelineConfig,
    TradingConfig,
    get_config,
    set_config,
)


class TestLLMConfig:
    def test_defaults(self):
        cfg = LLMConfig()
        assert cfg.deep_think_model == "deepseek-pro"
        assert cfg.quick_think_model == "deepseek-flash"
        assert cfg.fallback_model == "deepseek-pro"
        assert cfg.temperature_deep == 0.3
        assert cfg.temperature_quick == 0.7
        assert cfg.max_tokens_deep == 8192
        assert cfg.max_tokens_quick == 2048


class TestFieldConfig:
    def test_defaults(self):
        cfg = FieldConfig()
        assert cfg.grid_size == (256, 256)
        assert cfg.diffusion_rate_signal == 0.1
        assert cfg.diffusion_rate_nutrient == 0.05
        assert cfg.diffusion_rate_damage == 0.02
        assert cfg.decay_rate == 0.01
        assert cfg.dt == 0.01
        assert cfg.spectral_method is True


class TestAgentConfig:
    def test_defaults(self):
        cfg = AgentConfig()
        assert cfg.max_agents == 100
        assert cfg.branch_probability == 0.05
        assert cfg.apoptose_threshold == 0.1
        assert cfg.myelinate_threshold == 100
        assert cfg.enactive_temperature == 1.0
        assert cfg.prediction_horizon == 10


class TestL6Config:
    def test_defaults(self):
        cfg = L6Config()
        assert cfg.scan_interval_seconds == 3600
        assert cfg.auto_refactor_enabled is True
        assert cfg.require_human_approval is True
        assert cfg.max_pending_approvals == 10
        assert cfg.crystallize_confidence_threshold == 0.6

    def test_m1_settings(self):
        cfg = L6Config()
        assert cfg.scan_interval_seconds == 3600
        assert cfg.max_pending_approvals == 10

    def test_m2_settings(self):
        cfg = L6Config()
        assert cfg.max_generation_retries == 3
        assert cfg.min_backtest_sharpe == 0.3

    def test_m5_settings(self):
        cfg = L6Config()
        assert cfg.rate_limit_per_minute == 60
        assert cfg.rate_limit_per_hour == 1000

    def test_m7_settings(self):
        cfg = L6Config()
        assert cfg.emergence_min_agents == 3
        assert cfg.crystallize_confidence_threshold == 0.6


class TestCoreConfig:
    def test_defaults(self):
        cfg = CoreConfig()
        assert cfg.event_bus_backlog == 10000
        assert cfg.skill_registry_auto_reload is True
        assert cfg.cognitive_depth_default == 3


class TestPipelineConfig:
    def test_defaults(self):
        cfg = PipelineConfig()
        assert cfg.max_pipeline_depth == 8
        assert cfg.layer_timeout_seconds == 30.0
        assert cfg.pipeline_tick_interval == 0.1


class TestBridgeConfig:
    def test_defaults(self):
        cfg = BridgeConfig()
        assert cfg.dna_vector_dimensions == 6
        assert cfg.ktd_fin_barra_factors == 7


class TestMonitoringConfig:
    def test_defaults(self):
        cfg = MonitoringConfig()
        assert cfg.prometheus_port == 9090


class TestTradingConfig:
    def test_defaults(self):
        cfg = TradingConfig()
        assert cfg.risk_gate_count == 5
        assert len(cfg.risk_gate_factions) == 3


class TestAutocatalyticConfig:
    def test_defaults(self):
        cfg = AutocatalyticConfig()
        assert cfg.catalysis_ring_min_size == 3
        assert cfg.catalysis_graph_max_nodes == 500


class TestAppConfig:
    def test_default_creation(self):
        cfg = AppConfig()
        assert cfg.field.grid_size == (256, 256)
        assert cfg.llm.deep_think_model == "deepseek-pro"
        assert cfg.l6.scan_interval_seconds == 3600
        assert cfg.agent.max_agents == 100

    def test_from_yaml(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        try:
            f.write("""field:
  grid_size: [512, 512]
  diffusion_rate_signal: 0.15
llm:
  deep_think_model: "gpt-5"
agent:
  max_agents: 50
l6:
  scan_interval_seconds: 1800
  auto_refactor_enabled: false
""")
            f.close()
            cfg = AppConfig.from_yaml(Path(f.name))
            assert cfg.field.grid_size == (512, 512)
            assert cfg.llm.deep_think_model == "gpt-5"
            assert cfg.agent.max_agents == 50
            assert cfg.l6.scan_interval_seconds == 1800
            assert cfg.l6.auto_refactor_enabled is False
        finally:
            os.unlink(f.name)

    def test_from_yaml_default_path(self):
        """Test from_yaml with no path argument (uses env or default)."""
        cfg = AppConfig.from_yaml()
        assert isinstance(cfg, AppConfig)
        assert cfg.field.grid_size == (256, 256)

    def test_from_yaml_nonexistent_file(self):
        cfg = AppConfig.from_yaml(Path("/nonexistent/path/config.yaml"))
        assert isinstance(cfg, AppConfig)
        assert cfg.field.grid_size == (256, 256)

    def test_to_yaml(self):
        cfg = AppConfig()
        fname = tempfile.mktemp(suffix=".yaml")
        try:
            cfg.to_yaml(Path(fname))
            content = Path(fname).read_text()
            assert "deep_think_model" in content
        finally:
            if Path(fname).exists():
                os.unlink(fname)


class TestConfigSingleton:
    def test_get_config_returns_singleton(self):
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_set_config_overrides(self):
        original = get_config()
        new_cfg = AppConfig()
        set_config(new_cfg)
        assert get_config() is new_cfg
        set_config(original)
