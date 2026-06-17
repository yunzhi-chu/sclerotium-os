/** Audit Trail store. */
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type {
  AuditRecord,
  CausalTrace,
  CounterfactualResult,
  AuditStats,
} from "@/types/audit";

interface AuditState {
  auditLogs: AuditRecord[];
  causalTrace: CausalTrace | null;
  counterfactualResult: CounterfactualResult | null;
  stats: AuditStats | null;
  loading: boolean;

  setAuditLogs: (logs: AuditRecord[]) => void;
  appendAuditLogs: (logs: AuditRecord[]) => void;
  setCausalTrace: (trace: CausalTrace | null) => void;
  setCounterfactualResult: (result: CounterfactualResult | null) => void;
  setStats: (stats: AuditStats) => void;
  setLoading: (loading: boolean) => void;
}

export const useAuditStore = create<AuditState>()(
  immer((set) => ({
    auditLogs: [],
    causalTrace: null,
    counterfactualResult: null,
    stats: null,
    loading: false,

    setAuditLogs: (logs) => set({ auditLogs: logs }),
    appendAuditLogs: (logs) =>
      set((st) => {
        st.auditLogs.push(...logs);
        if (st.auditLogs.length > 500) st.auditLogs.splice(0, st.auditLogs.length - 500);
      }),
    setCausalTrace: (trace) => set({ causalTrace: trace }),
    setCounterfactualResult: (result) => set({ counterfactualResult: result }),
    setStats: (stats) => set({ stats }),
    setLoading: (loading) => set({ loading }),
  }))
);
