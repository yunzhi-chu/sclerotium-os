/** L6 Cognitive Core types. */

export interface ArchitectureIssue {
  id: string;
  dimension: ScanDimension;
  title: string;
  description: string;
  severity: "critical" | "high" | "medium" | "low";
  auto_fixable: boolean;
  status: "open" | "in_progress" | "fixed" | "approved" | "rejected";
  source_file?: string;
  line_range?: [number, number];
  suggestion?: string;
  created_at: number;
  fixed_at?: number;
}

export type ScanDimension =
  | "redundancy"
  | "coupling"
  | "latency"
  | "algorithm_gap"
  | "skill_gap"
  | "bottleneck"
  | "dead_code"
  | "error_pattern";

export const SCAN_DIMENSION_LABELS: Record<ScanDimension, string> = {
  redundancy: "Redundancy",
  coupling: "Coupling",
  latency: "Latency",
  algorithm_gap: "Algorithm Gap",
  skill_gap: "Skill Gap",
  bottleneck: "Bottleneck",
  dead_code: "Dead Code",
  error_pattern: "Error Pattern",
};

export interface L6Health {
  health_score: number;
  open_critical: number;
  open_high: number;
  open_medium: number;
  open_low: number;
  fixed_total: number;
  pending_approvals: number;
  last_scan_at: number;
}

export interface MAERScore {
  ma: number;
  er: number;
  ma_pass: boolean;
  er_pass: boolean;
  gap: number;
  gap_pass: boolean;
}

export interface FINALBenchReport {
  stage1_temporal: StageResult;
  stage2_provenance: StageResult;
  stage3_logic: StageResult;
  stage4_brave_search: StageResult;
  maer: MAERScore;
  overall_pass: boolean;
  timestamp: number;
}

export interface StageResult {
  stage: number;
  name: string;
  result: "pass" | "fail" | "warn" | "pending";
  score: number;
  details: string[];
  warnings: string[];
}

export interface EmergenceEvent {
  id: string;
  event_type: "independent_discovery" | "collaboration" | "crystallization";
  agents_involved: string[];
  pattern_name?: string;
  confidence?: number;
  description: string;
  timestamp: number;
}

export interface CreateAbilityRequest {
  gap_type: "skill" | "strategy" | "indicator";
  description: string;
  domain?: string;
  requirements?: string[];
}

export interface CreateAbilityStatus {
  status: "initiated" | "analyzing" | "generating" | "validating" | "sandboxing" | "completed" | "failed";
  progress: number;
  stage: string;
  result?: Record<string, unknown>;
}

export interface Goal {
  id: string;
  domain: string;
  direction: string;
  feasibility: number;
  info_gain: number;
  learning_progress: number;
  deployed: boolean;
  progress: number;
}
