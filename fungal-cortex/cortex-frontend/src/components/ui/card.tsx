import { type ReactNode } from "react";

export interface CardProps {
  children?: ReactNode;
  header?: ReactNode;
  action?: ReactNode;
  glow?: boolean;
  className?: string;
  padded?: boolean;
  onClick?: () => void;
}

function Card({
  children,
  header,
  action,
  glow = false,
  className = "",
  padded = true,
  onClick,
}: CardProps) {
  return (
    <div onClick={onClick}
      className={[
        "rounded-xl border bg-[#141428]",
        glow
          ? "border-[#00d4aa]/30 shadow-[0_0_20px_rgba(0,212,170,0.15)]"
          : "border-[#1e1e3a]",
        className,
      ].join(" ")}
    >
      {(header || action) && (
        <div className="flex items-center justify-between px-5 pt-4 pb-3">
          {header && (
            <div className="text-sm font-semibold text-white">{header}</div>
          )}
          {action && <div className="flex items-center gap-2">{action}</div>}
        </div>
      )}
      {children && (
        <div className={padded ? "px-5 pb-5" : ""}>
          {children}
        </div>
      )}
    </div>
  );
}

export { Card };
