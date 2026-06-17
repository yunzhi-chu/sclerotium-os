/** Skill Registry types. */

export interface SkillDNA {
  picker: number;
  timer: number;
  risk_control: number;
  frequency: number;
  complexity: number;
  holding_period: number;
}

export interface Skill {
  id: string;
  name: string;
  version: string;
  category: SkillCategory;
  description: string;
  triggers: string[];
  dependencies: string[];
  catalyzes: string[];
  catalyzed_by: string[];
  dna?: SkillDNA;
  call_count: number;
  error_count: number;
  avg_latency_ms: number;
  is_active: boolean;
  module: string;
}

export type SkillCategory =
  | "adaptive_engine"
  | "data_provider"
  | "alphaear"
  | "quant_strategy"
  | "agent_plugin"
  | "vertical_plugin"
  | "l6_core"
  | "l6_safety"
  | "l6_rules"
  | "orchestration"
  | "trading"
  | "monitoring";

export const SKILL_CATEGORY_LABELS: Record<SkillCategory, string> = {
  adaptive_engine: "Adaptive Engine",
  data_provider: "Data Provider",
  alphaear: "AlphaEar",
  quant_strategy: "Quant Strategy",
  agent_plugin: "Agent Plugin",
  vertical_plugin: "Vertical Plugin",
  l6_core: "L6 Core",
  l6_safety: "L6 Safety",
  l6_rules: "L6 Rules",
  orchestration: "Orchestration",
  trading: "Trading",
  monitoring: "Monitoring",
};

export interface CatalysisEdge {
  source: string;
  target: string;
  weight: number;
  evidence: string;
  edge_type: string;
}

export interface RAFSet {
  members: string[];
  density: number;
  cycles: string[][];
  sustainability: number;
}

export interface CatalysisGraph {
  nodes: Record<string, Skill>;
  edges: CatalysisEdge[];
  raf_sets: RAFSet[];
  total_cycles: number;
  node_count: number;
  edge_count: number;
}

export interface PhaseTransitionMeter {
  current_rings: number;
  n_crit: number;
  state: "pre_critical" | "critical" | "supercritical" | "degenerate";
  distance_to_critical: number;
  is_autopoietic: boolean;
}
