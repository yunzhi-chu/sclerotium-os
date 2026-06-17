import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type {
  L6Health,
  ArchitectureIssue,
  FINALBenchReport,
  EmergenceEvent,
  CreateAbilityStatus,
  Goal,
} from "@/types/l6";

interface L6State {
  health: L6Health | null;
  issues: ArchitectureIssue[];
  finalBench: FINALBenchReport | null;
  emergenceEvents: EmergenceEvent[];
  goals: Goal[];
  createStatus: CreateAbilityStatus | null;
  issueFilter: string | null;

  setHealth: (h: L6Health) => void;
  setIssues: (i: ArchitectureIssue[]) => void;
  updateIssue: (id: string, patch: Partial<ArchitectureIssue>) => void;
  setFinalBench: (f: FINALBenchReport) => void;
  addEmergenceEvent: (e: EmergenceEvent) => void;
  setGoals: (g: Goal[]) => void;
  setCreateStatus: (s: CreateAbilityStatus | null) => void;
  setIssueFilter: (f: string | null) => void;
}

export const useL6Store = create<L6State>()(
  immer((set) => ({
    health: null,
    issues: [],
    finalBench: null,
    emergenceEvents: [],
    goals: [],
    createStatus: null,
    issueFilter: null,

    setHealth: (h) => set({ health: h }),
    setIssues: (i) => set({ issues: i }),
    updateIssue: (id, patch) =>
      set((s) => {
        const idx = s.issues.findIndex((i) => i.id === id);
        if (idx >= 0) Object.assign(s.issues[idx], patch);
      }),
    setFinalBench: (f) => set({ finalBench: f }),
    addEmergenceEvent: (e) =>
      set((s) => {
        s.emergenceEvents.unshift(e);
        if (s.emergenceEvents.length > 200) s.emergenceEvents.pop();
      }),
    setGoals: (g) => set({ goals: g }),
    setCreateStatus: (s) => set({ createStatus: s }),
    setIssueFilter: (f) => set({ issueFilter: f }),
  }))
);
