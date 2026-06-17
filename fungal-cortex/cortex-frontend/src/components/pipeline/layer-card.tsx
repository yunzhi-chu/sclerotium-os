"use client";

import { useState, useCallback } from "react";
import { usePipelineStore } from "@/stores/pipeline-store";
import { LAYER_NAMES, LAYER_COLORS, type LayerLevel, type LayerStatus } from "@/types/pipeline";

interface LayerCardProps {
  level: LayerLevel;
  status: LayerStatus;
  isBottleneck: boolean;
}

function Sparkline({ data, color, height = 32, width = 80 }: { data: number[]; color: string; height?: number; width?: number }) {
  if (data.length < 2) {
    return (
      <div className="flex items-center justify-center" style={{ width, height }}>
        <span className="text-[8px] text-gray-600 font-mono">no data</span>
      </div>
    );
  }

  const recent = data.slice(-40);
  const min = Math.min(...recent);
  const max = Math.max(...recent);
  const range = Math.max(max - min, 1);

  const points = recent
    .map((v, i) => {
      const x = (i / (recent.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 2) - 1;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} className="shrink-0">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.8"
      />
    </svg>
  );
}

function ErrorRateBar({ rate }: { rate: number }) {
  const pct = Math.min(100, rate * 100);
  const barColor = pct > 5 ? "#ef4444" : pct > 2 ? "#f59e0b" : "#22c55e";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-full rounded-full bg-[#1a1a35] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${pct}%`, backgroundColor: barColor }}
        />
      </div>
      <span className="text-[10px] font-mono w-10 text-right text-gray-400">
        {pct.toFixed(1)}%
      </span>
    </div>
  );
}

function DetailRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-[11px] text-gray-500">{label}</span>
      <span
        className="text-[11px] font-mono font-semibold"
        style={{ color: color ?? "#e2e8f0" }}
      >
        {value}
      </span>
    </div>
  );
}

export default function LayerCard({ level, status, isBottleneck }: LayerCardProps) {
  const [expanded, setExpanded] = useState(false);
  const pipelineHistory = usePipelineStore((s) => s.pipelineHistory);

  const color = LAYER_COLORS[level];
  const name = LAYER_NAMES[level];

  const toggle = useCallback(() => setExpanded((e) => !e), []);

  const statusColor =
    status.status === "healthy"
      ? "#22c55e"
      : status.status === "degraded"
      ? "#f59e0b"
      : "#ef4444";

  const borderStyle = isBottleneck
    ? "border-[#ef4444] shadow-[0_0_12px_rgba(239,68,68,0.3)]"
    : "border-cortex-border";

  return (
    <div
      className={[
        "relative rounded-lg border bg-cortex-surface overflow-hidden",
        "transition-all duration-200 cursor-pointer select-none",
        "hover:border-opacity-70",
        borderStyle,
      ].join(" ")}
      onClick={toggle}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggle();
        }
      }}
    >
      {/* Vertical color bar */}
      <div
        className="absolute left-0 top-0 bottom-0 w-1"
        style={{ backgroundColor: color }}
      />

      <div className="pl-4 pr-4 py-3">
        {/* Header row */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-white">{level}</span>
            <span className="text-[10px] text-gray-400 truncate max-w-[120px]">{name}</span>
          </div>
          <div className="flex items-center gap-2">
            {/* Bottleneck badge */}
            {isBottleneck && (
              <span className="px-1.5 py-0.5 rounded bg-[#ef4444]/20 text-[#ef4444] text-[8px] font-mono font-bold">
                BOTTLENECK
              </span>
            )}
            {/* Status badge */}
            <span
              className="px-1.5 py-0.5 rounded text-[8px] font-mono font-bold"
              style={{
                backgroundColor: `${statusColor}22`,
                color: statusColor,
              }}
            >
              {status.status.toUpperCase()}
            </span>
            {/* Expand icon */}
            <svg
              className={`w-3 h-3 text-gray-500 transition-transform duration-200 ${
                expanded ? "rotate-180" : ""
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>

        {/* Main metrics */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 mb-2">
          <div>
            <span className="text-[10px] text-gray-500">Throughput</span>
            <div className="text-sm font-mono font-bold" style={{ color }}>
              {status.throughput.toFixed(1)} <span className="text-[9px] text-gray-500 font-normal">ops/s</span>
            </div>
          </div>
          <div>
            <span className="text-[10px] text-gray-500">Latency</span>
            <div className="text-sm font-mono font-bold text-yellow-400">
              {status.latency_ms.toFixed(1)} <span className="text-[9px] text-gray-500 font-normal">ms</span>
            </div>
          </div>
          <div>
            <span className="text-[10px] text-gray-500">Queue Depth</span>
            <div className="text-sm font-mono font-bold text-gray-200">
              {status.queue_depth}
            </div>
          </div>
          <div>
            <span className="text-[10px] text-gray-500">Agents</span>
            <div className="text-sm font-mono font-bold text-gray-200">
              {status.agent_count}
            </div>
          </div>
        </div>

        {/* Error rate bar */}
        <div className="mb-2">
          <span className="text-[10px] text-gray-500 block mb-1">Error Rate</span>
          <ErrorRateBar rate={status.error_rate} />
        </div>

        {/* Sparkline */}
        <div>
          <span className="text-[10px] text-gray-500 block mb-1">Throughput History</span>
          <Sparkline data={pipelineHistory} color={color} width={80} height={28} />
        </div>
      </div>

      {/* Expanded detail section */}
      {expanded && (
        <div className="border-t border-cortex-border px-4 py-3 bg-[#0f0f20]">
          <div className="text-[10px] text-gray-400 font-semibold mb-2 uppercase tracking-wider">
            Detailed Metrics
          </div>
          <DetailRow label="Layer Level" value={level} color={color} />
          <DetailRow label="Layer Name" value={name} />
          <DetailRow label="Throughput" value={`${status.throughput.toFixed(2)} ops/s`} color={color} />
          <DetailRow label="Latency" value={`${status.latency_ms.toFixed(2)} ms`} color="#fbbf24" />
          <DetailRow
            label="Error Rate"
            value={`${(status.error_rate * 100).toFixed(3)}%`}
            color={status.error_rate > 0.05 ? "#ef4444" : "#22c55e"}
          />
          <DetailRow label="Queue Depth" value={String(status.queue_depth)} />
          <DetailRow label="Agent Count" value={String(status.agent_count)} />
          <DetailRow
            label="Status"
            value={status.status.toUpperCase()}
            color={statusColor}
          />
          <DetailRow
            label="Bottleneck"
            value={isBottleneck ? "YES" : "NO"}
            color={isBottleneck ? "#ef4444" : "#22c55e"}
          />
        </div>
      )}
    </div>
  );
}
