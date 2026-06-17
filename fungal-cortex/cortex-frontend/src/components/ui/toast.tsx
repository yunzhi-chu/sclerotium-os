"use client";

import {
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ToastType = "success" | "error" | "warning" | "info";

interface ToastMessage {
  id: string;
  text: string;
  type: ToastType;
}

// ---------------------------------------------------------------------------
// Event emitter (simple global pub/sub)
// ---------------------------------------------------------------------------

type Listener = (msg: ToastMessage) => void;

let listeners: Listener[] = [];

function emit(msg: ToastMessage) {
  listeners.forEach((fn) => fn(msg));
}

function subscribe(fn: Listener) {
  listeners.push(fn);
  return () => {
    listeners = listeners.filter((l) => l !== fn);
  };
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useToast() {
  const toast = useCallback((text: string, type: ToastType = "info") => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    emit({ id, text, type });
  }, []);

  return { toast };
}

// ---------------------------------------------------------------------------
// ToastContainer (renders stacked toasts)
// ---------------------------------------------------------------------------

const typeStyles: Record<ToastType, string> = {
  success: "border-l-[#22c55e] bg-[#22c55e]/10",
  error: "border-l-[#ef4444] bg-[#ef4444]/10",
  warning: "border-l-[#f59e0b] bg-[#f59e0b]/10",
  info: "border-l-[#00d4aa] bg-[#00d4aa]/10",
};

const typeIcons: Record<ToastType, ReactNode> = {
  success: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6L9 17l-5-5" />
    </svg>
  ),
  error: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  ),
  warning: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  info: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00d4aa" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  ),
};

function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const timersRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  useEffect(() => {
    const unsub = subscribe((msg) => {
      setToasts((prev) => [...prev, msg]);

      const timer = setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== msg.id));
        timersRef.current.delete(msg.id);
      }, 4000);

      timersRef.current.set(msg.id, timer);
    });

    return () => {
      unsub();
      timersRef.current.forEach((t) => clearTimeout(t));
    };
  }, []);

  const dismiss = useCallback((id: string) => {
    const timer = timersRef.current.get(id);
    if (timer) clearTimeout(timer);
    setToasts((prev) => prev.filter((t) => t.id !== id));
    timersRef.current.delete(id);
  }, []);

  if (toasts.length === 0) return null;

  const container = (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col-reverse gap-2 pointer-events-none">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={[
            "pointer-events-auto flex items-start gap-3 rounded-lg border border-[#1e1e3a] py-3 pl-3 pr-4 shadow-lg",
            "min-w-[280px] max-w-sm",
            "animate-slide-up",
            typeStyles[toast.type],
          ].join(" ")}
          role="alert"
        >
          <span className="mt-0.5 shrink-0">{typeIcons[toast.type]}</span>
          <p className="flex-1 text-sm text-[#c0c0e0]">{toast.text}</p>
          <button
            type="button"
            onClick={() => dismiss(toast.id)}
            className="shrink-0 text-[#666688] hover:text-white transition-colors"
            aria-label="Dismiss"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      ))}

      {/* Inline keyframes for slide-up animation */}
      <style>{`
        @keyframes toast-slide-up {
          from {
            opacity: 0;
            transform: translateY(16px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-slide-up {
          animation: toast-slide-up 0.25s ease-out;
        }
      `}</style>
    </div>
  );

  if (typeof window === "undefined") return null;

  return createPortal(container, document.body);
}

export { ToastContainer };
