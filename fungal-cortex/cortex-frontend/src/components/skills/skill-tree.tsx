"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSkillStore } from "@/stores/skill-store";
import { type SkillCategory, type Skill, type CatalysisEdge } from "@/types/skill";

/* ─── Color palette by category ─── */
const CAT_COLORS: Record<SkillCategory, string> = {
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

/* ─── Simulation node ─── */
interface SimNode {
  id: string;
  skill: Skill;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

/* ─── Force layout ─── */
function runForceLayout(
  nodes: SimNode[],
  edges: CatalysisEdge[],
  width: number,
  height: number,
  iterations: number,
): SimNode[] {
  const kRep = 2000;
  const kAtt = 0.008;
  const kCenter = 0.005;
  const damping = 0.7;
  const restLength = 80;

  for (let iter = 0; iter < iterations; iter++) {
    /* Repulsion */
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        let dx = nodes[j].x - nodes[i].x;
        let dy = nodes[j].y - nodes[i].y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = kRep / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        nodes[i].vx -= fx;
        nodes[i].vy -= fy;
        nodes[j].vx += fx;
        nodes[j].vy += fy;
      }
    }

    /* Attraction along edges */
    for (const edge of edges) {
      const s = nodes.find((n) => n.id === edge.source);
      const t = nodes.find((n) => n.id === edge.target);
      if (!s || !t) continue;
      let dx = t.x - s.x;
      let dy = t.y - s.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = kAtt * (dist - restLength);
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      s.vx += fx;
      s.vy += fy;
      t.vx -= fx;
      t.vy -= fy;
    }

    /* Center gravity */
    for (const node of nodes) {
      node.vx += (width / 2 - node.x) * kCenter;
      node.vy += (height / 2 - node.y) * kCenter;
    }

    /* Update */
    for (const node of nodes) {
      node.vx *= damping;
      node.vy *= damping;
      node.x += node.vx;
      node.y += node.vy;
      node.x = Math.max(20, Math.min(width - 20, node.x));
      node.y = Math.max(20, Math.min(height - 20, node.y));
    }
  }
  return nodes;
}

/* ─── RAF cycle sets ─── */
function useCycleMembers(): Set<string> {
  const graph = useSkillStore((s) => s.graph);
  return useMemo(() => {
    if (!graph) return new Set();
    const members = new Set<string>();
    for (const raf of graph.raf_sets) {
      for (const cycle of raf.cycles) {
        for (const id of cycle) {
          members.add(id);
        }
      }
    }
    return members;
  }, [graph]);
}

/* ─── Component ─── */
const SVG_W = 800;
const SVG_H = 600;
const MIN_R = 6;
const MAX_R = 22;

export function SkillTree() {
  const graph = useSkillStore((s) => s.graph);
  const selectedSkill = useSkillStore((s) => s.selectedSkill);
  const selectSkill = useSkillStore((s) => s.selectSkill);

  const cycleMembers = useCycleMembers();
  const containerRef = useRef<HTMLDivElement>(null);
  const [dim, setDim] = useState({ w: SVG_W, h: SVG_H });
  const [nodes, setNodes] = useState<SimNode[]>([]);
  const [hovered, setHovered] = useState<string | null>(null);
  const [dragId, setDragId] = useState<string | null>(null);

  /* View transform (pan + zoom) */
  const [view, setView] = useState({ x: 0, y: 0, scale: 1 });
  const [isPanning, setIsPanning] = useState(false);
  const panStart = useRef({ x: 0, y: 0, vx: 0, vy: 0 });

  /* Responsive */
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      for (const e of entries) {
        setDim({ w: e.contentRect.width, h: e.contentRect.height });
      }
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  /* Initialize force layout */
  useEffect(() => {
    if (!graph || graph.node_count === 0) return;
    const skillList = Object.values(graph.nodes);
    const simNodes: SimNode[] = skillList.map((sk, i) => {
      const angle = (2 * Math.PI * i) / skillList.length;
      const radius = 150 + Math.random() * 100;
      return {
        id: sk.id,
        skill: sk,
        x: dim.w / 2 + Math.cos(angle) * radius,
        y: dim.h / 2 + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
      };
    });
    const result = runForceLayout(simNodes, graph.edges, dim.w, dim.h, 150);
    setNodes(result);
  }, [graph, dim.w, dim.h]);

  /* Edge rendering */
  const edges = useMemo(() => {
    if (!graph) return [];
    return graph.edges.map((e) => {
      const s = nodes.find((n) => n.id === e.source);
      const t = nodes.find((n) => n.id === e.target);
      if (!s || !t) return null;
      const isStrong = e.weight >= 0.5 || e.edge_type === "strong";
      const isHighlighted =
        selectedSkill &&
        (e.source === selectedSkill.id || e.target === selectedSkill.id);
      return { s, t, isStrong, isHighlighted, edge: e };
    }).filter(Boolean);
  }, [graph, nodes, selectedSkill]);

  /* Event handlers */
  const handleNodePointerDown = useCallback(
    (e: React.PointerEvent, id: string) => {
      e.stopPropagation();
      setDragId(id);
      const el = e.currentTarget as SVGElement;
      el.setPointerCapture(e.pointerId);
    },
    [],
  );

  const handleSvgPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (dragId) {
        setNodes((prev) =>
          prev.map((n) =>
            n.id === dragId
              ? { ...n, x: n.x + e.movementX / view.scale, y: n.y + e.movementY / view.scale }
              : n,
          ),
        );
      }
      if (isPanning) {
        setView((v) => ({
          ...v,
          x: v.x + e.movementX,
          y: v.y + e.movementY,
        }));
      }
    },
    [dragId, isPanning, view.scale],
  );

  const handleSvgPointerUp = useCallback(() => {
    setDragId(null);
    setIsPanning(false);
  }, []);

  const handleBackgroundPointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (e.target === e.currentTarget) {
        setIsPanning(true);
        panStart.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y };
      }
    },
    [view],
  );

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setView((v) => ({ ...v, scale: Math.max(0.2, Math.min(5, v.scale * delta)) }));
  }, []);

  const nodeCount = nodes.length;
  const totalCount = graph?.node_count ?? 0;

  return (
    <div ref={containerRef} className="rounded-lg border border-[#1e1e3a] bg-[#141428] overflow-hidden flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#1e1e3a]">
        <span className="text-xs font-semibold uppercase tracking-wider text-[#a0a0c0]">
          Skill Network
        </span>
        <span className="text-[10px] text-[#a0a0c0] tabular-nums">
          Showing {nodeCount} of {totalCount} skills
          {graph && graph.total_cycles > 0 && (
            <span className="ml-2 text-[#f59e0b]">{graph.total_cycles} cycles</span>
          )}
        </span>
      </div>

      {/* SVG canvas */}
      <svg
        width={dim.w}
        height={dim.h}
        className="block cursor-grab active:cursor-grabbing"
        onPointerMove={handleSvgPointerMove}
        onPointerUp={handleSvgPointerUp}
        onPointerDown={handleBackgroundPointerDown}
        onWheel={handleWheel}
        style={{ minHeight: 400 }}
      >
        <g transform={`translate(${view.x}, ${view.y}) scale(${view.scale})`}>
          {/* Edges */}
          {edges.map((item) => {
            if (!item) return null;
            const { s, t, isStrong, isHighlighted, edge } = item;
            return (
              <line
                key={`${edge.source}-${edge.target}`}
                x1={s.x}
                y1={s.y}
                x2={t.x}
                y2={t.y}
                stroke={isHighlighted ? "#00d4aa" : "#1e1e3a"}
                strokeWidth={isHighlighted ? 2 : isStrong ? 1.5 : 1}
                strokeDasharray={isStrong ? "none" : "5,3"}
                opacity={isHighlighted ? 0.9 : 0.5}
              />
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            const color = CAT_COLORS[node.skill.category] ?? "#6b7280";
            const r = MIN_R + (MAX_R - MIN_R) * Math.min(node.skill.call_count / 100, 1);
            const isSelected = selectedSkill?.id === node.id;
            const isHovered = hovered === node.id;
            const inCycle = cycleMembers.has(node.id);

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                onPointerDown={(e) => handleNodePointerDown(e, node.id)}
                onPointerEnter={() => setHovered(node.id)}
                onPointerLeave={() => setHovered((h) => (h === node.id ? null : h))}
                onClick={(e) => {
                  e.stopPropagation();
                  selectSkill(node.skill);
                }}
                style={{ cursor: "pointer" }}
              >
                {/* RAF cycle ring */}
                {inCycle && (
                  <circle
                    r={r + 5}
                    fill="none"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    opacity={0.7}
                    className="edge-pulse"
                  />
                )}

                {/* Main circle */}
                <circle
                  r={r}
                  fill={color}
                  fillOpacity={isSelected ? 1 : isHovered ? 0.9 : 0.7}
                  stroke={isSelected ? "#fff" : "none"}
                  strokeWidth={isSelected ? 2 : 0}
                />

                {/* Hover tooltip */}
                {isHovered && (
                  <g>
                    <rect
                      x={-60}
                      y={-r - 30}
                      width={120}
                      height={22}
                      rx={4}
                      fill="#0a0a0f"
                      fillOpacity={0.95}
                      stroke="#1e1e3a"
                      strokeWidth={1}
                    />
                    <text
                      x={0}
                      y={-r - 15}
                      textAnchor="middle"
                      className="fill-white text-[9px] font-medium"
                    >
                      {node.skill.name}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
