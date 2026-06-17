/** Audit Trail — full-chain audit log + causal trace + counterfactual. */
"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuditStore } from "@/stores/audit-store";
import { useWebSocket } from "@/hooks/use-websocket";
import { api } from "@/lib/api-client";
import type { AuditRecord, CausalTrace, CausalEdge } from "@/types/audit";

export default function AuditPage() {
  const [activeTab, setActiveTab] = useState<"log" | "trace" | "counterfactual">("log");
  const [selectedEvent, setSelectedEvent] = useState<AuditRecord | null>(null);
  const [filterType, setFilterType] = useState<string>("");

  const {
    auditLogs, causalTrace, counterfactualResult,
    setAuditLogs, setCausalTrace, setCounterfactualResult, setStats,
  } = useAuditStore();

  // Fetch initial data
  useEffect(() => {
    api.getAudit().then((raw) => {
      const mapped = (Array.isArray(raw) ? raw : []).map(
        (r, i) =>
          ({
            id: (r.id as string) ?? `audit-${1000 + i}`,
            timestamp: (r.timestamp as number) ?? Date.now() - i * 60000,
            event_type: (r.event_type as string) ?? "signal",
            source_module: (r.source_module as string) ?? "pipeline",
            source_agent_id: (r.source_agent_id as string) ?? "",
            operation: (r.operation as string) ?? "execute",
            result: (r.result as "success" | "failure" | "pending") ?? "success",
            evidence_hash: (r.evidence_hash as string) ?? "",
            details: (r.details as Record<string, unknown>) ?? {},
            severity: (r.severity as "info" | "warning" | "critical") ?? "info",
          }) as AuditRecord,
      );
      setAuditLogs(mapped);
      // Derive stats from fetched data
      setStats({
        total_events: mapped.length,
        by_type: {},
        by_severity: {},
        by_module: {},
        recent_critical: mapped.filter((a) => a.severity === "critical").length,
      });
    }).catch(() => {});
    // Fetch causal trace for first audit record as preview
    api.getAudit({ limit: "5" }).then((raw) => {
      const logs = Array.isArray(raw) ? raw : [];
      if (logs.length > 0) {
        const firstId = (logs[0] as Record<string, unknown>).id as string;
        if (firstId) {
          api.getCausalTrace(firstId).then((traceRaw) => {
            if (traceRaw && typeof traceRaw === "object") {
              setCausalTrace(traceRaw as unknown as CausalTrace);
            }
          }).catch(() => {});
        }
      }
    }).catch(() => {});
  }, [setAuditLogs, setCausalTrace, setStats]);

  // Subscribe to audit WebSocket
  useWebSocket("audit", "audit", (data: unknown) => {
    const d = data as Record<string, unknown>;
    if (d.logs && Array.isArray(d.logs)) {
      const mapped: AuditRecord[] = (d.logs as Array<Record<string, unknown>>).map(
        (log) => ({
          id: (log.id as string) ?? "",
          timestamp: (log.timestamp as number) ?? Date.now(),
          event_type: (log.event_type as string) ?? "signal",
          source_module: (log.source_module as string) ?? "",
          source_agent_id: (log.source_agent_id as string) ?? "",
          operation: (log.operation as string) ?? "",
          result: (log.result as "success" | "failure" | "pending") ?? "success",
          evidence_hash: (log.evidence_hash as string) ?? "",
          details: (log.details as Record<string, unknown>) ?? {},
          severity: (log.severity as "info" | "warning" | "critical") ?? "info",
        }),
      );
      setAuditLogs(mapped);
    }
    if (d.causal_trace && typeof d.causal_trace === "object") {
      setCausalTrace(d.causal_trace as CausalTrace);
    }
    if (d.stats && typeof d.stats === "object") {
      setStats(d.stats as {
        total_events: number;
        by_type: Record<string, number>;
        by_severity: Record<string, number>;
        by_module: Record<string, number>;
        recent_critical: number;
      });
    }
    if (d.counterfactual_result && typeof d.counterfactual_result === "object") {
      setCounterfactualResult(d.counterfactual_result as {
        original_outcome: Record<string, unknown>;
        counterfactual_outcome: Record<string, unknown>;
        differences: Record<string, { original: unknown; counterfactual: unknown }>;
        confidence: number;
      });
    }
  });

  const logs = auditLogs;
  const logsCount = logs.length;
  const criticalCount = logs.filter((a) => a.severity === "critical").length;
  const filtered = logs.filter((a) => !filterType || a.event_type === filterType);
  const trace = causalTrace;

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-bold font-mono text-cortex-primary">Audit Trail</h1>
        <div className="flex gap-2">
          <Badge variant="info">{logsCount} events</Badge>
          <Badge variant="warning">{criticalCount} critical</Badge>
        </div>
      </div>

      <div className="flex gap-1 mb-4 border-b border-cortex-border pb-2">
        {([["log", "Audit Log"], ["trace", "Causal Trace"], ["counterfactual", "Counterfactual"]] as const).map(([key, label]) => (
          <button
            key={key}
            className={`px-3 py-1 text-xs rounded-t ${activeTab === key ? "bg-cortex-border text-white" : "text-gray-500"}`}
            onClick={() => setActiveTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === "log" && (
        <div className="grid grid-cols-4 gap-4">
          {/* Filter */}
          <div className="col-span-1 space-y-2">
            <Input placeholder="Filter type..." value={filterType} onChange={(e) => setFilterType(e.target.value)} />
            <div className="text-[10px] text-gray-500 space-y-0.5">
              <div>Success: {logs.filter((a) => a.result === "success").length}</div>
              <div>Failure: {logs.filter((a) => a.result === "failure").length}</div>
              <div>Critical: {criticalCount}</div>
            </div>
            <Button variant="ghost" size="sm" onClick={() => {
              navigator.clipboard.writeText(JSON.stringify(logs, null, 2));
            }}>
              Export JSON
            </Button>
          </div>

          {/* Log table */}
          <div className="col-span-3">
            <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
              {logs.length === 0 ? (
                <div className="text-xs text-gray-500 p-8 text-center">No audit events yet. Events appear when the system processes signals, trades, or risk checks.</div>
              ) : (
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-cortex-bg">
                    <tr className="text-gray-500 border-b border-cortex-border">
                      <th className="text-left p-2 font-normal">Time</th>
                      <th className="text-left p-2 font-normal">Type</th>
                      <th className="text-left p-2 font-normal">Module</th>
                      <th className="text-left p-2 font-normal">Agent</th>
                      <th className="text-left p-2 font-normal">Operation</th>
                      <th className="text-left p-2 font-normal">Result</th>
                      <th className="text-left p-2 font-normal">Hash</th>
                      <th className="text-left p-2 font-normal">Severity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((log) => (
                      <tr
                        key={log.id}
                        className={`border-b border-cortex-border/30 cursor-pointer hover:bg-cortex-border/20 transition-colors ${
                          selectedEvent?.id === log.id ? "bg-cortex-primary/10" : ""
                        }`}
                        onClick={() => setSelectedEvent(selectedEvent?.id === log.id ? null : log)}
                      >
                        <td className="p-2 font-mono text-gray-500">{new Date(log.timestamp).toLocaleTimeString()}</td>
                        <td className="p-2"><Badge variant="default" size="sm">{log.event_type}</Badge></td>
                        <td className="p-2 text-gray-400">{log.source_module}</td>
                        <td className="p-2 font-mono text-gray-500">{log.source_agent_id ?? "—"}</td>
                        <td className="p-2 text-gray-400">{log.operation}</td>
                        <td className="p-2">
                          <Badge variant={log.result === "success" ? "success" : "danger"} size="sm">{log.result}</Badge>
                        </td>
                        <td className="p-2 font-mono text-[9px] text-gray-600">{log.evidence_hash?.slice(0, 16) ?? "—"}...</td>
                        <td className="p-2">
                          <span className={`w-2 h-2 rounded-full inline-block ${
                            log.severity === "critical" ? "bg-red-500" : log.severity === "warning" ? "bg-amber-500" : "bg-blue-500"
                          }`} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Expanded detail */}
            {selectedEvent && (
              <Card className="mt-3">
                <div className="text-xs font-bold mb-2">Event Detail: {selectedEvent.id}</div>
                <pre className="text-[10px] font-mono text-gray-400 bg-cortex-bg rounded p-3 overflow-x-auto max-h-40">
                  {JSON.stringify(selectedEvent.details, null, 2)}
                </pre>
              </Card>
            )}
          </div>
        </div>
      )}

      {activeTab === "trace" && (
        <div className="grid grid-cols-2 gap-4">
          {trace ? (
            <>
              <Card header="Causal Trace">
                <div className="flex flex-col items-center">
                  {/* Root */}
                  <div className="p-3 rounded bg-red-900/20 border border-red-900/30 text-center w-48 mb-2">
                    <div className="text-[10px] text-red-400">ROOT EVENT</div>
                    <div className="text-xs font-mono">{trace.root_event.operation}</div>
                    <div className="text-[9px] text-gray-500">{trace.root_event.event_type}</div>
                  </div>

                  {/* Upstream */}
                  <div className="text-[10px] text-gray-500 mb-1">▲ Upstream Causes</div>
                  <div className="flex gap-2 mb-4">
                    {trace.upstream.map((e) => (
                      <div key={e.id} className="p-2 rounded bg-cortex-border/30 text-center text-[10px]">
                        <div className="font-mono text-gray-300">{e.operation}</div>
                        <div className="text-gray-500">{e.event_type}</div>
                      </div>
                    ))}
                  </div>

                  {/* Downstream */}
                  <div className="text-[10px] text-gray-500 mb-1">▼ Downstream Effects</div>
                  <div className="flex gap-2">
                    {trace.downstream.map((e) => (
                      <div key={e.id} className="p-2 rounded bg-cortex-border/30 text-center text-[10px]">
                        <div className="font-mono text-gray-300">{e.operation}</div>
                        <div className="text-gray-500">{e.event_type}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>

              <Card header="Causal Edges">
                <div className="space-y-2">
                  {trace.causal_graph.map((edge: CausalEdge, i: number) => (
                    <div key={i} className="p-2 rounded bg-cortex-border/30 text-xs flex items-center gap-2">
                      <span className="font-mono text-gray-500 text-[10px]">{edge.from.slice(0, 12)}</span>
                      <span className="flex-1 text-center">
                        <Badge variant="info" size="sm">{edge.relationship}</Badge>
                        <span className="text-[10px] text-gray-500 ml-1">{(edge.confidence * 100).toFixed(0)}%</span>
                      </span>
                      <span className="font-mono text-gray-500 text-[10px]">{edge.to.slice(0, 12)}</span>
                    </div>
                  ))}
                </div>
              </Card>
            </>
          ) : (
            <div className="col-span-2 text-xs text-gray-500 p-8 text-center">
              No causal trace data available. Traces appear when events are linked through causal analysis.
            </div>
          )}
        </div>
      )}

      {activeTab === "counterfactual" && (
        <div className="grid grid-cols-2 gap-4">
          <Card header="Scenario Configuration">
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Event ID</label>
                <Input placeholder="audit-1003" />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Variable Overrides (JSON)</label>
                <textarea className="w-full bg-cortex-bg border border-cortex-border rounded px-3 py-2 text-sm text-gray-200 h-32 font-mono"
                  defaultValue='{"signal_strength": 0.2, "position_pct": 0}' />
              </div>
              <Button variant="primary">Run Counterfactual</Button>
            </div>
          </Card>

          <Card header="Results">
            {counterfactualResult ? (
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded bg-cortex-border/30">
                  <div className="text-[10px] text-gray-500 mb-2">Original Outcome</div>
                  <div className="text-xs space-y-1 font-mono">
                    {Object.entries(counterfactualResult.original_outcome ?? {}).map(([key, value]) => (
                      <div key={key}>
                        <span className="text-green-400">{key}: </span>
                        <span>{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="p-3 rounded bg-cortex-border/30">
                  <div className="text-[10px] text-gray-500 mb-2">Counterfactual</div>
                  <div className="text-xs space-y-1 font-mono">
                    {Object.entries(counterfactualResult.counterfactual_outcome ?? {}).map(([key, value]) => (
                      <div key={key}>
                        <span className="text-red-400">{key}: </span>
                        <span>{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-xs text-gray-500 p-4 text-center">
                No counterfactual results yet. Configure a scenario and run it to see results.
              </div>
            )}
            <div className="mt-3 text-center">
              <Badge variant="warning">
                Confidence: {counterfactualResult ? `${(counterfactualResult.confidence * 100).toFixed(0)}%` : "—"}
              </Badge>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
