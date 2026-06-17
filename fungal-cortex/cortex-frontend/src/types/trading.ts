/** Trading Desk types. */

export interface Position {
  symbol: string;
  name: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  pnl_pct: number;
  pnl_amount: number;
  weight: number;
  sector: string;
  signal_strength: number;
  risk_status: "pass" | "warn" | "block";
}

export interface Signal {
  symbol: string;
  action: "buy" | "sell" | "hold";
  position_pct: number;
  confidence: number;
  reason_chain: string[];
  generated_at: number;
  layers_used: string[];
}

export interface PortfolioOverview {
  total_value: number;
  cash: number;
  market_value: number;
  daily_pnl: number;
  daily_pnl_pct: number;
  total_pnl: number;
  total_pnl_pct: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  position_count: number;
  sector_weights: Record<string, number>;
}

export interface PnLPoint {
  timestamp: number;
  equity: number;
  benchmark: number;
  pnl: number;
}

export interface Order {
  order_id: string;
  symbol: string;
  side: "buy" | "sell";
  quantity: number;
  price: number;
  status: "pending" | "filled" | "cancelled" | "rejected";
  filled_qty: number;
  created_at: number;
}

export interface MarketTick {
  symbol: string;
  market: "CN" | "HK" | "US";
  price: number;
  volume: number;
  bid: number;
  ask: number;
  bid_size: number;
  ask_size: number;
  turnover: number;
  timestamp: number;
}

export interface OHLCBar {
  symbol: string;
  interval: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: number;
}
