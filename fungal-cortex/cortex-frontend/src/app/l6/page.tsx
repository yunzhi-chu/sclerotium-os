/** L6 Console -- Metacognitive control center. */
"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Gauge } from "@/components/ui/gauge";
import { Button } from "@/components/ui/button";
import { BarChart } from "@/components/charts/bar-chart";
import { useL6Store } from "@/stores/l6-store";
import { useWebSocket } from "@/hooks/use-websocket";
import { api } from "@/lib/api-client";
import {
  SCAN_DIMENSION_LABELS,
  type ArchitectureIssue,
  type EmergenceEvent,
  type Goal,
  type ScanDimension,
} from "@/types/l6";

interface ScanDimData {
  dimension: ScanDimension;
  score: number;
  issues_count: number;
}

/* Fallback scan dimensions for initial render before WS data arrives. */
const FALLBACK_SCAN_DIMS: ScanDimData[] = [
  { dimension: "redundancy", score: 85, issues_count: 1 },
  { dimension: "coupling", score: 62, issues_count: 3 },
  { dimension: "latency", score: 91, issues_count: 0 },
  { dimension: "algorithm_gap", score: 70, issues_count: 2 },
  { dimension: "skill_gap", score: 55, issues_count: 4 },
  { dimension: "bottleneck", score: 88, issues_count: 1 },
  { dimension: "dead_code", score: 78, issues_count: 2 },
  { dimension: "error_pattern", score: 94, issues_count: 0 },
];

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const s = Math.floor(diff / 1000);
  if (s < 10) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// FINAL Bench thresholds (constants, not from API)
const BENCH_THRESHOLDS = [
  { label: "MA Score", key: "ma" as const, threshold: 0.694 },
  { label: "ER Score", key: "er" as const, threshold: 0.302 },
  { label: "Gap", key: "gap" as const, threshold: 0.3 },
] as const;

export default function L6ConsolePage() {
  const [activeTab, setActiveTab] = useState<string>("overview");
  const [expandedIssue, setExpandedIssue] = useState<string | null>(null);
  const [scanDims, setScanDims] = useState<ScanDimData[]>(FALLBACK_SCAN_DIMS);

  const {
    health,
    issues,
    finalBench,
    emergenceEvents,
    goals,
    setHealth,
    setIssues,
    setFinalBench,
    addEmergenceEvent,
    setGoals,
  } = useL6Store();

  // Warm-up connection on mount
  useEffect(() => {
    api.getHealth().catch(() => {});
  }, []);

  // Subscribe to L6 WebSocket
  useWebSocket("l6", "l6", (data: unknown) => {
    const d = data as Record<string, unknown>;

    // Health update
    if (d.health_score !== undefined) {
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

    // Scan dimensions
    if (d.scan_dimensions && Array.isArray(d.scan_dimensions)) {
      setScanDims(d.scan_dimensions as ScanDimData[]);
    }

    // Issues list
    if (d.issues && Array.isArray(d.issues)) {
      const mapped: ArchitectureIssue[] = (
        d.issues as Array<Record<string, unknown>>
      ).map((iss) => ({
        id: (iss.id as string) ?? "",
        dimension: (iss.dimension as ScanDimension) ?? "coupling",
        title: (iss.title as string) ?? "",
        description: (iss.description as string) ?? "",
        severity: (iss.severity as ArchitectureIssue["severity"]) ?? "medium",
        auto_fixable: (iss.auto_fixable as boolean) ?? false,
        status: (iss.status as ArchitectureIssue["status"]) ?? "open",
        source_file: iss.source_file as string | undefined,
        line_range: iss.line_range as [number, number] | undefined,
        suggestion: iss.suggestion as string | undefined,
        created_at: (iss.created_at as number) ?? Date.now(),
        fixed_at: iss.fixed_at as number | undefined,
      }));
      setIssues(mapped);
    }

    // Single emergence event
    if (d.emergence_event) {
      const ev = d.emergence_event as Record<string, unknown>;
      addEmergenceEvent({
        id: (ev.id as string) ?? crypto.randomUUID(),
        event_type:
          (ev.event_type as EmergenceEvent["event_type"]) ??
          "independent_discovery",
        agents_involved: (ev.agents_involved as string[]) ?? [],
        description: (ev.description as string) ?? "",
        timestamp: (ev.timestamp as number) ?? Date.now(),
        confidence: ev.confidence as number | undefined,
        pattern_name: ev.pattern_name as string | undefined,
      });
    }

    // Goals list
    if (d.goals && Array.isArray(d.goals)) {
      const mapped: Goal[] = (
        d.goals as Array<Record<string, unknown>>
      ).map((g) => ({
        id: (g.id as string) ?? "",
        domain: (g.domain as string) ?? "",
        direction: (g.direction as string) ?? "",
        feasibility: (g.feasibility as number) ?? 0,
        info_gain: (g.info_gain as number) ?? 0,
        learning_progress: (g.learning_progress as number) ?? 0,
        deployed: (g.deployed as boolean) ?? false,
        progress: (g.progress as number) ?? 0,
      }));
      setGoals(mapped);
    }

    // FINAL Bench / MAER update
    if (d.maer) {
      const m = d.maer as Record<string, unknown>;
      setFinalBench({
        stage1_temporal:
          (d.stage1_temporal as any) ?? {
            stage: 1,
            name: "",
            result: "pending",
            score: 0,
            details: [],
            warnings: [],
          },
        stage2_provenance:
          (d.stage2_provenance as any) ?? {
            stage: 2,
            name: "",
            result: "pending",
            score: 0,
            details: [],
            warnings: [],
          },
        stage3_logic:
          (d.stage3_logic as any) ?? {
            stage: 3,
            name: "",
            result: "pending",
            score: 0,
            details: [],
            warnings: [],
          },
        stage4_brave_search:
          (d.stage4_brave_search as any) ?? {
            stage: 4,
            name: "",
            result: "pending",
            score: 0,
            details: [],
            warnings: [],
          },
        maer: {
          ma: (m.ma as number) ?? 0,
          er: (m.er as number) ?? 0,
          ma_pass: (m.ma_pass as boolean) ?? false,
          er_pass: (m.er_pass as boolean) ?? false,
          gap: (m.gap as number) ?? 0,
          gap_pass: (m.gap_pass as boolean) ?? false,
        },
        overall_pass: (d.overall_pass as boolean) ?? false,
        timestamp: (d.timestamp as number) ?? Date.now(),
      });
    }
  });

  const h = health;
  const maer = finalBench?.maer;
  const benchItems = BENCH_THRESHOLDS.map((bt) => {
    const val = maer ? maer[bt.key] : undefined;
    const passKey = `${bt.key}_pass` as "ma_pass" | "er_pass" | "gap_pass";
    const pass = maer ? maer[passKey] : undefined;
    return {
      label: bt.label,
      value: val ?? 0.72,
      threshold: bt.threshold,
      pass: pass ?? true,
    };
  });
  const allPass = finalBench?.overall_pass ?? true;
  const refactorCandidates = issues.filter(
    (i) =>
      (i.status === "open" || i.status === "in_progress") && i.auto_fixable,
  );

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-bold font-mono text-cortex-primary">
          L6 Cognitive Console
        </h1>
        <div className="flex gap-2">
          <Badge variant="success">L6 Active</Badge>
          <Button variant="primary" size="sm" onClick={() => {}}>
            Run Full Scan
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-cortex-border pb-2">
        {["overview", "scan-results", "ability-creator", "refactor", "goals"].map(
          (tab) => (
            <button
              key={tab}
              className={`px-3 py-1 text-xs rounded-t transition-colors ${
                activeTab === tab
                  ? "bg-cortex-border text-white"
                  : "text-gray-500 hover:text-white"
              }`}
              onClick={() => setActiveTab(tab)}
            >
              {tab === "overview"
                ? "Overview"
                : tab === "scan-results"
                  ? "Scan Results"
                  : tab === "ability-creator"
                    ? "Ability Creator"
                    : tab === "refactor"
                      ? "Refactor"
                      : "Goals"}
            </button>
          ),
        )}
      </div>

      {activeTab === "overview" && (
        <div className="grid grid-cols-12 gap-4">
          {/* Health gauge */}
          <div className="col-span-3">
            <Card className="text-center">
              <Gauge
                value={h?.health_score ?? 0}
                size={140}
                strokeWidth={12}
                color="#22c55e"
                showPercentage
              />
              <div className="text-sm text-green-400 font-bold mt-2">GOOD</div>
              <div className="grid grid-cols-3 gap-1 mt-3 text-[10px]">
                <div>
                  <div className="text-red-400 font-bold">
                    {h?.open_critical ?? 0}
                  </div>
                  <div className="text-gray-600">Critical</div>
                </div>
                <div>
                  <div className="text-amber-400 font-bold">
                    {h?.open_high ?? 0}
                  </div>
                  <div className="text-gray-600">High</div>
                </div>
                <div>
                  <div className="text-blue-400 font-bold">
                    {h?.fixed_total ?? 0}
                  </div>
                  <div className="text-gray-600">Fixed</div>
                </div>
              </div>
            </Card>
          </div>

          {/* Scan results bar chart */}
          <div className="col-span-5">
            <Card header="8-Dimension Scan">
              <BarChart
                data={scanDims.map((d) => ({
                  label: SCAN_DIMENSION_LABELS[d.dimension],
                  value: d.score,
                  color:
                    d.score > 80
                      ? "#22c55e"
                      : d.score > 60
                        ? "#f59e0b"
                        : "#ef4444",
                }))}
                horizontal
                height={200}
              />
            </Card>
          </div>

          {/* FINAL Bench */}
          <div className="col-span-4">
            <Card header="FINAL Bench">
              <div className="space-y-3">
                {benchItems.map((m) => (
                  <div key={m.label}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-400">{m.label}</span>
                      <span
                        className={
                          m.pass ? "text-green-400" : "text-red-400"
                        }
                      >
                        {m.value.toFixed(3)} / {m.threshold}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-cortex-border overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${m.pass ? "bg-green-500" : "bg-red-500"}`}
                        style={{
                          width: `${Math.min(100, (m.value / m.threshold) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
                <div className="text-center">
                  {allPass ? (
                    <Badge variant="success">ALL PASS</Badge>
                  ) : (
                    <Badge variant="danger">SOME FAILED</Badge>
                  )}
                </div>
              </div>
            </Card>
          </div>

          {/* Issues */}
          <div className="col-span-6">
            <Card
              header="Critical Issues"
              action={
                <Badge variant="warning">{issues.length} open</Badge>
              }
            >
              <div className="space-y-2">
                {issues.length === 0 ? (
                  <div className="text-xs text-gray-500 p-4">
                    No issues detected.
                  </div>
                ) : (
                  issues.map((issue) => (
                    <div
                      key={issue.id}
                      className="p-2 rounded bg-cortex-border/30 cursor-pointer"
                      onClick={() =>
                        setExpandedIssue(
                          expandedIssue === issue.id ? null : issue.id,
                        )
                      }
                    >
                      <div className="flex items-center gap-2 text-xs">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            issue.severity === "critical"
                              ? "bg-red-500"
                              : issue.severity === "high"
                                ? "bg-amber-500"
                                : "bg-blue-500"
                          }`}
                        />
                        <span className="flex-1">{issue.title}</span>
                        {issue.auto_fixable && (
                          <Badge variant="success" size="sm">
                            auto-fix
                          </Badge>
                        )}
                        <Badge
                          variant={
                            issue.status === "open" ? "warning" : "info"
                          }
                          size="sm"
                        >
                          {issue.status}
                        </Badge>
                      </div>
                      {expandedIssue === issue.id && (
                        <div className="mt-2 pt-2 border-t border-cortex-border/50 text-[10px] space-y-1 text-gray-500">
                          <div>Dimension: {issue.dimension}</div>
                          <div>
                            Suggestion:{" "}
                            {issue.suggestion ??
                              "Review and decouple shared dependencies"}
                          </div>
                          <div className="flex gap-2 mt-1">
                            <Button variant="primary" size="sm">
                              Approve Fix
                            </Button>
                            <Button variant="danger" size="sm">
                              Reject
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>

          {/* Emergence */}
          <div className="col-span-6">
            <Card header="Emergence Feed">
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {emergenceEvents.length === 0 ? (
                  <div className="text-xs text-gray-500 p-4">
                    Waiting for emergence events...
                  </div>
                ) : (
                  emergenceEvents.map((e) => (
                    <div
                      key={e.id}
                      className="p-2 rounded bg-cortex-border/20 text-xs flex items-start gap-2"
                    >
                      <span>
                        {e.event_type === "crystallization"
                          ? "\u{1F48E}"
                          : e.event_type === "collaboration"
                            ? "\u{1F91D}"
                            : "✨"}
                      </span>
                      <span className="flex-1 text-gray-300">
                        {e.description}
                      </span>
                      <div className="flex gap-1">
                        {e.agents_involved.map((a) => (
                          <Badge key={a} variant="info" size="sm">
                            {a}
                          </Badge>
                        ))}
                      </div>
                      <span className="text-gray-600">
                        {relativeTime(e.timestamp)}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </Card>
          </div>
        </div>
      )}

      {activeTab === "scan-results" && (
        <div className="space-y-3">
          {scanDims.map((dim) => (
            <Card
              key={dim.dimension}
              header={SCAN_DIMENSION_LABELS[dim.dimension]}
            >
              <div className="flex items-center gap-4">
                <div className="w-32">
                  <div className="text-xs text-gray-500 mb-1">Score</div>
                  <div className="h-2 rounded-full bg-cortex-border overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${dim.score}%`,
                        backgroundColor:
                          dim.score > 80
                            ? "#22c55e"
                            : dim.score > 60
                              ? "#f59e0b"
                              : "#ef4444",
                      }}
                    />
                  </div>
                </div>
                <span className="text-sm font-mono font-bold">
                  {dim.score}/100
                </span>
                <span className="text-xs text-gray-500">
                  {dim.issues_count} issue
                  {dim.issues_count !== 1 ? "s" : ""}
                </span>
              </div>
            </Card>
          ))}
        </div>
      )}

      {activeTab === "ability-creator" && (
        <Card header="M2 Ability Creation Factory">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-400 block mb-1">
                  Gap Type
                </label>
                <select className="w-full bg-cortex-bg border border-cortex-border rounded px-3 py-2 text-sm text-gray-200">
                  <option value="skill">Skill</option>
                  <option value="strategy">Strategy</option>
                  <option value="indicator">Indicator</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">
                  Description
                </label>
                <textarea
                  className="w-full bg-cortex-bg border border-cortex-border rounded px-3 py-2 text-sm text-gray-200 h-20"
                  placeholder="Describe the capability needed..."
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">
                  Domain
                </label>
                <input
                  className="w-full bg-cortex-bg border border-cortex-border rounded px-3 py-2 text-sm text-gray-200"
                  placeholder="e.g., china-finance"
                />
              </div>
              <Button variant="primary">Create Ability</Button>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-2">
                Creation Pipeline
              </div>
              <div className="space-y-2">
                {[
                  "Initiated",
                  "Analyzing Requirements",
                  "Generating Code",
                  "Validating Syntax",
                  "Sandbox Testing",
                  "Completed",
                ].map((stage, i) => (
                  <div key={stage} className="flex items-center gap-2 text-xs">
                    <span
                      className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] ${
                        i < 1
                          ? "bg-cortex-primary text-cortex-bg"
                          : "bg-cortex-border text-gray-500"
                      }`}
                    >
                      {i + 1}
                    </span>
                    <span
                      className={i < 1 ? "text-white" : "text-gray-600"}
                    >
                      {stage}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      {activeTab === "refactor" && (
        <Card header="Auto-Refactor Pending Approvals">
          <div className="space-y-3">
            {refactorCandidates.length === 0 ? (
              <div className="text-xs text-gray-500 p-4">
                No pending refactor candidates.
              </div>
            ) : (
              refactorCandidates.map((ref) => (
                <div
                  key={ref.id}
                  className="p-3 rounded bg-cortex-border/30"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-cortex-primary">
                      {ref.source_file}
                      {ref.line_range
                        ? `:${ref.line_range[0]}-${ref.line_range[1]}`
                        : ""}
                    </span>
                    <div className="flex gap-1">
                      <Button variant="primary" size="sm">
                        Approve
                      </Button>
                      <Button variant="danger" size="sm">
                        Reject
                      </Button>
                    </div>
                  </div>
                  <div className="text-xs text-gray-400 mb-2">
                    {ref.suggestion ?? ref.title}
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2 rounded bg-red-900/20 border border-red-900/30">
                      <div className="text-[10px] text-red-400 mb-1">
                        Before
                      </div>
                      <pre className="text-[10px] text-gray-400 whitespace-pre font-mono">
                        {ref.title}
                      </pre>
                    </div>
                    <div className="p-2 rounded bg-green-900/20 border border-green-900/30">
                      <div className="text-[10px] text-green-400 mb-1">
                        After
                      </div>
                      <pre className="text-[10px] text-gray-300 whitespace-pre font-mono">
                        {ref.suggestion ?? "Optimized implementation"}
                      </pre>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      )}

      {activeTab === "goals" && (
        <Card header="Global Goals Explorer">
          <div className="space-y-3">
            {goals.length === 0 ? (
              <div className="text-xs text-gray-500 p-4">
                No goals configured.
              </div>
            ) : (
              goals.map((g) => (
                <div
                  key={g.id}
                  className="p-3 rounded bg-cortex-border/30"
                >
                  <div className="flex items-center justify-between mb-1">
                    <div>
                      <Badge variant="info" size="sm">
                        {g.domain}
                      </Badge>
                      <span className="text-xs ml-2 text-gray-300">
                        {g.direction}
                      </span>
                    </div>
                    <Badge
                      variant={
                        g.feasibility > 0.7
                          ? "success"
                          : g.feasibility > 0.4
                            ? "warning"
                            : "danger"
                      }
                      size="sm"
                    >
                      {(g.feasibility * 100).toFixed(0)}% feasible
                    </Badge>
                  </div>
                  <div className="h-1.5 rounded-full bg-cortex-border overflow-hidden mt-2">
                    <div
                      className="h-full rounded-full bg-cortex-primary transition-all"
                      style={{ width: `${g.progress}%` }}
                    />
                  </div>
                  <div className="text-[10px] text-right text-gray-600 mt-1">
                    {g.progress}% complete
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
