/** Skill Registry — 209 skills management + catalysis graph. */
"use client";

import { useEffect, useState, useMemo } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useSkillStore } from "@/stores/skill-store";
import { useWebSocket } from "@/hooks/use-websocket";
import { api } from "@/lib/api-client";
import type { Skill, SkillCategory, SkillDNA } from "@/types/skill";

const CATEGORIES: { key: SkillCategory; label: string; color: string }[] = [
  { key: "adaptive_engine", label: "Adaptive Engine", color: "#00d4aa" },
  { key: "data_provider", label: "Data Provider", color: "#3b82f6" },
  { key: "alphaear", label: "AlphaEar", color: "#8b5cf6" },
  { key: "quant_strategy", label: "Quant Strategy", color: "#f59e0b" },
  { key: "agent_plugin", label: "Agent Plugin", color: "#22c55e" },
  { key: "vertical_plugin", label: "Vertical Plugin", color: "#ec4899" },
  { key: "l6_core", label: "L6 Core", color: "#ef4444" },
  { key: "l6_safety", label: "L6 Safety", color: "#f97316" },
  { key: "l6_rules", label: "L6 Rules", color: "#84cc16" },
  { key: "orchestration", label: "Orchestration", color: "#06b6d4" },
  { key: "trading", label: "Trading", color: "#14b8a6" },
  { key: "monitoring", label: "Monitoring", color: "#a855f7" },
];

export default function SkillsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterCategory, setFilterCategory] = useState<SkillCategory | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);

  const {
    skills, phaseMeter,
    setSkills, setGraph, setPhaseMeter,
  } = useSkillStore();

  // Fetch initial skill data
  useEffect(() => {
    api.getSkills().then((data) => {
      const mapped: Skill[] = (data as Record<string, unknown>[]).map((item) => ({
        id: (item.id as string) ?? "",
        name: (item.name as string) ?? "",
        version: (item.version as string) ?? "1.0.0",
        category: (item.category as SkillCategory) ?? "quant_strategy",
        description: (item.description as string) ?? "",
        triggers: (item.triggers as string[]) ?? [],
        dependencies: (item.dependencies as string[]) ?? [],
        catalyzes: (item.catalyzes as string[]) ?? [],
        catalyzed_by: (item.catalyzed_by as string[]) ?? [],
        dna: item.dna as SkillDNA | undefined,
        call_count: (item.call_count as number) ?? 0,
        error_count: (item.error_count as number) ?? 0,
        avg_latency_ms: (item.avg_latency_ms as number) ?? 0,
        is_active: (item.is_active as boolean) ?? true,
        module: (item.module as string) ?? "",
      }));
      setSkills(mapped);
    }).catch(() => {});
  }, []);

  // Subscribe to skill registry WebSocket for live updates
  useWebSocket("skills", "skills", (data: unknown) => {
    const d = data as Record<string, unknown>;
    if (d.skills && Array.isArray(d.skills)) {
      const mapped: Skill[] = (d.skills as Array<Record<string, unknown>>).map((item) => ({
        id: (item.id as string) ?? "",
        name: (item.name as string) ?? "",
        version: (item.version as string) ?? "1.0.0",
        category: (item.category as SkillCategory) ?? "quant_strategy",
        description: (item.description as string) ?? "",
        triggers: (item.triggers as string[]) ?? [],
        dependencies: (item.dependencies as string[]) ?? [],
        catalyzes: (item.catalyzes as string[]) ?? [],
        catalyzed_by: (item.catalyzed_by as string[]) ?? [],
        dna: item.dna as SkillDNA | undefined,
        call_count: (item.call_count as number) ?? 0,
        error_count: (item.error_count as number) ?? 0,
        avg_latency_ms: (item.avg_latency_ms as number) ?? 0,
        is_active: (item.is_active as boolean) ?? true,
        module: (item.module as string) ?? "",
      }));
      setSkills(mapped);
    }
    if (d.graph) {
      setGraph(d.graph as any);
    }
    if (d.phase_meter) {
      setPhaseMeter(d.phase_meter as any);
    }
  });

  // Compute category counts from actual skills data
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const s of skills) {
      counts[s.category] = (counts[s.category] || 0) + 1;
    }
    return counts;
  }, [skills]);

  // Count skills involved in catalysis
  const catalyzingCount = useMemo(() => {
    return skills.filter((s) => s.catalyzes.length > 0).length;
  }, [skills]);

  // Filtered skill list based on search + category
  const filteredSkills = useMemo(() => {
    return skills.filter((s) => {
      if (filterCategory && s.category !== filterCategory) return false;
      if (searchQuery && !s.name.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      return true;
    });
  }, [skills, searchQuery, filterCategory]);

  // Phase transition derived values
  const phasePct = phaseMeter
    ? Math.min((phaseMeter.current_rings / phaseMeter.n_crit) * 100, 100)
    : 0;

  const phaseBadgeVariant =
    phaseMeter?.state === "critical" || phaseMeter?.state === "degenerate"
      ? "danger"
      : phaseMeter?.state === "supercritical"
        ? "warning"
        : "success";

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-bold font-mono text-cortex-primary">Skill Registry</h1>
        <div className="flex gap-2">
          <Badge variant="info">{skills.length} Skills</Badge>
          <Badge variant="warning">{catalyzingCount} Catalyzing</Badge>
          <Badge variant={phaseBadgeVariant}>
            Phase: {(phaseMeter?.state ?? "pre_critical").toUpperCase()}
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Category filter sidebar */}
        <div className="col-span-2 space-y-1">
          <Input
            placeholder="Search skills..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <div className="mt-2 space-y-0.5">
            <button
              className={`w-full text-left text-xs px-2 py-1 rounded ${!filterCategory ? "bg-cortex-primary/20 text-cortex-primary" : "text-gray-500 hover:text-white"}`}
              onClick={() => setFilterCategory(null)}
            >
              All ({skills.length})
            </button>
            {CATEGORIES.map((cat) => (
              <button
                key={cat.key}
                className={`w-full text-left text-xs px-2 py-1 rounded flex items-center gap-1.5 ${
                  filterCategory === cat.key ? "bg-cortex-primary/20 text-cortex-primary" : "text-gray-500 hover:text-white"
                }`}
                onClick={() => setFilterCategory(filterCategory === cat.key ? null : cat.key)}
              >
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: cat.color }} />
                {cat.label}
                <span className="ml-auto text-gray-600">{categoryCounts[cat.key] ?? 0}</span>
              </button>
            ))}
          </div>

          {/* Phase Transition Meter */}
          <Card className="mt-4">
            <div className="text-[10px] text-gray-500 mb-1">Phase Transition</div>
            <div className="h-2 rounded-full bg-cortex-border overflow-hidden mb-1">
              <div className="h-full rounded-full bg-amber-500" style={{ width: `${phasePct}%` }} />
            </div>
            <div className="flex justify-between text-[9px]">
              <span className="text-gray-600">{phaseMeter?.current_rings ?? 0} rings</span>
              <span className="text-gray-600">N_crit={phaseMeter?.n_crit ?? 10}</span>
            </div>
            <div className={`text-[10px] mt-1 ${phaseMeter?.state === "critical" ? "text-amber-400" : "text-gray-500"}`}>
              {(phaseMeter?.state ?? "pre_critical").toUpperCase()}
            </div>
          </Card>
        </div>

        {/* Skill grid */}
        <div className="col-span-7">
          {filteredSkills.length === 0 ? (
            <div className="text-xs text-gray-500 text-center py-16">
              {skills.length === 0
                ? "No skills loaded yet. Waiting for data..."
                : "No skills match your search. Try a different query or category."}
            </div>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-2">
                {filteredSkills.slice(0, 30).map((skill) => {
                  const cat = CATEGORIES.find((c) => c.key === skill.category);
                  return (
                    <Card
                      key={skill.id}
                      className={`cursor-pointer transition-all ${
                        selectedSkill?.id === skill.id ? "ring-1 ring-cortex-primary" : ""
                      } ${!skill.is_active ? "opacity-50" : ""}`}
                      onClick={() => setSelectedSkill(skill)}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: cat?.color ?? "#666" }} />
                        <div className="text-xs font-mono font-bold truncate">{skill.name}</div>
                      </div>
                      <div className="flex gap-1 flex-wrap">
                        <Badge variant="default" size="sm">{cat?.label ?? skill.category}</Badge>
                        {skill.call_count > 5000 && <Badge variant="warning" size="sm">hot</Badge>}
                        {!skill.is_active && <Badge variant="danger" size="sm">inactive</Badge>}
                      </div>
                    </Card>
                  );
                })}
              </div>
              {filteredSkills.length > 30 && (
                <div className="text-center text-xs text-gray-600 mt-3">
                  Showing 30 of {filteredSkills.length} skills. Refine search to see more.
                </div>
              )}
            </>
          )}
        </div>

        {/* Skill detail panel */}
        <div className="col-span-3">
          {selectedSkill ? (
            <Card>
              <div className="text-sm font-bold font-mono text-cortex-primary mb-2">{selectedSkill.name}</div>
              <Badge variant="default" size="sm">{selectedSkill.category}</Badge>
              <span className="text-xs text-gray-500 ml-2">v{selectedSkill.version}</span>
              <p className="text-xs text-gray-400 mt-2">{selectedSkill.description}</p>

              <div className="mt-3 space-y-1">
                <div className="text-[10px] text-gray-500">DNA Vector</div>
                {(["picker", "timer", "risk_control", "frequency", "complexity", "holding_period"] as (keyof SkillDNA)[]).map((dim) => (
                  <div key={dim} className="flex items-center gap-2">
                    <span className="text-[9px] text-gray-600 w-20">{dim.replace("_", " ")}</span>
                    <div className="flex-1 h-1 rounded-full bg-cortex-border overflow-hidden">
                      <div className="h-full rounded-full bg-cortex-primary" style={{ width: `${(selectedSkill.dna?.[dim] ?? 0) * 100}%` }} />
                    </div>
                    <span className="text-[9px] font-mono w-8 text-right">{((selectedSkill.dna?.[dim] ?? 0) * 100).toFixed(0)}</span>
                  </div>
                ))}
              </div>

              <div className="mt-3 grid grid-cols-2 gap-1 text-[10px]">
                <div className="text-gray-500">Calls</div>
                <div className="text-right font-mono">{selectedSkill.call_count.toLocaleString()}</div>
                <div className="text-gray-500">Errors</div>
                <div className="text-right font-mono text-red-400">{selectedSkill.error_count}</div>
                <div className="text-gray-500">Avg Latency</div>
                <div className="text-right font-mono">{selectedSkill.avg_latency_ms.toFixed(0)}ms</div>
                <div className="text-gray-500">Status</div>
                <div className="text-right">
                  <Badge variant={selectedSkill.is_active ? "success" : "danger"} size="sm">
                    {selectedSkill.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
              </div>

              {selectedSkill.catalyzes.length > 0 && (
                <div className="mt-3 pt-2 border-t border-cortex-border">
                  <div className="text-[10px] text-gray-500 mb-1">Catalyzes</div>
                  {selectedSkill.catalyzes.map((id) => (
                    <Badge key={id} variant="info" size="sm">{id}</Badge>
                  ))}
                </div>
              )}
            </Card>
          ) : (
            <Card>
              <div className="text-xs text-gray-600 text-center py-8">
                Select a skill to view details
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
