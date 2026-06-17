"use client";

import { useRef, useState, useMemo, useCallback } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useTradingStore } from "@/stores/trading-store";
import type { Position } from "@/types/trading";

type SortKey = keyof Position;
type SortDir = "asc" | "desc";

interface ColumnDef {
  key: SortKey;
  label: string;
  width: number;
  align: "left" | "right";
  render: (p: Position) => string | React.ReactNode;
}

function fmtCurrency(v: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(v);
}

function fmtInt(v: number): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(v);
}

function RiskDot({ status }: { status: Position["risk_status"] }) {
  const colorMap: Record<Position["risk_status"], string> = {
    pass: "bg-[#22c55e]",
    warn: "bg-[#f59e0b]",
    block: "bg-[#ef4444]",
  };
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full ${colorMap[status]} shrink-0`}
      title={status}
    />
  );
}

const COLUMNS: ColumnDef[] = [
  { key: "symbol", label: "Symbol", width: 90, align: "left", render: (p) => <span className="font-medium text-white">{p.symbol}</span> },
  { key: "name", label: "Name", width: 130, align: "left", render: (p) => <span className="text-[#a0a0c0] truncate block">{p.name}</span> },
  { key: "quantity", label: "Qty", width: 80, align: "right", render: (p) => fmtInt(p.quantity) },
  { key: "avg_cost", label: "Avg Cost", width: 95, align: "right", render: (p) => fmtCurrency(p.avg_cost) },
  { key: "current_price", label: "Price", width: 90, align: "right", render: (p) => fmtCurrency(p.current_price) },
  { key: "market_value", label: "Mkt Val", width: 100, align: "right", render: (p) => fmtCurrency(p.market_value) },
  {
    key: "pnl_pct",
    label: "P&L%",
    width: 80,
    align: "right",
    render: (p) => (
      <span className={`font-medium ${p.pnl_pct >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"}`}>
        {p.pnl_pct >= 0 ? "+" : ""}
        {p.pnl_pct.toFixed(2)}%
      </span>
    ),
  },
  {
    key: "pnl_amount",
    label: "P&L$",
    width: 100,
    align: "right",
    render: (p) => (
      <span className={`font-medium ${p.pnl_amount >= 0 ? "text-[#22c55e]" : "text-[#ef4444]"}`}>
        {p.pnl_amount >= 0 ? "+" : ""}
        {fmtCurrency(p.pnl_amount)}
      </span>
    ),
  },
  { key: "weight", label: "Wt%", width: 70, align: "right", render: (p) => `${p.weight.toFixed(1)}%` },
  { key: "sector", label: "Sector", width: 100, align: "left", render: (p) => <span className="text-[#a0a0c0]">{p.sector}</span> },
  { key: "signal_strength", label: "Signal", width: 72, align: "right", render: (p) => <span className="text-[#a0a0c0] text-xs">{p.signal_strength.toFixed(2)}</span> },
  {
    key: "risk_status",
    label: "Risk",
    width: 70,
    align: "left",
    render: (p) => (
      <span className="flex items-center gap-1.5">
        <RiskDot status={p.risk_status} />
        <span className="text-xs capitalize text-[#a0a0c0]">{p.risk_status}</span>
      </span>
    ),
  },
];

const TOTAL_WIDTH = COLUMNS.reduce((s, c) => s + c.width, 0);
const ROW_HEIGHT = 42;

export function PositionTable() {
  const positions = useTradingStore((s) => s.positions);
  const selectSymbol = useTradingStore((s) => s.selectSymbol);

  const [sortKey, setSortKey] = useState<SortKey>("symbol");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [filter, setFilter] = useState("");

  const scrollRef = useRef<HTMLDivElement>(null);

  const sorted = useMemo(() => {
    const q = filter.toLowerCase();
    let filtered = positions;
    if (q) {
      filtered = positions.filter(
        (p) =>
          p.symbol.toLowerCase().includes(q) ||
          p.name.toLowerCase().includes(q) ||
          p.sector.toLowerCase().includes(q),
      );
    }
    return [...filtered].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      const dir = sortDir === "asc" ? 1 : -1;
      if (typeof aVal === "string" && typeof bVal === "string") {
        return aVal.localeCompare(bVal) * dir;
      }
      return ((aVal as number) - (bVal as number)) * dir;
    });
  }, [positions, sortKey, sortDir, filter]);

  const virtualizer = useVirtualizer({
    count: sorted.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 8,
  });

  const handleSort = useCallback(
    (key: SortKey) => {
      setSortKey((prev) => {
        if (prev === key) {
          setSortDir((d) => (d === "asc" ? "desc" : "asc"));
          return prev;
        }
        setSortDir("asc");
        return key;
      });
    },
    [],
  );

  return (
    <div className="rounded-lg border border-[#1e1e3a] bg-[#141428] overflow-hidden flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#1e1e3a]">
        <input
          type="text"
          placeholder="Search symbol, name, sector..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="w-60 bg-[#0a0a0f] border border-[#1e1e3a] rounded px-2.5 py-1.5 text-sm text-white placeholder-[#a0a0c0] focus:outline-none focus:border-[#00d4aa] transition-colors"
        />
        <span className="text-xs text-[#a0a0c0] tabular-nums">
          Showing {sorted.length} of {positions.length} positions
        </span>
      </div>

      {/* Column headers */}
      <div
        className="flex border-b border-[#1e1e3a] bg-[#0a0a0f] sticky top-0 z-10 shrink-0"
        style={{ width: TOTAL_WIDTH }}
      >
        {COLUMNS.map((col) => {
          const active = sortKey === col.key;
          return (
            <button
              key={col.key}
              onClick={() => handleSort(col.key)}
              className={`shrink-0 h-9 flex items-center gap-1 px-2 text-[10px] font-semibold uppercase tracking-wider transition-colors cursor-pointer ${
                col.align === "right" ? "justify-end" : "justify-start"
              } ${active ? "text-[#00d4aa]" : "text-[#a0a0c0] hover:text-white"}`}
              style={{ width: col.width }}
            >
              {col.label}
              {active && (
                <span className="text-[9px]">{sortDir === "asc" ? "▲" : "▼"}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Virtualized rows */}
      <div ref={scrollRef} className="overflow-auto" style={{ maxHeight: 420 }}>
        <div style={{ width: TOTAL_WIDTH, position: "relative", height: `${virtualizer.getTotalSize()}px` }}>
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const pos = sorted[virtualRow.index];
            return (
              <div
                key={pos.symbol}
                onClick={() => selectSymbol(pos.symbol)}
                className="flex absolute inset-x-0 hover:bg-[#1a1a35] cursor-pointer border-b border-[#1e1e3a]/30 transition-colors"
                style={{
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                {COLUMNS.map((col) => (
                  <div
                    key={col.key}
                    className={`shrink-0 flex items-center px-2 text-sm truncate ${
                      col.align === "right" ? "justify-end" : "justify-start"
                    }`}
                    style={{ width: col.width }}
                  >
                    {col.render(pos)}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
