"use client";

import { useMemo, useRef } from "react";
import { usePipelineStore } from "@/stores/pipeline-store";
import { LAYER_NAMES, LAYER_COLORS, type LayerLevel } from "@/types/pipeline";

const LAYER_LEVELS: LayerLevel[] = ["L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7"];
const SVG_WIDTH = 1200;
const SVG_HEIGHT = 480;
const LAYER_W = 84;
const LAYER_H = 210;
const LAYER_Y = 160;
const FLOW_LINE_COUNT = 4;

const LAYER_X_POSITIONS: Record<LayerLevel, number> = {
  L0: 60,
  L1: 207,
  L2: 354,
  L3: 501,
  L4: 648,
  L5: 795,
  L6: 942,
  L7: 1089,
};

function formatThroughput(val: number): string {
  if (val >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`;
  if (val >= 1_000) return `${(val / 1_000).toFixed(1)}K`;
  return val.toFixed(1);
}

export default function PipelineFlow() {
  const containerRef = useRef<HTMLDivElement>(null);
  const snapshot = usePipelineStore((s) => s.snapshot);
  const pipelineHistory = usePipelineStore((s) => s.pipelineHistory);

  const { layers, bottleneckAt, bottleneckScore, totalThroughput, avgLatency } = useMemo(() => {
    if (!snapshot) {
      return {
        layers: [] as {
          level: LayerLevel;
          throughput: number;
          latency: number;
          errorRate: number;
          queueDepth: number;
          agentCount: number;
          status: string;
        }[],
        bottleneckAt: null as LayerLevel | null,
        bottleneckScore: 0,
        totalThroughput: 0,
        avgLatency: 0,
      };
    }
    return {
      layers: snapshot.layers.map((l) => ({
        level: l.level,
        throughput: l.throughput,
        latency: l.latency_ms,
        errorRate: l.error_rate,
        queueDepth: l.queue_depth,
        agentCount: l.agent_count,
        status: l.status,
      })),
      bottleneckAt: snapshot.bottleneck_at,
      bottleneckScore: snapshot.bottleneck_score,
      totalThroughput: snapshot.total_throughput,
      avgLatency: snapshot.avg_end_to_end_ms,
    };
  }, [snapshot]);

  const layerMap = useMemo(() => {
    const map = new Map<LayerLevel, (typeof layers)[number]>();
    for (const l of layers) map.set(l.level, l);
    return map;
  }, [layers]);

  const maxThroughput = useMemo(
    () => Math.max(1, ...layers.map((l) => l.throughput)),
    [layers]
  );

  return (
    <div
      ref={containerRef}
      className="relative w-full overflow-hidden rounded-xl border border-cortex-border bg-cortex-surface p-4"
    >
      {/* Header stats */}
      <div className="mb-3 flex items-center justify-between text-xs text-gray-400">
        <span className="font-mono">
          Total Throughput:{" "}
          <span className="text-cortex-primary font-semibold">
            {formatThroughput(totalThroughput)}
          </span>{" "}
          ops/s
        </span>
        <span className="font-mono">
          Avg E2E:{" "}
          <span className="text-yellow-400 font-semibold">{avgLatency.toFixed(1)}</span> ms
        </span>
        <span className="font-mono">
          History: <span className="text-blue-400 font-semibold">{pipelineHistory.length}</span> pts
        </span>
      </div>

      {/* SVG Flow Diagram */}
      <svg
        viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
        className="w-full h-auto"
        style={{ maxHeight: "420px" }}
      >
        <defs>
          {/* Bottleneck red glow */}
          <filter id="bottleneck-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feFlood floodColor="#ef4444" floodOpacity="0.7" result="color" />
            <feComposite in="color" in2="blur" operator="in" result="glow" />
            <feMerge>
              <feMergeNode in="glow" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Critical layer pulse */}
          <filter id="critical-pulse">
            <feGaussianBlur stdDeviation="3" result="blur">
              <animate
                attributeName="stdDeviation"
                values="2;6;2"
                dur="2s"
                repeatCount="indefinite"
              />
            </feGaussianBlur>
            <feFlood floodColor="#ef4444" floodOpacity="0.6" result="color" />
            <feComposite in="color" in2="blur" operator="in" result="glow" />
            <feMerge>
              <feMergeNode in="glow" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Flow gradients between layers */}
          {LAYER_LEVELS.slice(0, -1).map((level, i) => {
            const fromColor = LAYER_COLORS[level];
            const toLevel = LAYER_LEVELS[i + 1];
            const toColor = LAYER_COLORS[toLevel];
            const gradId = `flow-grad-${i}`;
            return (
              <linearGradient key={gradId} id={gradId} x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor={fromColor} stopOpacity="0.6" />
                <stop offset="100%" stopColor={toColor} stopOpacity="0.6" />
              </linearGradient>
            );
          })}

          {/* Inner glow for layer tops */}
          <linearGradient id="inner-glow" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.08" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Vertical grid lines */}
        {LAYER_LEVELS.map((level) => {
          const cx = LAYER_X_POSITIONS[level];
          return (
            <line
              key={`grid-${level}`}
              x1={cx}
              y1={LAYER_Y - 30}
              x2={cx}
              y2={LAYER_Y + LAYER_H + 10}
              stroke="#1e1e3a"
              strokeWidth="1"
              strokeDasharray="3 3"
              opacity="0.4"
            />
          );
        })}

        {/* Animated flow lines between layers */}
        {LAYER_LEVELS.slice(0, -1).map((fromLevel, i) => {
          const toLevel = LAYER_LEVELS[i + 1];
          const fromLayer = layerMap.get(fromLevel);
          const toLayer = layerMap.get(toLevel);
          if (!fromLayer || !toLayer) return null;

          const x1 = LAYER_X_POSITIONS[fromLevel] + LAYER_W / 2;
          const x2 = LAYER_X_POSITIONS[toLevel] - LAYER_W / 2;
          const gap = x2 - x1;

          const flowValue = (fromLayer.throughput + toLayer.throughput) / 2;
          const flowRatio = flowValue / Math.max(1, maxThroughput);
          const strokeW = Math.max(2, flowRatio * 14);

          const statusMap: Record<string, number> = {
            healthy: 1.0,
            degraded: 0.55,
            critical: 0.4,
          };
          const baseOpacity = statusMap[fromLayer.status] ?? 0.6;

          return Array.from({ length: FLOW_LINE_COUNT }, (_, p) => {
            const t = (p + 0.5) / FLOW_LINE_COUNT;
            const y = LAYER_Y + t * LAYER_H;
            const spread = strokeW * 0.3 * (t - 0.5);
            const py = y + spread;

            const cp1x = x1 + gap * 0.35;
            const cp2x = x2 - gap * 0.35;
            const pathD = `M ${x1} ${py} C ${cp1x} ${py}, ${cp2x} ${py}, ${x2} ${py}`;

            const isCritical = fromLayer.status === "critical";
            const isDegraded = fromLayer.status === "degraded";
            const opacity = isCritical
              ? Math.max(0.25, baseOpacity)
              : isDegraded
              ? 0.45
              : baseOpacity;

            return (
              <g key={`flow-${i}-${p}`}>
                {isCritical && (
                  <path
                    d={pathD}
                    fill="none"
                    stroke="#ef4444"
                    strokeWidth={strokeW + 4}
                    opacity="0.15"
                    strokeLinecap="round"
                  />
                )}
                <path
                  d={pathD}
                  fill="none"
                  stroke={`url(#flow-grad-${i})`}
                  strokeWidth={strokeW}
                  opacity={opacity}
                  strokeLinecap="round"
                  strokeDasharray="6 4"
                  className="flow-dash"
                />
              </g>
            );
          });
        })}

        {/* Layer columns */}
        {LAYER_LEVELS.map((level) => {
          const layer = layerMap.get(level);
          const cx = LAYER_X_POSITIONS[level];
          const x = cx - LAYER_W / 2;
          const color = LAYER_COLORS[level];
          const isBottleneck = bottleneckAt === level;
          const isCritical = layer?.status === "critical";
          const isDegraded = layer?.status === "degraded";
          const status = layer?.status ?? "healthy";

          let rectOpacity = 0.85;
          if (isDegraded) rectOpacity = 0.5;
          if (isCritical) rectOpacity = 0.8;

          const layerFill = isDegraded ? `${color}66` : color;
          const filterId = isBottleneck
            ? "bottleneck-glow"
            : isCritical
            ? "critical-pulse"
            : undefined;

          const statusDotColor =
            status === "healthy"
              ? "#22c55e"
              : status === "degraded"
              ? "#f59e0b"
              : "#ef4444";

          return (
            <g key={`layer-${level}`}>
              {/* Bottleneck pulsing ring */}
              {isBottleneck && (
                <>
                  <rect
                    x={x - 4}
                    y={LAYER_Y - 4}
                    width={LAYER_W + 8}
                    height={LAYER_H + 8}
                    rx={14}
                    ry={14}
                    fill="none"
                    stroke="#ef4444"
                    strokeWidth="2"
                    opacity="0.5"
                    strokeDasharray="4 3"
                  >
                    <animate
                      attributeName="opacity"
                      values="0.3;0.8;0.3"
                      dur="1.5s"
                      repeatCount="indefinite"
                    />
                  </rect>
                  <g transform={`translate(${cx}, ${LAYER_Y + LAYER_H + 28})`}>
                    <rect x={-45} y={-11} width={90} height={22} rx={4} fill="#ef4444" opacity="0.2" />
                    <text
                      x={0}
                      y={4}
                      textAnchor="middle"
                      fill="#ef4444"
                      fontSize="11"
                      fontFamily="monospace"
                    >
                      bottleneck: {(bottleneckScore * 100).toFixed(0)}%
                    </text>
                  </g>
                </>
              )}

              {/* Main layer rect */}
              <rect
                x={x}
                y={LAYER_Y}
                width={LAYER_W}
                height={LAYER_H}
                rx={10}
                ry={10}
                fill={layerFill}
                opacity={rectOpacity}
                stroke={isCritical ? "#ef4444" : `${color}66`}
                strokeWidth={isCritical ? 2 : 1}
                filter={filterId}
              >
                {isCritical && (
                  <animate
                    attributeName="stroke"
                    values="#ef4444;#ff6b6b;#ef4444"
                    dur="2s"
                    repeatCount="indefinite"
                  />
                )}
              </rect>

              {/* Inner glow overlay */}
              <rect
                x={x}
                y={LAYER_Y}
                width={LAYER_W}
                height={LAYER_H * 0.3}
                rx={10}
                ry={10}
                fill="url(#inner-glow)"
                opacity="0.15"
              />

              {/* Layer name inside */}
              <text
                x={cx}
                y={LAYER_Y + LAYER_H / 2 - 4}
                textAnchor="middle"
                fill="#e2e8f0"
                fontSize="13"
                fontWeight="600"
                fontFamily="sans-serif"
              >
                {level}
              </text>
              <text
                x={cx}
                y={LAYER_Y + LAYER_H / 2 + 14}
                textAnchor="middle"
                fill="#a0a0c0"
                fontSize="9"
                fontFamily="sans-serif"
              >
                {LAYER_NAMES[level]}
              </text>

              {/* Status dot */}
              <circle cx={cx} cy={LAYER_Y + LAYER_H - 16} r={4} fill={statusDotColor} opacity={0.9} />
              <text
                x={cx + 9}
                y={LAYER_Y + LAYER_H - 13}
                fill="#888"
                fontSize="9"
                fontFamily="monospace"
              >
                {status}
              </text>

              {/* Throughput above */}
              <text
                x={cx}
                y={LAYER_Y - 10}
                textAnchor="middle"
                fill={color}
                fontSize="15"
                fontWeight="700"
                fontFamily="monospace"
              >
                {layer ? formatThroughput(layer.throughput) : "---"}
              </text>
              <text
                x={cx}
                y={LAYER_Y + 4}
                textAnchor="middle"
                fill="#555"
                fontSize="8"
                fontFamily="monospace"
              >
                ops/s
              </text>

              {/* Mini metrics inside */}
              {layer && (
                <g opacity="0.55">
                  <text
                    x={cx}
                    y={LAYER_Y + LAYER_H / 2 + 32}
                    textAnchor="middle"
                    fill="#888"
                    fontSize="8"
                    fontFamily="monospace"
                  >
                    {layer.latency.toFixed(0)}ms | Q:{layer.queueDepth}
                  </text>
                  <text
                    x={cx}
                    y={LAYER_Y + LAYER_H / 2 + 44}
                    textAnchor="middle"
                    fill="#888"
                    fontSize="8"
                    fontFamily="monospace"
                  >
                    E:{(layer.errorRate * 100).toFixed(1)}% | A:{layer.agentCount}
                  </text>
                </g>
              )}
            </g>
          );
        })}

        {/* Flow percentage indicators */}
        {LAYER_LEVELS.slice(0, -1).map((_, i) => {
          const fromLevel = LAYER_LEVELS[i];
          const toLevel = LAYER_LEVELS[i + 1];
          const fromLayer = layerMap.get(fromLevel);
          const toLayer = layerMap.get(toLevel);
          if (!fromLayer || !toLayer) return null;

          const x1 = LAYER_X_POSITIONS[fromLevel] + LAYER_W / 2;
          const x2 = LAYER_X_POSITIONS[toLevel] - LAYER_W / 2;
          const midX = (x1 + x2) / 2;
          const flowValue = (fromLayer.throughput + toLayer.throughput) / 2;
          const flowRatio = flowValue / Math.max(1, maxThroughput);

          return (
            <text
              key={`pct-${i}`}
              x={midX}
              y={LAYER_Y + LAYER_H + 50}
              textAnchor="middle"
              fill="#555"
              fontSize="8"
              fontFamily="monospace"
            >
              {(flowRatio * 100).toFixed(0)}% flow
            </text>
          );
        })}
      </svg>

      {/* Status summary bar */}
      <div className="mt-3 flex flex-wrap items-center gap-3 border-t border-cortex-border pt-3 text-[10px] text-gray-500 font-mono">
        <span>
          Status:{" "}
          {layers
            .map((l) =>
              l.status === "healthy"
                ? "OK"
                : l.status === "degraded"
                ? "DEG"
                : "CRIT"
            )
            .join(" | ")}
        </span>
        <span className="ml-auto">
          Updated:{" "}
          {snapshot?.timestamp
            ? new Date(snapshot.timestamp).toLocaleTimeString()
            : "---"}
        </span>
      </div>

      <style jsx>{`
        @keyframes flowDash {
          to {
            stroke-dashoffset: -20;
          }
        }
        :global(.flow-dash) {
          animation: flowDash 1.2s linear infinite;
        }
      `}</style>
    </div>
  );
}
