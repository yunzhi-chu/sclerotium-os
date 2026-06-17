"use client";

import { useRef, useEffect, useCallback, memo } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface OHLCBar {
  time: string | number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

interface TradingViewChartProps {
  /** OHLC data series */
  data: OHLCBar[];
  /** Chart height in pixels */
  height: number;
  /** Chart width in pixels (defaults to container width) */
  width?: number;
  /** Show volume bars at the bottom */
  showVolume?: boolean;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const COLORS = {
  bg: "#0a0a0f",
  surface: "#141428",
  border: "#1e1e3a",
  bullish: "#22c55e",
  bearish: "#ef4444",
  volumeBull: "rgba(34, 197, 94, 0.35)",
  volumeBear: "rgba(239, 68, 68, 0.35)",
  grid: "rgba(30, 30, 58, 0.5)",
  text: "#94a3b8",
  primary: "#00d4aa",
  crosshair: "rgba(0, 212, 170, 0.3)",
};

const CANDLE_WIDTH = 0.6; // fraction of available slot width
const VOLUME_HEIGHT_RATIO = 0.2; // bottom 20% for volume

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const TradingViewChart = memo(function TradingViewChart({
  data,
  height,
  width: explicitWidth,
  showVolume = true,
}: TradingViewChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const animationRef = useRef<number | null>(null);
  const crosshairRef = useRef<{ x: number; y: number } | null>(null);

  // -----------------------------------------------------------------------
  // Drawing
  // -----------------------------------------------------------------------
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const rect = container.getBoundingClientRect();
    const w = explicitWidth ?? rect.width;
    const h = height;

    // HiDPI
    const dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.scale(dpr, dpr);

    if (data.length === 0) {
      ctx.fillStyle = COLORS.bg;
      ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = COLORS.text;
      ctx.font = "12px monospace";
      ctx.textAlign = "center";
      ctx.fillText("No data", w / 2, h / 2);
      return;
    }

    // Layout
    const volumeH = showVolume ? Math.floor(h * VOLUME_HEIGHT_RATIO) : 0;
    const chartH = h - volumeH;
    const padding = { top: 16, right: 12, bottom: 8, left: 48 };
    const plotW = w - padding.left - padding.right;
    const plotH = chartH - padding.top - padding.bottom;

    // Compute extremes
    let minLow = Infinity;
    let maxHigh = -Infinity;
    let maxVolume = 0;

    for (const bar of data) {
      if (bar.low < minLow) minLow = bar.low;
      if (bar.high > maxHigh) maxHigh = bar.high;
      if (bar.volume !== undefined && bar.volume > maxVolume) {
        maxVolume = bar.volume;
      }
    }

    const range = maxHigh - minLow || 1;
    const slotW = plotW / data.length;

    // Map helpers
    const yPrice = (price: number): number =>
      padding.top + plotH - ((price - minLow) / range) * plotH;
    const yVolume = (vol: number): number =>
      chartH + volumeH - (vol / (maxVolume || 1)) * volumeH;

    // Clear
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, w, h);

    // Surface
    ctx.fillStyle = COLORS.surface;
    ctx.fillRect(0, 0, w, chartH);

    // Grid lines
    ctx.strokeStyle = COLORS.grid;
    ctx.lineWidth = 0.5;
    const gridLines = 6;
    for (let i = 0; i <= gridLines; i++) {
      const y = padding.top + (plotH / gridLines) * i;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(w - padding.right, y);
      ctx.stroke();

      // Price labels
      const price = maxHigh - (range / gridLines) * i;
      ctx.fillStyle = COLORS.text;
      ctx.font = "10px monospace";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(formatPrice(price), padding.left - 6, y);
    }

    // Candles
    for (let i = 0; i < data.length; i++) {
      const bar = data[i];
      const x = padding.left + slotW * i + slotW / 2;
      const isBull = bar.close >= bar.open;
      const color = isBull ? COLORS.bullish : COLORS.bearish;

      // High-low line (wick)
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, yPrice(bar.high));
      ctx.lineTo(x, yPrice(bar.low));
      ctx.stroke();

      // Open tick (left side)
      const tickW = Math.max(2, slotW * CANDLE_WIDTH * 0.5);
      ctx.beginPath();
      ctx.moveTo(x - tickW, yPrice(bar.open));
      ctx.lineTo(x, yPrice(bar.open));
      ctx.stroke();

      // Close tick (right side)
      ctx.beginPath();
      ctx.moveTo(x, yPrice(bar.close));
      ctx.lineTo(x + tickW, yPrice(bar.close));
      ctx.stroke();

      // Volume bar
      if (showVolume && bar.volume !== undefined && bar.volume > 0) {
        const vBarW = Math.max(1, slotW * 0.6);
        const vx = padding.left + slotW * i + (slotW - vBarW) / 2;
        const vy = yVolume(bar.volume);
        ctx.fillStyle = isBull ? COLORS.volumeBull : COLORS.volumeBear;
        ctx.fillRect(vx, vy, vBarW, chartH + volumeH - vy);
      }
    }

    // Crosshair
    const ch = crosshairRef.current;
    if (ch && ch.x >= padding.left && ch.x <= w - padding.right) {
      ctx.strokeStyle = COLORS.crosshair;
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);

      // Vertical
      ctx.beginPath();
      ctx.moveTo(ch.x, 0);
      ctx.lineTo(ch.x, h);
      ctx.stroke();

      ctx.setLineDash([]);

      // Hovered bar info
      const idx = Math.round((ch.x - padding.left) / slotW - 0.5);
      if (idx >= 0 && idx < data.length) {
        const bar = data[idx];
        const info = `O:${bar.open}  H:${bar.high}  L:${bar.low}  C:${bar.close}`;
        ctx.fillStyle = "rgba(20, 20, 40, 0.9)";
        const textW = ctx.measureText(info).width;
        const boxX = Math.min(ch.x + 12, w - textW - 16);
        const boxY = 4;
        ctx.fillRect(boxX, boxY, textW + 16, 22);
        ctx.strokeStyle = COLORS.border;
        ctx.lineWidth = 1;
        ctx.strokeRect(boxX, boxY, textW + 16, 22);
        ctx.fillStyle = COLORS.primary;
        ctx.font = "11px monospace";
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.fillText(info, boxX + 8, boxY + 12);
      }
    }
  }, [data, height, explicitWidth, showVolume]);

  // -----------------------------------------------------------------------
  // Effects
  // -----------------------------------------------------------------------
  useEffect(() => {
    draw();
  }, [draw]);

  // Resize
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver(() => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      animationRef.current = requestAnimationFrame(draw);
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [draw]);

  // -----------------------------------------------------------------------
  // Mouse handlers
  // -----------------------------------------------------------------------
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;

      const rect = container.getBoundingClientRect();
      crosshairRef.current = {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      };
      draw();
    },
    [draw],
  );

  const handleMouseLeave = useCallback(() => {
    crosshairRef.current = null;
    draw();
  }, [draw]);

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  return (
    <div
      ref={containerRef}
      style={{
        width: explicitWidth ? `${explicitWidth}px` : "100%",
        height: `${height}px`,
        position: "relative",
        borderRadius: 8,
        overflow: "hidden",
        border: "1px solid",
        borderColor: COLORS.border,
        backgroundColor: COLORS.bg,
      }}
    >
      <canvas
        ref={canvasRef}
        style={{ display: "block", cursor: "crosshair" }}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      />
    </div>
  );
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatPrice(p: number): string {
  if (Math.abs(p) >= 1000) return p.toFixed(0);
  if (Math.abs(p) >= 1) return p.toFixed(2);
  return p.toFixed(4);
}

export type { TradingViewChartProps };
export { TradingViewChart };
