"""A-Share market data connector — wraps mootdx + Tencent API + akshare.

Implements the MarketConnector protocol for real A-stock data ingestion:
- mootdx TCP: K-line + 5-level order book + tick-by-tick trades
- Tencent HTTP: PE/PB/market cap/turnover/limit prices
- akshare: news/research reports/announcements/industry comparison

Dependencies: pip install mootdx akshare requests
"""

from __future__ import annotations

import time
import urllib.request
from datetime import datetime
from typing import Any

from src.trading.connectors.base import MarketConnector
from src.utils.logging import CortexLogger


def _get_prefix(code: str) -> str:
    """6-digit code → market prefix (sh/sz/bj)."""
    if code.startswith(("6", "9")):
        return "sh"
    elif code.startswith("8"):
        return "bj"
    return "sz"


def _normalize_code(code: str) -> str:
    """Normalize various ticket formats to pure 6-digit code."""
    code = code.upper().strip()
    for prefix in ("SH", "SZ", "BJ"):
        if code.startswith(prefix):
            code = code[2:]
    if "." in code:
        code = code.split(".")[0]
    return code


class AStockConnector:
    """A-share market data connector for real-time China stock data.

    Data sources (all free, no API key required):
    - mootdx: K-line + quotes + tick data (TCP, port 7709)
    - Tencent Finance: PE/PB/market cap/turnover/limit up-down
    - akshare: News, research reports, announcements
    - THS: Hot stocks + reason tags + northbound flows
    - Baidu PAE: Concept block attribution + fund flows
    - Eastmoney: Dragon tiger board + lockup expiry + industry

    Usage:
        connector = AStockConnector()
        connector.connect()
        ticks = connector.fetch_ticks(["000001", "688017"])
        ohlc = connector.fetch_ohlc("000001", interval="1d", limit=100)
        quotes = connector.get_tencent_quotes(["000001", "688017"])
    """

    # Available A-share index/ETF symbols for reference
    BENCHMARKS = {
        "000001.SH": "上证指数",
        "399001.SZ": "深证成指",
        "399006.SZ": "创业板指",
        "000688.SH": "科创50",
        "000300.SH": "沪深300",
    }

    def __init__(self, data_dir: str = "data/market/cn"):
        self._connected = False
        self._data_dir = data_dir
        self._logger = CortexLogger("astock_connector")
        self._mootdx_client = None
        self._subscribed_symbols: list[str] = []

    # ── Connection ──────────────────────────────────────────────────

    def connect(self) -> bool:
        """Establish connection to data sources (lazy, on first use)."""
        self._connected = True
        self._logger.info("astock_connector_connected", message="A-stock data sources ready")
        return True

    def disconnect(self) -> None:
        """Close all connections."""
        self._connected = False
        self._mootdx_client = None
        self._logger.info("astock_connector_disconnected")

    def is_connected(self) -> bool:
        return self._connected

    # ── mootdx TCP client (lazy init) ───────────────────────────────

    def _get_mootdx(self):
        """Lazy-init mootdx Quotes client."""
        if self._mootdx_client is None:
            try:
                from mootdx.quotes import Quotes
                self._mootdx_client = Quotes.factory(market="std")
            except ImportError:
                self._logger.warn("mootdx_not_installed", message="pip install mootdx for real-time A-stock data")
                return None
            except Exception as exc:
                self._logger.error("mootdx_connect_failed", error=str(exc))
                return None
        return self._mootdx_client

    # ── OHLC / K-line ───────────────────────────────────────────────

    def fetch_ohlc(
        self,
        symbol: str,
        interval: str = "1d",
        start: str = "",
        end: str = "",
        limit: int = 252,
    ) -> list[dict[str, Any]]:
        """Fetch OHLC bars using mootdx K-line data.

        Args:
            symbol: 6-digit A-stock code
            interval: 1d/1w/1M/1m/5m/15m/30m/60m
            limit: Number of bars to return
        """
        code = _normalize_code(symbol)
        client = self._get_mootdx()
        if client is None:
            return self._fallback_tencent_kline(code, interval, limit)

        # mootdx category: 4=daily, 5=weekly, 6=monthly, 7=1min, 8=5min, 9=15min, 10=30min, 11=60min
        category_map = {
            "1d": 4, "1w": 5, "1M": 6,
            "1m": 7, "5m": 8, "15m": 9, "30m": 10, "60m": 11,
        }
        category = category_map.get(interval, 4)
        market = 1 if code.startswith(("6", "9")) else 0

        try:
            bars = client.bars(symbol=code, category=category, offset=limit)
            results: list[dict[str, Any]] = []
            for bar in bars:
                results.append({
                    "symbol": symbol,
                    "date": str(bar.get("datetime", "")),
                    "open": float(bar.get("open", 0)),
                    "high": float(bar.get("high", 0)),
                    "low": float(bar.get("low", 0)),
                    "close": float(bar.get("close", 0)),
                    "volume": int(bar.get("vol", 0) or bar.get("volume", 0)),
                    "amount": float(bar.get("amount", 0)),
                })
            return results
        except Exception as exc:
            self._logger.warn("mootdx_ohlc_failed", symbol=code, error=str(exc))
            return self._fallback_tencent_kline(code, interval, limit)

    def _fallback_tencent_kline(
        self, code: str, interval: str, limit: int
    ) -> list[dict[str, Any]]:
        """Fallback: build minimal OHLC from Tencent real-time quote."""
        quotes = self.get_tencent_quotes([code])
        if code not in quotes:
            return []
        q = quotes[code]
        return [{
            "symbol": code,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "open": q.get("open", q["price"]),
            "high": q.get("high", q["price"]),
            "low": q.get("low", q["price"]),
            "close": q["price"],
            "volume": 0,
        }]

    # ── Tick / Real-time ─────────────────────────────────────────────

    def fetch_ticks(
        self, symbols: list[str], start: str = "", end: str = "", limit: int = 1000
    ) -> list[dict[str, Any]]:
        """Fetch real-time quotes for given symbols (via Tencent API)."""
        quotes = self.get_tencent_quotes(symbols)
        results: list[dict[str, Any]] = []
        for sym in symbols:
            code = _normalize_code(sym)
            if code in quotes:
                q = quotes[code]
                results.append({
                    "symbol": sym,
                    "price": q["price"],
                    "volume": int(q.get("volume", 0)),
                    "change_pct": q.get("change_pct", 0),
                    "timestamp": time.time(),
                    "bid": q.get("price", 0),
                    "ask": q.get("price", 0),
                })
        return results

    def subscribe_realtime(self, symbols: list[str]) -> bool:
        """Mark symbols for real-time subscription."""
        self._subscribed_symbols = [_normalize_code(s) for s in symbols]
        return True

    def get_market_status(self) -> str:
        """Return current A-share market status based on time/day.

        A-share trading hours (CST, UTC+8):
        - Morning: 09:30–11:30
        - Afternoon: 13:00–15:00
        """
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        # Weekday check
        if now.weekday() >= 5:
            return "closed"
        # Pre-open
        if hour == 9 and minute < 30:
            return "pre_open"
        # Morning session
        if hour == 9 or hour == 10 or (hour == 11 and minute <= 30):
            return "open"
        # Lunch break
        if hour == 11 or (hour == 12 and minute < 60):
            return "closed"
        # Afternoon session
        if hour == 13 or hour == 14:
            return "open"
        # After close but still on trading day
        if hour >= 15:
            return "closed"
        return "closed"

    # ── Tencent Finance API (PE/PB/Market Cap) ──────────────────────

    def get_tencent_quotes(self, codes: list[str]) -> dict[str, dict[str, Any]]:
        """Batch fetch Tencent Finance real-time quotes.

        Returns dict[normalized_code, {name, price, pe_ttm, pb, mcap_yi, ...}]
        """
        codes = [_normalize_code(c) for c in codes]
        prefixed = []
        for c in codes:
            prefixed.append(f"{_get_prefix(c)}{c}")

        url = "https://qt.gtimg.cn/q=" + ",".join(prefixed)
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0")
            resp = urllib.request.urlopen(req, timeout=10)
            data = resp.read().decode("gbk")
        except Exception as exc:
            self._logger.warn("tencent_api_failed", error=str(exc))
            return {}

        result: dict[str, dict[str, Any]] = {}
        for line in data.strip().split(";"):
            if not line.strip() or "=" not in line or '"' not in line:
                continue
            key = line.split("=")[0].split("_")[-1]
            vals = line.split('"')[1].split("~")
            if len(vals) < 53:
                continue
            code = key[2:]
            result[code] = {
                "name": vals[1],
                "price": float(vals[3]) if vals[3] else 0.0,
                "last_close": float(vals[4]) if vals[4] else 0.0,
                "open": float(vals[5]) if vals[5] else 0.0,
                "change_amt": float(vals[31]) if vals[31] else 0.0,
                "change_pct": float(vals[32]) if vals[32] else 0.0,
                "high": float(vals[33]) if vals[33] else 0.0,
                "low": float(vals[34]) if vals[34] else 0.0,
                "amount_wan": float(vals[37]) if vals[37] else 0.0,
                "turnover_pct": float(vals[38]) if vals[38] else 0.0,
                "pe_ttm": float(vals[39]) if vals[39] else 0.0,
                "amplitude_pct": float(vals[43]) if vals[43] else 0.0,
                "mcap_yi": float(vals[44]) if vals[44] else 0.0,
                "float_mcap_yi": float(vals[45]) if vals[45] else 0.0,
                "pb": float(vals[46]) if vals[46] else 0.0,
                "limit_up": float(vals[47]) if vals[47] else 0.0,
                "limit_down": float(vals[48]) if vals[48] else 0.0,
                "vol_ratio": float(vals[49]) if vals[49] else 0.0,
                "pe_static": float(vals[52]) if vals[52] else 0.0,
            }
        return result

    # ── Research Reports (Eastmoney) ─────────────────────────────────

    def fetch_research_reports(self, code: str, max_pages: int = 3) -> list[dict[str, Any]]:
        """Fetch research reports from Eastmoney report API."""
        import requests as _r

        code = _normalize_code(code)
        session = _r.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://data.eastmoney.com/",
        })

        reports: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            try:
                params = {
                    "industryCode": "*", "pageSize": "50", "industry": "*",
                    "rating": "*", "ratingChange": "*",
                    "beginTime": "2000-01-01", "endTime": "2030-01-01",
                    "pageNo": str(page), "fields": "", "qType": "0",
                    "orgCode": "", "code": code, "rcode": "",
                    "p": str(page), "pageNum": str(page), "pageNumber": str(page),
                }
                r = session.get(
                    "https://reportapi.eastmoney.com/report/list",
                    params=params, timeout=30,
                )
                d = r.json()
                rows = d.get("data") or []
                if not rows:
                    break
                for row in rows:
                    reports.append({
                        "title": row.get("title", ""),
                        "org": row.get("orgSName", ""),
                        "date": (row.get("publishDate") or "")[:10],
                        "rating": row.get("emRatingName", ""),
                        "eps_cur": row.get("predictThisYearEps", 0),
                        "eps_next": row.get("predictNextYearEps", 0),
                        "industry": row.get("indvInduName", ""),
                    })
                time.sleep(0.3)
            except Exception as exc:
                self._logger.warn("eastmoney_reports_failed", code=code, error=str(exc))
                break
        return reports

    # ── News (akshare) ───────────────────────────────────────────────

    def fetch_news(self, code: str) -> list[dict[str, Any]]:
        """Fetch stock-specific news via akshare."""
        try:
            import akshare as ak
            df = ak.stock_news_em(symbol=code)
            news: list[dict[str, Any]] = []
            for _, row in df.head(20).iterrows():
                news.append({
                    "title": row.get("新闻标题", ""),
                    "content": str(row.get("新闻内容", ""))[:500],
                    "time": str(row.get("发布时间", "")),
                    "source": row.get("文章来源", ""),
                })
            return news
        except ImportError:
            return []
        except Exception as exc:
            self._logger.warn("akshare_news_failed", code=code, error=str(exc))
            return []

    # ── Industry Comparison ──────────────────────────────────────────

    def fetch_industry_comparison(self, top_n: int = 20) -> dict[str, Any]:
        """Fetch THS industry sector ranking."""
        try:
            import akshare as ak
            df = ak.stock_board_industry_summary_ths()
            if df.empty:
                return {"top": [], "bottom": [], "total": 0}

            rows: list[dict[str, Any]] = []
            for i, row in df.iterrows():
                rows.append({
                    "rank": i + 1,
                    "name": row.get("板块", ""),
                    "change_pct": float(row.get("涨跌幅", 0)),
                    "turnover_yi": float(row.get("总成交额", 0)),
                    "up_count": int(row.get("上涨家数", 0)),
                    "down_count": int(row.get("下跌家数", 0)),
                    "leader": row.get("领涨股", ""),
                })
            return {
                "top": rows[:top_n],
                "bottom": rows[-top_n:] if len(rows) > top_n else [],
                "total": len(rows),
            }
        except ImportError:
            return {"top": [], "bottom": [], "total": 0}
        except Exception as exc:
            self._logger.warn("industry_comparison_failed", error=str(exc))
            return {"top": [], "bottom": [], "total": 0}

    # ── Concept Blocks (Baidu PAE) ───────────────────────────────────

    def fetch_concept_blocks(self, code: str) -> dict[str, Any]:
        """Fetch concept/industry/region attribution via Baidu PAE."""
        import requests as _r

        code = _normalize_code(code)
        try:
            url = (
                f"https://finance.pae.baidu.com/api/getrelatedblock"
                f"?code={code}&market=ab&typeCode=all&finClientType=pc"
            )
            headers = {
                "Host": "finance.pae.baidu.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0.0.0",
                "Accept": "application/vnd.finance-web.v1+json",
                "Origin": "https://gushitong.baidu.com",
                "Referer": "https://gushitong.baidu.com/",
            }
            r = _r.get(url, headers=headers, timeout=10)
            d = r.json()
            if str(d.get("ResultCode", -1)) != "0":
                return {"industry": [], "concept": [], "region": []}

            result: dict[str, Any] = {"industry": [], "concept": [], "region": []}
            for block in d.get("Result", []):
                block_type = block.get("type", "")
                for item in block.get("list", []):
                    entry = {
                        "name": item.get("name", ""),
                        "change_pct": item.get("increase", ""),
                        "desc": item.get("desc", ""),
                    }
                    if "行业" in block_type:
                        result["industry"].append(entry)
                    elif "概念" in block_type:
                        result["concept"].append(entry)
                    elif "地域" in block_type:
                        result["region"].append(entry)
            return result
        except Exception as exc:
            self._logger.warn("baidu_pae_failed", code=code, error=str(exc))
            return {"industry": [], "concept": [], "region": []}

    # ── Hot Stocks with Reason Tags (THS) ────────────────────────────

    def fetch_hot_stocks(self, date: str = "") -> list[dict[str, Any]]:
        """Fetch THS hot stocks with reason tags."""
        import requests as _r
        from datetime import date as _date

        if not date:
            date = _date.today().strftime("%Y-%m-%d")

        try:
            url = (
                f"http://zx.10jqka.com.cn/event/api/getharden/"
                f"date/{date}/orderby/date/orderway/desc/charset/GBK/"
            )
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/117.0.0.0 Safari/537.36"
            }
            r = _r.get(url, headers=headers, timeout=10)
            data = r.json()
            if data.get("errocode", 0) != 0:
                return []

            stocks: list[dict[str, Any]] = []
            for row in data.get("data") or []:
                stocks.append({
                    "code": row.get("code", ""),
                    "name": row.get("name", ""),
                    "reason": row.get("reason", ""),
                    "close": float(row.get("close", 0)),
                    "change_pct": float(row.get("zhangfu", 0)),
                    "turnover_pct": float(row.get("huanshou", 0)),
                    "amount": float(row.get("chengjiaoe", 0)),
                })
            return stocks
        except Exception as exc:
            self._logger.warn("ths_hot_stocks_failed", error=str(exc))
            return []

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "type": "astock",
            "subscribed": len(self._subscribed_symbols),
        }
