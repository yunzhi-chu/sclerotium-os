
type StatusDotColor = "healthy" | "degraded" | "critical" | "inactive";

export interface StatusDotProps {
  color?: StatusDotColor;
  pulse?: boolean;
  className?: string;
}

const colorMap: Record<StatusDotColor, string> = {
  healthy: "#22c55e",
  degraded: "#f59e0b",
  critical: "#ef4444",
  inactive: "#666688",
};

function StatusDot({
  color = "inactive",
  pulse = false,
  className = "",
}: StatusDotProps) {
  const fill = colorMap[color];

  return (
    <span
      className={[
        "inline-flex items-center justify-center relative",
        className,
      ].join(" ")}
      aria-label={`Status: ${color}`}
    >
      {/* Base dot */}
      <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
        <circle cx="5" cy="5" r="4" fill={fill} />
      </svg>

      {/* Pulse ring */}
      {pulse && (
        <svg
          className="absolute inset-0"
          width="10"
          height="10"
          viewBox="0 0 10 10"
          aria-hidden="true"
          style={{
            animation: "sd-pulse 1.8s ease-in-out infinite",
          }}
        >
          <circle cx="5" cy="5" r="4" fill="none" stroke={fill} strokeWidth="1" />
        </svg>
      )}

      {pulse && (
        <style>{`
          @keyframes sd-pulse {
            0%, 100% { opacity: 0.6; transform: scale(1); }
            50% { opacity: 0; transform: scale(2); }
          }
        `}</style>
      )}
    </span>
  );
}

export { StatusDot };
export type { StatusDotColor };
