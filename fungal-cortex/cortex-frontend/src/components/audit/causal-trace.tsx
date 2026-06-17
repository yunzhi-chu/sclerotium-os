"use client";

import { useCallback, useMemo, useState } from "react";
import type { CausalTrace, AuditRecord, CausalEdge } from "@/types/audit";

/* ─── Result badge colors ─── */
const RESULT_COLORS: Record<string, string> = {
  success: "bg-[#22c55e]/15 text-[#22c55e]",
  failure: "bg-[#ef4444]/15 text-[#ef4444]",
  pending: "bg-[#f59e0b]/15 text-[#f59e0b]",
};

/* ─── Props ─── */
interface CausalTraceProps {
  trace?: CausalTrace | null;
  eventId?: string;
  _onFetch?: (eventId: string) => Promise<CausalTrace>;
  loading?: boolean;
}

/* ─── Helpers ─── */
function formatTime(ts: number): string {
  return new Date(ts).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

interface TraceNode extends AuditRecord {
  direction: "upstream" | "downstream" | "root";
  incomingEdges: CausalEdge[];
  outgoingEdges: CausalEdge[];
}

/* ─── Component ─── */
export function CausalTrace({ trace, eventId, loading = false }: CausalTraceProps) {
  const [selectedNode, setSelectedNode] = useState<AuditRecord | null>(null);

  const resolvedTrace = trace;

  /* Build enriched node list */
  const allNodes: TraceNode[] = useMemo(() => {
    if (!resolvedTrace) return [];
    const nodes: TraceNode[] = [];

    /* Root */
    nodes.push({
      ...resolvedTrace.root_event,
      direction: "root",
      incomingEdges: [],
      outgoingEdges: [],
    });

    /* Upstream */
    for (const ev of resolvedTrace.upstream) {
      nodes.push({
        ...ev,
        direction: "upstream",
        incomingEdges: [],
        outgoingEdges: [],
      });
    }

    /* Downstream */
    for (const ev of resolvedTrace.downstream) {
      nodes.push({
        ...ev,
        direction: "downstream",
        incomingEdges: [],
        outgoingEdges: [],
      });
    }

    /* Attach edges */
    for (const edge of resolvedTrace.causal_graph) {
      const fromNode = nodes.find((n) => n.id === edge.from);
      const toNode = nodes.find((n) => n.id === edge.to);
      if (fromNode) fromNode.outgoingEdges.push(edge);
      if (toNode) toNode.incomingEdges.push(edge);
    }

    return nodes;
  }, [resolvedTrace]);

  /* Layout positions */
  const nodePositions = useMemo(() => {
    if (allNodes.length === 0) return {};
    const positions: Record<string, { x: number; y: number }> = {};
    const W = 800;
    const H = 500;
    const centerY = H / 2;
    const gap = 70;

    const upstream = allNodes.filter((n) => n.direction === "upstream");
    const downstream = allNodes.filter((n) => n.direction === "downstream");
    const root = allNodes.find((n) => n.direction === "root");

    /* Root at center */
    if (root) {
      positions[root.id] = { x: W / 2, y: centerY };
    }

    /* Upstream above */
    const upCount = upstream.length;
    upCount > 0 &&
      upstream.forEach((n, i) => {
        const totalW = (upCount - 1) * gap;
        positions[n.id] = { x: W / 2 - totalW / 2 + i * gap, y: centerY - 120 };
      });

    /* Downstream below */
    const downCount = downstream.length;
    downCount > 0 &&
      downstream.forEach((n, i) => {
        const totalW = (downCount - 1) * gap;
        positions[n.id] = { x: W / 2 - totalW / 2 + i * gap, y: centerY + 120 };
      });

    return positions;
  }, [allNodes]);

  const handleNodeClick = useCallback((node: AuditRecord) => {
    setSelectedNode((prev) => (prev?.id === node.id ? null : node));
  }, []);

  /* Loading state */
  if (loading) {
    return (
      <div className="rounded-lg border border-[#1e1e3a] bg-[#141428] p-6 text-center text-sm text-[#a0a0c0]">
        Loading causal trace...
      </div>
    );
  }

  /* Empty state */
  if (!resolvedTrace) {
    return (
      <div className="rounded-lg border border-[#1e1e3a] bg-[#141428] p-6 text-center text-sm text-[#a0a0c0]">
        {eventId
          ? `No trace found for event ${eventId}`
          : "No trace data available. Pass a CausalTrace or eventId."}
      </div>
    );
  }

  const hasUpstream = resolvedTrace.upstream.length > 0;
  const hasDownstream = resolvedTrace.downstream.length > 0;

  return (
    <div className="rounded-lg border border-[#1e1e3a] bg-[#141428] overflow-hidden flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#1e1e3a]">
        <span className="text-xs font-semibold uppercase tracking-wider text-[#a0a0c0]">
          Causal Trace
        </span>
        <div className="flex items-center gap-2 text-[10px] text-[#a0a0c0]">
          <span>
            {resolvedTrace.upstream.length} cause{resolvedTrace.upstream.length !== 1 ? "s" : ""}
          </span>
          <span>&middot;</span>
          <span>
            {resolvedTrace.downstream.length} effect
            {resolvedTrace.downstream.length !== 1 ? "s" : ""}
          </span>
          <span>&middot;</span>
          <span>{resolvedTrace.causal_graph.length} edges</span>
        </div>
      </div>

      {/* SVG canvas */}
      <svg
        width="100%"
        height={500}
        viewBox="0 0 800 500"
        className="block"
        style={{ minHeight: 400 }}
      >
        <defs>
          <marker
            id="causalArrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto"
          >
            <path d="M0,1 L8,5 L0,9 Z" fill="#a0a0c0" />
          </marker>
          <marker
            id="causalArrowHighlight"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto"
          >
            <path d="M0,1 L8,5 L0,9 Z" fill="#00d4aa" />
          </marker>
        </defs>

        {/* Direction labels */}
        {hasUpstream && (
          <text x="400" y="30" textAnchor="middle" className="fill-[#a0a0c0] text-[10px] font-semibold uppercase tracking-wider">
            Causes (Upstream)
          </text>
        )}
        {hasDownstream && (
          <text x="400" y="478" textAnchor="middle" className="fill-[#a0a0c0] text-[10px] font-semibold uppercase tracking-wider">
            Effects (Downstream)
          </text>
        )}

        {/* Edges */}
        {resolvedTrace.causal_graph.map((edge, i) => {
          const fromPos = nodePositions[edge.from];
          const toPos = nodePositions[edge.to];
          if (!fromPos || !toPos) return null;
          const isHighlighted = selectedNode && (selectedNode.id === edge.from || selectedNode.id === edge.to);
          return (
            <g key={`edge-${i}`}>
              <line
                x1={fromPos.x}
                y1={fromPos.y + 20}
                x2={toPos.x}
                y2={toPos.y - 20}
                stroke={isHighlighted ? "#00d4aa" : "#a0a0c0"}
                strokeWidth={isHighlighted ? 2 : 1}
                markerEnd={isHighlighted ? "url(#causalArrowHighlight)" : "url(#causalArrow)"}
                opacity={isHighlighted ? 1 : 0.5}
              />
              {/* Edge label */}
              <text
                x={(fromPos.x + toPos.x) / 2}
                y={(fromPos.y + toPos.y) / 2 - 6}
                textAnchor="middle"
                className="fill-[#a0a0c0] text-[8px]"
              >
                {edge.relationship} ({edge.confidence}%)
              </text>
            </g>
          );
        })}

        {/* Nodes */}
        {allNodes.map((node) => {
          const pos = nodePositions[node.id];
          if (!pos) return null;
          const isSelected = selectedNode?.id === node.id;
          const isRoot = node.direction === "root";
          const nodeW = isRoot ? 200 : 170;
          const nodeH = isRoot ? 50 : 44;

          return (
            <g
              key={node.id}
              transform={`translate(${pos.x - nodeW / 2}, ${pos.y - nodeH / 2})`}
              onClick={() => handleNodeClick(node)}
              style={{ cursor: "pointer" }}
            >
              <rect
                width={nodeW}
                height={nodeH}
                rx={8}
                ry={8}
                fill={isRoot ? "#00d4aa" : isSelected ? "#1a1a35" : "#141428"}
                stroke={isSelected ? "#00d4aa" : isRoot ? "#00d4aa" : "#1e1e3a"}
                strokeWidth={isSelected || isRoot ? 2 : 1}
              />
              <text
                x={nodeW / 2}
                y={14}
                textAnchor="middle"
                className={isRoot ? "fill-[#0a0a0f] text-[10px] font-bold" : "fill-white text-[10px] font-medium"}
              >
                {node.event_type.replace(/_/g, " ")}
              </text>
              <text
                x={nodeW / 2}
                y={28}
                textAnchor="middle"
                className={isRoot ? "fill-[#0a0a0f] text-[8px]" : "fill-[#a0a0c0] text-[8px]"}
              >
                {formatTime(node.timestamp)}
              </text>
              {/* Result badge */}
              <rect x={nodeW / 2 - 24} y={32} width={48} height={14} rx={4} fill="#0a0a0f" opacity={0.8} />
              <text
                x={nodeW / 2}
                y={43}
                textAnchor="middle"
                className={`text-[8px] font-semibold uppercase ${RESULT_COLORS[node.result]?.replace("bg-[#22c55e]/15", "").replace("bg-[#ef4444]/15", "").replace("bg-[#f59e0b]/15", "").trim() || "fill-[#a0a0c0]"}`}
              >
                {node.result}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Selected node details sidebar */}
      {selectedNode && (
        <div className="border-t border-[#1e1e3a] p-3 bg-[#0a0a0f]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[#a0a0c0]">
              Event Details
            </span>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-[10px] text-[#a0a0c0] hover:text-white transition-colors"
            >
              Close
            </button>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
            <span className="text-[#a0a0c0]">ID:</span>
            <span className="text-white font-mono">{selectedNode.id}</span>
            <span className="text-[#a0a0c0]">Event:</span>
            <span className="text-white">{selectedNode.event_type.replace(/_/g, " ")}</span>
            <span className="text-[#a0a0c0]">Source:</span>
            <span className="text-white">{selectedNode.source_module}</span>
            <span className="text-[#a0a0c0]">Operation:</span>
            <span className="text-white">{selectedNode.operation}</span>
            <span className="text-[#a0a0c0]">Result:</span>
            <span className="text-white">{selectedNode.result}</span>
            <span className="text-[#a0a0c0]">Severity:</span>
            <span className="text-white capitalize">{selectedNode.severity}</span>
            <span className="text-[#a0a0c0]">Evidence:</span>
            <span className="text-white font-mono text-[10px]">{selectedNode.evidence_hash.slice(0, 16)}...</span>
          </div>
          {Object.keys(selectedNode.details).length > 0 && (
            <details className="mt-2">
              <summary className="text-[10px] text-[#a0a0c0] cursor-pointer hover:text-white">
                View Details JSON
              </summary>
              <pre className="text-[10px] text-[#c0c0e0] font-mono mt-1 whitespace-pre-wrap max-h-32 overflow-auto bg-[#141428] rounded p-2">
                {JSON.stringify(selectedNode.details, null, 2)}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
