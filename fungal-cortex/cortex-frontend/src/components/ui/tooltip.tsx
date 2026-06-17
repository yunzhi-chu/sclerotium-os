"use client";

import { useState, useRef, type ReactNode } from "react";

type TooltipPosition = "top" | "bottom" | "left" | "right";

export interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  position?: TooltipPosition;
  className?: string;
}

const positionClasses: Record<TooltipPosition, string> = {
  top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
  bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
  left: "right-full top-1/2 -translate-y-1/2 mr-2",
  right: "left-full top-1/2 -translate-y-1/2 ml-2",
};

const arrowClasses: Record<TooltipPosition, string> = {
  top: "top-full left-1/2 -translate-x-1/2 border-l-[#1e1e3a] border-r-[#1e1e3a] border-b-transparent border-t-[#1e1e3a]",
  bottom:
    "bottom-full left-1/2 -translate-x-1/2 border-l-[#1e1e3a] border-r-[#1e1e3a] border-t-transparent border-b-[#1e1e3a]",
  left: "left-full top-1/2 -translate-y-1/2 border-t-[#1e1e3a] border-b-[#1e1e3a] border-r-transparent border-l-[#1e1e3a]",
  right:
    "right-full top-1/2 -translate-y-1/2 border-t-[#1e1e3a] border-b-[#1e1e3a] border-l-transparent border-r-[#1e1e3a]",
};

function Tooltip({
  content,
  children,
  position = "top",
  className = "",
}: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const show = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setVisible(true);
  };

  const hide = () => {
    timeoutRef.current = setTimeout(() => setVisible(false), 80);
  };

  return (
    <span
      className={["relative inline-flex", className].join(" ")}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}

      {visible && content && (
        <span
          className={[
            "absolute z-50",
            "pointer-events-none select-none",
            "whitespace-nowrap",
            "rounded-md border border-[#1e1e3a] bg-[#141428] px-2.5 py-1.5 text-xs text-[#c0c0e0] shadow-lg",
            positionClasses[position],
          ].join(" ")}
          role="tooltip"
        >
          {content}
          {/* Arrow */}
          <span
            className={[
              "absolute size-0 border-[5px]",
              arrowClasses[position],
            ].join(" ")}
            aria-hidden="true"
          />
        </span>
      )}
    </span>
  );
}

export { Tooltip };
export type { TooltipPosition };
