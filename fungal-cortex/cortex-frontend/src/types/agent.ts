/** Agent types shared across the frontend. */

export type AgentSpecialty =
  | "regime"
  | "strategy"
  | "indicator"
  | "tactical"
  | "risk";

export type AgentRole =
  | "boundary_setter"
  | "axis_definer"
  | "constraint_enforcer"
  | "resource_allocator"
  | "lifecycle_manager";

export type AgentLifecycle =
  | "spawning"
  | "active"
  | "idle"
  | "promoting"
  | "apoptosing"
  | "dead";

export type AgentStatus = "idle" | "busy" | "overloaded" | "offline";

export const SPECIALTY_COLORS: Record<AgentSpecialty, string> = {
  regime: "#ff6644",
  strategy: "#44aaff",
  indicator: "#44ff88",
  tactical: "#ffaa44",
  risk: "#ff44aa",
};

export const SPECIALTY_LABELS: Record<AgentSpecialty, string> = {
  regime: "Regime",
  strategy: "Strategy",
  indicator: "Indicator",
  tactical: "Tactical",
  risk: "Risk",
};

export const LIFECYCLE_COLORS: Record<AgentLifecycle, string> = {
  spawning: "#44ff88",
  active: "#00ff88",
  idle: "#666688",
  promoting: "#ffaa44",
  apoptosing: "#ff4444",
  dead: "#333355",
};

export interface AgentNode {
  id: string;
  name: string;
  specialty: AgentSpecialty;
  role: AgentRole;
  lifecycle: AgentLifecycle;
  status: AgentStatus;
  performance_score: number;
  task_count: number;
  error_count: number;
  avg_latency_ms: number;
  x: number;
  y: number;
  z: number;
  connected_agents: string[];
  catalyzed_by: string[];
  catalyzes: string[];
}

export interface HyphalEdge {
  id: string;
  source: string;
  target: string;
  weight: number;
  edge_type: "signal" | "nutrient" | "damage" | "catalysis" | "data";
  flow_rate: number;
  is_active: boolean;
}

export interface AgentNetwork {
  nodes: AgentNode[];
  edges: HyphalEdge[];
  total_agents: number;
  active_agents: number;
  cycles_found: number;
  phase: "pre_critical" | "critical" | "supercritical" | "degenerate";
}
