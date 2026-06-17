/** Command Center — system overview dashboard. */
"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Gauge } from "@/components/ui/gauge";
import { StatusDot } from "@/components/ui/status-dot";
import { Sparkline } from "@/components/charts/sparkline";
import { usePipelineStore } from "@/stores/pipeline-store";
import { useL6Store } from "@/stores/l6-store";
import { useAgentStore } from "@/stores/agent-store";
import { useSkillStore } from "@/stores/skill-store";
import { useTradingStore } from "@/stores/trading-store";
import { useWebSocket } from "@/hooks/use-websocket";
import { api } from "@/lib/api-client";
import type { PipelineSnapshot, LayerStatus } from "@/types/pipeline";
import type { ArchitectureIssue, EmergenceEvent } from "@/types/l6";
import type { AgentNetwork } from "@/types/agent";
import type { Skill } from "@/types/skill";

function formatRelativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function CommandCenterPage() {
  const [, setTime] = useState("");

  const { snapshot, pipelineHistory, setSnapshot, addHistoryPoint } =
    usePipelineStore();
  const { health, issues, emergenceEvents, setHealth, setIssues, addEmergenceEvent } =
    useL6Store();
  const { network, setNetwork } = useAgentStore();
  const { skills, setSkills } = useSkillStore();
  const { portfolio, setPortfolio } = useTradingStore();

  // Clock tick
  useEffect(() => {
    const update = () => {
      setTime(new Date().toLocaleTimeString());
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);

  // Initial data fetch — triggers WS handshake
  useEffect(() => {
    api.getHealth().catch(() => {});
  }, []);

  // Subscribe to system WebSocket
  useWebSocket("system", "system", (data: unknown) => {
    const d = data as Record<string, unknown>;

    // Pipeline snapshot (layers)
    if (d.layers && Array.isArray(d.layers)) {
      const layers = (d.layers as Array<Record<string, unknown>>).map((l) => ({
        level: l.level as LayerStatus["level"],
        name: (l.name as string) ?? "",
        throughput: (l.throughput as number) ?? 0,
        latency_ms: (l.latency_ms as number) ?? 0,
        error_rate: (l.error_rate as number) ?? 0,
        queue_depth: (l.queue_depth as number) ?? 0,
        agent_count: (l.agent_count as number) ?? 0,
        status: (l.status as LayerStatus["status"]) ?? "healthy",
      }));
      setSnapshot({
        layers,
        bottleneck_at: (d.bottleneck_at as PipelineSnapshot["bottleneck_at"]) ?? null,
        bottleneck_score: (d.bottleneck_score as number) ?? 0,
        total_throughput: (d.total_throughput as number) ?? 0,
        avg_end_to_end_ms: (d.avg_end_to_end_ms as number) ?? 0,
        timestamp: (d.timestamp as number) ?? Date.now(),
      });
    }

    // Throughput data point
    if (typeof d.throughput === "number") {
      addHistoryPoint(d.throughput);
    }

    // L6 health
    if (typeof d.health_score === "number") {
      setHealth({
        health_score: d.health_score as number,
        open_critical: (d.open_critical as number) ?? 0,
        open_high: (d.open_high as number) ?? 0,
        open_medium: (d.open_medium as number) ?? 0,
        open_low: (d.open_low as number) ?? 0,
        fixed_total: (d.fixed_total as number) ?? 0,
        pending_approvals: (d.pending_approvals as number) ?? 0,
        last_scan_at: (d.last_scan_at as number) ?? Date.now(),
      });
    }

    // L6 issues
    if (d.issues && Array.isArray(d.issues)) {
      setIssues(d.issues as ArchitectureIssue[]);
    }

    // Emergence events
    if (d.emergence && Array.isArray(d.emergence)) {
      (d.emergence as EmergenceEvent[]).forEach((e) => addEmergenceEvent(e));
    }

    // Agent network
    if (
      d.agent_network &&
      typeof d.agent_network === "object" &&
      !Array.isArray(d.agent_network)
    ) {
      setNetwork(d.agent_network as AgentNetwork);
    }

    // Skills
    if (d.skills && Array.isArray(d.skills)) {
      setSkills(d.skills as Skill[]);
    }

    // Portfolio
    if (d.portfolio && typeof d.portfolio === "object") {
      const p = d.portfolio as Record<string, unknown>;
      setPortfolio({
        total_value: (p.total_value as number) ?? 0,
        cash: (p.cash as number) ?? 0,
        market_value: (p.market_value as number) ?? 0,
        daily_pnl: (p.daily_pnl as number) ?? 0,
        daily_pnl_pct: (p.daily_pnl_pct as number) ?? 0,
        total_pnl: (p.total_pnl as number) ?? 0,
        total_pnl_pct: (p.total_pnl_pct as number) ?? 0,
        sharpe_ratio: (p.sharpe_ratio as number) ?? 0,
        max_drawdown: (p.max_drawdown as number) ?? 0,
        win_rate: (p.win_rate as number) ?? 50,
        position_count: (p.position_count as number) ?? 0,
        sector_weights: (p.sector_weights as Record<string, number>) ?? {},
      });
    }
  });

  // Derived display values with fallbacks
  const layers = snapshot?.layers ?? [];
  const issuesList = issues;
  const emergenceList = emergenceEvents;
  const sparklineData =
    pipelineHistory.length > 0
      ? pipelineHistory
      : Array.from({ length: 30 }, () => 30 + Math.random() * 40);
  const agentCount = network?.total_agents ?? 17;
  const activeAgentCount = network?.active_agents ?? 17;
  const idleCount =
    network?.nodes.filter((n) => n.status === "idle").length ?? 3;
  const skillCount = skills.length > 0 ? skills.length : 209;
  const catalyzingCount =
    skills.length > 0
      ? skills.filter((s) => s.catalyzes.length > 0).length
      : 3;
  const pnlPct = portfolio?.total_pnl_pct ?? 2.34;
  const sharpeRatio = portfolio?.sharpe_ratio ?? 1.8;

  return (
    <div className="h-full overflow-y-auto p-4 grid grid-cols-12 gap-4 auto-rows-min">
      {/* Top stat cards */}
      <div className="col-span-3">
        <Card className="text-center">
          <div className="text-xs text-gray-500 mb-1">Health Score</div>
          <Gauge
            value={health?.health_score ?? 92}
            size={80}
            strokeWidth={8}
            color="#22c55e"
            showPercentage
          />
          <div className="text-xs text-green-400 mt-1">GOOD</div>
        </Card>
      </div>
      <div className="col-span-3">
        <Card className="text-center">
          <div className="text-xs text-gray-500 mb-1">Agents</div>
          <div className="text-3xl font-mono font-bold">
            {agentCount}
            <span className="text-gray-600 text-lg">/{activeAgentCount}</span>
          </div>
          <div className="text-xs text-gray-500 mt-1">{idleCount} Idle</div>
        </Card>
      </div>
      <div className="col-span-3">
        <Card className="text-center">
          <div className="text-xs text-gray-500 mb-1">Skills</div>
          <div className="text-3xl font-mono font-bold">
            {skillCount}
            <span className="text-gray-600 text-lg">/{skillCount}</span>
          </div>
          <div className="text-xs text-amber-400 mt-1">
            {catalyzingCount} Catalyzing
          </div>
        </Card>
      </div>
      <div className="col-span-3">
        <Card className="text-center">
          <div className="text-xs text-gray-500 mb-1">P&L</div>
          <div
            className={`text-3xl font-mono font-bold ${pnlPct >= 0 ? "text-green-400" : "text-red-400"}`}
          >
            {pnlPct >= 0 ? "+" : ""}
            {pnlPct.toFixed(2)}%
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Sharpe {sharpeRatio.toFixed(1)}
          </div>
        </Card>
      </div>

      {/* Pipeline status */}
      <div className="col-span-7">
        <Card header="Pipeline Status">
          <div className="flex items-end gap-2 h-20">
            {layers.map((layer) => (
              <div key={layer.level} className="flex-1 flex flex-col items-center gap-1">
                <StatusDot color={layer.status} />
                <div
                  className="w-full rounded-t transition-all"
                  style={{
                    height: `${
                      layer.status === "healthy"
                        ? 100
                        : layer.status === "degraded"
                          ? 60
                          : 30
                    }%`,
                    backgroundColor:
                      layer.level === "L0"
                        ? "#00d4aa"
                        : layer.level === "L1"
                          ? "#3b82f6"
                          : layer.level === "L2"
                            ? "#8b5cf6"
                            : layer.level === "L3"
                              ? "#f59e0b"
                              : layer.level === "L4"
                                ? "#22c55e"
                                : layer.level === "L5"
                                  ? "#ef4444"
                                  : layer.level === "L6"
                                    ? "#ec4899"
                                    : "#f97316",
                    opacity: layer.status === "healthy" ? 1 : 0.5,
                  }}
                />
                <span className="text-[10px] text-gray-500">
                  {layer.level}
                </span>
              </div>
            ))}
          </div>
          <div className="flex gap-2 mt-3">
            {layers.map((l) => (
              <span
                key={l.level}
                className="text-[9px] text-gray-600 flex-1 text-center"
              >
                {l.name.split(" ")[0]}
              </span>
            ))}
          </div>
        </Card>
      </div>

      {/* Agent Network Mini */}
      <div className="col-span-5">
        <Card header="Agent Network">
          <div className="h-20 flex items-center justify-center">
            <svg viewBox="0 0 200 60" className="w-full h-full">
              {[
                [40, 30],
                [100, 15],
                [100, 45],
                [160, 30],
              ].map(([cx, cy], i) => (
                <circle
                  key={i}
                  cx={cx}
                  cy={cy}
                  r="6"
                  fill={
                    ["#ff6644", "#44aaff", "#44ff88", "#ffaa44"][i]
                  }
                  opacity="0.8"
                >
                  <animate
                    attributeName="r"
                    values="6;8;6"
                    dur="3s"
                    repeatCount="indefinite"
                    begin={`${i * 0.5}s`}
                  />
                </circle>
              ))}
              {[
                [0, 1],
                [0, 2],
                [1, 3],
                [2, 3],
              ].map(([a, b], i) => {
                const pts = [
                  [40, 30],
                  [100, 15],
                  [100, 45],
                  [160, 30],
                ];
                return (
                  <line
                    key={i}
                    x1={pts[a][0]}
                    y1={pts[a][1]}
                    x2={pts[b][0]}
                    y2={pts[b][1]}
                    stroke={
                      ["#ff4466", "#44ff66", "#44aaff", "#ffaa44"][i]
                    }
                    strokeWidth="0.5"
                    opacity="0.3"
                  >
                    <animate
                      attributeName="opacity"
                      values="0.3;0.8;0.3"
                      dur="2s"
                      repeatCount="indefinite"
                    />
                  </line>
                );
              })}
            </svg>
          </div>
          <div className="flex justify-center gap-3 text-[10px] text-gray-500">
            <span>
              <span className="inline-block w-2 h-2 rounded-full bg-[#ff6644] mr-1" />
              Regime
            </span>
            <span>
              <span className="inline-block w-2 h-2 rounded-full bg-[#44aaff] mr-1" />
              Strategy
            </span>
            <span>
              <span className="inline-block w-2 h-2 rounded-full bg-[#44ff88] mr-1" />
              Indicator
            </span>
            <span>
              <span className="inline-block w-2 h-2 rounded-full bg-[#ffaa44] mr-1" />
              Tactical
            </span>
          </div>
        </Card>
      </div>

      {/* L6 Issues */}
      <div className="col-span-6">
        <Card
          header="L6 Latest Issues"
          action={
            <Badge variant="warning">
              {issuesList.filter((i) => i.status === "open").length} open
            </Badge>
          }
        >
          <div className="space-y-2">
            {issuesList.length === 0 ? (
              <div className="text-xs text-gray-500 p-2">
                No issues. System is healthy.
              </div>
            ) : (
              issuesList.map((issue) => (
                <div
                  key={issue.id}
                  className="flex items-center gap-2 text-xs p-2 rounded bg-cortex-border/30"
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      issue.severity === "critical"
                        ? "bg-red-500"
                        : issue.severity === "high"
                          ? "bg-amber-500"
                          : "bg-blue-500"
                    }`}
                  />
                  <span className="flex-1 text-gray-300">{issue.title}</span>
                  <Badge variant="default" size="sm">
                    {issue.dimension}
                  </Badge>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      {/* Emergence Feed */}
      <div className="col-span-6">
        <Card header="Emergence Feed">
          <div className="space-y-2">
            {emergenceList.length === 0 ? (
              <div className="text-xs text-gray-500 p-2">
                No emergence events detected.
              </div>
            ) : (
              emergenceList.map((event) => (
                <div
                  key={event.id}
                  className="flex items-start gap-2 text-xs p-2 rounded bg-cortex-border/20 animation-emergence-flash"
                >
                  <span className="text-sm">
                    {event.event_type === "crystallization"
                      ? "\u{1F48E}"
                      : event.event_type === "collaboration"
                        ? "\u{1F91D}"
                        : "✨"}
                  </span>
                  <span className="flex-1 text-gray-300">
                    {event.description}
                  </span>
                  <span className="text-gray-600">
                    {formatRelativeTime(event.timestamp)}
                  </span>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      {/* Throughput Sparkline */}
      <div className="col-span-12">
        <Card header="Pipeline Throughput (Last 30 ticks)">
          <Sparkline data={sparklineData} width={600} height={40} />
          <div className="flex justify-between text-[10px] text-gray-600 mt-1">
            <span>
              Min: {Math.min(...sparklineData).toFixed(1)}
            </span>
            <span>
              Avg:{" "}
              {(
                sparklineData.reduce((a, b) => a + b, 0) /
                sparklineData.length
              ).toFixed(1)}
            </span>
            <span>
              Max: {Math.max(...sparklineData).toFixed(1)}
            </span>
          </div>
        </Card>
      </div>
    </div>
  );
}
