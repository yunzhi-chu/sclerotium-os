"use client";

import { useEffect, useCallback, type ReactNode } from "react";
import { createPortal } from "react-dom";

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children?: ReactNode;
  actions?: ReactNode;
  /** Optional className to override container styles */
  className?: string;
}

function Modal({
  open,
  onClose,
  title,
  children,
  actions,
  className = "",
}: ModalProps) {
  const handleEscape = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (open) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [open, handleEscape]);

  if (!open) return null;

  const modal = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        className={[
          "relative z-10 w-full max-w-md rounded-xl border border-[#1e1e3a] bg-[#141428] shadow-2xl",
          "translate-y-0 opacity-100 transition-all duration-200 ease-out",
          className,
        ].join(" ")}
      >
        {/* Header */}
        {title && (
          <div className="flex items-center justify-between border-b border-[#1e1e3a] px-5 py-4">
            <h2 className="text-base font-semibold text-white">{title}</h2>
            <button
              type="button"
              onClick={onClose}
              className="flex size-7 items-center justify-center rounded-md text-[#666688] transition-colors hover:bg-[#1e1e3a] hover:text-white"
              aria-label="Close"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        )}

        {/* Body */}
        {children && <div className="px-5 py-4">{children}</div>}

        {/* Footer */}
        {actions && (
          <div className="flex items-center justify-end gap-3 border-t border-[#1e1e3a] px-5 py-4">
            {actions}
          </div>
        )}
      </div>
    </div>
  );

  if (typeof window === "undefined") return null;

  return createPortal(modal, document.body);
}

export { Modal };
