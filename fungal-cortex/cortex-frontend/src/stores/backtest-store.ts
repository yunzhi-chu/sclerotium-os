import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type {
  BacktestStrategy,
  EquityPoint,
  BarraFactor,
  BacktestConfig,
  BacktestResult,
} from "@/types/backtest";

interface BacktestState {
  strategies: BacktestStrategy[];
  equityCurve: EquityPoint[];
  barraFactors: BarraFactor[];
  config: BacktestConfig | null;
  results: BacktestResult[];
  selectedStrategyId: string | null;
  running: boolean;

  setStrategies: (s: BacktestStrategy[]) => void;
  setEquityCurve: (e: EquityPoint[]) => void;
  setBarraFactors: (f: BarraFactor[]) => void;
  setConfig: (c: BacktestConfig) => void;
  setResults: (r: BacktestResult[]) => void;
  selectStrategy: (id: string | null) => void;
  setRunning: (r: boolean) => void;
}

export const useBacktestStore = create<BacktestState>()(
  immer((set) => ({
    strategies: [],
    equityCurve: [],
    barraFactors: [],
    config: null,
    results: [],
    selectedStrategyId: null,
    running: false,

    setStrategies: (strategies) => set({ strategies }),
    setEquityCurve: (equityCurve) => set({ equityCurve }),
    setBarraFactors: (barraFactors) => set({ barraFactors }),
    setConfig: (config) => set({ config }),
    setResults: (results) => set({ results }),
    selectStrategy: (selectedStrategyId) => set({ selectedStrategyId }),
    setRunning: (running) => set({ running }),
  }))
);
