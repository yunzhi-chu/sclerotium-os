/** Agent Network — 3D Mycelial Network Topology. */
"use client";

import { Suspense } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

function AgentNetwork3D() {
  return (
    <div className="relative w-full h-full">
      {/* Fallback SVG visualization until R3F components are loaded */}
      <svg viewBox="0 0 800 600" className="w-full h-full" preserveAspectRatio="xMidYMid meet">
        <defs>
          <radialGradient id="bg" cx="50%" cy="50%">
            <stop offset="0%" stopColor="#141428" />
            <stop offset="100%" stopColor="#0a0a0f" />
          </radialGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect width="800" height="600" fill="url(#bg)" />

        {/* Edges */}
        {[
          [200, 100, 350, 200], [200, 100, 350, 400],
          [350, 200, 500, 150], [350, 200, 500, 300],
          [350, 400, 500, 300], [350, 400, 500, 450],
          [500, 150, 650, 300], [500, 300, 650, 300], [500, 450, 650, 300],
        ].map(([x1, y1, x2, y2], i) => (
          <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
            stroke={["#ff4466", "#44ff66", "#44aaff", "#ffaa44", "#888899"][i % 5]}
            strokeWidth={0.5 + (i % 3) * 0.5}
            opacity={0.3 + Math.sin(i) * 0.2}>
            <animate attributeName="opacity" values="0.2;0.6;0.2" dur={`${2 + i}s`} repeatCount="indefinite" />
          </line>
        ))}

        {/* Nodes */}
        {[
          { x: 200, y: 100, r: 12, color: "#ff6644", label: "Regime-1" },
          { x: 350, y: 200, r: 15, color: "#44aaff", label: "Strategy-1" },
          { x: 350, y: 400, r: 10, color: "#44ff88", label: "Indicator-1" },
          { x: 500, y: 150, r: 14, color: "#ffaa44", label: "Tactical-1" },
          { x: 500, y: 300, r: 8, color: "#ff44aa", label: "Risk-1" },
          { x: 500, y: 450, r: 11, color: "#44aaff", label: "Strategy-2" },
          { x: 650, y: 300, r: 13, color: "#ff6644", label: "Regime-2" },
        ].map((node, i) => (
          <g key={i}>
            <circle cx={node.x} cy={node.y} r={node.r + 4} fill={node.color} opacity="0.1" filter="url(#glow)">
              <animate attributeName="r" values={`${node.r + 2};${node.r + 6};${node.r + 2}`} dur="3s" repeatCount="indefinite" />
            </circle>
            <circle cx={node.x} cy={node.y} r={node.r} fill={node.color} opacity="0.8" />
            <text x={node.x} y={node.y + node.r + 12} textAnchor="middle" fill="#888" fontSize="8" fontFamily="monospace">
              {node.label}
            </text>
          </g>
        ))}

        {/* Catalytic cycle highlight */}
        <path d="M 350,200 Q 425,175 500,150 Q 575,225 500,300 Q 425,375 350,400 Q 275,300 350,200"
          fill="none" stroke="#ffaa44" strokeWidth="1" strokeDasharray="6,3" opacity="0.5">
          <animate attributeName="stroke-dashoffset" from="18" to="0" dur="2s" repeatCount="indefinite" />
        </path>
      </svg>

      <div className="absolute bottom-3 left-3 bg-cortex-surface/90 rounded p-2 text-[10px] space-y-1">
        <div className="text-cortex-primary font-bold mb-1">Legend</div>
        {[
          ["#ff6644", "Regime"], ["#44aaff", "Strategy"], ["#44ff88", "Indicator"],
          ["#ffaa44", "Tactical"], ["#ff44aa", "Risk"],
        ].map(([c, l]) => (
          <div key={l} className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ backgroundColor: c }} />{l}</div>
        ))}
        <div className="pt-1 border-t border-cortex-border mt-1">
          <span className="text-amber-400">--- Catalytic Cycle</span>
        </div>
      </div>

      <div className="absolute top-3 right-3 bg-cortex-surface/90 rounded p-2">
        <Badge variant="success">Phase: Critical</Badge>
      </div>
    </div>
  );
}

function AgentDetailPanel() {
  return (
    <Card header="Agent Detail" className="absolute bottom-3 right-3 w-64 z-10">
      <div className="text-xs space-y-1">
        <div className="font-bold text-cortex-primary">Strategy-1</div>
        <div className="text-gray-500">Role: boundary_setter</div>
        <div className="text-gray-500">Status: <span className="text-green-400">Active</span></div>
        <div className="text-gray-500">Performance: <span className="text-green-400">0.92</span></div>
        <div className="text-gray-500">Tasks: 847 | Errors: 3</div>
        <div className="text-gray-500">Avg Latency: 234ms</div>
        <div className="mt-2 pt-2 border-t border-cortex-border">
          <div className="text-[10px] text-gray-600">Catalyzed by: Regime-1</div>
          <div className="text-[10px] text-gray-600">Catalyzes: Tactical-1, Risk-1</div>
        </div>
      </div>
    </Card>
  );
}

export default function AgentsPage() {
  return (
    <div className="h-full relative">
      <Suspense fallback={<div className="flex items-center justify-center h-full text-gray-500">Loading 3D Network...</div>}>
        <AgentNetwork3D />
      </Suspense>
      <AgentDetailPanel />
    </div>
  );
}
