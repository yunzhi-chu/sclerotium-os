/** Perspective WASM loader — lazy-load for charts that need it. */

let perspectiveModule: unknown = null;
let loadPromise: Promise<unknown> | null = null;

export async function loadPerspective(): Promise<unknown> {
  if (perspectiveModule) return perspectiveModule;
  if (loadPromise) return loadPromise;

  loadPromise = (async () => {
    if (typeof window === "undefined") return null;
    // Dynamic import — Perspective is loaded on-demand in the browser only
    try {
      const mod = await import("@finos/perspective");
      perspectiveModule = mod.default ?? mod;
      return perspectiveModule;
    } catch {
      console.warn("Perspective not available — using fallback charts");
      return null;
    }
  })();

  return loadPromise;
}

export function isPerspectiveAvailable(): boolean {
  return perspectiveModule !== null;
}

/** Fallback: use a lightweight canvas-based table rendering when Perspective isn't loaded. */
export function createFallbackViewer(
  container: HTMLElement,
  columns: string[],
  rows: Record<string, unknown>[]
): { update: (rows: Record<string, unknown>[]) => void; destroy: () => void } {
  const table = document.createElement("table");
  table.className = "w-full text-xs font-mono border-collapse";

  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  columns.forEach((col) => {
    const th = document.createElement("th");
    th.className = "text-left p-2 border-b border-cortex-border text-cortex-primary sticky top-0 bg-cortex-surface";
    th.textContent = col;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

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
        td.textContent = String(row[col] ?? "");
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
