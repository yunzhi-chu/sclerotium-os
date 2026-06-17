'use client';

import { useRef, useEffect, useCallback } from 'react';
import { FieldRenderer } from '@/lib/field-renderer';
import { useFieldStore } from '@/stores/field-store';

export interface FieldData {
  signal: Float64Array;
  nutrient: Float64Array;
  damage: Float64Array;
  temperature: Float64Array;
}

interface StigmergyCanvasProps {
  /** Raw field concentration arrays (must all be the same length). */
  data: FieldData | null;
  /** Grid resolution width used when data was generated. */
  gridWidth: number;
  /** Grid resolution height used when data was generated. */
  gridHeight: number;
}

/**
 * WebGL2 field heatmap canvas that renders the Stigmergy field
 * (signal / nutrient / damage / temperature) using the FieldRenderer.
 *
 * Manages its own canvas element, resize observer, and requestAnimationFrame
 * loop. Reads activeLayer and isPlaying from the field store.
 */
export function StigmergyCanvas({
  data,
  gridWidth,
  gridHeight,
}: StigmergyCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<FieldRenderer | null>(null);
  const rafRef = useRef<number>(0);

  const activeLayer = useFieldStore((s) => s.activeLayer);
  const isPlaying = useFieldStore((s) => s.isPlaying);

  // -- Initialize / destroy FieldRenderer ----------------------------------
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    let renderer: FieldRenderer;
    try {
      renderer = new FieldRenderer(canvas);
    } catch (err) {
      console.error('[StigmergyCanvas] WebGL2 init failed:', err);
      return;
    }

    renderer.resize(gridWidth, gridHeight);
    rendererRef.current = renderer;

    return () => {
      renderer.destroy();
      rendererRef.current = null;
      cancelAnimationFrame(rafRef.current);
    };
  }, [gridWidth, gridHeight]);

  // -- Sync active layer uniform -------------------------------------------
  useEffect(() => {
    rendererRef.current?.setLayer(activeLayer);
  }, [activeLayer]);

  // -- Push new field data into textures -----------------------------------
  useEffect(() => {
    if (!data || !rendererRef.current) return;
    rendererRef.current.updateTextures(data);
  }, [data]);

  // -- Start / stop render loop --------------------------------------------
  useEffect(() => {
    rendererRef.current?.stop();

    if (isPlaying && rendererRef.current) {
      rendererRef.current.start();
    }
  }, [isPlaying]);

  // -- Resize handling -----------------------------------------------------
  const handleResize = useCallback(() => {
    const container = containerRef.current;
    const renderer = rendererRef.current;
    if (!container || !renderer) return;

    const rect = container.getBoundingClientRect();
    const w = Math.floor(rect.width);
    const h = Math.floor(rect.height);

    const canvas = canvasRef.current;
    if (canvas) {
      canvas.width = w;
      canvas.height = h;
    }
    renderer.resize(w, h);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const ro = new ResizeObserver(handleResize);
    ro.observe(container);
    handleResize();

    return () => ro.disconnect();
  }, [handleResize]);

  // -- Cleanup on unmount is handled by the first effect's return ----------

  return (
    <div
      ref={containerRef}
      className="canvas-container"
      style={{ position: 'absolute', inset: 0 }}
    >
      <canvas
        ref={canvasRef}
        style={{ display: 'block', width: '100%', height: '100%' }}
      />
    </div>
  );
}
