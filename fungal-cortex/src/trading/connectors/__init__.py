"""Market data connectors for Fungal Cortex v2.0.

Each connector implements the MarketConnector protocol and provides
real-time or historical data for a specific market.

Supported connectors:
- AStockConnector: A-share data via mootdx + Tencent + akshare
- GlobalStockConnector: US/HK stocks via Yahoo + Sina + Tencent
- CSVConnector: Local CSV file data source
"""

from __future__ import annotations

from src.trading.connectors.base import MarketConnector
from src.trading.connectors.astock_connector import AStockConnector
from src.trading.connectors.csv_connector import CSVConnector
from src.trading.connectors.global_connector import GlobalStockConnector

__all__ = [
    "MarketConnector",
    "AStockConnector",
    "CSVConnector",
    "GlobalStockConnector",
]
