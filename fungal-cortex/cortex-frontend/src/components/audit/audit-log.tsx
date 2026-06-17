"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import type { AuditRecord, AuditFilter } from "@/types/audit";

/* ─── Constants ─── */
const ROW_HEIGHT = 40;

const EVENT_TYPES = [
  "signal_generated",
  "position_opened",
  "position_closed",
  "order_submitted",
  "order_filled",
  "order_cancelled",
  "error",
  "system",
  "config_change",
  "skill_invocation",
  "skill_error",
  "cycle_detected",
  "transition",
];

const SEVERITIES = ["info", "warning", "critical"] as const;

const SEVERITY_DOT: Record<string, string> = {
  info: "bg-[#3b82f6]",
  warning: "bg-[#f59e0b]",
  critical: "bg-[#ef4444]",
};

const RESULT_BADGE: Record<string, string> = {
  success: "bg-[#22c55e]/15 text-[#22c55e]",
  failure: "bg-[#ef4444]/15 text-[#ef4444]",
  pending: "bg-[#f59e0b]/15 text-[#f59e0b]",
};

/* ─── Column definition ─── */
interface ColumnDef {
  key: string;
  label: string;
  width: number;
  render: (r: AuditRecord) => React.ReactNode;
}

const COLUMNS: ColumnDef[] = [
  {
    key: "timestamp",
    label: "Timestamp",
    width: 140,
    render: (r) => (
      <span className="text-[11px] text-[#a0a0c0] font-mono">
        {new Date(r.timestamp).toLocaleString("en-US", {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })}
      </span>
    ),
  },
  {
    key: "event_type",
    label: "Event Type",
    width: 130,
    render: (r) => (
      <span className="text-xs text-white font-medium">{r.event_type.replace(/_/g, " ")}</span>
    ),
  },
  {
    key: "source_module",
    label: "Source",
    width: 110,
    render: (r) => <span className="text-xs text-[#a0a0c0]">{r.source_module}</span>,
  },
  {
    key: "source_agent_id",
    label: "Agent ID",
    width: 100,
    render: (r) => (
      <span className="text-xs text-[#a0a0c0] font-mono">{r.source_agent_id ?? "-"}</span>
    ),
  },
  {
    key: "operation",
    label: "Operation",
    width: 130,
    render: (r) => <span className="text-xs text-[#c0c0e0]">{r.operation}</span>,
  },
  {
    key: "result",
    label: "Result",
    width: 85,
    render: (r) => (
      <span
        className={`text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded ${RESULT_BADGE[r.result]}`}
      >
        {r.result}
      </span>
    ),
  },
  {
    key: "severity",
    label: "Sev",
    width: 55,
    render: (r) => (
      <span className="flex items-center gap-1">
        <span className={`inline-block w-2 h-2 rounded-full ${SEVERITY_DOT[r.severity]}`} />
        <span className="text-[10px] text-[#a0a0c0] capitalize">{r.severity}</span>
      </span>
    ),
  },
  {
    key: "evidence_hash",
    label: "Evidence",
    width: 100,
    render: (r) => (
      <span className="text-[10px] text-[#a0a0c0] font-mono" title={r.evidence_hash}>
        {r.evidence_hash.slice(0, 10)}...
      </span>
    ),
  },
];

const TOTAL_WIDTH = COLUMNS.reduce((s, c) => s + c.width, 0);

/* ─── Props ─── */
interface AuditLogProps {
  records?: AuditRecord[];
  loading?: boolean;
  onFetch?: (filter: AuditFilter) => void;
}

/* ─── Component ─── */
export function AuditLog({ records = [] }: AuditLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [filter, setFilter] = useState<AuditFilter>({
    time_start: undefined,
    time_end: undefined,
    event_types: [],
    severity: [],
    source_module: "",
  });
  const [localEventTypes, setLocalEventTypes] = useState<string[]>([]);
  const [localSeverities, setLocalSeverities] = useState<string[]>([]);

  /* Filter records */
  const filtered = useMemo(() => {
    return records.filter((r) => {
      if (localEventTypes.length > 0 && !localEventTypes.includes(r.event_type)) return false;
      if (localSeverities.length > 0 && !localSeverities.includes(r.severity)) return false;
      if (filter.time_start && r.timestamp < filter.time_start) return false;
      if (filter.time_end && r.timestamp > filter.time_end) return false;
      if (filter.source_module && !r.source_module.toLowerCase().includes(filter.source_module.toLowerCase()))
        return false;
      return true;
    });
  }, [records, filter, localEventTypes, localSeverities]);

  const virtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 8,
  });

  /* Toggle severity checkbox */
  const toggleSeverity = useCallback((sev: string) => {
    setLocalSeverities((prev) =>
      prev.includes(sev) ? prev.filter((s) => s !== sev) : [...prev, sev],
    );
  }, []);

  /* Toggle event type */
  const toggleEventType = useCallback((et: string) => {
    setLocalEventTypes((prev) =>
      prev.includes(et) ? prev.filter((e) => e !== et) : [...prev, et],
    );
  }, []);

  /* Export JSON */
  const handleExport = useCallback(() => {
    const json = JSON.stringify(filtered, null, 2);
    navigator.clipboard.writeText(json).catch(() => {
      /* clipboard not available */
    });
  }, [filtered]);

  const filterStats = {
    total: records.length,
    filtered: filtered.length,
    crit: records.filter((r) => r.severity === "critical").length,
    warn: records.filter((r) => r.severity === "warning").length,
  };

  return (
    <div className="rounded-lg border border-[#1e1e3a] bg-[#141428] overflow-hidden flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#1e1e3a]">
        <span className="text-xs font-semibold uppercase tracking-wider text-[#a0a0c0]">
          Audit Log
        </span>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-[#a0a0c0] tabular-nums">
            {filterStats.filtered} of {filterStats.total} records
            {filterStats.crit > 0 && (
              <span className="ml-1.5 text-[#ef4444]">({filterStats.crit} critical)</span>
            )}
          </span>
          <button
            onClick={handleExport}
            className="text-[10px] px-2 py-1 rounded bg-[#1e1e3a] text-[#a0a0c0] hover:text-white transition-colors"
          >
            Export JSON
          </button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3 px-3 py-2 border-b border-[#1e1e3a] flex-wrap">
        {/* Time range */}
        <div className="flex items-center gap-1.5">
          <label className="text-[9px] text-[#a0a0c0] uppercase tracking-wider">From</label>
          <input
            type="date"
            className="w-28 bg-[#0a0a0f] border border-[#1e1e3a] rounded px-1.5 py-1 text-[10px] text-white font-mono focus:outline-none focus:border-[#00d4aa]"
            onChange={(e) =>
              setFilter((f) => ({
                ...f,
                time_start: e.target.value ? new Date(e.target.value).getTime() : undefined,
              }))
            }
          />
          <label className="text-[9px] text-[#a0a0c0] uppercase tracking-wider">To</label>
          <input
            type="date"
            className="w-28 bg-[#0a0a0f] border border-[#1e1e3a] rounded px-1.5 py-1 text-[10px] text-white font-mono focus:outline-none focus:border-[#00d4aa]"
            onChange={(e) =>
              setFilter((f) => ({
                ...f,
                time_end: e.target.value
                  ? new Date(e.target.value).getTime() + 86400000
                  : undefined,
              }))
            }
          />
        </div>

        {/* Event type multi-select */}
        <div className="flex flex-wrap gap-1">
          {EVENT_TYPES.slice(0, 6).map((et) => (
            <button
              key={et}
              onClick={() => toggleEventType(et)}
              className={`text-[9px] px-1.5 py-0.5 rounded transition-colors ${
                localEventTypes.includes(et)
                  ? "bg-[#00d4aa] text-[#0a0a0f]"
                  : "bg-[#1e1e3a] text-[#a0a0c0] hover:text-white"
              }`}
            >
              {et.replace(/_/g, " ")}
            </button>
          ))}
          {localEventTypes.length > 6 && (
            <span className="text-[9px] text-[#00d4aa]">+{localEventTypes.length - 6} more</span>
          )}
        </div>

        {/* Severity checkboxes */}
        <div className="flex items-center gap-1.5">
          {SEVERITIES.map((sev) => (
            <label key={sev} className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={localSeverities.includes(sev)}
                onChange={() => toggleSeverity(sev)}
                className="w-2.5 h-2.5 accent-[#00d4aa]"
              />
              <span className="text-[9px] text-[#a0a0c0] capitalize">{sev}</span>
            </label>
          ))}
        </div>

        {/* Source module input */}
        <input
          type="text"
          placeholder="Module..."
          value={filter.source_module ?? ""}
          onChange={(e) => setFilter((f) => ({ ...f, source_module: e.target.value }))}
          className="w-24 bg-[#0a0a0f] border border-[#1e1e3a] rounded px-1.5 py-1 text-[10px] text-white placeholder-[#a0a0c0] focus:outline-none focus:border-[#00d4aa]"
        />
      </div>

      {/* Column headers */}
      <div
        className="flex border-b border-[#1e1e3a] bg-[#0a0a0f] shrink-0"
        style={{ width: TOTAL_WIDTH }}
      >
        {COLUMNS.map((col) => (
          <div
            key={col.key}
            className="shrink-0 h-8 flex items-center px-2 text-[9px] font-semibold uppercase tracking-wider text-[#a0a0c0]"
            style={{ width: col.width }}
          >
            {col.label}
          </div>
        ))}
      </div>

      {/* Virtual rows */}
      <div ref={scrollRef} className="overflow-auto" style={{ maxHeight: 420 }}>
        <div style={{ width: TOTAL_WIDTH, position: "relative", height: `${virtualizer.getTotalSize()}px` }}>
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const rec = filtered[virtualRow.index];
            const isExpanded = expandedRow === rec.id;
            return (
              <div key={rec.id}>
                <div
                  onClick={() => setExpandedRow(isExpanded ? null : rec.id)}
                  className="flex absolute inset-x-0 hover:bg-[#1a1a35] cursor-pointer border-b border-[#1e1e3a]/30 transition-colors"
                  style={{
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                  {COLUMNS.map((col) => (
                    <div
                      key={col.key}
                      className="shrink-0 flex items-center px-2 truncate"
                      style={{ width: col.width }}
                    >
                      {col.render(rec)}
                    </div>
                  ))}
                </div>

                {/* Expanded detail panel */}
                {isExpanded && (
                  <div
                    className="bg-[#0a0a0f] border-b border-[#1e1e3a] p-3"
                    style={{
                      transform: `translateY(${virtualRow.start}px)`,
                      marginTop: `${virtualRow.size}px`,
                    }}
                  >
                    <pre className="text-[10px] text-[#c0c0e0] font-mono whitespace-pre-wrap overflow-x-auto max-h-48">
                      {JSON.stringify(rec.details, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
