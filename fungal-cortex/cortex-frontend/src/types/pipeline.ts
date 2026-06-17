/** L0-L7 Cognitive Pipeline types. */

export type LayerLevel = "L0" | "L1" | "L2" | "L3" | "L4" | "L5" | "L6" | "L7";

export interface LayerStatus {
  level: LayerLevel;
  name: string;
  throughput: number;
  latency_ms: number;
  error_rate: number;
  queue_depth: number;
  agent_count: number;
  status: "healthy" | "degraded" | "critical";
}

export interface PipelineSnapshot {
  layers: LayerStatus[];
  bottleneck_at: LayerLevel | null;
  bottleneck_score: number;
  total_throughput: number;
  avg_end_to_end_ms: number;
  timestamp: number;
}

export interface LayerEdge {
  from: LayerLevel;
  to: LayerLevel;
  data_flow: number;
  data_type: string;
  is_active: boolean;
}

export interface PipelineEvent {
  event_id: string;
  event_type: string;
  layer: LayerLevel;
  data: Record<string, unknown>;
  timestamp: number;
}

export interface DebateClaim {
  id: string;
  symbol: string;
  thesis: string;
  bull_confidence: number;
  bear_confidence: number;
  bull_arguments: number;
  bear_arguments: number;
  status: "open" | "resolved_bull" | "resolved_bear" | "stalemate";
  field_strength: number;
}

export interface RiskGateStatus {
  gate_id: number;
  name: string;
  faction: "aggressive" | "conservative" | "neutral";
  result: "pass" | "warn" | "block";
  current_value: number;
  limit: number;
}

export const LAYER_NAMES: Record<LayerLevel, string> = {
  L0: "Adaptive Engine",
  L1: "Data Layer",
  L2: "Analysis Layer",
  L3: "Debate Layer",
  L4: "Research Layer",
  L5: "Trading Layer",
  L6: "Risk Layer",
  L7: "Decision Layer",
};

export const LAYER_COLORS: Record<LayerLevel, string> = {
  L0: "#00d4aa",
  L1: "#3b82f6",
  L2: "#8b5cf6",
  L3: "#f59e0b",
  L4: "#22c55e",
  L5: "#ef4444",
  L6: "#ec4899",
  L7: "#f97316",
};
