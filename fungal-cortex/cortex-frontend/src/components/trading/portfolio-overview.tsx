"use client";

import { useEffect, useRef, useState } from "react";
import { useTradingStore } from "@/stores/trading-store";

function useAnimatedValue(target: number, duration = 800): number {
  const [value, setValue] = useState(target);
  const prevRef = useRef(target);
  const rafRef = useRef(0);

  useEffect(() => {
    const start = prevRef.current;
    const delta = target - start;
    if (Math.abs(delta) < 0.001) {
      setValue(target);
      return;
    }
    const t0 = performance.now();
    const animate = (now: number) => {
      const p = Math.min((now - t0) / duration, 1);
      const eased = 1 - (1 - p) ** 3;
      setValue(start + delta * eased);
      if (p < 1) rafRef.current = requestAnimationFrame(animate);
    };
    prevRef.current = target;
    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, duration]);

  return value;
}

function fmtCurrency(v: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(v);
}

function fmtChange(v: number): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

interface MetricCardData {
  label: string;
  value: string;
  change?: { text: string; positive: boolean } | null;
}

function MetricCard({ label, value, change }: MetricCardData) {
  return (
    <div className="rounded-lg border border-[#1e1e3a] bg-[#141428] p-4 flex flex-col gap-1.5">
      <span className="text-[10px] font-semibold uppercase tracking-widest text-[#a0a0c0]">
        {label}
      </span>
      <span className="text-2xl font-bold text-white tabular-nums leading-tight">
        {value}
      </span>
      {change && (
        <span
          className={`flex items-center gap-1 text-xs font-medium ${
            change.positive ? "text-[#22c55e]" : "text-[#ef4444]"
          }`}
        >
          {change.positive ? "▲" : "▼"} {change.text}
        </span>
      )}
    </div>
  );
}

export function PortfolioOverview() {
  const portfolio = useTradingStore((s) => s.portfolio);

  const animTotalValue = useAnimatedValue(portfolio?.total_value ?? 0);
  const animCash = useAnimatedValue(portfolio?.cash ?? 0);
  const animDailyPnl = useAnimatedValue(portfolio?.daily_pnl ?? 0);
  const animTotalPnl = useAnimatedValue(portfolio?.total_pnl ?? 0);
  const animSharpe = useAnimatedValue(portfolio?.sharpe_ratio ?? 0);
  const animWinRate = useAnimatedValue(portfolio?.win_rate ?? 0);

  if (!portfolio) {
    return (
      <div className="rounded-lg border border-[#1e1e3a] bg-[#141428] p-6 text-center text-sm text-[#a0a0c0]">
        No portfolio data available
      </div>
    );
  }

  const cards: MetricCardData[] = [
    { label: "Total Value", value: fmtCurrency(animTotalValue) },
    { label: "Cash", value: fmtCurrency(animCash) },
    {
      label: "Daily P&L",
      value: `${portfolio.daily_pnl >= 0 ? "+" : ""}${fmtCurrency(animDailyPnl)}`,
      change: {
        text: fmtChange(portfolio.daily_pnl_pct),
        positive: portfolio.daily_pnl >= 0,
      },
    },
    {
      label: "Total P&L",
      value: `${portfolio.total_pnl >= 0 ? "+" : ""}${fmtCurrency(animTotalPnl)}`,
      change: {
        text: fmtChange(portfolio.total_pnl_pct),
        positive: portfolio.total_pnl >= 0,
      },
    },
    { label: "Sharpe Ratio", value: animSharpe.toFixed(2) },
    { label: "Win Rate", value: `${animWinRate.toFixed(1)}%` },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
      {cards.map((c) => (
        <MetricCard key={c.label} label={c.label} value={c.value} change={c.change} />
      ))}
    </div>
  );
}
