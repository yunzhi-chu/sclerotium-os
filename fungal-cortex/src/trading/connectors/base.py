"""Abstract MarketConnector protocol for Fungal Cortex data sources."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MarketConnector(Protocol):
    """Protocol for market data source connectors.

    Implementations provide tick data, OHLC bars, and market status
    for a specific market (A-shares, HK, US, etc.).
    """

    def connect(self) -> bool:
        """Establish connection to the data source."""
        ...

    def disconnect(self) -> None:
        """Close connection to the data source."""
        ...

    def is_connected(self) -> bool:
        """Return whether the connector is currently connected."""
        ...

    def fetch_ticks(
        self, symbols: list[str], start: str = "", end: str = "", limit: int = 1000
    ) -> list[dict[str, Any]]:
        """Fetch historical tick data for given symbols."""
        ...

    def fetch_ohlc(
        self,
        symbol: str,
        interval: str = "1d",
        start: str = "",
        end: str = "",
        limit: int = 252,
    ) -> list[dict[str, Any]]:
        """Fetch OHLC bars for a symbol."""
        ...

    def subscribe_realtime(self, symbols: list[str]) -> bool:
        """Subscribe to real-time data for given symbols."""
        ...

    def get_market_status(self) -> str:
        """Return the current market status (open/closed/pre_market/after_hours)."""
        ...
