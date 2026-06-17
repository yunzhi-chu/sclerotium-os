import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type { Skill, CatalysisGraph, PhaseTransitionMeter } from "@/types/skill";

interface SkillState {
  skills: Skill[];
  graph: CatalysisGraph | null;
  phaseMeter: PhaseTransitionMeter | null;
  selectedSkill: Skill | null;
  searchQuery: string;
  filterCategory: string | null;

  setSkills: (s: Skill[]) => void;
  updateSkill: (id: string, patch: Partial<Skill>) => void;
  setGraph: (g: CatalysisGraph) => void;
  setPhaseMeter: (p: PhaseTransitionMeter) => void;
  selectSkill: (s: Skill | null) => void;
  setSearchQuery: (q: string) => void;
  setFilterCategory: (c: string | null) => void;
}

export const useSkillStore = create<SkillState>()(
  immer((set) => ({
    skills: [],
    graph: null,
    phaseMeter: null,
    selectedSkill: null,
    searchQuery: "",
    filterCategory: null,

    setSkills: (skills) => set({ skills }),
    updateSkill: (id, patch) =>
      set((s) => {
        const idx = s.skills.findIndex((sk) => sk.id === id);
        if (idx >= 0) Object.assign(s.skills[idx], patch);
      }),
    setGraph: (graph) => set({ graph }),
    setPhaseMeter: (p) => set({ phaseMeter: p }),
    selectSkill: (skill) => set({ selectedSkill: skill }),
    setSearchQuery: (q) => set({ searchQuery: q }),
    setFilterCategory: (c) => set({ filterCategory: c }),
  }))
);
