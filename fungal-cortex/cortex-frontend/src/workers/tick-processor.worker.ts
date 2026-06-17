/** Web Worker: Tick data processing — OHLC aggregation, ring buffer, sparkline generation. */

interface TickMessage {
  type: "tick";
  symbol: string;
  price: number;
  volume: number;
  timestamp: number;
}

interface TickData {
  symbol: string;
  price: number;
  volume: number;
  timestamp: number;
}

const RING_BUFFER_SIZE = 500;
const tickBuffers: Map<string, TickData[]> = new Map();
const ohlcCache: Map<string, Map<string, OHLCAgg[]>> = new Map();

interface OHLCAgg {
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: number;
}

interface OHLCRequest {
  type: "get_ohlc";
  symbol: string;
  interval: string;
  count?: number;
}

interface BatchMessage {
  type: "batch";
  ticks: TickData[];
  ohlc: Record<string, OHLCAgg[]>;
  sparklines: Record<string, string>;
}

const INTERVAL_MS: Record<string, number> = {
  "1m": 60_000,
  "5m": 300_000,
  "15m": 900_000,
  "1h": 3_600_000,
  "1d": 86_400_000,
};

let lastEmit = 0;
const THROTTLE_MS = 16;

function ensureBuffer(symbol: string): TickData[] {
  let buf = tickBuffers.get(symbol);
  if (!buf) {
    buf = [];
    tickBuffers.set(symbol, buf);
  }
  return buf;
}

function pushTick(symbol: string, tick: TickData): void {
  const buf = ensureBuffer(symbol);
  buf.push(tick);
  if (buf.length > RING_BUFFER_SIZE) buf.shift();
}

function updateOHLC(symbol: string, tick: TickData): void {
  let symCache = ohlcCache.get(symbol);
  if (!symCache) {
    symCache = new Map();
    ohlcCache.set(symbol, symCache);
  }

  for (const [interval, ms] of Object.entries(INTERVAL_MS)) {
    let bars = symCache.get(interval);
    if (!bars) {
      bars = [];
      symCache.set(interval, bars);
    }

    const bucket = Math.floor(tick.timestamp / ms) * ms;
    const last = bars[bars.length - 1];

    if (last && last.timestamp === bucket) {
      last.high = Math.max(last.high, tick.price);
      last.low = Math.min(last.low, tick.price);
      last.close = tick.price;
      last.volume += tick.volume;
    } else {
      bars.push({
        open: tick.price,
        high: tick.price,
        low: tick.price,
        close: tick.price,
        volume: tick.volume,
        timestamp: bucket,
      });
      if (bars.length > 200) bars.shift();
    }
  }
}

function generateSparkline(ticks: TickData[]): string {
  if (ticks.length < 2) return "";
  const w = 80;
  const h = 20;
  const prices = ticks.map((t) => t.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;

  const points = prices.map(
    (p, i) =>
      `${(i / (prices.length - 1)) * w},${h - ((p - min) / range) * h}`
  );
  return `<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg"><polyline points="${points.join(" ")}" fill="none" stroke="#00d4aa" stroke-width="1"/></svg>`;
}

function collectBatch(): BatchMessage {
  const ohlc: Record<string, OHLCAgg[]> = {};
  ohlcCache.forEach((intervals, sym) => {
    const m1 = intervals.get("1m");
    if (m1) ohlc[sym] = m1.slice(-10);
  });

  const sparklines: Record<string, string> = {};
  tickBuffers.forEach((ticks, sym) => {
    sparklines[sym] = generateSparkline(ticks);
  });

  return {
    type: "batch",
    ticks: Array.from(tickBuffers.values()).flat().slice(-100),
    ohlc,
    sparklines,
  };
}

self.onmessage = (e: MessageEvent<TickMessage | OHLCRequest>) => {
  const msg = e.data;

  if (msg.type === "tick") {
    const tick: TickData = {
      symbol: msg.symbol,
      price: msg.price,
      volume: msg.volume,
      timestamp: msg.timestamp,
    };
    pushTick(msg.symbol, tick);
    updateOHLC(msg.symbol, tick);

    const now = Date.now();
    if (now - lastEmit >= THROTTLE_MS) {
      lastEmit = now;
      self.postMessage(collectBatch());
    }
  }

  if (msg.type === "get_ohlc") {
    const symCache = ohlcCache.get(msg.symbol);
    const bars = symCache?.get(msg.interval)?.slice(-(msg.count ?? 100)) ?? [];
    self.postMessage({ type: "ohlc", symbol: msg.symbol, interval: msg.interval, bars });
  }
};

export {};
