"use client";

import { useEffect, useState, useMemo, memo } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BarItem {
  label: string;
  value: number;
  color?: string;
}

interface BarChartProps {
  /** Bar data sorted in display order (top-to-bottom for horizontal, left-to-right for vertical) */
  data: BarItem[];
  /** If true, bars run horizontally (left-to-right); otherwise vertical (bottom-to-up) */
  horizontal?: boolean;
  /** Chart height in pixels */
  height: number;
  /** Show numeric value at the end of each bar */
  showValues?: boolean;
}

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const BAR_COLORS = [
  "#00d4aa",
  "#7c3aed",
  "#3b82f6",
  "#f59e0b",
  "#22c55e",
  "#ef4444",
  "#ec4899",
  "#14b8a6",
  "#f97316",
  "#6366f1",
];

const BG = "#0a0a0f";
const BORDER = "#1e1e3a";
const TEXT = "#94a3b8";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const BarChart = memo(function BarChart({
  data,
  horizontal = false,
  height,
  showValues = true,
}: BarChartProps) {
  const [animated, setAnimated] = useState(false);

  // Trigger animation on mount
  useEffect(() => {
    const id = requestAnimationFrame(() => {
      setAnimated(true);
    });
    return () => cancelAnimationFrame(id);
  }, []);

  // Reset animation when data changes
  useEffect(() => {
    setAnimated(false);
    const id = requestAnimationFrame(() => {
      setAnimated(true);
    });
    return () => cancelAnimationFrame(id);
  }, [data]);

  // Layout dimensions
  const dimensions = useMemo(() => {
    if (data.length === 0) {
      return { width: 300, chartW: 260, chartH: height - 40, barArea: height - 40 };
    }

    if (horizontal) {
      const padding = { top: 12, right: 16, bottom: 12, left: 80 };
      const chartW = 400 - padding.left - padding.right;
      const barArea = height - padding.top - padding.bottom;
      return {
        width: 400,
        chartW,
        chartH: barArea,
        barArea,
        padding,
        barH: Math.max(12, barArea / data.length - 4),
      };
    }

    const padding = { top: 12, right: 16, bottom: 40, left: 48 };
    const chartW = 400 - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;
    return {
      width: 400,
      chartW,
      chartH,
      padding,
      barW: Math.max(8, chartW / data.length - 4),
    };
  }, [data, height, horizontal]);

  if (data.length === 0) {
    return (
      <svg width={dimensions.width} height={height}>
        <rect x={0} y={0} width={dimensions.width} height={height} fill={BG} rx={8} />
        <rect
          x={0}
          y={0}
          width={dimensions.width}
          height={height}
          fill="none"
          stroke={BORDER}
          strokeWidth={1}
          rx={8}
        />
        <text
          x={dimensions.width / 2}
          y={height / 2}
          textAnchor="middle"
          dominantBaseline="middle"
          fill={TEXT}
          fontSize={12}
          fontFamily="monospace"
        >
          No data
        </text>
      </svg>
    );
  }

  const maxVal = Math.max(...data.map((d) => Math.abs(d.value)), 1);

  return (
    <svg
      width={dimensions.width}
      height={height}
      style={{ overflow: "visible" }}
    >
      <rect x={0} y={0} width={dimensions.width} height={height} fill={BG} rx={8} />
      <rect
        x={0}
        y={0}
        width={dimensions.width}
        height={height}
        fill="none"
        stroke={BORDER}
        strokeWidth={1}
        rx={8}
      />

      {horizontal ? renderHorizontalBars() : renderVerticalBars()}
    </svg>
  );

  // -----------------------------------------------------------------------
  // Horizontal bars
  // -----------------------------------------------------------------------
  function renderHorizontalBars() {
    const { padding, chartW, barArea, barH } = dimensions as typeof dimensions & {
      padding: { top: number; right: number; bottom: number; left: number };
      barH: number;
    };

    return (
      <g>
        {data.map((item, i) => {
          const y = padding.top + (barArea / data.length) * i + 2;
          const barW = animated ? (Math.abs(item.value) / maxVal) * chartW : 0;
          const color = item.color ?? BAR_COLORS[i % BAR_COLORS.length];
          const isNeg = item.value < 0;
          const x = isNeg ? padding.left + chartW - barW : padding.left;

          return (
            <g key={`h-${i}`}>
              {/* Label */}
              <text
                x={padding.left - 6}
                y={y + barH / 2 + 1}
                textAnchor="end"
                dominantBaseline="middle"
                fill={TEXT}
                fontSize={11}
                fontFamily="monospace"
              >
                {item.label}
              </text>

              {/* Bar */}
              <rect
                x={x}
                y={y}
                width={barW}
                height={barH}
                fill={color}
                rx={2}
                opacity={0.85}
              >
                <animate
                  attributeName="width"
                  from="0"
                  to={barW}
                  dur="0.6s"
                  fill="freeze"
                  calcMode="spline"
                  keySplines="0.4 0 0.2 1"
                  keyTimes="0;1"
                />
              </rect>

              {/* Value */}
              {showValues && (
                <text
                  x={isNeg ? x - 4 : x + barW + 4}
                  y={y + barH / 2 + 1}
                  textAnchor={isNeg ? "end" : "start"}
                  dominantBaseline="middle"
                  fill={color}
                  fontSize={10}
                  fontFamily="monospace"
                  fontWeight={500}
                >
                  {formatBarValue(item.value)}
                </text>
              )}
            </g>
          );
        })}
      </g>
    );
  }

  // -----------------------------------------------------------------------
  // Vertical bars
  // -----------------------------------------------------------------------
  function renderVerticalBars() {
    const { padding, chartW, chartH, barW } = dimensions as typeof dimensions & {
      padding: { top: number; right: number; bottom: number; left: number };
      barW: number;
    };

    return (
      <g>
        {/* Baseline */}
        <line
          x1={padding.left}
          y1={padding.top + chartH}
          x2={padding.left + chartW}
          y2={padding.top + chartH}
          stroke={BORDER}
          strokeWidth={1}
        />

        {data.map((item, i) => {
          const x = padding.left + (chartW / data.length) * i + 2;
          const barH = animated ? (Math.abs(item.value) / maxVal) * chartH : 0;
          const color = item.color ?? BAR_COLORS[i % BAR_COLORS.length];
          const y = padding.top + chartH - barH;
          const isNeg = item.value < 0;
          const baselineY = padding.top + chartH;

          return (
            <g key={`v-${i}`}>
              {/* Bar */}
              <rect
                x={x}
                y={isNeg ? baselineY : y}
                width={barW}
                height={barH}
                fill={color}
                rx={1}
                opacity={0.85}
              >
                <animate
                  attributeName="height"
                  from="0"
                  to={barH}
                  dur="0.6s"
                  fill="freeze"
                  calcMode="spline"
                  keySplines="0.4 0 0.2 1"
                  keyTimes="0;1"
                />
                {isNeg && (
                  <animate
                    attributeName="y"
                    from={baselineY}
                    to={baselineY}
                    dur="0.6s"
                    fill="freeze"
                  />
                )}
              </rect>

              {/* Label */}
              <text
                x={x + barW / 2}
                y={baselineY + 14}
                textAnchor="middle"
                fill={TEXT}
                fontSize={10}
                fontFamily="monospace"
              >
                {item.label}
              </text>

              {/* Value */}
              {showValues && (
                <text
                  x={x + barW / 2}
                  y={isNeg ? baselineY + 12 : y - 4}
                  textAnchor="middle"
                  fill={color}
                  fontSize={10}
                  fontFamily="monospace"
                  fontWeight={500}
                >
                  {formatBarValue(item.value)}
                </text>
              )}
            </g>
          );
        })}
      </g>
    );
  }
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatBarValue(v: number): string {
  if (Number.isInteger(v)) return v.toString();
  if (Math.abs(v) >= 100) return v.toFixed(1);
  if (Math.abs(v) >= 1) return v.toFixed(2);
  return v.toFixed(4);
}

export type { BarChartProps, BarItem };
export { BarChart };
