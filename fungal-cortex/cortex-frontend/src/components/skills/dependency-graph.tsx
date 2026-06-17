"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { useSkillStore } from "@/stores/skill-store";
import type { Skill } from "@/types/skill";

const NODE_W = 130;
const NODE_H = 34;
const LAYER_GAP_X = 180;
const LAYER_GAP_Y = 50;
const PADDING = 40;

/* ─── SVG arrow marker ─── */
const MARKER_ID = "depArrowhead";

interface LayoutNode {
  skill: Skill;
  x: number;
  y: number;
  layer: number;
}

interface LayoutEdge {
  from: LayoutNode;
  to: LayoutNode;
  isDirect: boolean;
}

/* ─── Simple layered layout ─── */
function buildLayout(skills: Skill[], _selectedId: string | null): { nodes: LayoutNode[]; edges: LayoutEdge[] } {
  /* Build adjacency */
  const skillMap = new Map(skills.map((s) => [s.id, s]));
  const outgoing = new Map<string, string[]>();
  for (const s of skills) {
    outgoing.set(s.id, [...s.dependencies]);
  }

  /* Topological sort → layer assignment */
  const layer = new Map<string, number>();
  const visited = new Set<string>();
  function assign(id: string): number {
    if (layer.has(id)) return layer.get(id)!;
    if (visited.has(id)) return 0; /* cycle guard */
    visited.add(id);
    const deps = outgoing.get(id) ?? [];
    const maxDepLayer = deps.length === 0 ? 0 : Math.max(...deps.map(assign)) + 1;
    layer.set(id, maxDepLayer);
    return maxDepLayer;
  }
  for (const s of skills) {
    if (!visited.has(s.id)) assign(s.id);
  }

  /* Position nodes by layer */
  const layers = new Map<number, string[]>();
  for (const [id, l] of layer) {
    if (!layers.has(l)) layers.set(l, []);
    layers.get(l)!.push(id);
  }

  const nodes: LayoutNode[] = [];
  for (const [l, ids] of layers) {
    const sorted = ids.sort((a, b) => (skillMap.get(a)?.name ?? "").localeCompare(skillMap.get(b)?.name ?? ""));
    sorted.forEach((id, i) => {
      const sk = skillMap.get(id)!;
      nodes.push({
        skill: sk,
        x: PADDING + l * LAYER_GAP_X,
        y: PADDING + i * LAYER_GAP_Y,
        layer: l,
      });
    });
  }

  /* Edges: only direct dependencies (transitive reduction) */
  const nodeMap = new Map(nodes.map((n) => [n.skill.id, n]));
  const edges: LayoutEdge[] = [];
  for (const s of skills) {
    const from = nodeMap.get(s.id);
    if (!from) continue;
    for (const depId of s.dependencies) {
      const to = nodeMap.get(depId);
      if (!to) continue;
      /* Transitive reduction: skip if there's an indirect path */
      const indirect = skills.some(
        (m) => m.id !== s.id && m.id !== depId && m.dependencies.includes(depId) && s.dependencies.includes(m.id),
      );
      edges.push({ from, to, isDirect: !indirect });
    }
  }

  return { nodes, edges };
}

/* ─── Phase Transition Meter ─── */
function PhaseMeter() {
  const phaseMeter = useSkillStore((s) => s.phaseMeter);
  if (!phaseMeter) return null;

  const ratio = phaseMeter.n_crit > 0 ? phaseMeter.current_rings / phaseMeter.n_crit : 0;
  const pct = Math.min(ratio * 100, 100);

  const stateColors: Record<string, string> = {
    pre_critical: "#3b82f6",
    critical: "#f59e0b",
    supercritical: "#ef4444",
    degenerate: "#6b7280",
  };
  const stateLabels: Record<string, string> = {
    pre_critical: "Pre-Critical",
    critical: "Critical",
    supercritical: "Supercritical",
    degenerate: "Degenerate",
  };

  return (
    <div className="px-3 py-2 border-b border-[#1e1e3a]">
      <div className="flex items-center gap-3">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-[#a0a0c0] shrink-0">
          Phase Transition
        </span>
        <div className="flex-1 h-2 bg-[#1e1e3a] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${pct}%`,
              backgroundColor: stateColors[phaseMeter.state] ?? "#3b82f6",
            }}
          />
        </div>
        <span className="text-[10px] font-mono text-[#a0a0c0] shrink-0">
          {phaseMeter.current_rings}/{phaseMeter.n_crit}
        </span>
        <span
          className="text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded shrink-0"
          style={{
            backgroundColor: `${stateColors[phaseMeter.state]}20`,
            color: stateColors[phaseMeter.state],
          }}
        >
          {stateLabels[phaseMeter.state]}
        </span>
      </div>
    </div>
  );
}

/* ─── Legend ─── */
function Legend() {
  return (
    <div className="flex items-center gap-4 px-3 py-1.5 border-b border-[#1e1e3a]">
      <span className="text-[10px] text-[#a0a0c0]">Legend:</span>
      <span className="flex items-center gap-1 text-[10px] text-[#a0a0c0]">
        <svg width="14" height="10" viewBox="0 0 14 10">
          <line x1="0" y1="5" x2="14" y2="5" stroke="#00d4aa" strokeWidth="2" />
        </svg>
        Direct Dep
      </span>
      <span className="flex items-center gap-1 text-[10px] text-[#a0a0c0]">
        <svg width="14" height="10" viewBox="0 0 14 10">
          <line x1="0" y1="5" x2="14" y2="5" stroke="#1e1e3a" strokeWidth="1.5" strokeDasharray="3,3" />
        </svg>
        Transitive
      </span>
      <span className="flex items-center gap-1 text-[10px] text-[#a0a0c0]">
        <svg width="14" height="10" viewBox="0 0 14 10">
          <rect x="0" y="0" width="10" height="10" rx="2" fill="none" stroke="#f59e0b" strokeWidth="1.5" />
        </svg>
        Selected
      </span>
    </div>
  );
}

/* ─── Main component ─── */
export function DependencyGraph() {
  const skills = useSkillStore((s) => s.skills);
  const selectedSkill = useSkillStore((s) => s.selectedSkill);
  const selectSkill = useSkillStore((s) => s.selectSkill);

  const containerRef = useRef<HTMLDivElement>(null);
  const [viewScale, setViewScale] = useState(1);

  const layout = useMemo(() => buildLayout(skills, selectedSkill?.id ?? null), [skills]);

  /* Selected skill path highlighting */
  const highlightSet = useMemo(() => {
    if (!selectedSkill) return new Set<string>();
    const hs = new Set<string>();
    hs.add(selectedSkill.id);
    const deps = new Set(selectedSkill.dependencies);
    for (const depId of deps) hs.add(depId);
    for (const s of skills) {
      if (s.dependencies.includes(selectedSkill.id)) hs.add(s.id);
    }
    return hs;
  }, [selectedSkill, skills]);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setViewScale((s) => Math.max(0.3, Math.min(3, s * delta)));
  }, []);

  const totalW = layout.nodes.length > 0
    ? Math.max(...layout.nodes.map((n) => n.x)) + NODE_W + PADDING
    : 400;
  const totalH = layout.nodes.length > 0
    ? Math.max(...layout.nodes.map((n) => n.y)) + NODE_H + PADDING
    : 300;

  if (skills.length === 0) {
    return (
      <div className="rounded-lg border border-[#1e1e3a] bg-[#141428] p-6 text-center text-sm text-[#a0a0c0]">
        No skill data available
      </div>
    );
  }

  return (
    <div ref={containerRef} className="rounded-lg border border-[#1e1e3a] bg-[#141428] overflow-hidden flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#1e1e3a]">
        <span className="text-xs font-semibold uppercase tracking-wider text-[#a0a0c0]">
          Dependency Graph
        </span>
        <span className="text-[10px] text-[#a0a0c0] tabular-nums">
          {layout.nodes.length} skills, {layout.edges.length} edges
        </span>
      </div>

      <PhaseMeter />
      <Legend />

      {/* SVG canvas */}
      <svg
        width="100%"
        height={420}
        viewBox={`0 0 ${Math.max(totalW, 600) / viewScale} ${Math.max(totalH, 350) / viewScale}`}
        className="block"
        onWheel={handleWheel}
        style={{ minHeight: 350, cursor: "grab" }}
      >
        <defs>
          <marker
            id={MARKER_ID}
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="8"
            markerHeight="8"
            orient="auto"
          >
            <path d="M0,0 L10,5 L0,10 Z" fill="#a0a0c0" />
          </marker>
          <marker
            id={`${MARKER_ID}-highlight`}
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="8"
            markerHeight="8"
            orient="auto"
          >
            <path d="M0,0 L10,5 L0,10 Z" fill="#00d4aa" />
          </marker>
        </defs>

        {/* Edges */}
        {layout.edges.map((edge, i) => {
          const fromCx = edge.from.x + NODE_W / 2;
          const fromCy = edge.from.y + NODE_H / 2;
          const toCx = edge.to.x + NODE_W / 2;
          const toCy = edge.to.y + NODE_H / 2;
          const isHighlighted =
            highlightSet.has(edge.from.skill.id) && highlightSet.has(edge.to.skill.id);

          return (
            <line
              key={`edge-${i}`}
              x1={fromCx}
              y1={fromCy}
              x2={toCx}
              y2={toCy}
              stroke={isHighlighted ? "#00d4aa" : "#1e1e3a"}
              strokeWidth={isHighlighted ? 2 : edge.isDirect ? 1.5 : 1}
              strokeDasharray={edge.isDirect ? "none" : "4,3"}
              markerEnd={isHighlighted ? `url(#${MARKER_ID}-highlight)` : `url(#${MARKER_ID})`}
              opacity={isHighlighted ? 1 : 0.5}
            />
          );
        })}

        {/* Nodes */}
        {layout.nodes.map((node) => {
          const isSelected = selectedSkill?.id === node.skill.id;
          const isHighlighted = highlightSet.has(node.skill.id);

          return (
            <g
              key={node.skill.id}
              transform={`translate(${node.x}, ${node.y})`}
              onClick={() => selectSkill(node.skill)}
              style={{ cursor: "pointer" }}
            >
              <rect
                width={NODE_W}
                height={NODE_H}
                rx={6}
                ry={6}
                fill={isSelected ? "#00d4aa" : isHighlighted ? "#1a1a35" : "#141428"}
                stroke={isSelected ? "#00d4aa" : isHighlighted ? "#3b82f6" : "#1e1e3a"}
                strokeWidth={isSelected ? 2 : isHighlighted ? 1.5 : 1}
              />
              <text
                x={NODE_W / 2}
                y={NODE_H / 2 + 4}
                textAnchor="middle"
                className={`text-[10px] font-medium ${
                  isSelected ? "fill-[#0a0a0f]" : "fill-[#e2e8f0]"
                }`}
              >
                {node.skill.name.length > 14
                  ? node.skill.name.slice(0, 12) + "..."
                  : node.skill.name}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
