import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type {
  Position,
  Signal,
  PortfolioOverview,
  PnLPoint,
  Order,
  MarketTick,
  OHLCBar,
} from "@/types/trading";

interface TradingState {
  portfolio: PortfolioOverview | null;
  positions: Position[];
  signals: Signal[];
  pnlHistory: PnLPoint[];
  orders: Order[];
  selectedSymbol: string | null;
  activeMarket: "CN" | "HK" | "US";
  ticks: MarketTick[];
  ohlc: Record<string, OHLCBar[]>;

  setPortfolio: (p: PortfolioOverview) => void;
  setPositions: (p: Position[]) => void;
  addSignal: (s: Signal) => void;
  addPnlPoint: (p: PnLPoint) => void;
  addOrder: (o: Order) => void;
  updateOrder: (id: string, patch: Partial<Order>) => void;
  selectSymbol: (s: string | null) => void;
  setActiveMarket: (m: "CN" | "HK" | "US") => void;
  setTicks: (t: MarketTick[]) => void;
  setOHLC: (symbol: string, bars: OHLCBar[]) => void;
}

export const useTradingStore = create<TradingState>()(
  immer((set) => ({
    portfolio: null,
    positions: [],
    signals: [],
    pnlHistory: [],
    orders: [],
    selectedSymbol: null,
    activeMarket: "CN",
    ticks: [],
    ohlc: {},

    setPortfolio: (p) => set({ portfolio: p }),
    setPositions: (p) => set({ positions: p }),
    addSignal: (s) =>
      set((st) => {
        st.signals.unshift(s);
        if (st.signals.length > 50) st.signals.pop();
      }),
    addPnlPoint: (p) =>
      set((st) => {
        st.pnlHistory.push(p);
        if (st.pnlHistory.length > 500) st.pnlHistory.splice(0, 50);
      }),
    addOrder: (o) => set((st) => { st.orders.unshift(o); }),
    updateOrder: (id, patch) =>
      set((st) => {
        const idx = st.orders.findIndex((o) => o.order_id === id);
        if (idx >= 0) Object.assign(st.orders[idx], patch);
      }),
    selectSymbol: (s) => set({ selectedSymbol: s }),
    setActiveMarket: (m) => set({ activeMarket: m }),
    setTicks: (t) => set({ ticks: t }),
    setOHLC: (symbol, bars) =>
      set((st) => {
        st.ohlc[symbol] = bars;
      }),
  }))
);
