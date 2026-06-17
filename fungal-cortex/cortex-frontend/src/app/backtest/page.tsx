/** Backtest Lab — strategy selector, config, results, risk decomposition. */
"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useBacktestStore } from "@/stores/backtest-store";
import { useWebSocket } from "@/hooks/use-websocket";
import { api } from "@/lib/api-client";
import type { SkillDNA } from "@/types/skill";
import type {
  BacktestStrategy,
  EquityPoint,
  BarraFactor,
  BacktestResult,
  BacktestConfig,
} from "@/types/backtest";

/** Fallback config for initial render when store is empty. */
const FALLBACK_CONFIG: BacktestConfig = {
  start_date: "2020-01-01",
  end_date: "2026-06-12",
  initial_capital: 1_000_000,
  commission: 0.0003,
  slippage: 0.001,
  benchmark: "CSI 300",
};

export default function BacktestPage() {
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null);

  const {
    strategies, equityCurve, barraFactors, config, results, running,
    setStrategies, setEquityCurve, setBarraFactors, setConfig,
    setResults, setRunning,
  } = useBacktestStore();

  // Fetch initial backtest data
  useEffect(() => {
    api.getStrategies().catch(() => {});
  }, []);

  // Subscribe to backtest WebSocket
  useWebSocket("backtest", "backtest", (data: unknown) => {
    const d = data as Record<string, unknown>;

    if (d.strategies && Array.isArray(d.strategies)) {
      const mapped: BacktestStrategy[] = (d.strategies as Array<Record<string, unknown>>).map(
        (s) => ({
          id: (s.id as string) ?? "",
          name: (s.name as string) ?? "",
          sharpe: (s.sharpe as number) ?? 0,
          max_drawdown: (s.max_drawdown as number) ?? 0,
          annual_return: (s.annual_return as number) ?? 0,
          win_rate: (s.win_rate as number) ?? 0,
          dna: (s.dna as SkillDNA) ?? {
            picker: 0.5,
            timer: 0.5,
            risk_control: 0.5,
            frequency: 0.5,
            complexity: 0.5,
            holding_period: 0.5,
          },
          trades: (s.trades as number) ?? 0,
          is_active: (s.is_active as boolean) ?? true,
        }),
      );
      setStrategies(mapped);
    }

    if (d.equity_curve && Array.isArray(d.equity_curve)) {
      const mapped: EquityPoint[] = (d.equity_curve as Array<Record<string, unknown>>).map(
        (p) => ({
          t: (p.t as number) ?? 0,
          strategy: (p.strategy as number) ?? 0,
          benchmark: (p.benchmark as number) ?? 0,
        }),
      );
      setEquityCurve(mapped);
    }

    if (d.barra_factors && Array.isArray(d.barra_factors)) {
      const mapped: BarraFactor[] = (d.barra_factors as Array<Record<string, unknown>>).map(
        (f) => ({
          factor: (f.factor as string) ?? "",
          exposure: (f.exposure as number) ?? 0,
          return: (f.return as number) ?? 0,
          risk: (f.risk as number) ?? 0,
        }),
      );
      setBarraFactors(mapped);
    }

    if (d.config) {
      const c = d.config as Record<string, unknown>;
      setConfig({
        start_date: (c.start_date as string) ?? FALLBACK_CONFIG.start_date,
        end_date: (c.end_date as string) ?? FALLBACK_CONFIG.end_date,
        initial_capital: (c.initial_capital as number) ?? FALLBACK_CONFIG.initial_capital,
        commission: (c.commission as number) ?? FALLBACK_CONFIG.commission,
        slippage: (c.slippage as number) ?? FALLBACK_CONFIG.slippage,
        benchmark: (c.benchmark as string) ?? FALLBACK_CONFIG.benchmark,
      });
    }

    if (d.results && Array.isArray(d.results)) {
      const mapped: BacktestResult[] = (d.results as Array<Record<string, unknown>>).map(
        (r) => ({
          id: (r.id as string) ?? "",
          strategy_name: (r.strategy_name as string) ?? "",
          sharpe: (r.sharpe as number) ?? 0,
          max_drawdown: (r.max_drawdown as number) ?? 0,
          win_rate: (r.win_rate as number) ?? 0,
          annual_return: (r.annual_return as number) ?? 0,
          calmar: (r.calmar as number) ?? 0,
          systematic_risk: (r.systematic_risk as number) ?? 0,
          specific_risk: (r.specific_risk as number) ?? 0,
        }),
      );
      setResults(mapped);
    }

    if (d.running !== undefined) {
      setRunning(d.running as boolean);
    }
  });

  const cfg = config ?? FALLBACK_CONFIG;
  const strategiesList = strategies;
  const eqCurve = equityCurve;
  const barra = barraFactors;

  // Compute aggregate metrics from strategy data
  const aggSharpe =
    strategiesList.length > 0
      ? (
          strategiesList.reduce((sum, s) => sum + s.sharpe, 0) /
          strategiesList.length
        ).toFixed(2)
      : "—";
  const aggMaxDd =
    strategiesList.length > 0
      ? Math.min(...strategiesList.map((s) => s.max_drawdown)).toFixed(1)
      : "—";
  const aggWinRate =
    strategiesList.length > 0
      ? (
          strategiesList.reduce((sum, s) => sum + s.win_rate, 0) /
          strategiesList.length
        ).toFixed(1)
      : "—";
  const aggReturn =
    strategiesList.length > 0
      ? (
          strategiesList.reduce((sum, s) => sum + s.annual_return, 0) /
          strategiesList.length
        ).toFixed(1)
      : "—";

  // Use the first result's calmar, or compute a rough one
  const aggCalmar =
    results.length > 0
      ? results[0].calmar.toFixed(2)
      : "—";

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-bold font-mono text-cortex-primary">Backtest Lab</h1>
        <div className="flex gap-2">
          <Badge variant="info">
            {strategiesList.length > 0
              ? `${strategiesList.length} strategies`
              : "Loading..."}
          </Badge>
          <Badge variant={running ? "success" : "default"}>
            {running ? "Running..." : "Sandbox: Active"}
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Strategy list */}
        <div className="col-span-1 space-y-2 max-h-[600px] overflow-y-auto">
          {strategiesList.length === 0 ? (
            <div className="text-xs text-gray-500 p-4">No strategies loaded. Start a backtest to generate strategies.</div>
          ) : (
            strategiesList.map((s) => (
              <Card key={s.id}
                className={`cursor-pointer transition-all ${selectedStrategy === s.id ? "ring-1 ring-cortex-primary glow-primary" : ""} ${!s.is_active ? "opacity-50" : ""}`}
                onClick={() => setSelectedStrategy(s.id)}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-mono font-bold">{s.name}</span>
                  <Badge variant={s.sharpe > 2 ? "success" : s.sharpe > 1 ? "warning" : "danger"} size="sm">
                    Sharpe {s.sharpe.toFixed(1)}
                  </Badge>
                </div>
                <div className="grid grid-cols-3 gap-1 text-[10px]">
                  <div>
                    <span className="text-gray-600">Return</span>
                    <div className="font-mono text-green-400">+{s.annual_return.toFixed(1)}%</div>
                  </div>
                  <div>
                    <span className="text-gray-600">MDD</span>
                    <div className="font-mono text-red-400">{s.max_drawdown.toFixed(1)}%</div>
                  </div>
                  <div>
                    <span className="text-gray-600">WinRate</span>
                    <div className="font-mono">{s.win_rate.toFixed(0)}%</div>
                  </div>
                </div>
                <div className="mt-2 flex gap-1">
                  {(["picker", "timer", "risk_control", "frequency", "complexity", "holding_period"] as (keyof SkillDNA)[]).map((dim) => (
                    <div key={dim} className="h-1 flex-1 rounded-full bg-cortex-border overflow-hidden" title={`${dim}: ${(s.dna[dim] * 100).toFixed(0)}`}>
                      <div className="h-full rounded-full bg-cortex-primary" style={{ width: `${s.dna[dim] * 100}%` }} />
                    </div>
                  ))}
                </div>
              </Card>
            ))
          )}
        </div>

        {/* Results area */}
        <div className="col-span-2 space-y-4">
          {/* Config */}
          <Card header="Backtest Configuration">
            <div className="grid grid-cols-4 gap-3">
              {[
                ["Start Date", cfg.start_date],
                ["End Date", cfg.end_date],
                ["Initial Capital", `$${(cfg.initial_capital / 1_000_000).toFixed(1)}M`],
                ["Commission", `${(cfg.commission * 100).toFixed(2)}%`],
              ].map(([label, value]) => (
                <div key={String(label)}>
                  <div className="text-[10px] text-gray-500">{label}</div>
                  <div className="text-sm font-mono">{value}</div>
                </div>
              ))}
            </div>
            <div className="mt-3">
              <Button variant="primary" onClick={() => {
                setRunning(true);
                api.createBacktest({
                  start_date: cfg.start_date,
                  end_date: cfg.end_date,
                  initial_capital: cfg.initial_capital,
                  commission: cfg.commission,
                  slippage: cfg.slippage,
                  benchmark: cfg.benchmark,
                }).catch(() => {});
              }}>
                {running ? "Running..." : "Run Backtest"}
              </Button>
            </div>
          </Card>

          {/* Equity Curve */}
          <Card header="Equity Curve: Strategy vs Benchmark">
            <div className="relative h-48">
              {eqCurve.length === 0 ? (
                <div className="flex items-center justify-center h-full text-xs text-gray-500">
                  Run a backtest to see the equity curve.
                </div>
              ) : (
                <>
                  <svg viewBox={`0 0 600 160`} className="w-full h-full" preserveAspectRatio="xMidYMid meet">
                    {/* Grid lines */}
                    {[0, 0.25, 0.5, 0.75, 1].map((pct) => (
                      <line key={pct} x1="0" y1={pct * 160} x2="600" y2={pct * 160}
                        stroke="#1e1e3a" strokeWidth="0.5" />
                    ))}
                    {/* Benchmark line */}
                    <polyline
                      points={eqCurve.map((p, i) => `${(i / eqCurve.length) * 600},${160 - ((p.benchmark - 900000) / 300000) * 160}`).join(" ")}
                      fill="none" stroke="#888899" strokeWidth="1" strokeDasharray="4,4"
                    />
                    {/* Strategy line */}
                    <polyline
                      points={eqCurve.map((p, i) => `${(i / eqCurve.length) * 600},${160 - ((p.strategy - 900000) / 300000) * 160}`).join(" ")}
                      fill="none" stroke="#22c55e" strokeWidth="1.5"
                    />
                    {/* Gradient fill under strategy */}
                    <polygon
                      points={`${eqCurve.map((p, i) => `${(i / eqCurve.length) * 600},${160 - ((p.strategy - 900000) / 300000) * 160}`).join(" ")} 600,160 0,160`}
                      fill="url(#equityGrad)" opacity="0.15"
                    />
                    <defs>
                      <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#22c55e" />
                        <stop offset="100%" stopColor="#22c55e" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute top-2 left-2 flex gap-3 text-[10px]">
                    <span className="text-green-400">● Strategy</span>
                    <span className="text-gray-500">- - Benchmark</span>
                  </div>
                </>
              )}
            </div>
          </Card>

          {/* Performance metrics */}
          <div className="grid grid-cols-5 gap-2">
            {([
              ["Sharpe", aggSharpe, "text-green-400"],
              ["Max DD", aggMaxDd !== "—" ? `${aggMaxDd}%` : "—", "text-red-400"],
              ["Win Rate", aggWinRate !== "—" ? `${aggWinRate}%` : "—", "text-white"],
              ["Ann. Return", aggReturn !== "—" ? `+${aggReturn}%` : "—", "text-green-400"],
              ["Calmar", aggCalmar, "text-green-400"],
            ] as const).map(([label, value, cls]) => (
              <Card key={label} className="text-center">
                <div className="text-[10px] text-gray-500">{label}</div>
                <div className={`text-lg font-mono font-bold ${cls}`}>{value}</div>
              </Card>
            ))}
          </div>

          {/* Barra Attribution */}
          <Card header="Barra 7-Factor Risk Attribution">
            <div className="space-y-2">
              {barra.length === 0 ? (
                <div className="text-xs text-gray-500">Run a backtest to see factor attribution.</div>
              ) : (
                <>
                  {barra.map((f) => (
                    <div key={f.factor} className="flex items-center gap-3">
                      <span className="text-xs text-gray-400 w-20">{f.factor}</span>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 rounded-full bg-cortex-border overflow-hidden">
                            <div
                              className={`h-full rounded-full ${f.exposure > 0 ? "bg-green-500" : "bg-red-500"}`}
                              style={{ width: `${Math.abs(f.exposure) * 100}%` }}
                            />
                          </div>
                          <span className="text-[10px] font-mono w-8 text-right">{f.exposure.toFixed(2)}</span>
                        </div>
                      </div>
                      <span className="text-[10px] font-mono w-16 text-right text-gray-500">{f.risk.toFixed(1)}% risk</span>
                    </div>
                  ))}
                  <div className="pt-2 border-t border-cortex-border">
                    <div className="flex justify-between text-xs">
                      <span className="text-gray-400">Systematic Risk</span>
                      <span className="font-mono">
                        {results.length > 0 ? `${results[0].systematic_risk.toFixed(1)}%` : "—"}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs mt-1">
                      <span className="text-gray-400">Specific Risk</span>
                      <span className="font-mono">
                        {results.length > 0 ? `${results[0].specific_risk.toFixed(1)}%` : "—"}
                      </span>
                    </div>
                  </div>
                </>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
