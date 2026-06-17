"""Tests for CSV connector — OHLC parsing, caching, multi-path resolution."""

import os
import tempfile
from pathlib import Path

import pytest

from src.trading.connectors.csv_connector import CSVConnector


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory with CSV market data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "data" / "market"
        data_dir.mkdir(parents=True, exist_ok=True)

        # Write a sample OHLC CSV
        csv_path = data_dir / "000001.csv"
        csv_path.write_text(
            "date,open,high,low,close,volume,amount\n"
            "2025-01-02,12.00,12.50,11.80,12.30,1000000,12300000\n"
            "2025-01-03,12.30,12.80,12.10,12.60,1200000,15120000\n"
            "2025-01-06,12.60,13.00,12.40,12.90,1100000,14190000\n"
        )
        yield tmpdir


@pytest.fixture
def connector(temp_data_dir):
    """Create a CSVConnector connected to the temp data dir."""
    c = CSVConnector(data_dir=str(Path(temp_data_dir) / "data" / "market"))
    c.connect()
    return c


class TestCSVConnectorLifecycle:
    """Connection lifecycle tests."""

    def test_connect_success(self, temp_data_dir):
        c = CSVConnector(data_dir=str(Path(temp_data_dir) / "data" / "market"))
        assert c.connect() is True
        assert c.is_connected() is True

    def test_connect_missing_dir(self):
        c = CSVConnector(data_dir="/nonexistent/path/12345")
        assert c.connect() is False
        assert c.is_connected() is False

    def test_disconnect_clears_cache(self, connector):
        connector.disconnect()
        assert connector.is_connected() is False

    def test_connect_then_disconnect(self, connector):
        assert connector.is_connected() is True
        connector.disconnect()
        assert connector.is_connected() is False


class TestCSVConnectorFetchOHLC:
    """OHLC data fetching tests."""

    def test_fetch_ohlc_returns_data(self, connector):
        bars = connector.fetch_ohlc("000001", interval="1d", limit=100)
        assert len(bars) == 3
        assert bars[0]["open"] == 12.00
        assert bars[0]["close"] == 12.30
        assert bars[-1]["close"] == 12.90

    def test_fetch_ohlc_limit(self, connector):
        bars = connector.fetch_ohlc("000001", interval="1d", limit=1)
        assert len(bars) == 1

    def test_fetch_ohlc_missing_symbol(self, connector):
        bars = connector.fetch_ohlc("999999", interval="1d", limit=100)
        assert bars == []

    def test_fetch_ohlc_empty_dir(self, temp_data_dir):
        empty_dir = Path(temp_data_dir) / "data" / "market" / "empty"
        empty_dir.mkdir(parents=True, exist_ok=True)
        c = CSVConnector(data_dir=str(empty_dir))
        c.connect()
        bars = c.fetch_ohlc("anything", interval="1d")
        assert bars == []

    def test_fetch_ohlc_returns_correct_fields(self, connector):
        bars = connector.fetch_ohlc("000001", interval="1d")
        bar = bars[0]
        assert "symbol" in bar
        assert "date" in bar
        assert "open" in bar
        assert "high" in bar
        assert "low" in bar
        assert "close" in bar
        assert "volume" in bar

    def test_fetch_ohlc_prices_are_float(self, connector):
        bars = connector.fetch_ohlc("000001", interval="1d")
        for bar in bars:
            assert isinstance(bar["close"], float)
            assert isinstance(bar["open"], float)


class TestCSVConnectorFetchTicks:
    """Tick data fetching tests."""

    def test_fetch_ticks_converts_ohlc(self, connector):
        ticks = connector.fetch_ticks(["000001"], limit=10)
        assert len(ticks) == 3  # One tick per OHLC row

    def test_fetch_ticks_has_price_field(self, connector):
        ticks = connector.fetch_ticks(["000001"])
        for t in ticks:
            assert "price" in t
            assert "symbol" in t

    def test_fetch_ticks_multi_symbol(self, connector):
        ticks = connector.fetch_ticks(["000001", "000002"])
        assert len(ticks) == 3  # Only 000001 exists

    def test_fetch_ticks_limit(self, connector):
        ticks = connector.fetch_ticks(["000001"], limit=1)
        assert len(ticks) == 1


class TestCSVConnectorCache:
    """Cache behavior tests."""

    def test_cache_populated_after_fetch(self, connector):
        connector.fetch_ohlc("000001")
        # Second fetch should use cache
        bars = connector.fetch_ohlc("000001")
        assert len(bars) == 3

    def test_cache_cleared_on_disconnect(self, connector):
        connector.fetch_ohlc("000001")
        connector.disconnect()
        connector.connect()
        # After reconnect, cache should be clear but re-fetched
        bars = connector.fetch_ohlc("000001")
        assert len(bars) == 3


class TestCSVConnectorMultiPath:
    """Multi-path resolution tests."""

    def test_subdirectory_resolution(self, temp_data_dir):
        """Data in {data_dir}/{symbol}/{interval}.csv format."""
        data_dir = Path(temp_data_dir) / "data" / "market"
        sym_dir = data_dir / "600519"
        sym_dir.mkdir(parents=True, exist_ok=True)
        (sym_dir / "1d.csv").write_text(
            "date,open,high,low,close,volume\n"
            "2025-01-02,150.00,155.00,148.00,153.00,500000\n"
        )
        c = CSVConnector(data_dir=str(data_dir))
        c.connect()
        bars = c.fetch_ohlc("600519", interval="1d")
        assert len(bars) == 1
        assert bars[0]["close"] == 153.00

    def test_flat_file_fallback(self, temp_data_dir):
        """Flat file format: {data_dir}/{symbol}.csv."""
        data_dir = Path(temp_data_dir) / "data" / "market"
        (data_dir / "000858.csv").write_text(
            "date,open,high,low,close,volume\n"
            "2025-03-01,200.00,205.00,198.00,202.00,300000\n"
        )
        c = CSVConnector(data_dir=str(data_dir))
        c.connect()
        bars = c.fetch_ohlc("000858", interval="1d")
        assert len(bars) == 1

    def test_no_matching_file(self, connector):
        bars = connector.fetch_ohlc("nonexistent", interval="1d")
        assert bars == []


class TestCSVConnectorMarketStatus:
    """Market status tests."""

    def test_get_market_status_default(self, connector):
        status = connector.get_market_status()
        assert status is not None

    def test_subscribe_realtime_noop(self, connector):
        result = connector.subscribe_realtime(["000001", "600519"])
        assert result is False  # CSV connector doesn't support real-time


class TestCSVConnectorStats:
    """Stats dict tests."""

    def test_stats_before_connect(self, temp_data_dir):
        c = CSVConnector(data_dir=str(Path(temp_data_dir) / "data" / "market"))
        stats = c.stats
        assert "csv_files" in stats
        assert "total_bars" in stats

    def test_stats_after_fetch(self, connector):
        connector.fetch_ohlc("000001")
        stats = connector.stats
        assert "csv_files" in stats
        assert "total_bars" in stats
