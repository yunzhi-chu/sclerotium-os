/** Audit Trail types. */

export interface AuditRecord {
  id: string;
  timestamp: number;
  event_type: string;
  source_module: string;
  source_agent_id?: string;
  operation: string;
  result: "success" | "failure" | "pending";
  evidence_hash: string;
  details: Record<string, unknown>;
  severity: "info" | "warning" | "critical";
}

export interface CausalTrace {
  root_event: AuditRecord;
  upstream: AuditRecord[];
  downstream: AuditRecord[];
  causal_graph: CausalEdge[];
  timestamp: number;
}

export interface CausalEdge {
  from: string;
  to: string;
  relationship: string;
  confidence: number;
}

export interface CounterfactualRequest {
  original_event_id: string;
  scenario: Record<string, unknown>;
  variables: string[];
}

export interface CounterfactualResult {
  original_outcome: Record<string, unknown>;
  counterfactual_outcome: Record<string, unknown>;
  differences: Record<string, { original: unknown; counterfactual: unknown }>;
  confidence: number;
}

export interface AuditFilter {
  time_start?: number;
  time_end?: number;
  event_types?: string[];
  severity?: string[];
  source_module?: string;
  limit?: number;
  offset?: number;
}

export interface AuditStats {
  total_events: number;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  by_module: Record<string, number>;
  recent_critical: number;
}
