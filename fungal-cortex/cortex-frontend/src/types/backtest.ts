/** Backtest Lab types. */

import type { SkillDNA } from "@/types/skill";

export interface BacktestStrategy {
  id: string;
  name: string;
  sharpe: number;
  max_drawdown: number;
  annual_return: number;
  win_rate: number;
  dna: SkillDNA;
  trades: number;
  is_active: boolean;
}

export interface EquityPoint {
  t: number;
  strategy: number;
  benchmark: number;
}

export interface BarraFactor {
  factor: string;
  exposure: number;
  return: number;
  risk: number;
}

export interface BacktestConfig {
  start_date: string;
  end_date: string;
  initial_capital: number;
  commission: number;
  slippage: number;
  benchmark: string;
}

export interface BacktestResult {
  id: string;
  strategy_name: string;
  sharpe: number;
  max_drawdown: number;
  win_rate: number;
  annual_return: number;
  calmar: number;
  systematic_risk: number;
  specific_risk: number;
}

export interface BacktestState {
  strategies: BacktestStrategy[];
  equityCurve: EquityPoint[];
  barraFactors: BarraFactor[];
  config: BacktestConfig;
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
