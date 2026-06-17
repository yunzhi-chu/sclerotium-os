'use client';

import { useCallback } from 'react';
import { useFieldStore } from '@/stores/field-store';
import type { FieldLayer } from '@/types/field';

/* ------------------------------------------------------------------ */
/*  Layer config                                                      */
/* ------------------------------------------------------------------ */

interface LayerConfig {
  key: FieldLayer;
  label: string;
  /** Color used for the selector dot and active indicator. */
  accent: string;
  /** CSS gradient string (dark → bright) matching the field-renderer shader. */
  gradient: string;
}

const LAYERS: LayerConfig[] = [
  {
    key: 'signal',
    label: 'Signal',
    accent: '#ff4466',
    gradient: 'linear-gradient(to right, #0d051a, #3a0a1a, #8a1530, #e6264d)',
  },
  {
    key: 'nutrient',
    label: 'Nutrient',
    accent: '#44ff66',
    gradient: 'linear-gradient(to right, #050d05, #0a3a15, #1a8a30, #26d93e)',
  },
  {
    key: 'damage',
    label: 'Damage',
    accent: '#888899',
    gradient: 'linear-gradient(to right, #0d0d14, #2a2a3a, #55556a, #7a7a8a)',
  },
  {
    key: 'temperature',
    label: 'Temperature',
    accent: '#ffaa44',
    gradient: 'linear-gradient(to right, #050d1a, #1a2a3a, #8a5a10, #ff9916)',
  },
];

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

/**
 * Color legend bar for the Stigmergy field heatmap.
 *
 * Displays a gradient bar with min/max labels, plus layer selector
 * buttons that update the field store's activeLayer.
 */
export function FieldLegend() {
  const activeLayer = useFieldStore((s) => s.activeLayer);
  const setActiveLayer = useFieldStore((s) => s.setActiveLayer);

  const current = LAYERS.find((l) => l.key === activeLayer) ?? LAYERS[0];

  const handleLayerChange = useCallback(
    (layer: FieldLayer) => {
      setActiveLayer(layer);
    },
    [setActiveLayer],
  );

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-[#1e1e3a] bg-[#0a0a0f]/85 px-3 py-2.5 backdrop-blur-sm">
      {/* Layer selector buttons */}
      <div className="flex gap-1.5">
        {LAYERS.map((layer) => {
          const isActive = activeLayer === layer.key;
          return (
            <button
              key={layer.key}
              type="button"
              onClick={() => handleLayerChange(layer.key)}
              className="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs transition-all"
              style={{
                backgroundColor: isActive
                  ? `${layer.accent}22`
                  : 'transparent',
                color: isActive ? layer.accent : '#888899',
              }}
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: layer.accent }}
              />
              {layer.label}
            </button>
          );
        })}
      </div>

      {/* Gradient bar with min / max labels */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-[#666688]">0</span>
        <div
          className="h-3 flex-1 rounded"
          style={{
            background: current.gradient,
            boxShadow: `0 0 8px ${current.accent}33`,
          }}
        />
        <span className="text-[10px] text-[#666688]">1</span>
      </div>
    </div>
  );
}
