/** GET /api/health — system health endpoint. */
import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    health_score: 92,
    open_critical: 2,
    open_high: 3,
    open_medium: 5,
    open_low: 8,
    fixed_total: 47,
    pending_approvals: 2,
    agents: { total: 20, active: 17, idle: 3 },
    skills: { total: 209, active: 209, catalyzing: 3 },
    pipeline: {
      throughput: 847.3,
      avg_latency_ms: 234,
      bottleneck_at: "L3",
    },
    phase: "critical",
    last_scan_at: Date.now(),
    uptime_seconds: 1234567,
  });
}
