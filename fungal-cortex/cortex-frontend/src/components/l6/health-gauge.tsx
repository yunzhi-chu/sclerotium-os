"use client";

import { useMemo } from "react";
import { useL6Store } from "@/stores/l6-store";

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function describeArc(
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number,
  sweep: number
): string {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArc = Math.abs(endAngle - startAngle) > 180 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} ${sweep} ${end.x} ${end.y}`;
}

function getHealthColor(score: number): string {
  if (score >= 70) return "#22c55e";
  if (score >= 40) return "#f59e0b";
  return "#ef4444";
}

function getHealthLabel(score: number): string {
  if (score >= 70) return "GOOD";
  if (score >= 40) return "WARNING";
  return "CRITICAL";
}

function getHealthLabelColor(score: number): string {
  if (score >= 70) return "#22c55e";
  if (score >= 40) return "#f59e0b";
  return "#ef4444";
}

interface StatBlockProps {
  label: string;
  value: number;
  color: string;
}

function StatBlock({ label, value, color }: StatBlockProps) {
  return (
    <div className="flex flex-col items-center">
      <span className="text-lg font-mono font-bold" style={{ color }}>
        {value}
      </span>
      <span className="text-[9px] text-gray-500 mt-0.5 whitespace-nowrap">{label}</span>
    </div>
  );
}

export default function HealthGauge() {
  const health = useL6Store((s) => s.health);

  const score = health?.health_score ?? 0;
  const openCritical = health?.open_critical ?? 0;
  const openHigh = health?.open_high ?? 0;
  const pendingApprovals = health?.pending_approvals ?? 0;

  const color = getHealthColor(score);
  const label = getHealthLabel(score);
  const labelColor = getHealthLabelColor(score);

  // Gauge arc parameters
  const cx = 140;
  const cy = 145;
  const r = 100;
  const startAngle = 135;
  const totalSweep = 270;
  const currentAngle = startAngle + (score / 100) * totalSweep;

  // Determine which color zones to show
  const redEnd = startAngle + (40 / 100) * totalSweep;
  const yellowEnd = startAngle + (70 / 100) * totalSweep;

  const normalizeAngle = (a: number) => (a > 360 ? a - 360 : a);

  const arcTrack = useMemo(
    () => describeArc(cx, cy, r, startAngle, normalizeAngle(startAngle + totalSweep), 1),
    []
  );

  const arcRed = useMemo(
    () => describeArc(cx, cy, r, startAngle, normalizeAngle(Math.min(currentAngle, redEnd)), 1),
    [score]
  );

  const arcYellow = useMemo(
    () =>
      currentAngle > redEnd
        ? describeArc(
            cx,
            cy,
            r,
            normalizeAngle(redEnd),
            normalizeAngle(Math.min(currentAngle, yellowEnd)),
            1
          )
        : "",
    [score]
  );

  const arcGreen = useMemo(
    () =>
      currentAngle > yellowEnd
        ? describeArc(
            cx,
            cy,
            r,
            normalizeAngle(yellowEnd),
            normalizeAngle(Math.min(currentAngle, startAngle + totalSweep)),
            1
          )
        : "",
    [score]
  );

  return (
    <div className="rounded-xl border border-cortex-border bg-cortex-surface p-4">
      <div className="text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wider">
        L6 System Health
      </div>

      {/* SVG Gauge */}
      <div className="relative flex justify-center">
        <svg viewBox="0 0 280 220" className="w-full max-w-[280px] h-auto">
          {/* Background track */}
          <path
            d={arcTrack}
            fill="none"
            stroke="#1e1e3a"
            strokeWidth="14"
            strokeLinecap="round"
          />

          {/* Red zone (0-40) */}
          {arcRed && score > 0 && (
            <path
              d={arcRed}
              fill="none"
              stroke="#ef4444"
              strokeWidth="14"
              strokeLinecap="round"
              className="gauge-fill"
              style={{ transition: "d 0.6s ease-out" }}
            />
          )}

          {/* Yellow zone (40-70) */}
          {arcYellow && (
            <path
              d={arcYellow}
              fill="none"
              stroke="#f59e0b"
              strokeWidth="14"
              strokeLinecap="round"
              className="gauge-fill"
              style={{ transition: "d 0.6s ease-out" }}
            />
          )}

          {/* Green zone (70-100) */}
          {arcGreen && (
            <path
              d={arcGreen}
              fill="none"
              stroke="#22c55e"
              strokeWidth="14"
              strokeLinecap="round"
              className="gauge-fill"
              style={{ transition: "d 0.6s ease-out" }}
            />
          )}

          {/* Inner circle mask */}
          <circle cx={cx} cy={cy} r={r - 10} fill="#141428" />

          {/* Center text: score */}
          <text
            x={cx}
            y={cy - 3}
            textAnchor="middle"
            fill={color}
            fontSize="42"
            fontWeight="800"
            fontFamily="monospace"
            className="gauge-text"
            style={{ transition: "fill 0.6s ease-out" }}
          >
            {score}
          </text>

          {/* /100 label */}
          <text
            x={cx}
            y={cy + 18}
            textAnchor="middle"
            fill="#666"
            fontSize="13"
            fontFamily="sans-serif"
          >
            / 100
          </text>

          {/* Status label */}
          <text
            x={cx}
            y={cy + 40}
            textAnchor="middle"
            fill={labelColor}
            fontSize="16"
            fontWeight="700"
            fontFamily="monospace"
            className="gauge-text"
            style={{ transition: "fill 0.6s ease-out" }}
          >
            {label}
          </text>

          {/* Tick marks along arc */}
          {[0, 25, 50, 75, 100].map((val) => {
            const angle = startAngle + (val / 100) * totalSweep;
            const normAngle = angle > 360 ? angle - 360 : angle;
            const outer = polarToCartesian(cx, cy, r + 8, normAngle);
            const inner = polarToCartesian(cx, cy, r + 16, normAngle);
            const tickColor =
              val <= 40 ? "#ef4444" : val <= 70 ? "#f59e0b" : "#22c55e";
            return (
              <g key={`tick-${val}`}>
                <line
                  x1={outer.x}
                  y1={outer.y}
                  x2={inner.x}
                  y2={inner.y}
                  stroke={tickColor}
                  strokeWidth="1.5"
                  opacity="0.6"
                />
                <text
                  x={inner.x}
                  y={inner.y + (normAngle > 180 && normAngle < 360 ? 0 : 4)}
                  textAnchor="middle"
                  fill="#555"
                  fontSize="8"
                  fontFamily="monospace"
                  dy={normAngle > 180 && normAngle < 360 ? 12 : -4}
                >
                  {val}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Mini stats below */}
      <div className="flex items-center justify-around mt-3 pt-3 border-t border-cortex-border">
        <StatBlock label="Open Critical" value={openCritical} color="#ef4444" />
        <StatBlock label="Open High" value={openHigh} color="#f59e0b" />
        <StatBlock
          label="Pending Approvals"
          value={pendingApprovals}
          color="#3b82f6"
        />
      </div>

      <style jsx>{`
        @keyframes gaugeFill {
          from {
            stroke-dashoffset: 0;
          }
        }
      `}</style>
    </div>
  );
}
