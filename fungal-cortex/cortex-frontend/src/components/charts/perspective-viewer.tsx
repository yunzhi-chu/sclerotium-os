"use client";

import {
  useRef,
  useEffect,
  useState,
  forwardRef,
  useImperativeHandle,
  type ForwardedRef,
} from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PerspectiveViewerHandle {
  /** Replace all data in the viewer with a new dataset. */
  update: (data: Record<string, unknown>[]) => void;
}

interface PerspectiveViewerProps {
  columns: string[];
  initialData: Record<string, unknown>[];
  height?: number | string;
}

// ---------------------------------------------------------------------------
// Perspective viewer
// ---------------------------------------------------------------------------

export const PerspectiveViewer = forwardRef(function PerspectiveViewer(
  { columns, initialData, height = 400 }: PerspectiveViewerProps,
  ref: ForwardedRef<PerspectiveViewerHandle>,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const fallbackRef = useRef<{
    update: (rows: Record<string, unknown>[]) => void;
    destroy: () => void;
  } | null>(null);
  const perspectiveRef = useRef<{
    worker: unknown;
    table: unknown;
    viewer: HTMLElement;
  } | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );

  // -----------------------------------------------------------------------
  // Imperative handle – external callers can .update(newData)
  // -----------------------------------------------------------------------
  useImperativeHandle(
    ref,
    () => ({
      update: (data: Record<string, unknown>[]) => {
        if (perspectiveRef.current) {
          // Perspective table replace
          const table = perspectiveRef.current.table as {
            replace?: (data: unknown) => Promise<void>;
            update?: (data: unknown) => Promise<void>;
            delete?: () => Promise<void>;
          };
          if (table.replace) {
            table.replace(data).catch(() => {
              /* fallback below */
            });
            return;
          }
        }
        // Fallback
        if (fallbackRef.current) {
          fallbackRef.current.update(data);
        }
      },
    }),
    [],
  );

  // -----------------------------------------------------------------------
  // Dynamic load: try Perspective, fall back to DOM table
  // -----------------------------------------------------------------------
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let cancelled = false;

    async function init() {
      const el = containerRef.current;
      if (!el) return;

      // 1. Clear container
      el.innerHTML = "";

      // 2. Try Perspective
      try {
        const mod = await import("@finos/perspective");

        if (cancelled) return;

        const perspective = mod.default ?? mod;
        const worker = perspective.worker?.();
        const table = worker?.table?.(
          columns.reduce(
            (acc, col) => {
              acc[col] = "string";
              return acc;
            },
            {} as Record<string, string>,
          ),
        );

        if (table && table.update) {
          await table.update(initialData);

          // Create the Perspective viewer element
          const viewer = document.createElement(
            "perspective-viewer",
          ) as unknown as HTMLElement & {
            load?: (data: unknown) => Promise<void>;
            setAttribute: (k: string, v: string) => void;
          };

          // Dark theme attributes
          viewer.setAttribute("theme", "Pro Dark");
          viewer.setAttribute("columns", JSON.stringify(columns));
          viewer.style.width = "100%";
          viewer.style.height = "100%";
          el.appendChild(viewer);

          if (viewer.load) {
            await viewer.load(table);
          }

          perspectiveRef.current = { worker, table, viewer };
          if (!cancelled) setStatus("ready");
          return;
        }
      } catch {
        // Perspective not available – fall through to fallback
      }

      if (cancelled) return;

      // 3. Fallback DOM table
      setStatus("ready");
      fallbackRef.current = createFallbackViewer(
        el,
        columns,
        initialData,
      );
    }

    init().catch(() => {
      if (!cancelled) {
        setStatus("error");
      }
    });

    return () => {
      cancelled = true;
      if (perspectiveRef.current) {
        const { table } = perspectiveRef.current;
        (table as { delete?: () => Promise<void> }).delete?.().catch(() => {});
      }
      if (fallbackRef.current) {
        fallbackRef.current.destroy();
      }
      perspectiveRef.current = null;
      fallbackRef.current = null;
    };
    // Only run on mount; columns/initialData changes are handled via .update()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  const resolvedHeight = typeof height === "number" ? `${height}px` : height;

  return (
    <div
      style={{ height: resolvedHeight, position: "relative", overflow: "auto" }}
      className="rounded-lg border border-cortex-border bg-cortex-surface"
    >
      {/* Loading spinner */}
      {status === "loading" && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexDirection: "column",
            gap: 12,
          }}
        >
          <svg
            width={32}
            height={32}
            viewBox="0 0 24 24"
            fill="none"
            style={{ animation: "spin 0.8s linear infinite" }}
          >
            <circle
              cx={12}
              cy={12}
              r={10}
              stroke="currentColor"
              strokeWidth={2}
              opacity={0.2}
            />
            <path
              d="M12 2a10 10 0 0 1 10 10"
              stroke="#00d4aa"
              strokeWidth={2}
              strokeLinecap="round"
            />
            <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
          </svg>
          <span className="text-xs text-cortex-primary/60 font-mono">
            Loading viewer...
          </span>
        </div>
      )}

      {/* Error state */}
      {status === "error" && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span className="text-xs text-cortex-danger font-mono">
            Failed to load viewer.
          </span>
        </div>
      )}

      {/* Viewer container */}
      <div
        ref={containerRef}
        style={{ width: "100%", height: "100%", display: status === "ready" ? "block" : "none" }}
      />
    </div>
  );
});

// ---------------------------------------------------------------------------
// Fallback: lightweight DOM table when Perspective is not available
// ---------------------------------------------------------------------------

function createFallbackViewer(
  container: HTMLElement,
  columns: string[],
  rows: Record<string, unknown>[],
): { update: (rows: Record<string, unknown>[]) => void; destroy: () => void } {
  const table = document.createElement("table");
  table.className = "w-full text-xs font-mono border-collapse";

  // Header
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  columns.forEach((col) => {
    const th = document.createElement("th");
    th.className =
      "text-left p-2 border-b border-cortex-border text-cortex-primary sticky top-0 bg-cortex-surface";
    th.textContent = col;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  // Body
  const tbody = document.createElement("tbody");
  table.appendChild(tbody);
  container.appendChild(table);

  function renderRows(data: Record<string, unknown>[]): void {
    tbody.innerHTML = "";
    data.forEach((row) => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-cortex-border/30";
      columns.forEach((col) => {
        const td = document.createElement("td");
        td.className = "p-2 border-b border-cortex-border/50";
        const val = row[col];
        if (typeof val === "number") {
          td.style.color = val >= 0 ? "#22c55e" : "#ef4444";
          td.style.fontVariantNumeric = "tabular-nums";
        }
        td.textContent = String(val ?? "");
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }

  renderRows(rows);

  return {
    update: (newRows) => renderRows(newRows),
    destroy: () => {
      container.removeChild(table);
    },
  };
}
