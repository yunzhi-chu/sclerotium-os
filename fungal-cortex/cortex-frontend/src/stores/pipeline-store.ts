import { create } from "zustand";
import type { PipelineSnapshot, DebateClaim, RiskGateStatus } from "@/types/pipeline";

interface PipelineState {
  snapshot: PipelineSnapshot | null;
  debates: DebateClaim[];
  riskGates: RiskGateStatus[];
  pipelineHistory: number[];

  setSnapshot: (s: PipelineSnapshot) => void;
  setDebates: (d: DebateClaim[]) => void;
  setRiskGates: (g: RiskGateStatus[]) => void;
  addHistoryPoint: (throughput: number) => void;
}

export const usePipelineStore = create<PipelineState>()((set) => ({
  snapshot: null,
  debates: [],
  riskGates: [],
  pipelineHistory: [],

  setSnapshot: (snapshot) => set({ snapshot }),
  setDebates: (debates) => set({ debates }),
  setRiskGates: (riskGates) => set({ riskGates }),
  addHistoryPoint: (throughput) =>
    set((s) => ({
      pipelineHistory: [...s.pipelineHistory.slice(-500), throughput],
    })),
}));
