import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type { AgentNetwork, AgentNode, HyphalEdge } from "@/types/agent";

interface AgentState {
  network: AgentNetwork | null;
  selectedNode: AgentNode | null;
  hoveredNode: AgentNode | null;
  filterSpecialty: string | null;
  showCatalysis: boolean;
  showInactive: boolean;

  setNetwork: (n: AgentNetwork) => void;
  updateNode: (id: string, patch: Partial<AgentNode>) => void;
  addEdge: (edge: HyphalEdge) => void;
  removeEdge: (id: string) => void;
  selectNode: (node: AgentNode | null) => void;
  hoverNode: (node: AgentNode | null) => void;
  setFilterSpecialty: (s: string | null) => void;
  toggleCatalysis: () => void;
  toggleInactive: () => void;
}

export const useAgentStore = create<AgentState>()(
  immer((set) => ({
    network: null,
    selectedNode: null,
    hoveredNode: null,
    filterSpecialty: null,
    showCatalysis: true,
    showInactive: false,

    setNetwork: (n) => set({ network: n }),
    updateNode: (id, patch) =>
      set((s) => {
        if (!s.network) return;
        const idx = s.network.nodes.findIndex((n) => n.id === id);
        if (idx >= 0) Object.assign(s.network.nodes[idx], patch);
      }),
    addEdge: (edge) =>
      set((s) => {
        if (s.network) s.network.edges.push(edge);
      }),
    removeEdge: (id) =>
      set((s) => {
        if (!s.network) return;
        s.network.edges = s.network.edges.filter((e) => e.id !== id);
      }),
    selectNode: (node) => set({ selectedNode: node }),
    hoverNode: (node) => set({ hoveredNode: node }),
    setFilterSpecialty: (s) => set({ filterSpecialty: s }),
    toggleCatalysis: () => set((s) => ({ showCatalysis: !s.showCatalysis })),
    toggleInactive: () => set((s) => ({ showInactive: !s.showInactive })),
  }))
);
