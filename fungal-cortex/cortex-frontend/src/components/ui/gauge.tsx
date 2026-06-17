"use client";

export interface GaugeProps {
  /** Value between 0 and 100 */
  value: number;
  /** Diameter in pixels (default 120) */
  size?: number;
  /** Stroke width in pixels (default 8) */
  strokeWidth?: number;
  /** Color of the progress arc (default theme primary) */
  color?: string;
  /** Optional label displayed below the percentage */
  label?: string;
  /** Whether to show the percentage text in the center (default true) */
  showPercentage?: boolean;
  className?: string;
}

function Gauge({
  value,
  size = 120,
  strokeWidth = 8,
  color = "#00d4aa",
  label,
  showPercentage = true,
  className = "",
}: GaugeProps) {
  const clamped = Math.max(0, Math.min(100, value));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;
  const center = size / 2;
  const fontSize = size * 0.2;

  return (
    <div
      className={["inline-flex flex-col items-center gap-1.5", className].join(" ")}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        aria-hidden="true"
      >
        {/* Background track */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="#1e1e3a"
          strokeWidth={strokeWidth}
        />

        {/* Progress arc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${center} ${center})`}
          className="transition-all duration-700 ease-out"
        />

        {/* Center text */}
        {showPercentage && (
          <text
            x={center}
            y={center}
            textAnchor="middle"
            dominantBaseline="central"
            fill="white"
            fontSize={fontSize}
            fontWeight={700}
            fontFamily="ui-monospace, monospace"
          >
            {Math.round(clamped)}%
          </text>
        )}
      </svg>

      {label && (
        <span className="text-xs text-[#666688] font-medium">{label}</span>
      )}
    </div>
  );
}

export { Gauge };
