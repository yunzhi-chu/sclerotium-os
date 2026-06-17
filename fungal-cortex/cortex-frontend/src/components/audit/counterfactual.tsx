"use client";

import { useCallback, useState } from "react";
import type { CounterfactualResult } from "@/types/audit";

/* ─── Diff highlighting ─── */
function DiffValue({ original, counterfactual }: { original: unknown; counterfactual: unknown }) {
  const same = JSON.stringify(original) === JSON.stringify(counterfactual);
  return (
    <div className={`grid grid-cols-2 gap-2 rounded p-1.5 ${same ? "" : "bg-[#f59e0b]/10"}`}>
      <span className={`text-xs font-mono ${same ? "text-[#a0a0c0]" : "text-[#e2e8f0]"}`}>
        {String(original)}
      </span>
      <span className={`text-xs font-mono ${same ? "text-[#a0a0c0]" : "text-[#f59e0b]"}`}>
        {String(counterfactual)}
        {!same && <span className="ml-1 text-[#f59e0b]">&#9888;</span>}
      </span>
    </div>
  );
}

/* ─── Counterfactual history item ─── */
interface HistoryItem {
  id: string;
  eventId: string;
  scenario: Record<string, unknown>;
  confidence: number;
  timestamp: number;
}

/* ─── Variable override row ─── */
interface VarOverride {
  key: string;
  value: string;
}

/* ─── Props ─── */
interface CounterfactualProps {
  onRun?: (eventId: string, overrides: Record<string, unknown>) => Promise<CounterfactualResult>;
  result?: CounterfactualResult | null;
  loading?: boolean;
}

/* ─── Component ─── */
export function Counterfactual({ onRun, result, loading = false }: CounterfactualProps) {
  const [eventId, setEventId] = useState("");
  const [variables, setVariables] = useState<VarOverride[]>([{ key: "", value: "" }]);
  const [localResult, setLocalResult] = useState<CounterfactualResult | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const resolvedResult = result ?? localResult;

  const addVariable = useCallback(() => {
    setVariables((prev) => [...prev, { key: "", value: "" }]);
  }, []);

  const removeVariable = useCallback((idx: number) => {
    setVariables((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const updateVariable = useCallback(
    (idx: number, field: "key" | "value", val: string) => {
      setVariables((prev) =>
        prev.map((v, i) => (i === idx ? { ...v, [field]: val } : v)),
      );
    },
    [],
  );

  const handleRun = useCallback(async () => {
    setError(null);
    if (!eventId.trim()) {
      setError("Event ID is required");
      return;
    }

    const overrides: Record<string, unknown> = {};
    for (const v of variables) {
      if (v.key.trim()) {
        /* Try to parse as number */
        const num = Number(v.value);
        overrides[v.key.trim()] = isNaN(num) ? v.value : num;
      }
    }

    if (onRun) {
      try {
        const res = await onRun(eventId.trim(), overrides);
        setLocalResult(res);
        setHistory((prev) => [
          {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            eventId: eventId.trim(),
            scenario: overrides,
            confidence: res.confidence,
            timestamp: Date.now(),
          },
          ...prev.slice(0, 19),
        ]);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to run counterfactual");
      }
    } else {
      /* Simulated result for demonstration */
      const simResult: CounterfactualResult = {
        original_outcome: { signal: "buy", confidence: 0.82, expected_pnl: 1250 },
        counterfactual_outcome: { signal: "hold", confidence: 0.65, expected_pnl: 0 },
        differences: {
          signal: { original: "buy", counterfactual: "hold" },
          confidence: { original: 0.82, counterfactual: 0.65 },
          expected_pnl: { original: 1250, counterfactual: 0 },
        },
        confidence: 0.73,
      };
      setLocalResult(simResult);
      setHistory((prev) => [
        {
          id: `sim-${Date.now()}`,
          eventId: eventId.trim(),
          scenario: overrides,
          confidence: simResult.confidence,
          timestamp: Date.now(),
        },
        ...prev.slice(0, 19),
      ]);
    }
  }, [eventId, variables, onRun]);

  return (
    <div className="rounded-lg border border-[#1e1e3a] bg-[#141428] overflow-hidden flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#1e1e3a]">
        <span className="text-xs font-semibold uppercase tracking-wider text-[#a0a0c0]">
          Counterfactual Analysis
        </span>
        {resolvedResult && (
          <span className="text-[10px] text-[#a0a0c0] tabular-nums">
            Score: <span className="text-[#00d4aa] font-semibold">{(resolvedResult.confidence * 100).toFixed(0)}%</span>
          </span>
        )}
      </div>

      {/* Input form */}
      <div className="p-3 border-b border-[#1e1e3a] flex flex-col gap-2.5">
        {/* Event ID */}
        <div className="flex items-center gap-2">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-[#a0a0c0] w-20 shrink-0">
            Event ID
          </label>
          <input
            type="text"
            value={eventId}
            onChange={(e) => setEventId(e.target.value)}
            placeholder="e.g. evt_abc123"
            className="flex-1 bg-[#0a0a0f] border border-[#1e1e3a] rounded px-2 py-1.5 text-xs text-white placeholder-[#a0a0c0] focus:outline-none focus:border-[#00d4aa] font-mono"
          />
        </div>

        {/* Variable overrides */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#a0a0c0]">
              Variable Overrides
            </span>
            <button
              onClick={addVariable}
              className="text-[10px] px-2 py-0.5 rounded bg-[#1e1e3a] text-[#a0a0c0] hover:text-white transition-colors"
            >
              + Add
            </button>
          </div>
          {variables.map((v, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <input
                type="text"
                value={v.key}
                onChange={(e) => updateVariable(i, "key", e.target.value)}
                placeholder="variable"
                className="w-28 bg-[#0a0a0f] border border-[#1e1e3a] rounded px-1.5 py-1 text-[10px] text-white placeholder-[#a0a0c0] focus:outline-none focus:border-[#00d4aa] font-mono"
              />
              <span className="text-[#a0a0c0] text-[10px]">=</span>
              <input
                type="text"
                value={v.value}
                onChange={(e) => updateVariable(i, "value", e.target.value)}
                placeholder="value"
                className="flex-1 bg-[#0a0a0f] border border-[#1e1e3a] rounded px-1.5 py-1 text-[10px] text-white placeholder-[#a0a0c0] focus:outline-none focus:border-[#00d4aa] font-mono"
              />
              {variables.length > 1 && (
                <button
                  onClick={() => removeVariable(i)}
                  className="text-[#ef4444] hover:text-[#f87171] text-[12px] leading-none"
                >
                  &times;
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Run button + error */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleRun}
            disabled={loading || !eventId.trim()}
            className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider rounded bg-[#00d4aa] text-[#0a0a0f] hover:bg-[#00e8bb] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "Running..." : "Run Counterfactual"}
          </button>
          {error && <span className="text-[10px] text-[#ef4444]">{error}</span>}
        </div>
      </div>

      {/* Results */}
      {resolvedResult && (
        <div className="p-3 border-b border-[#1e1e3a] flex flex-col gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[#a0a0c0]">
            Comparison
          </span>

          {/* Column headers */}
          <div className="grid grid-cols-3 gap-2 text-[9px] font-semibold uppercase tracking-wider text-[#a0a0c0] px-1.5">
            <span>Field</span>
            <span>Original</span>
            <span>Counterfactual</span>
          </div>

          {/* Differences */}
          {Object.entries(resolvedResult.differences).map(([field, diff]) => (
            <div key={field} className="grid grid-cols-3 gap-2 items-center px-1.5">
              <span className="text-[10px] text-[#c0c0e0] font-medium">{field}</span>
              <DiffValue original={diff.original} counterfactual={diff.counterfactual} />
            </div>
          ))}

          {/* Full outcome comparison */}
          <details className="mt-1">
            <summary className="text-[10px] text-[#a0a0c0] cursor-pointer hover:text-white">
              View Full Outcomes JSON
            </summary>
            <div className="grid grid-cols-2 gap-2 mt-1">
              <div>
                <span className="text-[9px] text-[#a0a0c0] uppercase tracking-wider">Original</span>
                <pre className="text-[10px] text-[#c0c0e0] font-mono mt-0.5 whitespace-pre-wrap overflow-auto max-h-24 bg-[#0a0a0f] rounded p-1.5">
                  {JSON.stringify(resolvedResult.original_outcome, null, 2)}
                </pre>
              </div>
              <div>
                <span className="text-[9px] text-[#a0a0c0] uppercase tracking-wider">Counterfactual</span>
                <pre className="text-[10px] text-[#c0c0e0] font-mono mt-0.5 whitespace-pre-wrap overflow-auto max-h-24 bg-[#0a0a0f] rounded p-1.5">
                  {JSON.stringify(resolvedResult.counterfactual_outcome, null, 2)}
                </pre>
              </div>
            </div>
          </details>
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <div className="flex-1 overflow-auto max-h-40">
          <div className="px-3 py-1.5 border-b border-[#1e1e3a]">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#a0a0c0]">
              Recent Counterfactuals ({history.length})
            </span>
          </div>
          <div className="flex flex-col">
            {history.map((h) => (
              <div
                key={h.id}
                onClick={() => {
                  /* Click to re-run with same params */
                  setEventId(h.eventId);
                }}
                className="px-3 py-1.5 border-b border-[#1e1e3a]/30 hover:bg-[#1a1a35] cursor-pointer transition-colors flex items-center justify-between"
              >
                <div className="flex flex-col gap-0.5">
                  <span className="text-[10px] text-white font-mono">{h.eventId}</span>
                  <span className="text-[9px] text-[#a0a0c0]">
                    {Object.keys(h.scenario).join(", ") || "no overrides"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-[#00d4aa] font-semibold">
                    {(h.confidence * 100).toFixed(0)}%
                  </span>
                  <span className="text-[9px] text-[#a0a0c0] font-mono">
                    {new Date(h.timestamp).toLocaleTimeString("en-US", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
