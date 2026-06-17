import { useEffect, useRef } from "react";
import { useWebSocket } from "./use-websocket";
import { useFieldStore } from "@/stores/field-store";
import type { FieldAgentPosition } from "@/types/field";

interface FieldUpdate {
  signal: Float64Array;
  nutrient: Float64Array;
  damage: Float64Array;
  temperature: Float64Array;
  agents: FieldAgentPosition[];
}

export function useStigmergyField(enabled: boolean = true): void {
  const setAgentPositions = useFieldStore((s) => s.setAgentPositions);
  const workerRef = useRef<Worker | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useWebSocket(
    "field",
    "field_update",
    (data) => {
      const update = data as FieldUpdate;
      if (update.agents) setAgentPositions(update.agents);
      // Field texture rendering handled by the FieldRenderer in the component
    },
    enabled
  );

  useEffect(() => {
    if (!enabled) return;
    const worker = new Worker(
      new URL("@/workers/field-solver.worker.ts", import.meta.url)
    );
    workerRef.current = worker;
    return () => worker.terminate();
  }, [enabled]);

  // Expose worker and canvas refs for the field component
  (useStigmergyField as unknown as Record<string, unknown>)._workerRef = workerRef;
  (useStigmergyField as unknown as Record<string, unknown>)._canvasRef = canvasRef;
}
