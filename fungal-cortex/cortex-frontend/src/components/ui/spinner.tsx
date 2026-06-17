
type SpinnerSize = "xs" | "sm" | "md" | "lg" | "xl";

export interface SpinnerProps {
  size?: SpinnerSize;
  color?: string;
  className?: string;
}

const dimensionMap: Record<SpinnerSize, number> = {
  xs: 14,
  sm: 18,
  md: 24,
  lg: 32,
  xl: 44,
};

const strokeWidthMap: Record<SpinnerSize, number> = {
  xs: 2.5,
  sm: 2.5,
  md: 3,
  lg: 3,
  xl: 3.5,
};

function Spinner({
  size = "md",
  color = "currentColor",
  className = "",
}: SpinnerProps) {
  const dim = dimensionMap[size];
  const sw = strokeWidthMap[size];

  return (
    <svg
      className={["animate-spin", className].filter(Boolean).join(" ")}
      width={dim}
      height={dim}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke={color}
        strokeWidth={sw}
        strokeLinecap="round"
        strokeDasharray="31.4 31.4"
        className="opacity-25"
      />
      <path
        d="M12 2a10 10 0 019.95 9"
        stroke={color}
        strokeWidth={sw}
        strokeLinecap="round"
      />
    </svg>
  );
}

export { Spinner };
export type { SpinnerSize };
