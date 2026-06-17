/** Stigmergy Field — PDE reaction-diffusion-convection heatmap. */
"use client";

import { useEffect, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useFieldStore } from "@/stores/field-store";
import { useWebSocket } from "@/hooks/use-websocket";
import { api } from "@/lib/api-client";
import type { FieldLayer, FieldAgentPosition } from "@/types/field";

const FIELD_SIZE = 400;

const LAYER_INFO: Record<FieldLayer, { label: string; color: string; desc: string }> = {
  signal: { label: "Signal", color: "#ff4466", desc: "Agent communication deposits" },
  nutrient: { label: "Nutrient", color: "#44ff66", desc: "Resource availability gradient" },
  damage: { label: "Damage", color: "#888899", desc: "Error/failure accumulation" },
  temperature: { label: "Temperature", color: "#ff8844", desc: "Local kinetic energy" },
};

function toColor(val: number, layer: FieldLayer): string {
  // Dark (low) → bright (high)
  const r = Math.floor(10 + val * 240);
  const g = Math.floor(val * 100);
  const b = Math.floor(10 + val * 100);
  if (layer === "signal") return `rgb(${r},${g},${b})`;
  if (layer === "nutrient") return `rgb(${g},${r},${b})`;
  if (layer === "damage") return `rgb(${Math.floor(50 + val * 150)},${Math.floor(50 + val * 150)},${Math.floor(50 + val * 200)})`;
  return `rgb(${r},${Math.floor(50 + val * 150)},${b})`;
}

export default function FieldPage() {
  const {
    texture,
    agentPositions,
    activeLayer,
    showAgents,
    isPlaying,
    setTexture,
    setAgentPositions,
    setActiveLayer,
    toggleAgents,
    togglePlaying,
  } = useFieldStore();

  // Warm up API connection — real field data arrives via WebSocket
  useEffect(() => {
    api.getHealth().catch(() => {});
  }, []);

  // Subscribe to field WebSocket
  useWebSocket("field", "field", (data: unknown) => {
    const d = data as Record<string, unknown>;
    if (d.texture && typeof d.texture === "object") {
      const tex = d.texture as Record<string, unknown>;
      setTexture({
        width: (tex.width as number) ?? FIELD_SIZE,
        height: (tex.height as number) ?? FIELD_SIZE,
        rgba: (tex.rgba as Uint8Array) ?? new Uint8Array(FIELD_SIZE * FIELD_SIZE * 4),
      });
    }
    if (d.agents && Array.isArray(d.agents)) {
      const mapped: FieldAgentPosition[] = (d.agents as Array<Record<string, unknown>>).map((a) => ({
        agent_id: (a.agent_id as string) ?? "",
        x: (a.x as number) ?? 0,
        y: (a.y as number) ?? 0,
        specialty: (a.specialty as string) ?? "",
        trail: (a.trail as [number, number][]) ?? [],
      }));
      setAgentPositions(mapped);
    }
  });

  const renderCanvas = useCallback(
    (canvas: HTMLCanvasElement | null) => {
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      if (texture && texture.rgba && texture.rgba.length > 0) {
        const imgData = new ImageData(
          new Uint8ClampedArray(texture.rgba),
          texture.width,
          texture.height
        );
        ctx.putImageData(imgData, 0, 0);
      } else {
        // Fallback: dark empty canvas when no texture data yet
        ctx.fillStyle = "#0a0a0f";
        ctx.fillRect(0, 0, FIELD_SIZE, FIELD_SIZE);
      }

      // Draw agents from store data
      if (showAgents && agentPositions.length > 0) {
        const agentColors = ["#ff6644", "#44aaff", "#44ff88", "#ffaa44", "#ff44aa"];
        agentPositions.forEach((a, idx) => {
          const ax = a.x * FIELD_SIZE;
          const ay = a.y * FIELD_SIZE;
          const color = agentColors[idx % agentColors.length];
          ctx.beginPath();
          ctx.arc(ax, ay, 6, 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.fill();
          ctx.strokeStyle = "#fff";
          ctx.lineWidth = 1;
          ctx.stroke();
          // Trail arc
          if (a.trail && a.trail.length > 0) {
            ctx.beginPath();
            ctx.arc(ax, ay, 10, 0, Math.PI * 0.8);
            ctx.strokeStyle = color;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        });
      }
    },
    [texture, showAgents, agentPositions]
  );

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-bold font-mono text-cortex-primary">Stigmergy Field</h1>
        <div className="flex gap-2">
          <Badge variant="info">∂S/∂t = D∇²S - γS + C</Badge>
          <Button variant="ghost" size="sm" onClick={() => togglePlaying()}>
            {isPlaying ? "⏸" : "▶"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {/* Layer selector */}
        <div className="col-span-1 space-y-2">
          {(Object.entries(LAYER_INFO) as [FieldLayer, typeof LAYER_INFO[FieldLayer]][]).map(([key, info]) => (
            <Card
              key={key}
              className={`cursor-pointer transition-all ${activeLayer === key ? "ring-1 ring-cortex-primary" : ""}`}
              onClick={() => setActiveLayer(key)}
            >
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: info.color }} />
                <div>
                  <div className="text-xs font-bold">{info.label}</div>
                  <div className="text-[10px] text-gray-500">{info.desc}</div>
                </div>
              </div>
            </Card>
          ))}
          <div className="mt-4">
            <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
              <input type="checkbox" checked={showAgents} onChange={() => toggleAgents()}
                className="accent-cortex-primary" />
              Show Agents
            </label>
          </div>
        </div>

        {/* Field canvas */}
        <div className="col-span-3">
          <Card>
            <canvas
              ref={renderCanvas}
              width={FIELD_SIZE}
              height={FIELD_SIZE}
              className="w-full rounded"
              style={{ maxHeight: "calc(100vh - 180px)", objectFit: "contain" }}
            />
          </Card>
          {/* Legend */}
          <div className="flex items-center gap-2 mt-2 justify-center">
            <span className="text-[10px] text-gray-600">Low</span>
            <div className="h-3 w-48 rounded"
              style={{ background: `linear-gradient(to right, ${toColor(0, activeLayer)}, ${toColor(1, activeLayer)})` }} />
            <span className="text-[10px] text-gray-600">High</span>
          </div>
        </div>
      </div>
    </div>
  );
}
