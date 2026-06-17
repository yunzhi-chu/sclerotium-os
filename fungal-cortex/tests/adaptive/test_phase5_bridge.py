"""Tests for Phase 5.1: AdaptiveDebateBridge (HPA<->Immune)."""
import pytest
from src.adaptive.debate_adaptive_bridge import (
    AdaptiveDebateBridge, ImmuneState, DebateParams,
)


class TestAdaptiveDebateBridge:
    def test_bear_suppresses_immune(self):
        bridge = AdaptiveDebateBridge()
        params = bridge.adapt_from_regime("bear", 0, 0.9, 0.3)
        assert params.debate_rounds >= 2
        assert params.bear_weight > params.bull_weight
        assert params.confidence_threshold >= 0.65

    def test_bull_activates_immune(self):
        bridge = AdaptiveDebateBridge()
        params = bridge.adapt_from_regime("bull", 1, 0.85, 0.2)
        assert params.debate_rounds <= 2
        assert params.bull_weight >= 1.0

    def test_crash_maximum_suppression(self):
        bridge = AdaptiveDebateBridge()
        params = bridge.adapt_from_regime("crash", 0, 0.95, 0.1)
        assert bridge.get_immune_state() == ImmuneState.SUPPRESSED
        assert params.debate_rounds >= 3

    def test_equilibrium_normal(self):
        bridge = AdaptiveDebateBridge()
        params = bridge.adapt_from_regime("equilibrium", 2, 0.6, 1.0)
        assert bridge.get_immune_state() == ImmuneState.NORMAL

    def test_feedback_tighten_on_high_refute(self):
        bridge = AdaptiveDebateBridge()
        fb = bridge.feedback_to_regime(2, 8, 10)
        assert fb["direction"] == "tighten"

    def test_feedback_relax_on_high_verify(self):
        bridge = AdaptiveDebateBridge()
        fb = bridge.feedback_to_regime(8, 1, 10)
        assert fb["direction"] == "relax"

    def test_adapt_from_report(self):
        bridge = AdaptiveDebateBridge()
        params = bridge.adapt_from_regime_report({
            "regime_label": "bear_volatile", "regime_index": 0,
            "confidence": 0.8, "entropy": 0.5,
        })
        assert params.debate_rounds >= 2

    def test_cortisol_analog_range(self):
        bridge = AdaptiveDebateBridge()
        params_crash = bridge.adapt_from_regime("crash", 0, 0.99, 0.1)
        params_rally = bridge.adapt_from_regime("rally", 1, 0.9, 0.1)
        assert params_crash.confidence_threshold > params_rally.confidence_threshold
