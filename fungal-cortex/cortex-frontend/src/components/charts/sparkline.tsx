"use client";

import { useMemo, memo } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SparklineProps {
  /** Data series to plot */
  data: number[];
  /** SVG width */
  width?: number;
  /** SVG height */
  height?: number;
  /** Line color */
  color?: string;
  /** Show a highlight dot at the last data point */
  showDot?: boolean;
}

// ---------------------------------------------------------------------------
// Smooth polyline helper
// ---------------------------------------------------------------------------

/**
 * Generate an SVG path string for a smooth polyline using catmull-rom to
 * cubic-bezier conversion.  Produces a natural-looking curve through all
 * points without sharp corners.
 */
function smoothPath(points: { x: number; y: number }[]): string {
  if (points.length === 0) return "";
  if (points.length === 1) {
    return `M ${points[0].x},${points[0].y}`;
  }

  let d = `M ${points[0].x},${points[0].y}`;

  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(0, i - 1)];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[Math.min(points.length - 1, i + 2)];

    const tension = 0.3;
    const cp1x = p1.x + (p2.x - p0.x) * tension;
    const cp1y = p1.y + (p2.y - p0.y) * tension;
    const cp2x = p2.x - (p3.x - p1.x) * tension;
    const cp2y = p2.y - (p3.y - p1.y) * tension;

    d += ` C ${cp1x},${cp1y} ${cp2x},${cp2y} ${p2.x},${p2.y}`;
  }

  return d;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const Sparkline = memo(function Sparkline({
  data,
  width = 80,
  height = 24,
  color = "#00d4aa",
  showDot = false,
}: SparklineProps) {
  const points = useMemo(() => {
    if (data.length === 0) return [];

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const pad = 1;

    return data.map((value, i) => ({
      x: pad + (i / Math.max(data.length - 1, 1)) * (width - pad * 2),
      y: height - pad - ((value - min) / range) * (height - pad * 2),
    }));
  }, [data, width, height]);

  const linePath = useMemo(() => smoothPath(points), [points]);

  // Gradient fill: area below the line
  const fillPath = useMemo(() => {
    if (points.length < 2) return "";
    const bottom = height;
    return `${linePath} L ${points[points.length - 1].x},${bottom} L ${points[0].x},${bottom} Z`;
  }, [linePath, points, height]);

  const gradientId = useMemo(
    () => `sparkline-grad-${color.replace("#", "")}`,
    [color],
  );

  if (data.length === 0) {
    return (
      <svg width={width} height={height}>
        <rect
          x={0}
          y={0}
          width={width}
          height={height}
          fill="none"
          stroke="#1e1e3a"
          strokeWidth={1}
          rx={2}
        />
      </svg>
    );
  }

  return (
    <svg width={width} height={height}>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.3} />
          <stop offset="100%" stopColor={color} stopOpacity={0.02} />
        </linearGradient>
      </defs>

      {/* Area fill */}
      {fillPath && (
        <path d={fillPath} fill={`url(#${gradientId})`} />
      )}

      {/* Line */}
      {linePath && (
        <path
          d={linePath}
          fill="none"
          stroke={color}
          strokeWidth={1.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}

      {/* End dot */}
      {showDot && points.length > 0 && (
        <circle
          cx={points[points.length - 1].x}
          cy={points[points.length - 1].y}
          r={2.5}
          fill={color}
          stroke="#0a0a0f"
          strokeWidth={1}
        />
      )}
    </svg>
  );
});

export type { SparklineProps };
export { Sparkline };
