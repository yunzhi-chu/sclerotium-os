import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type { FieldSettings, FieldAgentPosition, FieldLayer, FieldTexture } from "@/types/field";

interface FieldState {
  texture: FieldTexture | null;
  agentPositions: FieldAgentPosition[];
  settings: FieldSettings;
  activeLayer: FieldLayer;
  showGradients: boolean;
  showAgents: boolean;
  showEquations: boolean;
  isPlaying: boolean;
  speed: number;

  setTexture: (t: FieldTexture) => void;
  setAgentPositions: (p: FieldAgentPosition[]) => void;
  updateSettings: (patch: Partial<FieldSettings>) => void;
  setActiveLayer: (l: FieldLayer) => void;
  toggleGradients: () => void;
  toggleAgents: () => void;
  toggleEquations: () => void;
  togglePlaying: () => void;
  setSpeed: (s: number) => void;
}

const DEFAULT_SETTINGS: FieldSettings = {
  diffusion_signal: 0.1,
  diffusion_nutrient: 0.05,
  diffusion_damage: 0.02,
  decay_signal: 0.01,
  decay_nutrient: 0.005,
  decay_damage: 0.002,
  convection_x: 0.0,
  convection_y: 0.0,
  agent_deposit_rate: 0.1,
};

export const useFieldStore = create<FieldState>()(
  immer((set) => ({
    texture: null,
    agentPositions: [],
    settings: DEFAULT_SETTINGS,
    activeLayer: "signal",
    showGradients: true,
    showAgents: true,
    showEquations: false,
    isPlaying: true,
    speed: 1.0,

    setTexture: (t) => set({ texture: t }),
    setAgentPositions: (p) => set({ agentPositions: p }),
    updateSettings: (patch) =>
      set((s) => {
        Object.assign(s.settings, patch);
      }),
    setActiveLayer: (l) => set({ activeLayer: l }),
    toggleGradients: () => set((s) => ({ showGradients: !s.showGradients })),
    toggleAgents: () => set((s) => ({ showAgents: !s.showAgents })),
    toggleEquations: () => set((s) => ({ showEquations: !s.showEquations })),
    togglePlaying: () => set((s) => ({ isPlaying: !s.isPlaying })),
    setSpeed: (speed) => set({ speed }),
  }))
);
