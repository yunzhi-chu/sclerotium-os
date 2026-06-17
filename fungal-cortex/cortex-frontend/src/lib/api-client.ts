/** REST API client for Fungal Cortex backend. */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    throw new ApiError(res.status, `API ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  // Health
  getHealth: () => request<Record<string, unknown>>("/api/health"),

  // Skills
  getSkills: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<Record<string, unknown>[]>(`/api/skills${qs}`);
  },
  getSkill: (id: string) => request<Record<string, unknown>>(`/api/skills/${id}`),
  activateSkill: (id: string) =>
    request<Record<string, unknown>>(`/api/skills/${id}/activate`, { method: "POST" }),

  // Strategies
  getStrategies: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<Record<string, unknown>[]>(`/api/strategies${qs}`);
  },

  // Backtest
  createBacktest: (config: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/backtest", {
      method: "POST",
      body: JSON.stringify(config),
    }),
  getBacktest: (id: string) => request<Record<string, unknown>>(`/api/backtest/${id}`),

  // Audit
  getAudit: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return request<Record<string, unknown>[]>(`/api/audit${qs}`);
  },
  getCausalTrace: (id: string) =>
    request<Record<string, unknown>>(`/api/audit/${id}/causal-trace`),

  // L6
  triggerScan: () =>
    request<Record<string, unknown>>("/api/l6/scan", { method: "POST" }),
  approveRefactor: (id: string) =>
    request<Record<string, unknown>>(`/api/l6/refactor/${id}/approve`, { method: "POST" }),
  createAbility: (req: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/l6/create-ability", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  getEmergence: () => request<Record<string, unknown>[]>("/api/l6/emergence"),
  crystallize: (id: string) =>
    request<Record<string, unknown>>(`/api/l6/crystallize/${id}`, { method: "POST" }),

  // Goals
  getGoals: () => request<Record<string, unknown>[]>("/api/goals"),
  deployGoal: (goal: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/goals/deploy", {
      method: "POST",
      body: JSON.stringify(goal),
    }),

  // Gateway
  getServices: () => request<Record<string, unknown>[]>("/api/gateway/services"),
  registerService: (svc: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/gateway/register", {
      method: "POST",
      body: JSON.stringify(svc),
    }),

  // Rules
  getRuleTests: () => request<Record<string, unknown>[]>("/api/rules/tests"),
  generateRules: (spec: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/rules/generate", {
      method: "POST",
      body: JSON.stringify(spec),
    }),
};

export { ApiError };
export default api;
