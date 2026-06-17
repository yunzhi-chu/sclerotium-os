/** Market Data — multi-market quotes, charts, news, sentiment. */
"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkline } from "@/components/charts/sparkline";
import { useMarketStore } from "@/stores/market-store";
import type { MarketQuote, NewsItem } from "@/stores/market-store";
import { useWebSocket } from "@/hooks/use-websocket";
import { api } from "@/lib/api-client";

type Market = "CN" | "HK" | "US";

const MARKETS: { key: Market; label: string; color: string }[] = [
  { key: "CN", label: "A-Share", color: "#ff4444" },
  { key: "HK", label: "HK", color: "#ffaa44" },
  { key: "US", label: "US", color: "#4488ff" },
];

// Fallback chart data for initial render
const FALLBACK_CHART = Array.from({ length: 60 }, (_, i) => 12.5 + Math.sin(i / 5) * 1.5 + i * 0.02);

export default function MarketPage() {
  const [activeMarket, setActiveMarket] = useState<Market | null>(null);

  const {
    quotes, news, sentiment, chartData,
    setQuotes, setNews, setSentiment, setChartData, setTicks,
  } = useMarketStore();

  // Fetch initial data
  useEffect(() => {
    api.getHealth().catch(() => {});
  }, []);

  // Subscribe to market WebSocket
  useWebSocket("market", "market", (data: unknown) => {
    const d = data as Record<string, unknown>;
    if (d.quotes && Array.isArray(d.quotes)) {
      setQuotes(d.quotes as MarketQuote[]);
    }
    if (d.news && Array.isArray(d.news)) {
      setNews(d.news as NewsItem[]);
    }
    if (d.sentiment !== undefined) {
      setSentiment(d.sentiment as number);
    }
    if (d.chart_data && Array.isArray(d.chart_data)) {
      setChartData(d.chart_data as number[]);
    }
    if (d.ticks && Array.isArray(d.ticks)) {
      setTicks(d.ticks as import("@/types/trading").MarketTick[]);
    }
  });

  const filtered = activeMarket
    ? quotes.filter((q) => q.market === activeMarket)
    : quotes;

  const displayChart = chartData.length > 0 ? chartData : FALLBACK_CHART;
  const displaySentiment = sentiment > 0 ? sentiment : 0.72;

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-bold font-mono text-cortex-primary">Market Data</h1>
        <div className="flex gap-1">
          <button className="px-3 py-1 text-xs rounded bg-cortex-border/30 text-gray-400"
            onClick={() => setActiveMarket(null)}>All</button>
          {MARKETS.map((m) => (
            <button key={m.key} className={`px-3 py-1 text-xs rounded ${activeMarket === m.key ? "text-white" : "text-gray-500"}`}
              style={{ backgroundColor: activeMarket === m.key ? m.color + "30" : "", border: activeMarket === m.key ? `1px solid ${m.color}` : "1px solid transparent" }}
              onClick={() => setActiveMarket(activeMarket === m.key ? null : m.key)}>
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Quote board */}
        <div className="col-span-2">
          <Card header="Quotes">
            {quotes.length === 0 ? (
              <div className="text-xs text-gray-500 p-4">No market data available. Waiting for WebSocket connection...</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-gray-500 border-b border-cortex-border">
                      <th className="text-left p-2 font-normal">Symbol</th>
                      <th className="text-left p-2 font-normal">Name</th>
                      <th className="text-right p-2 font-normal">Price</th>
                      <th className="text-right p-2 font-normal">Change%</th>
                      <th className="text-right p-2 font-normal">Volume</th>
                      <th className="text-left p-2 font-normal">Mkt</th>
                      <th className="text-left p-2 font-normal">Chart</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((q) => (
                      <tr key={q.symbol} className="border-b border-cortex-border/30 hover:bg-cortex-border/20">
                        <td className="p-2 font-mono text-cortex-primary">{q.symbol}</td>
                        <td className="p-2 text-gray-300">{q.name}</td>
                        <td className="p-2 font-mono text-right">{q.price.toFixed(2)}</td>
                        <td className={`p-2 font-mono text-right ${q.change > 0 ? "text-green-400" : "text-red-400"}`}>
                          {q.change > 0 ? "+" : ""}{q.change.toFixed(2)}%
                        </td>
                        <td className="p-2 font-mono text-right text-gray-500">{q.volume}</td>
                        <td className="p-2"><Badge variant="info" size="sm">{MARKETS.find((m) => m.key === q.market)?.label}</Badge></td>
                        <td className="p-2">
                          <Sparkline data={Array.from({ length: 20 }, () => q.price + (Math.random() - 0.5) * 0.5)} width={60} height={16} color={q.change > 0 ? "#22c55e" : "#ef4444"} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        {/* News + Sentiment */}
        <div className="col-span-1 space-y-4">
          <Card header="News Feed">
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {news.length === 0 ? (
                <div className="text-xs text-gray-500 p-2">No news items. Waiting for data...</div>
              ) : (
                news.map((n, i) => (
                  <div key={i} className="p-2 rounded bg-cortex-border/20 text-xs">
                    <div className="text-gray-300 mb-1">{n.title}</div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500">{n.source} · {n.time}</span>
                      <Badge variant={n.sentiment > 0.3 ? "success" : n.sentiment < -0.3 ? "danger" : "warning"} size="sm">
                        {n.sentiment > 0 ? "Bullish" : "Bearish"} {(n.sentiment * 100).toFixed(0)}%
                      </Badge>
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>

          <Card header="Sentiment Gauge">
            <div className="text-center">
              <div className="text-3xl font-bold text-green-400">{(displaySentiment * 100).toFixed(0)}%</div>
              <div className="text-xs text-gray-500">Overall Market Sentiment</div>
              <div className="h-2 rounded-full bg-cortex-border overflow-hidden mt-2">
                <div className="h-full rounded-full bg-gradient-to-r from-red-500 via-amber-500 to-green-500" style={{ width: `${displaySentiment * 100}%` }} />
              </div>
              <div className="flex justify-between text-[9px] text-gray-600 mt-0.5">
                <span>Bearish</span><span>Neutral</span><span>Bullish</span>
              </div>
            </div>
          </Card>

          <Card header="Chart: 000001.SZ">
            <Sparkline data={displayChart} width={280} height={60} />
            <div className="flex justify-between text-[10px] text-gray-600 mt-1">
              <span>{displayChart.length > 0 ? displayChart[0].toFixed(2) : "—"}</span>
              <span className={displayChart.length > 1 && displayChart[displayChart.length - 1] >= displayChart[0] ? "text-green-400" : "text-red-400"}>
                {displayChart.length > 1
                  ? ((displayChart[displayChart.length - 1] - displayChart[0]) >= 0 ? "+" : "") + (displayChart[displayChart.length - 1] - displayChart[0]).toFixed(2)
                  : "—"}
              </span>
              <span>{displayChart.length > 0 ? displayChart[displayChart.length - 1].toFixed(2) : "—"}</span>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
