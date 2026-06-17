import { type ReactNode } from "react";

type BadgeVariant = "default" | "success" | "warning" | "danger" | "info";
type BadgeSize = "sm" | "md";

export interface BadgeProps {
  variant?: BadgeVariant;
  size?: BadgeSize;
  dot?: boolean;
  children?: ReactNode;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  default: "bg-[#1e1e3a] text-[#a0a0c0]",
  success: "bg-[#22c55e]/15 text-[#22c55e]",
  warning: "bg-[#f59e0b]/15 text-[#f59e0b]",
  danger: "bg-[#ef4444]/15 text-[#ef4444]",
  info: "bg-[#00d4aa]/15 text-[#00d4aa]",
};

const dotColors: Record<BadgeVariant, string> = {
  default: "bg-[#666688]",
  success: "bg-[#22c55e]",
  warning: "bg-[#f59e0b]",
  danger: "bg-[#ef4444]",
  info: "bg-[#00d4aa]",
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: "px-2 py-0.5 text-[10px] gap-1",
  md: "px-2.5 py-1 text-xs gap-1.5",
};

const dotSizeClasses: Record<BadgeSize, string> = {
  sm: "size-1.5",
  md: "size-2",
};

function Badge({
  variant = "default",
  size = "sm",
  dot = false,
  children,
  className = "",
}: BadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-full font-medium leading-none",
        variantClasses[variant],
        sizeClasses[size],
        className,
      ].join(" ")}
    >
      {dot && (
        <span
          className={[
            "inline-block rounded-full shrink-0",
            dotColors[variant],
            dotSizeClasses[size],
          ].join(" ")}
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}

export { Badge };
export type { BadgeVariant, BadgeSize };
