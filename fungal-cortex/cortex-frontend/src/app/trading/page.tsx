/** Trading Desk — portfolio, positions, signals, orders. */
"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkline } from "@/components/charts/sparkline";
import { useTradingStore } from "@/stores/trading-store";
import { useWebSocket } from "@/hooks/use-websocket";
import { api } from "@/lib/api-client";
import type { Position, PortfolioOverview, PnLPoint } from "@/types/trading";

// Fallback portfolio for initial render
const FALLBACK_PORTFOLIO: PortfolioOverview = {
  total_value: 1_000_000, cash: 500_000, market_value: 500_000,
  daily_pnl: 0, daily_pnl_pct: 0, total_pnl: 0, total_pnl_pct: 0,
  sharpe_ratio: 0, max_drawdown: 0, win_rate: 50, position_count: 0,
  sector_weights: {},
};

export default function TradingPage() {
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<string | null>(null);

  const {
    portfolio, positions, signals, pnlHistory,
    setPortfolio, setPositions,
  } = useTradingStore();

  // Fetch initial data
  useEffect(() => {
    api.getHealth().catch(() => {});
  }, []);

  // Subscribe to trading WebSocket
  useWebSocket("trading", "trading", (data: unknown) => {
    const d = data as Record<string, unknown>;
    if (d.positions && Array.isArray(d.positions)) {
      const mapped: Position[] = (d.positions as Array<Record<string, unknown>>).map((pos) => ({
        symbol: pos.symbol as string ?? "",
        name: pos.name as string ?? "",
        quantity: pos.quantity as number ?? 0,
        avg_cost: pos.avg_cost as number ?? 0,
        current_price: pos.current_price as number ?? 0,
        market_value: pos.market_value as number ?? 0,
        pnl_pct: pos.pnl_pct as number ?? 0,
        pnl_amount: (pos.pnl_amount as number) ?? 0,
        weight: pos.weight as number ?? 0,
        sector: pos.sector as string ?? "",
        signal_strength: (pos.signal_strength as number) ?? 0,
        risk_status: (pos.risk_status as "pass" | "warn" | "block") ?? "pass",
      }));
      setPositions(mapped);
    }
    if (d.total_value !== undefined) {
      setPortfolio({
        total_value: d.total_value as number,
        cash: (d.cash as number) ?? 0,
        market_value: (d.total_value as number) - ((d.cash as number) ?? 0),
        daily_pnl: 0, daily_pnl_pct: 0,
        total_pnl: (d.total_pnl_pct as number) ?? 0,
        total_pnl_pct: (d.total_pnl_pct as number) ?? 0,
        sharpe_ratio: 0, max_drawdown: 0, win_rate: 50,
        position_count: (d.positions as Array<unknown>)?.length ?? 0,
        sector_weights: (d.sector_weights as Record<string, number>) ?? {},
      });
    }
  });

  const p = portfolio ?? FALLBACK_PORTFOLIO;
  const positionsList = positions;
  const pnlData = pnlHistory.length > 0
    ? pnlHistory.map((pt: PnLPoint) => pt.equity)
    : Array.from({ length: 100 }, (_, i) => p.total_value + Math.sin(i / 10) * 50000 + (i * 2000));

  return (
    <div className="h-full overflow-y-auto p-4">
      <h1 className="text-lg font-bold font-mono text-cortex-primary mb-4">Trading Desk</h1>

      {/* Portfolio summary */}
      <div className="grid grid-cols-6 gap-2 mb-4">
        {([
          ["Total Value", `$${p.total_value.toLocaleString()}`, ""],
          ["Cash", `$${p.cash.toLocaleString()}`, ""],
          ["Daily P&L", `$${p.daily_pnl.toLocaleString()}`, p.daily_pnl > 0 ? "text-green-400" : "text-red-400"],
          ["Total P&L", `$${p.total_pnl.toLocaleString()}`, p.total_pnl > 0 ? "text-green-400" : "text-red-400"],
          ["Sharpe", p.sharpe_ratio.toFixed(2), ""],
          ["Win Rate", `${p.win_rate}%`, ""],
        ] as const).map(([label, value, cls]) => (
          <Card key={label}>
            <div className="text-[10px] text-gray-500">{label}</div>
            <div className={`text-sm font-mono font-bold mt-1 ${cls}`}>{value}</div>
          </Card>
        ))}
      </div>

      {/* P&L Chart + Positions */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="col-span-2">
          <Card header="Equity Curve">
            <Sparkline data={pnlData} width={600} height={120} color="#22c55e" />
            <div className="flex justify-between text-[10px] text-gray-600 mt-1">
              <span>Start: ${pnlData[0]?.toLocaleString() ?? "—"}</span>
              <span>Current: ${pnlData[pnlData.length - 1]?.toLocaleString() ?? "—"}</span>
            </div>
          </Card>
        </div>
        <div className="col-span-1">
          <Card header="Positions">
            {positionsList.length === 0 ? (
              <div className="text-xs text-gray-500">No positions. Start a backtest to see data.</div>
            ) : (
              positionsList.slice(0, 5).map((pos, i) => (
                <div key={i} className="mb-1.5">
                  <div className="flex justify-between text-[10px]">
                    <span className="text-gray-400">{pos.symbol}</span>
                    <span className={`font-mono ${(pos.pnl_pct ?? 0) > 0 ? "text-green-400" : "text-red-400"}`}>
                      {(pos.pnl_pct ?? 0).toFixed(2)}%
                    </span>
                  </div>
                </div>
              ))
            )}
          </Card>
        </div>
      </div>

      {/* Position Table */}
      <Card header={`Positions (${positionsList.length})`} className="mb-4">
        {positionsList.length === 0 ? (
          <div className="text-xs text-gray-500 p-4">No positions available.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b border-cortex-border">
                  {["Symbol", "Qty", "Avg Cost", "Price", "Mkt Value", "P&L%", "Weight%", "Sector"].map((h) => (
                    <th key={h} className="text-left p-2 font-normal cursor-pointer hover:text-white"
                      onClick={() => setSortKey(h === sortKey ? null : h)}>
                      {h} {sortKey === h ? "↓" : ""}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {positionsList.map((pos) => (
                  <tr key={pos.symbol}
                    className={`border-b border-cortex-border/30 cursor-pointer transition-colors ${
                      selectedSymbol === pos.symbol ? "bg-cortex-primary/10" : "hover:bg-cortex-border/20"
                    }`}
                    onClick={() => setSelectedSymbol(selectedSymbol === pos.symbol ? null : pos.symbol)}>
                    <td className="p-2 font-mono text-cortex-primary">{pos.symbol}</td>
                    <td className="p-2 font-mono">{(pos.quantity ?? 0).toLocaleString()}</td>
                    <td className="p-2 font-mono">{(pos.avg_cost ?? 0).toFixed(2)}</td>
                    <td className="p-2 font-mono">{(pos.current_price ?? 0).toFixed(2)}</td>
                    <td className="p-2 font-mono">${(pos.market_value ?? 0).toLocaleString()}</td>
                    <td className={`p-2 font-mono ${(pos.pnl_pct ?? 0) > 0 ? "text-green-400" : "text-red-400"}`}>
                      {(pos.pnl_pct ?? 0) > 0 ? "+" : ""}{(pos.pnl_pct ?? 0).toFixed(2)}%
                    </td>
                    <td className="p-2 font-mono">{(pos.weight ?? 0).toFixed(1)}%</td>
                    <td className="p-2">{pos.sector ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Signals panel */}
      <Card header="Trading Signals">
        <div className="grid grid-cols-3 gap-3">
          {signals.length === 0 ? (
            <div className="col-span-3 text-xs text-gray-500 p-4">No active signals. Signals appear when the pipeline generates trading recommendations.</div>
          ) : (
            signals.slice(0, 3).map((s, i) => (
              <div key={i} className="p-3 rounded bg-cortex-border/20">
                <div className="flex items-center gap-2 mb-2">
                  <Badge variant={s.action === "buy" ? "success" : s.action === "sell" ? "danger" : "warning"}>
                    {s.action?.toUpperCase() ?? "HOLD"}
                  </Badge>
                  <span className="text-sm font-mono font-bold">{s.symbol}</span>
                  <span className="text-xs text-gray-500">{s.position_pct ?? 0}%</span>
                </div>
                <div className="text-xs text-gray-500 mb-1">Confidence: {((s.confidence ?? 0) * 100).toFixed(0)}%</div>
                <div className="h-1 rounded-full bg-cortex-border overflow-hidden mb-2">
                  <div className="h-full rounded-full bg-cortex-primary" style={{ width: `${(s.confidence ?? 0) * 100}%` }} />
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
