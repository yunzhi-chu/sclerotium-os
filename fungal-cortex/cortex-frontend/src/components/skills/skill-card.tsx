"use client";

import { useSkillStore } from "@/stores/skill-store";
import { SKILL_CATEGORY_LABELS, type SkillCategory } from "@/types/skill";

const CATEGORY_COLORS: Record<SkillCategory, string> = {
  adaptive_engine: "#f59e0b",
  data_provider: "#3b82f6",
  alphaear: "#22c55e",
  quant_strategy: "#7c3aed",
  agent_plugin: "#ec4899",
  vertical_plugin: "#14b8a6",
  l6_core: "#ef4444",
  l6_safety: "#f97316",
  l6_rules: "#06b6d4",
  orchestration: "#a855f7",
  trading: "#00d4aa",
  monitoring: "#6b7280",
};

const DNA_LABELS: { key: keyof import("@/types/skill").SkillDNA; label: string }[] = [
  { key: "picker", label: "Picker" },
  { key: "timer", label: "Timer" },
  { key: "risk_control", label: "Risk Control" },
  { key: "frequency", label: "Frequency" },
  { key: "complexity", label: "Complexity" },
  { key: "holding_period", label: "Holding Period" },
];

export function SkillCard() {
  const selectedSkill = useSkillStore((s) => s.selectedSkill);
  const selectSkill = useSkillStore((s) => s.selectSkill);
  const allSkills = useSkillStore((s) => s.skills);

  if (!selectedSkill) {
    return (
      <div className="rounded-lg border border-[#1e1e3a] bg-[#141428] p-6 text-center text-sm text-[#a0a0c0]">
        Select a skill to view details
      </div>
    );
  }

  const categoryColor = CATEGORY_COLORS[selectedSkill.category] ?? "#6b7280";
  const dna = selectedSkill.dna;

  const handleDependencyClick = (depId: string) => {
    const dep = allSkills.find((s) => s.id === depId);
    if (dep) selectSkill(dep);
  };

  return (
    <div className="rounded-lg border border-[#1e1e3a] bg-[#141428] overflow-hidden flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-[#1e1e3a] flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-white truncate">{selectedSkill.name}</h3>
            <span
              className="text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded shrink-0"
              style={{ backgroundColor: `${categoryColor}20`, color: categoryColor }}
            >
              {SKILL_CATEGORY_LABELS[selectedSkill.category]}
            </span>
          </div>
          <span className="text-[10px] text-[#a0a0c0] font-mono">
            v{selectedSkill.version} &middot; {selectedSkill.module}
          </span>
        </div>
        {selectedSkill.is_active ? (
          <span className="shrink-0 text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-[#22c55e]/15 text-[#22c55e]">
            Active
          </span>
        ) : (
          <span className="shrink-0 text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-[#ef4444]/15 text-[#ef4444]">
            Inactive
          </span>
        )}
      </div>

      {/* Description */}
      <div className="px-4 py-2.5 border-b border-[#1e1e3a]">
        <p className="text-xs text-[#c0c0e0] leading-relaxed">{selectedSkill.description}</p>
      </div>

      {/* DNA bars */}
      {dna && (
        <div className="px-4 py-3 border-b border-[#1e1e3a] flex flex-col gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[#a0a0c0]">
            DNA Profile
          </span>
          <div className="flex flex-col gap-1.5">
            {DNA_LABELS.map(({ key, label }) => {
              const val = dna[key];
              return (
                <div key={key} className="flex items-center gap-2">
                  <span className="text-[10px] text-[#a0a0c0] w-20 shrink-0">{label}</span>
                  <div className="flex-1 h-2 bg-[#1e1e3a] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${Math.min(val * 100, 100)}%`,
                        background: `linear-gradient(90deg, #00d4aa, ${categoryColor})`,
                      }}
                    />
                  </div>
                  <span className="text-[10px] text-white font-mono w-8 text-right">
                    {val.toFixed(2)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Triggers */}
      {selectedSkill.triggers.length > 0 && (
        <div className="px-4 py-2.5 border-b border-[#1e1e3a]">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[#a0a0c0] block mb-1.5">
            Triggers
          </span>
          <div className="flex flex-wrap gap-1">
            {selectedSkill.triggers.map((t) => (
              <span
                key={t}
                className="text-[9px] px-1.5 py-0.5 rounded bg-[#1e1e3a] text-[#a0a0c0] font-mono"
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Dependencies */}
      {selectedSkill.dependencies.length > 0 && (
        <div className="px-4 py-2.5 border-b border-[#1e1e3a]">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[#a0a0c0] block mb-1.5">
            Dependencies
          </span>
          <div className="flex flex-wrap gap-1">
            {selectedSkill.dependencies.map((depId) => {
              const dep = allSkills.find((s) => s.id === depId);
              return (
                <button
                  key={depId}
                  onClick={() => handleDependencyClick(depId)}
                  className="text-[10px] px-1.5 py-0.5 rounded bg-[#1e1e3a] text-[#3b82f6] hover:bg-[#2a2a5a] transition-colors cursor-pointer font-mono"
                >
                  {dep?.name ?? depId}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Catalyzes */}
      {selectedSkill.catalyzes.length > 0 && (
        <div className="px-4 py-2.5 border-b border-[#1e1e3a]">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[#a0a0c0] block mb-1.5">
            Catalyzes
          </span>
          <div className="flex flex-wrap gap-1">
            {selectedSkill.catalyzes.map((catId) => {
              const cat = allSkills.find((s) => s.id === catId);
              return (
                <button
                  key={catId}
                  onClick={() => handleDependencyClick(catId)}
                  className="text-[10px] px-1.5 py-0.5 rounded bg-[#1e1e3a] text-[#22c55e] hover:bg-[#2a2a5a] transition-colors cursor-pointer font-mono"
                >
                  {cat?.name ?? catId}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Catalyzed by */}
      {selectedSkill.catalyzed_by.length > 0 && (
        <div className="px-4 py-2.5 border-b border-[#1e1e3a]">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-[#a0a0c0] block mb-1.5">
            Catalyzed By
          </span>
          <div className="flex flex-wrap gap-1">
            {selectedSkill.catalyzed_by.map((catId) => {
              const cat = allSkills.find((s) => s.id === catId);
              return (
                <button
                  key={catId}
                  onClick={() => handleDependencyClick(catId)}
                  className="text-[10px] px-1.5 py-0.5 rounded bg-[#1e1e3a] text-[#f59e0b] hover:bg-[#2a2a5a] transition-colors cursor-pointer font-mono"
                >
                  {cat?.name ?? catId}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="px-4 py-3 flex flex-col gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[#a0a0c0]">
          Stats
        </span>
        <div className="grid grid-cols-3 gap-3">
          <div className="flex flex-col">
            <span className="text-[18px] font-bold text-white tabular-nums">{selectedSkill.call_count}</span>
            <span className="text-[9px] text-[#a0a0c0]">Calls</span>
          </div>
          <div className="flex flex-col">
            <span className="text-[18px] font-bold text-white tabular-nums">{selectedSkill.error_count}</span>
            <span className="text-[9px] text-[#a0a0c0]">Errors</span>
          </div>
          <div className="flex flex-col">
            <span className="text-[18px] font-bold text-white tabular-nums">{selectedSkill.avg_latency_ms}</span>
            <span className="text-[9px] text-[#a0a0c0]">Avg Latency</span>
          </div>
        </div>
      </div>
    </div>
  );
}
