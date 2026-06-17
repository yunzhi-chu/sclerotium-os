/** Cognitive Pipeline — L0→L7 real-time flow visualization. */
"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusDot } from "@/components/ui/status-dot";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useWebSocket } from "@/hooks/use-websocket";
import { api } from "@/lib/api-client";
import type { LayerLevel, LayerStatus, PipelineSnapshot, DebateClaim, RiskGateStatus } from "@/types/pipeline";
import { LAYER_NAMES, LAYER_COLORS } from "@/types/pipeline";

const ALL_LEVELS: LayerLevel[] = ["L0", "L1", "L2", "L3", "L4", "L5", "L6", "L7"];

function factionColor(faction: string): string {
  switch (faction) {
    case "aggressive":  return "#ff4444";
    case "neutral":     return "#ffaa44";
    case "conservative": return "#4488ff";
    default:            return "#888888";
  }
}

export default function PipelinePage() {
  const [selectedLayer, setSelectedLayer] = useState<LayerLevel | null>(null);
  const { snapshot, debates, riskGates, setSnapshot, setDebates, setRiskGates } = usePipelineStore();

  // Fetch initial data
  useEffect(() => {
    api.getHealth().catch(() => {});
  }, []);

  // Subscribe to pipeline WebSocket
  useWebSocket("pipeline", "pipeline_snapshot", (data: unknown) => {
    const d = data as Record<string, unknown>;
    if (d.layers && Array.isArray(d.layers)) {
      const snap: PipelineSnapshot = {
        layers: (d.layers as Array<Record<string, unknown>>).map((l) => ({
          level: l.level as LayerLevel,
          name: l.name as string,
          throughput: l.throughput as number,
          latency_ms: l.latency_ms as number,
          error_rate: l.error_rate as number,
          queue_depth: l.queue_depth as number,
          agent_count: l.agent_count as number,
          status: (l.status as "healthy" | "degraded" | "critical") ?? "healthy",
        })),
        bottleneck_at: d.bottleneck_at as LayerLevel | null,
        bottleneck_score: d.bottleneck_score as number,
        total_throughput: d.total_throughput as number,
        avg_end_to_end_ms: d.avg_end_to_end_ms as number,
        timestamp: d.timestamp as number,
      };
      setSnapshot(snap);
    }
    if (d.debates && Array.isArray(d.debates)) {
      setDebates(d.debates as DebateClaim[]);
    }
    if (d.riskGates && Array.isArray(d.riskGates)) {
      setRiskGates(d.riskGates as RiskGateStatus[]);
    }
  });

  function getLayer(level: LayerLevel): LayerStatus | undefined {
    return snapshot?.layers.find((l) => l.level === level);
  }

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-bold font-mono text-cortex-primary">L0→L7 Cognitive Pipeline</h1>
        <div className="flex gap-2">
          <Badge variant="success">Throughput: {snapshot?.total_throughput?.toLocaleString() ?? "—"} t/s</Badge>
          <Badge variant="info">E2E: {snapshot?.avg_end_to_end_ms ?? "—"}ms avg</Badge>
        </div>
      </div>

      {/* Sankey-style flow */}
      <Card className="mb-4">
        <div className="flex items-center gap-0 h-40 overflow-hidden">
          {ALL_LEVELS.map((level, i) => {
            const ls = getLayer(level);
            const status = ls?.status ?? "healthy";
            const width = `${100 / ALL_LEVELS.length}%`;
            const h = status === "healthy" ? "80%" : status === "degraded" ? "50%" : "25%";
            return (
              <div key={level} className="flex-1 flex flex-col items-center gap-1 relative" style={{ width }}>
                {/* Flow arrow from previous layer */}
                {i > 0 && (
                  <div className="absolute left-0 top-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-0.5">
                    <svg width="8" height="2" className="animate-flow-right">
                      <line x1="0" y1="1" x2="8" y2="1" stroke={LAYER_COLORS[level]} strokeWidth="1" opacity="0.5" />
                    </svg>
                  </div>
                )}
                <div
                  className="w-full rounded cursor-pointer transition-all hover:opacity-80"
                  style={{ height: h, backgroundColor: LAYER_COLORS[level], opacity: status === "healthy" ? 0.9 : 0.4 }}
                  onClick={() => setSelectedLayer(level)}
                />
                <span className="text-[9px] text-gray-500 mt-1">{level}</span>
                <span className="text-[8px] text-gray-600">{LAYER_NAMES[level].split(" ")[0]}</span>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Layer detail cards */}
      <div className="grid grid-cols-4 gap-3">
        {ALL_LEVELS.map((level) => {
          const ls = getLayer(level);
          const isSelected = selectedLayer === level;
          return (
            <Card
              key={level}
              className={`cursor-pointer transition-all ${isSelected ? "ring-1 ring-cortex-primary glow-primary" : ""}`}
              onClick={() => setSelectedLayer(level)}
            >
              <div className="flex items-center gap-2 mb-2">
                <div className="w-1 h-8 rounded" style={{ backgroundColor: LAYER_COLORS[level] }} />
                <div>
                  <div className="text-xs font-mono font-bold" style={{ color: LAYER_COLORS[level] }}>{level}</div>
                  <div className="text-[10px] text-gray-500">{LAYER_NAMES[level]}</div>
                </div>
                <div className="flex-1" />
                <StatusDot color={ls?.status ?? "healthy"} />
              </div>
              <div className="grid grid-cols-2 gap-1 text-[10px]">
                <div className="text-gray-600">Throughput</div>
                <div className="text-right font-mono">{ls?.throughput?.toFixed(1) ?? "—"}/s</div>
                <div className="text-gray-600">Latency</div>
                <div className="text-right font-mono">{ls?.latency_ms ?? "—"}ms</div>
                <div className="text-gray-600">Error Rate</div>
                <div className="text-right font-mono text-red-400">{ls?.error_rate?.toFixed(1) ?? "—"}%</div>
                <div className="text-gray-600">Queue</div>
                <div className="text-right font-mono">{ls?.queue_depth ?? "—"}</div>
                <div className="text-gray-600">Agents</div>
                <div className="text-right font-mono">{ls?.agent_count ?? "—"}</div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* L3 Debate section */}
      {selectedLayer === "L3" && (
        <Card header="L3 Debate — Active Claims" className="mt-4">
          <div className="grid grid-cols-2 gap-3">
            {debates.length === 0 ? (
              <div className="col-span-2 text-xs text-gray-500 p-4">No active debates.</div>
            ) : (
              debates.map((claim) => (
                <div key={claim.id} className="p-3 rounded bg-cortex-border/30">
                  <div className="text-xs font-bold mb-1">{claim.symbol}</div>
                  <div className="text-xs text-gray-400 mb-2">{claim.thesis}</div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-green-400">BULL</span>
                    <div className="flex-1 h-2 rounded-full bg-cortex-border overflow-hidden">
                      <div className="h-full bg-green-500 transition-all" style={{ width: `${claim.bull_confidence}%` }} />
                    </div>
                    <span className="text-[10px] text-red-400">{claim.bear_confidence}%</span>
                    <span className="text-[10px] text-red-400">BEAR</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      )}

      {/* Risk gates */}
      <Card header="L6 Risk Gates (3 Factions)" className="mt-4">
        <div className="grid grid-cols-3 gap-3">
          {riskGates.length === 0 ? (
            <div className="col-span-3 text-xs text-gray-500 p-4 text-center">No risk gate data available.</div>
          ) : (
            riskGates.map((g) => (
              <div key={g.gate_id} className="p-3 rounded bg-cortex-border/20 text-center">
                <div className="text-xs font-bold mb-1" style={{ color: factionColor(g.faction) }}>{g.name}</div>
                <div className="text-[9px] text-gray-500 font-mono">{g.current_value}/{g.limit}</div>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}
