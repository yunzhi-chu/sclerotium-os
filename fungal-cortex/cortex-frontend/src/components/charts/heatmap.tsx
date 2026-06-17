"use client";

import { useState, useMemo, memo, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface HeatmapCell {
  x: string | number;
  y: string | number;
  value: number;
}

type ColorScale = "red-green" | "blue-red" | "green-red";

interface HeatmapProps {
  /** Grid data points */
  data: HeatmapCell[];
  /** Labels for the X axis (order matters) */
  xLabels: (string | number)[];
  /** Labels for the Y axis (order matters) */
  yLabels: (string | number)[];
  /** Width in pixels */
  width: number;
  /** Height in pixels */
  height: number;
  /** Color scale scheme */
  colorScale?: ColorScale;
  /** Callback when a cell is clicked */
  onCellClick?: (cell: HeatmapCell) => void;
}

// ---------------------------------------------------------------------------
// Color interpolation
// ---------------------------------------------------------------------------

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function hexToRgb(hex: string): [number, number, number] {
  const val = parseInt(hex.replace("#", ""), 16);
  return [(val >> 16) & 255, (val >> 8) & 255, val & 255];
}

function rgbToHex(r: number, g: number, b: number): string {
  const clamp = (v: number) => Math.max(0, Math.min(255, Math.round(v)));
  return `#${[clamp(r), clamp(g), clamp(b)]
    .map((c) => c.toString(16).padStart(2, "0"))
    .join("")}`;
}

const SCALE_STOPS: Record<ColorScale, [string, string, string]> = {
  "red-green": ["#ef4444", "#fbbf24", "#22c55e"],
  "blue-red": ["#3b82f6", "#fbbf24", "#ef4444"],
  "green-red": ["#22c55e", "#fbbf24", "#ef4444"],
};

function interpolateColor(value: number, min: number, max: number, scale: ColorScale): string {
  if (max === min) return SCALE_STOPS[scale][1]; // midpoint
  const t = (value - min) / (max - min); // 0..1
  const stops = SCALE_STOPS[scale];
  const colors = stops.map(hexToRgb);

  // Three-stop interpolation: 0 -> stops[0], 0.5 -> stops[1], 1 -> stops[2]
  let r: number, g: number, b: number;
  if (t <= 0.5) {
    const t2 = t / 0.5; // 0..1 within first half
    r = lerp(colors[0][0], colors[1][0], t2);
    g = lerp(colors[0][1], colors[1][1], t2);
    b = lerp(colors[0][2], colors[1][2], t2);
  } else {
    const t2 = (t - 0.5) / 0.5; // 0..1 within second half
    r = lerp(colors[1][0], colors[2][0], t2);
    g = lerp(colors[1][1], colors[2][1], t2);
    b = lerp(colors[1][2], colors[2][2], t2);
  }

  return rgbToHex(r, g, b);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const Heatmap = memo(function Heatmap({
  data,
  xLabels,
  yLabels,
  width,
  height,
  colorScale = "red-green",
  onCellClick,
}: HeatmapProps) {
  const [tooltip, setTooltip] = useState<{
    cell: HeatmapCell;
    x: number;
    y: number;
  } | null>(null);

  // Build lookup map
  const valueMap = useMemo(() => {
    const map = new Map<string, number>();
    for (const cell of data) {
      map.set(`${cell.x}:${cell.y}`, cell.value);
    }
    return map;
  }, [data]);

  // Value range
  const { minVal, maxVal } = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    for (const cell of data) {
      if (cell.value < min) min = cell.value;
      if (cell.value > max) max = cell.value;
    }
    return { minVal: min, maxVal: max };
  }, [data]);

  const cols = xLabels.length;
  const rows = yLabels.length;

  // Layout
  const padding = { top: 4, right: 8, bottom: 28, left: 60 };
  const gridW = width - padding.left - padding.right;
  const gridH = height - padding.top - padding.bottom;
  const cellW = gridW / cols;
  const cellH = gridH / rows;

  // Y label width for alignment
  const yLabelWidth = padding.left - 8;

  const getValue = useCallback(
    (x: string | number, y: string | number): number | undefined => {
      return valueMap.get(`${x}:${y}`);
    },
    [valueMap],
  );

  const handleMouseEnter = useCallback(
    (cell: HeatmapCell, rect: DOMRect) => {
      setTooltip({
        cell,
        x: rect.left + rect.width / 2,
        y: rect.top - 4,
      });
    },
    [],
  );

  const handleMouseLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  return (
    <div style={{ position: "relative", width, height }}>
      <svg width={width} height={height}>
        {/* Background */}
        <rect x={0} y={0} width={width} height={height} fill="#0a0a0f" rx={8} />

        {/* X labels */}
        {xLabels.map((label, i) => (
          <text
            key={`xl-${i}`}
            x={padding.left + cellW * i + cellW / 2}
            y={height - 6}
            textAnchor="end"
            transform={`rotate(-35, ${padding.left + cellW * i + cellW / 2}, ${height - 6})`}
            fill="#94a3b8"
            fontSize={10}
            fontFamily="monospace"
          >
            {label}
          </text>
        ))}

        {/* Y labels */}
        {yLabels.map((label, i) => (
          <text
            key={`yl-${i}`}
            x={yLabelWidth}
            y={padding.top + cellH * i + cellH / 2 + 1}
            textAnchor="end"
            dominantBaseline="middle"
            fill="#94a3b8"
            fontSize={10}
            fontFamily="monospace"
          >
            {label}
          </text>
        ))}

        {/* Cells */}
        {yLabels.map((yLabel, ri) =>
          xLabels.map((xLabel, ci) => {
            const value = getValue(xLabel, yLabel);
            const fillColor =
              value !== undefined
                ? interpolateColor(value, minVal, maxVal, colorScale)
                : "#1e1e3a";

            const x = padding.left + cellW * ci;
            const y = padding.top + cellH * ri;

            return (
              <g key={`c-${ci}-${ri}`}>
                <rect
                  x={x + 1}
                  y={y + 1}
                  width={Math.max(0, cellW - 2)}
                  height={Math.max(0, cellH - 2)}
                  fill={fillColor}
                  rx={2}
                  opacity={value !== undefined ? 0.85 : 0.3}
                  style={{ cursor: onCellClick ? "pointer" : "default" }}
                  onClick={() => {
                    if (onCellClick && value !== undefined) {
                      onCellClick({ x: xLabel, y: yLabel, value });
                    }
                  }}
                  onMouseEnter={(e) => {
                    if (value !== undefined) {
                      const rect = (
                        e.currentTarget as SVGRectElement
                      ).getBoundingClientRect();
                      handleMouseEnter({ x: xLabel, y: yLabel, value }, rect);
                    }
                  }}
                  onMouseLeave={handleMouseLeave}
                />
                {/* Value text in cell */}
                {value !== undefined && cellW > 40 && cellH > 20 && (
                  <text
                    x={x + cellW / 2}
                    y={y + cellH / 2 + 1}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="#ffffff"
                    fontSize={Math.min(11, cellW * 0.22)}
                    fontFamily="monospace"
                    fontWeight={500}
                    opacity={0.9}
                  >
                    {formatHeatmapValue(value)}
                  </text>
                )}
              </g>
            );
          }),
        )}

        {/* Border */}
        <rect
          x={0}
          y={0}
          width={width}
          height={height}
          fill="none"
          stroke="#1e1e3a"
          strokeWidth={1}
          rx={8}
        />
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          style={{
            position: "fixed",
            left: tooltip.x,
            top: tooltip.y,
            transform: "translate(-50%, -100%)",
            background: "#141428",
            border: "1px solid #1e1e3a",
            borderRadius: 6,
            padding: "6px 10px",
            pointerEvents: "none",
            zIndex: 9999,
            whiteSpace: "nowrap",
            fontFamily: "monospace",
            fontSize: 11,
            color: "#e2e8f0",
          }}
        >
          <div>
            x: <span style={{ color: "#00d4aa" }}>{tooltip.cell.x}</span>
          </div>
          <div>
            y: <span style={{ color: "#00d4aa" }}>{tooltip.cell.y}</span>
          </div>
          <div>
            value:{" "}
            <span style={{ color: "#f59e0b" }}>
              {formatHeatmapValue(tooltip.cell.value)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatHeatmapValue(v: number): string {
  if (Number.isInteger(v)) return v.toString();
  if (Math.abs(v) >= 100) return v.toFixed(1);
  if (Math.abs(v) >= 1) return v.toFixed(2);
  return v.toFixed(4);
}

export type { HeatmapProps, ColorScale };
export { Heatmap };
