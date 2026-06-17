"""CSV-based market data connector for local file data sources.

Reads OHLCV data from CSV files organized as:
    data/market/{symbol}.csv or data/market/{symbol}/{interval}.csv

CSV columns: date, open, high, low, close, volume, [amount]
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from src.trading.connectors.base import MarketConnector
from src.utils.logging import CortexLogger


class CSVConnector:
    """Market data connector that reads from local CSV files.

    Implements the MarketConnector protocol for backtesting and
    offline analysis with historical data files.
    """

    def __init__(self, data_dir: str | None = None):
        self._data_dir = Path(data_dir) if data_dir else Path("data/market")
        self._connected = False
        self._cache: dict[str, list[dict[str, Any]]] = {}
        self._logger = CortexLogger("csv_connector")

    def connect(self) -> bool:
        """Verify data directory exists and is readable."""
        if not self._data_dir.exists():
            self._logger.warn("data_dir_missing", path=str(self._data_dir))
            return False
        self._connected = True
        self._logger.info("connector_connected", path=str(self._data_dir))
        return True

    def disconnect(self) -> None:
        self._connected = False
        self._cache.clear()

    def is_connected(self) -> bool:
        return self._connected

    def fetch_ticks(
        self, symbols: list[str], start: str = "", end: str = "", limit: int = 1000
    ) -> list[dict[str, Any]]:
        """Read tick-level data from CSV."""
        results: list[dict[str, Any]] = []
        for symbol in symbols:
            ohlc = self._read_csv(symbol, "1d")
            for row in ohlc[:limit]:
                results.append({
                    "symbol": symbol,
                    "price": row.get("close", 0),
                    "volume": row.get("volume", 0),
                    "timestamp": row.get("date", ""),
                })
        return results[-limit:]

    def fetch_ohlc(
        self,
        symbol: str,
        interval: str = "1d",
        start: str = "",
        end: str = "",
        limit: int = 252,
    ) -> list[dict[str, Any]]:
        """Read OHLC bars from CSV."""
        rows = self._read_csv(symbol, interval)
        if end:
            rows = [r for r in rows if r.get("date", "") <= end]
        if start:
            rows = [r for r in rows if r.get("date", "") >= start]
        # Add symbol to each row
        for row in rows:
            row["symbol"] = symbol
        return rows[-limit:]

    def subscribe_realtime(self, symbols: list[str]) -> bool:
        """CSV connector doesn't support real-time — returns False."""
        self._logger.info("realtime_unsupported", symbols=symbols)
        return False

    def get_market_status(self) -> str:
        """CSV data has no market status — always returns 'closed'."""
        return "closed"

    def _read_csv(self, symbol: str, interval: str) -> list[dict[str, Any]]:
        """Read a CSV file for a symbol and interval."""
        cache_key = f"{symbol}_{interval}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try multiple path patterns
        paths = [
            self._data_dir / f"{symbol}.csv",
            self._data_dir / symbol / f"{interval}.csv",
            self._data_dir / f"{symbol}_{interval}.csv",
        ]

        for path in paths:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        rows = []
                        for row in reader:
                            row = {k.strip().lower(): v.strip() for k, v in row.items()}
                            # Convert numeric fields
                            for col in ("open", "high", "low", "close", "volume", "amount"):
                                if col in row:
                                    try:
                                        row[col] = float(row[col])
                                    except (ValueError, TypeError):
                                        pass
                            rows.append(row)
                        self._cache[cache_key] = rows
                        self._logger.info("csv_loaded", symbol=symbol, path=str(path), rows=len(rows))
                        return rows
                except Exception as e:
                    self._logger.error("csv_read_error", path=str(path), error=str(e))

        self._logger.warn("csv_not_found", symbol=symbol, interval=interval)
        return []

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "csv_files": len(self._cache),
            "total_bars": sum(len(v) for v in self._cache.values()),
            "connected": self._connected,
            "data_dir": str(self._data_dir),
        }
