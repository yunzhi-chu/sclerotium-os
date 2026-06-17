"use client";

import { useState, useMemo } from "react";
import { useTradingStore } from "@/stores/trading-store";
import type { Signal } from "@/types/trading";

type ActionFilter = "all" | "buy" | "sell" | "hold";

const ACTION_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  buy: { bg: "bg-[#22c55e]/15", text: "text-[#22c55e]", label: "BUY" },
  sell: { bg: "bg-[#ef4444]/15", text: "text-[#ef4444]", label: "SELL" },
  hold: { bg: "bg-[#f59e0b]/15", text: "text-[#f59e0b]", label: "HOLD" },
};

function timeAgo(ts: number): string {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function Bar({ value, color }: { value: number; color: string }) {
  return (
    <div className="w-full h-1.5 bg-[#1e1e3a] rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-300 ${color}`}
        style={{ width: `${Math.min(value * 100, 100)}%` }}
      />
    </div>
  );
}

interface SignalCardProps {
  signal: Signal;
}

function SignalCard({ signal }: SignalCardProps) {
  const [expanded, setExpanded] = useState(false);
  const style = ACTION_STYLES[signal.action] ?? ACTION_STYLES.hold;

  return (
    <div
      className="rounded-lg border border-[#1e1e3a] bg-[#141428] p-3 flex flex-col gap-2.5 cursor-pointer hover:border-[#2a2a5a] transition-colors"
      onClick={() => setExpanded((e) => !e)}
    >
      {/* Top row: badge + symbol + time */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${style.bg} ${style.text}`}
          >
            {style.label}
          </span>
          <span className="text-sm font-semibold text-white">{signal.symbol}</span>
        </div>
        <span className="text-[10px] text-[#a0a0c0] font-mono">{timeAgo(signal.generated_at)}</span>
      </div>

      {/* Bars */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-2 text-[11px]">
          <span className="w-20 text-[#a0a0c0] shrink-0">Position</span>
          <div className="flex-1">
            <Bar value={signal.position_pct} color="bg-[#3b82f6]" />
          </div>
          <span className="w-10 text-right text-white font-mono text-[10px]">
            {(signal.position_pct * 100).toFixed(0)}%
          </span>
        </div>
        <div className="flex items-center gap-2 text-[11px]">
          <span className="w-20 text-[#a0a0c0] shrink-0">Confidence</span>
          <div className="flex-1">
            <Bar value={signal.confidence} color="bg-[#7c3aed]" />
          </div>
          <span className="w-10 text-right text-white font-mono text-[10px]">
            {(signal.confidence * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Expandable reason chain */}
      {expanded && signal.reason_chain.length > 0 && (
        <div className="border-t border-[#1e1e3a] pt-2 flex flex-col gap-1.5">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[#a0a0c0]">
            Reason Chain
          </span>
          <ul className="flex flex-col gap-1">
            {signal.reason_chain.map((reason, i) => (
              <li key={i} className="flex items-start gap-2 text-[11px] text-[#c0c0e0]">
                <span className="text-[#00d4aa] shrink-0 mt-0.5">
                  {/* Layer icon */}
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className="inline-block">
                    <rect x="0.5" y="0.5" width="9" height="9" rx="1.5" stroke="currentColor" strokeWidth="0.8" fill="none" />
                    <line x1="2.5" y1="5" x2="7.5" y2="5" stroke="currentColor" strokeWidth="0.8" />
                  </svg>
                </span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
          {signal.layers_used.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {signal.layers_used.map((layer) => (
                <span
                  key={layer}
                  className="text-[9px] px-1.5 py-0.5 rounded bg-[#1e1e3a] text-[#a0a0c0] font-mono"
                >
                  {layer}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Expand/collapse indicator */}
      <div className="flex justify-center">
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          className={`text-[#a0a0c0] transition-transform ${expanded ? "rotate-180" : ""}`}
        >
          <path d="M3 5L6 8L9 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  );
}

const FILTER_BTNS: { key: ActionFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "buy", label: "Buy" },
  { key: "sell", label: "Sell" },
  { key: "hold", label: "Hold" },
];

export function SignalPanel() {
  const signals = useTradingStore((s) => s.signals);
  const [filter, setFilter] = useState<ActionFilter>("all");

  const filtered = useMemo(() => {
    if (filter === "all") return signals;
    return signals.filter((s) => s.action === filter);
  }, [signals, filter]);

  return (
    <div className="rounded-lg border border-[#1e1e3a] bg-[#141428] overflow-hidden flex flex-col">
      {/* Header */}
      <div className="px-3 py-2 border-b border-[#1e1e3a] flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-[#a0a0c0]">
          Signals
        </span>
        <span className="text-[10px] text-[#a0a0c0] font-mono">{filtered.length} signals</span>
      </div>

      {/* Filter bar */}
      <div className="flex gap-1 px-3 py-2 border-b border-[#1e1e3a]">
        {FILTER_BTNS.map((btn) => (
          <button
            key={btn.key}
            onClick={() => setFilter(btn.key)}
            className={`px-2 py-1 text-[10px] font-medium uppercase tracking-wider rounded transition-colors ${
              filter === btn.key
                ? "bg-[#00d4aa] text-[#0a0a0f]"
                : "bg-[#1e1e3a] text-[#a0a0c0] hover:text-white"
            }`}
          >
            {btn.label}
          </button>
        ))}
      </div>

      {/* Signal list */}
      <div className="flex-1 overflow-auto flex flex-col gap-2 p-3 max-h-[420px]">
        {filtered.length === 0 ? (
          <div className="text-center text-sm text-[#a0a0c0] py-6">No signals</div>
        ) : (
          filtered.map((s, i) => <SignalCard key={`${s.symbol}-${s.generated_at}-${i}`} signal={s} />)
        )}
      </div>
    </div>
  );
}
