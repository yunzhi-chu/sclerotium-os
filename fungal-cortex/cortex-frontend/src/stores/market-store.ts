import { create } from "zustand";
import type { MarketTick, OHLCBar } from "@/types/trading";

export interface MarketQuote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  volume: string;
  market: "CN" | "HK" | "US";
}

export interface NewsItem {
  title: string;
  source: string;
  time: string;
  sentiment: number;
}

interface MarketState {
  ticks: MarketTick[];
  ohlc: Record<string, OHLCBar[]>;
  watchlist: string[];
  activeInterval: string;
  selectedSymbol: string | null;
  quotes: MarketQuote[];
  news: NewsItem[];
  sentiment: number;
  chartData: number[];

  setTicks: (t: MarketTick[]) => void;
  addTick: (t: MarketTick) => void;
  setOHLC: (symbol: string, bars: OHLCBar[]) => void;
  setWatchlist: (w: string[]) => void;
  setActiveInterval: (i: string) => void;
  setSelectedSymbol: (s: string | null) => void;
  setQuotes: (q: MarketQuote[]) => void;
  setNews: (n: NewsItem[]) => void;
  setSentiment: (s: number) => void;
  setChartData: (d: number[]) => void;
}

export const useMarketStore = create<MarketState>()((set) => ({
  ticks: [],
  ohlc: {},
  watchlist: ["000001.SZ", "600000.SH", "00700.HK", "AAPL"],
  activeInterval: "1m",
  selectedSymbol: null,
  quotes: [],
  news: [],
  sentiment: 0,
  chartData: [],

  setTicks: (ticks) => set({ ticks }),
  addTick: (tick) =>
    set((s) => ({
      ticks: [...s.ticks.slice(-99), tick],
    })),
  setOHLC: (symbol, bars) =>
    set((s) => ({ ohlc: { ...s.ohlc, [symbol]: bars } })),
  setWatchlist: (watchlist) => set({ watchlist }),
  setActiveInterval: (activeInterval) => set({ activeInterval }),
  setSelectedSymbol: (selectedSymbol) => set({ selectedSymbol }),
  setQuotes: (quotes) => set({ quotes }),
  setNews: (news) => set({ news }),
  setSentiment: (sentiment) => set({ sentiment }),
  setChartData: (chartData) => set({ chartData }),
}));
