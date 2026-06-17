"""Tests for Phase 3 Trading layer."""
import pytest
from src.trading.data_pipeline import DataPipeline, Market, MarketStatus, TickData, OHLCBar, MarketDataSource
from src.trading.risk_gate import RiskGate, RiskFaction, RiskGateResult, GateResult
from src.trading.portfolio_manager import PortfolioManager, PortfolioState, AllocationDecision, Position


class TestDataPipeline:
    @pytest.fixture
    def pipeline(self) -> DataPipeline:
        p = DataPipeline(tick_buffer_size=100)
        p.register_source(Market.CN, ["000001.SZ", "600000.SH"])
        p.set_market_status(Market.CN, MarketStatus.OPEN)
        return p

    def test_register_source(self, pipeline: DataPipeline) -> None:
        assert pipeline.get_market_status(Market.CN) == MarketStatus.OPEN

    def test_ingest_valid_tick(self, pipeline: DataPipeline) -> None:
        tick = TickData(symbol="000001.SZ", market=Market.CN, price=10.5, volume=1000)
        assert pipeline.ingest_tick(tick)

    def test_ingest_rejects_closed_market(self, pipeline: DataPipeline) -> None:
        pipeline.set_market_status(Market.CN, MarketStatus.CLOSED)
        tick = TickData(symbol="000001.SZ", market=Market.CN, price=10.5, volume=1000)
        assert not pipeline.ingest_tick(tick)

    def test_ingest_rejects_negative_price(self, pipeline: DataPipeline) -> None:
        with pytest.raises(ValueError):
            TickData(symbol="000001.SZ", market=Market.CN, price=-5.0, volume=1000)

    def test_ingest_rejects_old_timestamp(self, pipeline: DataPipeline) -> None:
        import time
        tick1 = TickData(symbol="000001.SZ", market=Market.CN, price=10.0, volume=100, timestamp=time.time())
        tick2 = TickData(symbol="000001.SZ", market=Market.CN, price=10.1, volume=100, timestamp=time.time() + 10)
        tick3 = TickData(symbol="000001.SZ", market=Market.CN, price=9.9, volume=100, timestamp=time.time() + 5)  # Out of order
        pipeline.ingest_tick(tick1)
        pipeline.ingest_tick(tick2)
        assert not pipeline.ingest_tick(tick3)

    def test_ohlc_bars_created(self, pipeline: DataPipeline) -> None:
        import time
        base = time.time()
        pipeline.ingest_tick(TickData("000001.SZ", Market.CN, 10.0, 100, base))
        pipeline.ingest_tick(TickData("000001.SZ", Market.CN, 10.5, 200, base + 30))
        pipeline.ingest_tick(TickData("000001.SZ", Market.CN, 9.8, 150, base + 50))
        bars = pipeline.get_ohlc("000001.SZ", "1m")
        assert len(bars) >= 1

    def test_get_ticks_filtered(self, pipeline: DataPipeline) -> None:
        pipeline.ingest_tick(TickData("000001.SZ", Market.CN, 10.0, 100))
        pipeline.ingest_tick(TickData("600000.SH", Market.CN, 20.0, 100))
        ticks = pipeline.get_ticks(symbol="000001.SZ")
        assert all(t.symbol == "000001.SZ" for t in ticks)

    def test_market_data_source_add_remove_symbol(self) -> None:
        source = MarketDataSource(Market.HK)
        source.add_symbol("00700.HK")
        assert "00700.HK" in source.symbols
        source.remove_symbol("00700.HK")
        assert "00700.HK" not in source.symbols

    def test_set_market_status(self, pipeline: DataPipeline) -> None:
        pipeline.set_market_status(Market.US, MarketStatus.PRE_OPEN)
        assert pipeline.get_market_status(Market.US) == MarketStatus.PRE_OPEN

    def test_stats(self, pipeline: DataPipeline) -> None:
        pipeline.ingest_tick(TickData("000001.SZ", Market.CN, 10.0, 100))
        s = pipeline.stats
        assert s["total_ticks"] == 1
        assert "markets" in s


class TestRiskGate:
    @pytest.fixture
    def gate(self) -> RiskGate:
        return RiskGate(faction=RiskFaction.NEUTRAL)

    def test_default_faction_neutral(self, gate: RiskGate) -> None:
        assert gate.faction == RiskFaction.NEUTRAL

    def test_position_limit_pass(self, gate: RiskGate) -> None:
        result = gate.check_position_limit(0.05, 1000000.0)
        assert result.result == GateResult.PASS

    def test_position_limit_warn(self, gate: RiskGate) -> None:
        result = gate.check_position_limit(0.12, 1000000.0)
        assert result.result in (GateResult.PASS, GateResult.WARN)

    def test_position_limit_block(self, gate: RiskGate) -> None:
        result = gate.check_position_limit(0.30, 1000000.0)
        assert result.result == GateResult.BLOCK

    def test_stop_loss_pass(self, gate: RiskGate) -> None:
        result = gate.check_stop_loss(0.05, 10.0, 9.5)
        assert result.result == GateResult.PASS

    def test_stop_loss_block(self, gate: RiskGate) -> None:
        result = gate.check_stop_loss(0.25, 10.0, 7.5)
        assert result.result == GateResult.BLOCK

    def test_aggressive_faction_higher_limits(self, gate: RiskGate) -> None:
        gate.set_faction(RiskFaction.AGGRESSIVE)
        result = gate.check_position_limit(0.10, 1000000.0)
        assert result.result == GateResult.PASS

    def test_conservative_faction_lower_limits(self) -> None:
        gate = RiskGate(faction=RiskFaction.CONSERVATIVE)
        result = gate.check_position_limit(0.20, 1000000.0)
        assert result.result == GateResult.BLOCK

    def test_check_all_five_gates(self, gate: RiskGate) -> None:
        results = gate.check_all(0.05, 0.05, 0.10, 0.30, 0.15)
        assert len(results) == 5

    def test_set_threshold_override(self, gate: RiskGate) -> None:
        gate.set_threshold("max_position_pct", 0.80)
        result = gate.check_position_limit(0.40, 1000000.0)
        assert result.result == GateResult.PASS

    def test_volatility_check(self, gate: RiskGate) -> None:
        result = gate.check_volatility(0.10)
        assert result.result == GateResult.PASS

    def test_correlation_check(self, gate: RiskGate) -> None:
        result = gate.check_correlation(0.80)
        assert result.result == GateResult.BLOCK

    def test_concentration_check(self, gate: RiskGate) -> None:
        result = gate.check_concentration(0.10)
        assert result.result == GateResult.PASS

    def test_stats(self, gate: RiskGate) -> None:
        gate.check_position_limit(0.05, 1000000.0)
        s = gate.stats
        assert s["faction"] == "neutral"
        assert "thresholds" in s


class TestPortfolioManager:
    @pytest.fixture
    def pm(self) -> PortfolioManager:
        return PortfolioManager(initial_cash=1_000_000.0)

    def test_initial_state(self, pm: PortfolioManager) -> None:
        assert pm.state.total_value == 1_000_000.0
        assert pm.state.position_count == 0

    def test_update_position_new(self, pm: PortfolioManager) -> None:
        pos = pm.update_position("000001.SZ", 10000, 10.0, 10.5, sector="finance")
        assert pos.symbol == "000001.SZ"
        assert pos.quantity == 10000

    def test_update_position_existing(self, pm: PortfolioManager) -> None:
        pm.update_position("000001.SZ", 5000, 10.0, 10.0)
        pos = pm.update_position("000001.SZ", 3000, 10.5, 10.5)
        assert pos.quantity == 8000
        assert 10.18 < pos.avg_cost < 10.2  # Weighted average

    def test_close_position(self, pm: PortfolioManager) -> None:
        pm.update_position("000001.SZ", 10000, 10.0, 10.0)
        pos = pm.close_position("000001.SZ", 11.0)
        assert pos is not None
        assert pos.realized_pnl == 10000.0

    def test_generate_allocation_buy(self, pm: PortfolioManager) -> None:
        decision = pm.generate_allocation("000001.SZ", signal_strength=0.8, target_weight=0.10)
        assert decision.action in ("buy", "increase")

    def test_generate_allocation_hold(self, pm: PortfolioManager) -> None:
        pm.update_position("000001.SZ", 10000, 10.0, 10.0, sector="finance")
        pm._recalculate_state()
        weight = pm.state.positions["000001.SZ"].weight
        decision = pm.generate_allocation("000001.SZ", signal_strength=0.5, target_weight=weight)
        assert decision.action == "hold"

    def test_generate_allocation_sell(self, pm: PortfolioManager) -> None:
        decision = pm.generate_allocation("hold-co", signal_strength=0.0, target_weight=0.0)
        assert decision.action in ("sell", "hold")

    def test_blocked_by_risk_gate(self, pm: PortfolioManager) -> None:
        gate = RiskGate(faction=RiskFaction.CONSERVATIVE)
        decision = pm.generate_allocation("risky", signal_strength=0.9, target_weight=0.50, risk_gates=[gate])
        assert decision.action == "hold"  # Blocked by risk gate

    def test_aggregate_factions(self, pm: PortfolioManager) -> None:
        aggressive = {"A": 0.30, "B": 0.10}
        neutral = {"A": 0.15, "B": 0.15}
        conservative = {"A": 0.08, "B": 0.08}
        consensus = pm.aggregate_factions(aggressive, neutral, conservative)
        assert "A" in consensus
        assert consensus["A"] < 0.30  # Dampened by neutral/conservative

    def test_rebalance_generates_decisions(self, pm: PortfolioManager) -> None:
        pm.update_position("A.SH", 5000, 10.0, 12.0, sector="tech")
        pm.update_position("B.SZ", 3000, 20.0, 18.0, sector="finance")
        decisions = pm.rebalance({"A.SH": 0.60, "B.SZ": 0.40})
        assert len(decisions) == 2

    def test_position_pnl_calculation(self, pm: PortfolioManager) -> None:
        pm.update_position("000001.SZ", 1000, 10.0, 12.0)
        pos = pm.state.positions["000001.SZ"]
        assert pos.pnl_pct > 0.0
        assert pos.market_value == 12000.0

    def test_sector_weights(self, pm: PortfolioManager) -> None:
        pm.update_position("A.SH", 5000, 10.0, 10.0, sector="tech")
        pm.update_position("B.SZ", 5000, 20.0, 20.0, sector="finance")
        assert "tech" in pm.state.sector_weights
        assert "finance" in pm.state.sector_weights

    def test_max_positions_limit(self, pm: PortfolioManager) -> None:
        pm_few = PortfolioManager(max_positions=2)
        pm_few.update_position("A", 100, 10.0, 10.0)
        pm_few.update_position("B", 100, 10.0, 10.0)
        decision = pm_few.generate_allocation("C", 0.8, 0.10)
        assert decision.action == "hold"

    def test_stats(self, pm: PortfolioManager) -> None:
        pm.update_position("000001.SZ", 1000, 10.0, 10.5, sector="finance")
        s = pm.stats
        assert s["position_count"] == 1
        assert s["total_value"] > 0
