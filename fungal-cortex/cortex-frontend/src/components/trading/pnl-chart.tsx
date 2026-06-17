"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTradingStore } from "@/stores/trading-store";

const PADDING = { top: 20, right: 16, bottom: 28, left: 60 };
const HEIGHT = 300;

interface TooltipState {
  x: number;
  y: number;
  equity: number;
  benchmark: number;
  time: string;
}

function formatTime(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

function formatDate(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function PnLChart() {
  const pnlHistory = useTradingStore((s) => s.pnlHistory);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dim, setDim] = useState({ width: 600 });
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const autoScrollRef = useRef<HTMLDivElement>(null);

  /* Responsive width */
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDim({ width: entry.contentRect.width });
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  /* Auto-scroll to latest */
  useEffect(() => {
    if (autoScrollRef.current) {
      autoScrollRef.current.scrollLeft = autoScrollRef.current.scrollWidth;
    }
  }, [pnlHistory.length]);

  const data = pnlHistory;
  const { width } = dim;
  const chartW = Math.max(width - PADDING.left - PADDING.right, 200);
  const chartH = HEIGHT - PADDING.top - PADDING.bottom;

  /* Scales */
  const minTime = data.length > 0 ? data[0].timestamp : 0;
  const maxTime = data.length > 0 ? data[data.length - 1].timestamp : 1;
  const timeRange = Math.max(maxTime - minTime, 1);

  let minEquity = Infinity;
  let maxEquity = -Infinity;
  for (const d of data) {
    if (d.equity < minEquity) minEquity = d.equity;
    if (d.equity > maxEquity) maxEquity = d.equity;
    if (d.benchmark < minEquity) minEquity = d.benchmark;
    if (d.benchmark > maxEquity) maxEquity = d.benchmark;
  }
  const equityPad = (maxEquity - minEquity) * 0.1 || 1;
  minEquity -= equityPad;
  maxEquity += equityPad;
  const equityRange = Math.max(maxEquity - minEquity, 1);

  const xScale = (ts: number) =>
    PADDING.left + ((ts - minTime) / timeRange) * chartW;
  const yScale = (v: number) =>
    PADDING.top + chartH - ((v - minEquity) / equityRange) * chartH;

  /* Path builders */
  const equityPath = data
    .map((d, i) => `${i === 0 ? "M" : "L"}${xScale(d.timestamp)},${yScale(d.equity)}`)
    .join(" ");

  const benchmarkPath = data
    .map((d, i) => `${i === 0 ? "M" : "L"}${xScale(d.timestamp)},${yScale(d.benchmark)}`)
    .join(" ");

  const areaPath =
    data.length > 0
      ? `${equityPath} L${xScale(data[data.length - 1].timestamp)},${yScale(minEquity)} L${xScale(data[0].timestamp)},${yScale(minEquity)} Z`
      : "";

  /* Y-axis ticks */
  const yTicks: number[] = [];
  const tickCount = 5;
  for (let i = 0; i <= tickCount; i++) {
    yTicks.push(minEquity + (equityRange / tickCount) * i);
  }

  /* X-axis ticks */
  const xTickInterval = Math.max(1, Math.floor(data.length / 6));
  const xTicks = data.filter((_, i) => i % xTickInterval === 0 || i === data.length - 1);

  /* Hover handler */
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (data.length === 0) return;
      const svg = e.currentTarget;
      const rect = svg.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;

      let closest = data[0];
      let minDist = Infinity;
      for (const d of data) {
        const dist = Math.abs(xScale(d.timestamp) - mouseX);
        if (dist < minDist) {
          minDist = dist;
          closest = d;
        }
      }

      setTooltip({
        x: xScale(closest.timestamp),
        y: yScale(closest.equity),
        equity: closest.equity,
        benchmark: closest.benchmark,
        time: formatTime(closest.timestamp),
      });
    },
    [data, minTime, timeRange, chartW, minEquity, equityRange, chartH],
  );

  const handleMouseLeave = useCallback(() => setTooltip(null), []);

  if (data.length === 0) {
    return (
      <div className="rounded-lg border border-[#1e1e3a] bg-[#141428] p-6 text-center text-sm text-[#a0a0c0]">
        No P&L history available
      </div>
    );
  }

  return (
    <div ref={containerRef} className="rounded-lg border border-[#1e1e3a] bg-[#141428] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[#1e1e3a]">
        <span className="text-xs font-semibold uppercase tracking-wider text-[#a0a0c0]">
          P&L Equity Curve
        </span>
        <div className="flex items-center gap-4 text-[11px]">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-[#00d4aa] inline-block" />
            Equity
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-[#a0a0c0] border-t border-dashed inline-block" />
            Benchmark
          </span>
        </div>
      </div>

      {/* Chart area with horizontal scroll for new data */}
      <div ref={autoScrollRef} className="overflow-x-auto">
        <svg
          width={Math.max(width, 500)}
          height={HEIGHT}
          className="block"
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          style={{ minWidth: 500 }}
        >
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#00d4aa" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#00d4aa" stopOpacity={0.02} />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {yTicks.map((v) => (
            <g key={v}>
              <line
                x1={PADDING.left}
                y1={yScale(v)}
                x2={PADDING.left + chartW}
                y2={yScale(v)}
                stroke="#1e1e3a"
                strokeWidth={1}
              />
              <text
                x={PADDING.left - 6}
                y={yScale(v) + 3}
                textAnchor="end"
                className="fill-[#a0a0c0] text-[10px] font-mono"
              >
                {v.toFixed(0)}
              </text>
            </g>
          ))}

          {/* X-axis labels */}
          {xTicks.map((d) => (
            <text
              key={d.timestamp}
              x={xScale(d.timestamp)}
              y={HEIGHT - 4}
              textAnchor="middle"
              className="fill-[#a0a0c0] text-[10px] font-mono"
            >
              {formatTime(d.timestamp)}
            </text>
          ))}

          {/* Area fill */}
          {areaPath && (
            <path d={areaPath} fill="url(#equityGradient)" />
          )}

          {/* Equity line */}
          <path d={equityPath} fill="none" stroke="#00d4aa" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />

          {/* Benchmark line */}
          <path d={benchmarkPath} fill="none" stroke="#a0a0c0" strokeWidth={1.5} strokeDasharray="6,4" strokeLinejoin="round" strokeLinecap="round" />

          {/* Hover crosshair */}
          {tooltip && (
            <>
              <line
                x1={tooltip.x}
                y1={PADDING.top}
                x2={tooltip.x}
                y2={PADDING.top + chartH}
                stroke="#a0a0c0"
                strokeWidth={1}
                strokeDasharray="3,3"
                opacity={0.5}
              />
              <circle cx={tooltip.x} cy={tooltip.y} r={4} fill="#00d4aa" stroke="#141428" strokeWidth={2} />
            </>
          )}
        </svg>
      </div>

      {/* Tooltip overlay */}
      {tooltip && (
        <div
          className="absolute pointer-events-none bg-[#0a0a0f] border border-[#1e1e3a] rounded px-2.5 py-1.5 text-xs shadow-lg z-20"
          style={{
            left: Math.min(tooltip.x + 12, width - 160),
            top: Math.max(tooltip.y - 50, 4),
          }}
        >
          <div className="text-[#a0a0c0]">{tooltip.time} {formatDate(data.find(d => Math.abs(xScale(d.timestamp) - tooltip.x) < 5)?.timestamp ?? 0)}</div>
          <div className="text-[#00d4aa] font-medium">Equity: {tooltip.equity.toFixed(2)}</div>
          <div className="text-[#a0a0c0]">Benchmark: {tooltip.benchmark.toFixed(2)}</div>
        </div>
      )}
    </div>
  );
}
