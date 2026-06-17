'use client';

import { useCallback } from 'react';
import { useAgentStore } from '@/stores/agent-store';
import type { AgentSpecialty } from '@/types/agent';
import { SPECIALTY_COLORS, SPECIALTY_LABELS } from '@/types/agent';

interface NetworkControlsProps {
  autoRotate: boolean;
  onToggleAutoRotate: () => void;
  wireframe: boolean;
  onToggleWireframe: () => void;
  onResetCamera: () => void;
}

const SPECIALTIES: AgentSpecialty[] = [
  'regime',
  'strategy',
  'indicator',
  'tactical',
  'risk',
];

/** Floating overlay panel for controlling the 3D mycelial network view. */
export function NetworkControls({
  autoRotate,
  onToggleAutoRotate,
  wireframe,
  onToggleWireframe,
  onResetCamera,
}: NetworkControlsProps) {
  const showCatalysis = useAgentStore((s) => s.showCatalysis);
  const toggleCatalysis = useAgentStore((s) => s.toggleCatalysis);
  const showInactive = useAgentStore((s) => s.showInactive);
  const toggleInactive = useAgentStore((s) => s.toggleInactive);
  const filterSpecialty = useAgentStore((s) => s.filterSpecialty);
  const setFilterSpecialty = useAgentStore((s) => s.setFilterSpecialty);

  const handleSpecialtyClick = useCallback(
    (spec: AgentSpecialty) => {
      setFilterSpecialty(filterSpecialty === spec ? null : spec);
    },
    [filterSpecialty, setFilterSpecialty],
  );

  return (
    <div className="pointer-events-none absolute bottom-4 right-4 z-20 flex flex-col gap-2">
      {/* Camera & display toggles */}
      <div className="pointer-events-auto flex flex-col gap-1.5 rounded-lg border border-[#1e1e3a] bg-[#0a0a0f]/90 px-3 py-2.5 backdrop-blur-sm">
        <span className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-[#666688]">
          Display
        </span>

        <button
          type="button"
          onClick={onToggleAutoRotate}
          className={`flex items-center gap-2 rounded px-2.5 py-1 text-xs transition-colors ${
            autoRotate
              ? 'bg-[#00d4aa]/15 text-[#00d4aa]'
              : 'text-[#888899] hover:bg-[#141428] hover:text-[#e2e8f0]'
          }`}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-current" />
          Auto-rotate
        </button>

        <button
          type="button"
          onClick={onToggleWireframe}
          className={`flex items-center gap-2 rounded px-2.5 py-1 text-xs transition-colors ${
            wireframe
              ? 'bg-[#7c3aed]/15 text-[#7c3aed]'
              : 'text-[#888899] hover:bg-[#141428] hover:text-[#e2e8f0]'
          }`}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-current" />
          Wireframe
        </button>

        <button
          type="button"
          onClick={toggleCatalysis}
          className={`flex items-center gap-2 rounded px-2.5 py-1 text-xs transition-colors ${
            showCatalysis
              ? 'bg-[#ffaa44]/15 text-[#ffaa44]'
              : 'text-[#888899] hover:bg-[#141428] hover:text-[#e2e8f0]'
          }`}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-current" />
          Catalysis
        </button>

        <button
          type="button"
          onClick={toggleInactive}
          className={`flex items-center gap-2 rounded px-2.5 py-1 text-xs transition-colors ${
            showInactive
              ? 'bg-[#666688]/15 text-[#666688]'
              : 'text-[#888899] hover:bg-[#141428] hover:text-[#e2e8f0]'
          }`}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-current" />
          Inactive
        </button>
      </div>

      {/* Specialty filters */}
      <div className="pointer-events-auto flex flex-col gap-1.5 rounded-lg border border-[#1e1e3a] bg-[#0a0a0f]/90 px-3 py-2.5 backdrop-blur-sm">
        <span className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-[#666688]">
          Specialty
        </span>

        <div className="flex flex-wrap gap-1.5">
          {SPECIALTIES.map((spec) => {
            const active = filterSpecialty === spec;
            const specColor = SPECIALTY_COLORS[spec];
            return (
              <button
                key={spec}
                type="button"
                onClick={() => handleSpecialtyClick(spec)}
                className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs transition-all ${
                  active
                    ? 'text-white ring-1'
                    : 'text-[#888899] hover:bg-[#141428] hover:text-[#e2e8f0]'
                }`}
                style={{
                  backgroundColor: active ? `${specColor}22` : 'transparent',
                }}
              >
                <span
                  className="h-2 w-2 rounded-full"
                  style={{ backgroundColor: specColor }}
                />
                {SPECIALTY_LABELS[spec]}
              </button>
            );
          })}
        </div>
      </div>

      {/* Reset camera */}
      <button
        type="button"
        onClick={onResetCamera}
        className="pointer-events-auto flex items-center gap-2 self-end rounded-lg border border-[#1e1e3a] bg-[#0a0a0f]/90 px-3 py-2 text-xs text-[#888899] backdrop-blur-sm transition-colors hover:bg-[#141428] hover:text-[#e2e8f0]"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
          <path d="M3 3v5h5" />
        </svg>
        Reset Camera
      </button>
    </div>
  );
}
