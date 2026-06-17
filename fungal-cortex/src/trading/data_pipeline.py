"""Data Pipeline — multi-market data ingestion (A-share / HK / US).

The data pipeline is L1 of the cognitive pipeline, handling:
- Multi-market data source abstraction (A-share, Hong Kong, US)
- Tick data buffering with ring buffer (cap at 10,000 events)
- OHLC aggregation (1min, 5min, 15min, 1hour, 1day)
- Data validation (price bounds, volume sanity, timestamp ordering)
- Market status tracking (open, closed, holiday, circuit_breaker)

Data sources are abstracted behind a common interface so AlphaEar skills
can consume any market through the same Stigmergy field API.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.utils.logging import CortexLogger


class Market(Enum):
    CN = "cn"  # A-share (Shanghai + Shenzhen)
    HK = "hk"  # Hong Kong
    US = "us"  # US markets


class MarketStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    PRE_OPEN = "pre_open"  # Auction period
    CIRCUIT_BREAKER = "circuit_breaker"
    HOLIDAY = "holiday"


@dataclass
class TickData:
    """A single market tick."""

    symbol: str
    market: Market
    price: float
    volume: int
    timestamp: float = field(default_factory=time.time)
    bid: float = 0.0
    ask: float = 0.0
    bid_size: int = 0
    ask_size: int = 0
    trade_type: str = ""  # buy, sell, cross

    def __post_init__(self) -> None:
        if self.price < 0:
            raise ValueError(f"Price must be non-negative, got {self.price}")
        if self.volume < 0:
            raise ValueError(f"Volume must be non-negative, got {self.volume}")


@dataclass
class OHLCBar:
    """OHLC bar for a given interval."""

    symbol: str
    interval: str  # "1m", "5m", "15m", "1h", "1d"
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: float
    complete: bool = True


class MarketDataSource:
    """Abstract data source for a specific market."""

    def __init__(self, market: Market, symbols: list[str] | None = None) -> None:
        self.market = market
        self._symbols = set(symbols or [])
        self._status = MarketStatus.CLOSED
        self._last_tick_time: float = 0.0
        self._tick_count = 0

    def add_symbol(self, symbol: str) -> None:
        self._symbols.add(symbol)

    def remove_symbol(self, symbol: str) -> None:
        self._symbols.discard(symbol)

    def set_status(self, status: MarketStatus) -> None:
        self._status = status

    @property
    def status(self) -> MarketStatus:
        return self._status

    @property
    def symbols(self) -> list[str]:
        return list(self._symbols)


class DataPipeline:
    """L1: Multi-market data ingestion and validation.

    Features:
    - Ring buffer for tick data (10,000 events cap)
    - OHLC aggregation for standard intervals
    - Price/volume validation (bounds checking)
    - Timestamp ordering enforcement
    - Market status awareness (don't process closed-market data)
    """

    INTERVALS = ["1m", "5m", "15m", "1h", "1d"]

    def __init__(self, tick_buffer_size: int = 10000) -> None:
        self._buffer_size = tick_buffer_size
        self._sources: dict[Market, MarketDataSource] = {
            m: MarketDataSource(market=m) for m in Market
        }
        self._tick_buffer: list[TickData] = []
        self._ohlc_bars: dict[str, list[OHLCBar]] = {}  # symbol_interval → bars
        self._logger = CortexLogger("data_pipeline")
        self._total_ticks = 0
        self._rejected_ticks = 0

    def register_source(self, market: Market, symbols: list[str]) -> MarketDataSource:
        """Register a market data source with symbols."""
        source = MarketDataSource(market=market, symbols=symbols)
        self._sources[market] = source
        self._logger.info("source_registered", market=market.value, symbols=len(symbols))
        return source

    def ingest_tick(self, tick: TickData) -> bool:
        """Ingest a single tick. Returns False if rejected."""
        source = self._sources.get(tick.market)
        if source is None or source.status != MarketStatus.OPEN:
            self._rejected_ticks += 1
            return False

        # Validate timestamp ordering
        if self._tick_buffer and tick.timestamp < self._tick_buffer[-1].timestamp:
            self._rejected_ticks += 1
            return False

        # Validate price bounds
        if tick.price <= 0 or (tick.price > 1e7):
            self._rejected_ticks += 1
            return False

        # Add to ring buffer
        self._tick_buffer.append(tick)
        self._total_ticks += 1
        source._tick_count += 1
        source._last_tick_time = tick.timestamp

        # Ring buffer eviction
        if len(self._tick_buffer) > self._buffer_size:
            self._tick_buffer = self._tick_buffer[-self._buffer_size // 2:]

        # Update OHLC for the tick's symbol
        self._update_ohlc(tick)

        return True

    def _update_ohlc(self, tick: TickData) -> None:
        """Update OHLC bars for all intervals using the new tick."""
        for interval in self.INTERVALS:
            key = f"{tick.symbol}_{interval}"
            bars = self._ohlc_bars.setdefault(key, [])

            interval_seconds = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "1d": 86400}
            bucket = int(tick.timestamp / interval_seconds[interval]) * interval_seconds[interval]

            if bars and bars[-1].timestamp == bucket and not bars[-1].complete:
                # Update existing bar
                bar = bars[-1]
                bar.high = max(bar.high, tick.price)
                bar.low = min(bar.low, tick.price)
                bar.close = tick.price
                bar.volume += tick.volume
            else:
                # New bar
                if bars and bars[-1].timestamp < bucket:
                    bars[-1].complete = True
                bars.append(OHLCBar(
                    symbol=tick.symbol,
                    interval=interval,
                    open=tick.price,
                    high=tick.price,
                    low=tick.price,
                    close=tick.price,
                    volume=tick.volume,
                    timestamp=bucket,
                    complete=False,
                ))

            # Cap OHLC bars per symbol-interval
            if len(bars) > 5000:
                self._ohlc_bars[key] = bars[-2500:]

    def get_ticks(self, symbol: str | None = None, limit: int = 100) -> list[TickData]:
        """Get recent ticks, optionally filtered by symbol."""
        filtered = [t for t in self._tick_buffer if symbol is None or t.symbol == symbol]
        return filtered[-limit:]

    def get_latest_ticks(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get latest ticks as dicts for WebSocket streaming."""
        ticks = list(self._tick_buffer)[-limit:]
        return [
            {"symbol": t.symbol, "price": t.price, "volume": t.volume, "timestamp": t.timestamp}
            for t in ticks
        ]

    def get_ohlc(self, symbol: str, interval: str = "1d", limit: int = 100) -> list[OHLCBar]:
        """Get OHLC bars for a symbol and interval."""
        key = f"{symbol}_{interval}"
        bars = self._ohlc_bars.get(key, [])
        return bars[-limit:]

    def get_market_status(self, market: Market) -> MarketStatus:
        """Get the current status of a market."""
        source = self._sources.get(market)
        return source.status if source else MarketStatus.CLOSED

    def set_market_status(self, market: Market, status: MarketStatus) -> None:
        """Update market status."""
        source = self._sources.get(market)
        if source:
            source.set_status(status)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "total_ticks": self._total_ticks,
            "rejected_ticks": self._rejected_ticks,
            "buffer_size": len(self._tick_buffer),
            "markets": {
                m.value: {
                    "status": s.status.value,
                    "symbols": len(s.symbols),
                    "ticks": s._tick_count,
                }
                for m, s in self._sources.items()
            },
            "tracked_ohlc_pairs": len(self._ohlc_bars),
        }

    # ── Connector Integration ─────────────────────────────────────────

    async def fetch_from_connector(
        self, connector: "AStockConnector | GlobalStockConnector", symbols: list[str]
    ) -> int:
        """Pull real-time data from a market connector into the pipeline.

        Args:
            connector: AStockConnector or GlobalStockConnector instance
            symbols: List of symbols to fetch
        Returns:
            Number of ticks ingested
        """
        from src.trading.connectors.astock_connector import AStockConnector
        from src.trading.connectors.global_connector import GlobalStockConnector

        ingested = 0

        if isinstance(connector, AStockConnector):
            market = Market.CN
            quotes = connector.get_tencent_quotes(symbols)
            for code, q in quotes.items():
                tick = TickData(
                    symbol=code,
                    market=market,
                    price=q["price"],
                    volume=0,
                    timestamp=time.time(),
                )
                if self.ingest_tick(tick):
                    ingested += 1

        elif isinstance(connector, GlobalStockConnector):
            if connector._market == "hk":
                market = Market.HK
            else:
                market = Market.US

            for sym in symbols:
                quote = connector.get_quote(sym)
                if quote and quote.get("price", 0) > 0:
                    tick = TickData(
                        symbol=sym,
                        market=market,
                        price=quote["price"],
                        volume=quote.get("volume", 0),
                        timestamp=time.time(),
                    )
                    if self.ingest_tick(tick):
                        ingested += 1

        return ingested

    async def poll_sources(self, connectors: dict[str, Any]) -> dict[str, int]:
        """Poll all registered connectors and ingest ticks.

        Args:
            connectors: dict with keys like "cn", "us", "hk" → connector instances
        Returns:
            dict of market → tick count ingested
        """
        results: dict[str, int] = {}
        for market_key, connector in connectors.items():
            if connector is not None and connector.is_connected():
                symbols = connector._subscribed_symbols
                if symbols:
                    count = await self.fetch_from_connector(connector, symbols)
                    results[market_key] = count
        return results
