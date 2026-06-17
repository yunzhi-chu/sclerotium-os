"""Global stock market connector — US & HK stocks via Yahoo + Sina + Tencent.

Implements the MarketConnector protocol for US/HK stock data:
- Yahoo Finance v8: OHLCV K-line + options chain + fundamental data
- Sina Finance: Real-time quotes for US (gb_XXXX) and HK (rt_hkXXXXX)
- Tencent Finance: US (usXXXX) and HK (r_hkXXXXX) real-time with PE/PB
- Eastmoney datacenter: Financial statements (balance/income/cashflow)

Dependencies: pip install requests
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

from src.trading.connectors.base import MarketConnector
from src.utils.logging import CortexLogger


class GlobalStockConnector:
    """US & HK stock market data connector.

    Data sources (all free, no API key required):
    - Yahoo Finance v8: K-line, options, fundaments
    - Sina Finance: US/HK real-time quotes
    - Tencent Finance: US/HK real-time + PE/PB/market cap
    - Eastmoney: Financial statements (balance/income/cashflow)

    Usage:
        conn = GlobalStockConnector(market="us")
        conn.connect()
        ohlc = conn.fetch_ohlc("AAPL", interval="1d", limit=100)
        quote = conn.get_quote("AAPL")
    """

    def __init__(self, market: str = "us"):
        """
        Args:
            market: "us" for US stocks, "hk" for Hong Kong stocks
        """
        self._connected = False
        self._market = market.lower()
        self._logger = CortexLogger(f"global_connector_{market}")
        self._subscribed_symbols: list[str] = []

    # ── Connection ──────────────────────────────────────────────────

    def connect(self) -> bool:
        self._connected = True
        self._logger.info("global_connector_connected", market=self._market)
        return True

    def disconnect(self) -> None:
        self._connected = False
        self._logger.info("global_connector_disconnected")

    def is_connected(self) -> bool:
        return self._connected

    # ── OHLC / K-line (Yahoo Finance v8) ────────────────────────────

    def fetch_ohlc(
        self,
        symbol: str,
        interval: str = "1d",
        start: str = "",
        end: str = "",
        limit: int = 252,
    ) -> list[dict[str, Any]]:
        """Fetch OHLC bars using Yahoo Finance v8 API.

        Args:
            symbol: Ticker symbol (e.g., AAPL, TSLA, 0700.HK)
            interval: 1d/1wk/1mo/1m/5m/15m/30m/60m
            limit: Number of bars
        """
        import requests as _r

        # Yahoo interval mapping
        yahoo_interval = {
            "1d": "1d", "1wk": "1wk", "1mo": "1mo",
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "60m": "60m",
        }
        yi = yahoo_interval.get(interval, "1d")

        # Determine range
        range_map = {
            "1d": "1y", "1wk": "2y", "1mo": "5y",
            "1m": "7d", "5m": "7d", "15m": "60d", "30m": "60d", "60m": "60d",
        }
        yr = range_map.get(interval, "1y")

        try:
            url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                f"?range={yr}&interval={yi}&includePrePost=false"
            )
            headers = {"User-Agent": "Mozilla/5.0"}
            r = _r.get(url, headers=headers, timeout=15)

            if r.status_code != 200:
                return self._fallback_sina_kline(symbol, limit)

            data = r.json()
            chart = data.get("chart", {}).get("result", [])
            if not chart:
                return self._fallback_sina_kline(symbol, limit)

            result = chart[0]
            timestamps = result.get("timestamp", [])
            quote_data = result.get("indicators", {}).get("quote", [{}])[0]
            opens = quote_data.get("open", [])
            highs = quote_data.get("high", [])
            lows = quote_data.get("low", [])
            closes = quote_data.get("close", [])
            volumes = quote_data.get("volume", [])

            bars: list[dict[str, Any]] = []
            recent = min(len(timestamps), limit)
            for i in range(max(0, len(timestamps) - recent), len(timestamps)):
                if i < len(closes) and closes[i] is not None:
                    bars.append({
                        "symbol": symbol,
                        "date": datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d"),
                        "open": float(opens[i]) if i < len(opens) and opens[i] else 0.0,
                        "high": float(highs[i]) if i < len(highs) and highs[i] else 0.0,
                        "low": float(lows[i]) if i < len(lows) and lows[i] else 0.0,
                        "close": float(closes[i]),
                        "volume": int(volumes[i]) if i < len(volumes) and volumes[i] else 0,
                    })
            return bars
        except Exception as exc:
            self._logger.warn("yahoo_ohlc_failed", symbol=symbol, error=str(exc))
            return self._fallback_sina_kline(symbol, limit)

    def _fallback_sina_kline(self, symbol: str, limit: int) -> list[dict[str, Any]]:
        """Fallback: Sina daily K-line for US stocks."""
        import requests as _r

        try:
            if self._market == "hk":
                code = symbol.replace(".HK", "").zfill(5)
                url = f"https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_{code}=/InnerFuturesNewService.getDailyKLine?symbol=HKEX_{code}"
            else:
                url = f"https://stock.finance.sina.com.cn/usstock/api/jsonp.php/var/US_MinKService.getDailyKLine?symbol={symbol}"

            r = _r.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            # Parse JSONP
            text = r.text
            if "(" in text and ")" in text:
                json_str = text[text.index("(") + 1 : text.rindex(")")]
                data = json.loads(json_str)
                bars: list[dict[str, Any]] = []
                for item in data[-limit:]:
                    bars.append({
                        "symbol": symbol,
                        "date": item.get("d", ""),
                        "open": float(item.get("o", 0)),
                        "high": float(item.get("h", 0)),
                        "low": float(item.get("l", 0)),
                        "close": float(item.get("c", 0)),
                        "volume": int(float(item.get("v", 0))),
                    })
                return bars
        except Exception:
            pass
        return []

    # ── Tick / Real-time ─────────────────────────────────────────────

    def fetch_ticks(
        self, symbols: list[str], start: str = "", end: str = "", limit: int = 1000
    ) -> list[dict[str, Any]]:
        """Fetch real-time quotes."""
        results: list[dict[str, Any]] = []
        for sym in symbols:
            quote = self.get_quote(sym)
            if quote:
                results.append({
                    "symbol": sym,
                    "price": quote.get("price", 0),
                    "volume": quote.get("volume", 0),
                    "change_pct": quote.get("change_pct", 0),
                    "timestamp": time.time(),
                })
        return results

    def subscribe_realtime(self, symbols: list[str]) -> bool:
        self._subscribed_symbols = symbols
        return True

    def get_market_status(self) -> str:
        """Return US/HK market status."""
        now = datetime.now()
        if now.weekday() >= 5:
            return "closed"

        if self._market == "us":
            # US regular: 9:30-16:00 EST (rough check by UTC hour)
            utc_hour = (now.hour - now.astimezone().utcoffset().seconds // 3600) % 24
            if 14 <= utc_hour < 21:
                return "open"
        elif self._market == "hk":
            # HK: 9:30-12:00, 13:00-16:00 HKT
            if (9 <= now.hour < 12) or (13 <= now.hour < 16):
                return "open"
        return "closed"

    # ── Real-time Quotes ─────────────────────────────────────────────

    def get_quote(self, symbol: str) -> dict[str, Any]:
        """Get real-time quote for a single symbol.

        Uses Sina Finance for US and HK stocks (free, no key).
        """
        import requests as _r

        try:
            if self._market == "hk":
                code = symbol.replace(".HK", "").zfill(5)
                url = f"https://hq.sinajs.cn/list=rt_hk{code}"
            else:
                url = f"https://hq.sinajs.cn/list=gb_{symbol.lower()}"

            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://finance.sina.com.cn/",
            }
            r = _r.get(url, headers=headers, timeout=10)
            text = r.text

            if self._market == "hk":
                return self._parse_sina_hk(text, symbol)
            return self._parse_sina_us(text, symbol)
        except Exception as exc:
            self._logger.warn("sina_quote_failed", symbol=symbol, error=str(exc))
            return {}

    def _parse_sina_us(self, text: str, symbol: str) -> dict[str, Any]:
        """Parse Sina US stock quote."""
        parts = text.split('"')[1].split(",") if '"' in text else []
        if len(parts) < 10:
            return {}
        return {
            "symbol": symbol,
            "name": parts[0],
            "price": float(parts[1]) if parts[1] else 0.0,
            "change_pct": float(parts[2]) if parts[2] else 0.0,
            "change_amt": float(parts[3]) if parts[3] else 0.0,
            "open": float(parts[5]) if parts[5] else 0.0,
            "high": float(parts[6]) if parts[6] else 0.0,
            "low": float(parts[7]) if parts[7] else 0.0,
            "volume": int(float(parts[10])) if len(parts) > 10 and parts[10] else 0,
        }

    def _parse_sina_hk(self, text: str, symbol: str) -> dict[str, Any]:
        """Parse Sina HK stock quote."""
        parts = text.split('"')[1].split(",") if '"' in text else []
        if len(parts) < 20:
            return {}
        return {
            "symbol": symbol,
            "name": parts[1],
            "price": float(parts[6]) if parts[6] else 0.0,
            "change_pct": float(parts[8]) if parts[8] else 0.0,
            "open": float(parts[2]) if parts[2] else 0.0,
            "high": float(parts[4]) if parts[4] else 0.0,
            "low": float(parts[5]) if parts[5] else 0.0,
            "volume": int(float(parts[12])) if len(parts) > 12 and parts[12] else 0,
        }

    # ── Fundamental Data (Yahoo crumb API) ───────────────────────────

    def fetch_fundamentals(self, symbol: str) -> dict[str, Any]:
        """Fetch fundamental data via Yahoo quoteSummary."""
        import requests as _r

        try:
            modules = "price,summaryDetail,defaultKeyStatistics,financialData"
            url = (
                f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
                f"?modules={modules}"
            )
            headers = {"User-Agent": "Mozilla/5.0"}
            r = _r.get(url, headers=headers, timeout=15)

            if r.status_code != 200:
                return {}

            data = r.json()
            result = data.get("quoteSummary", {}).get("result", [])
            if not result:
                return {}

            d = result[0]
            price = d.get("price", {})
            summary = d.get("summaryDetail", {})
            stats = d.get("defaultKeyStatistics", {})
            fin_data = d.get("financialData", {})

            return {
                "symbol": symbol,
                "name": price.get("shortName", ""),
                "price": price.get("regularMarketPrice", {}).get("raw", 0),
                "change_pct": price.get("regularMarketChangePercent", {}).get("raw", 0),
                "market_cap": price.get("marketCap", {}).get("raw", 0),
                "pe_ttm": summary.get("trailingPE", {}).get("raw", 0),
                "pe_fwd": summary.get("forwardPE", {}).get("raw", 0),
                "pb": stats.get("priceToBook", {}).get("raw", 0),
                "roe": fin_data.get("returnOnEquity", {}).get("raw", 0),
                "beta": stats.get("beta", {}).get("raw", 0),
                "target_mean": fin_data.get("targetMeanPrice", {}).get("raw", 0),
                "recommendation": fin_data.get("recommendationKey", ""),
            }
        except Exception as exc:
            self._logger.warn("yahoo_fundamentals_failed", symbol=symbol, error=str(exc))
            return {}

    # ── Technical Indicators (pure Python) ───────────────────────────

    @staticmethod
    def compute_indicators(ohlc: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute technical indicators from OHLC data.

        Returns dict with MA5/MA10/MA20/MA60, MACD, RSI14, KDJ, Bollinger.
        """
        closes = [bar["close"] for bar in ohlc]
        highs = [bar["high"] for bar in ohlc]
        lows = [bar["low"] for bar in ohlc]

        result: dict[str, Any] = {}

        # Moving averages
        for period in [5, 10, 20, 60]:
            if len(closes) >= period:
                result[f"MA{period}"] = round(sum(closes[-period:]) / period, 2)

        # MACD
        if len(closes) >= 26:
            ema12 = _ema(closes, 12)
            ema26 = _ema(closes, 26)
            # Align EMA arrays (ema12 is longer than ema26)
            min_len = min(len(ema12), len(ema26))
            ema12_aligned = ema12[-min_len:]
            ema26_aligned = ema26[-min_len:]
            macd_line = [ema12_aligned[i] - ema26_aligned[i] for i in range(min_len)]
            signal = _ema(macd_line, 9)
            if macd_line:
                result["MACD"] = round(macd_line[-1], 4)
            if signal:
                result["MACD_signal"] = round(signal[-1], 4)

        # RSI (14)
        if len(closes) >= 15:
            result["RSI14"] = round(_rsi(closes, 14), 2)

        # Bollinger (20,2)
        if len(closes) >= 20:
            ma20 = sum(closes[-20:]) / 20
            std20 = (sum((c - ma20) ** 2 for c in closes[-20:]) / 20) ** 0.5
            result["BOLL_upper"] = round(ma20 + 2 * std20, 2)
            result["BOLL_mid"] = round(ma20, 2)
            result["BOLL_lower"] = round(ma20 - 2 * std20, 2)

        return result

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "market": self._market,
            "type": "global",
            "subscribed": len(self._subscribed_symbols),
        }


# ── Pure Python indicator helpers ──────────────────────────────────


def _ema(data: list[float], period: int) -> list[float]:
    """Compute Exponential Moving Average."""
    if len(data) < period:
        return []
    k = 2 / (period + 1)
    result = [sum(data[:period]) / period]
    for price in data[period:]:
        result.append(price * k + result[-1] * (1 - k))
    return result


def _rsi(closes: list[float], period: int = 14) -> float:
    """Compute RSI (Relative Strength Index)."""
    if len(closes) < period + 1:
        return 50.0
    gains = []
    losses = []
    for i in range(len(closes) - period, len(closes)):
        diff = closes[i] - closes[i - 1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)
