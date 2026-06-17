'use client';

import { useRef, useState, useCallback, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stats } from '@react-three/drei';
import type { OrbitControls as OrbitControlsType } from 'three-stdlib';
import { useAgentStore } from '@/stores/agent-store';
import type { AgentNode as AgentNodeType, AgentSpecialty } from '@/types/agent';
import { SPECIALTY_COLORS, SPECIALTY_LABELS } from '@/types/agent';
import { AgentNode } from './agent-node';
import { HyphalEdge } from './hyphal-edge';
import { NetworkControls } from './network-controls';

/* ------------------------------------------------------------------ */
/*  Scene content — rendered inside the R3F Canvas                    */
/* ------------------------------------------------------------------ */

interface SceneContentProps {
  wireframe: boolean;
  autoRotate: boolean;
  controlsRef: React.RefObject<OrbitControlsType | null>;
}

function SceneContent({ wireframe, autoRotate, controlsRef }: SceneContentProps) {
  const network = useAgentStore((s) => s.network);
  const selectedNode = useAgentStore((s) => s.selectedNode);
  const selectNode = useAgentStore((s) => s.selectNode);
  const hoverNode = useAgentStore((s) => s.hoverNode);
  const filterSpecialty = useAgentStore((s) => s.filterSpecialty);
  const showCatalysis = useAgentStore((s) => s.showCatalysis);
  const showInactive = useAgentStore((s) => s.showInactive);

  // Wire OrbitControls ref back to parent
  const setOrbitControlsRef = useCallback(
    (ctl: OrbitControlsType | null) => {
      (controlsRef as React.MutableRefObject<OrbitControlsType | null>).current = ctl;
    },
    [controlsRef],
  );

  // Compute filtered nodes and build a position map for edges
  const { visibleNodes, positionMap } = useMemo(() => {
    const nodes = network?.nodes ?? [];
    const filtered: AgentNodeType[] = [];
    const map = new Map<string, [number, number, number]>();

    for (const n of nodes) {
      // Inactive filter
      if (!showInactive && (n.lifecycle === 'dead' || n.status === 'offline')) {
        continue;
      }
      // Specialty filter
      if (filterSpecialty && n.specialty !== filterSpecialty) {
        continue;
      }
      filtered.push(n);
      map.set(n.id, [n.x, n.y, n.z]);
    }

    return { visibleNodes: filtered, positionMap: map };
  }, [network, showInactive, filterSpecialty]);

  // Compute visible edges — both endpoints must be visible
  const visibleEdges = useMemo(() => {
    if (!network) return [];
    return network.edges.filter((e) => {
      if (!showCatalysis && e.edge_type === 'catalysis') return false;
      return positionMap.has(e.source) && positionMap.has(e.target);
    });
  }, [network, showCatalysis, positionMap]);

  // Handlers
  const handleNodeClick = useCallback(
    (node: AgentNodeType) => {
      selectNode(selectedNode?.id === node.id ? null : node);
    },
    [selectNode, selectedNode],
  );

  const handleNodeEnter = useCallback(
    (node: AgentNodeType) => hoverNode(node),
    [hoverNode],
  );

  const handleNodeLeave = useCallback(
    () => hoverNode(null),
    [hoverNode],
  );

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.4} />
      <pointLight position={[10, 10, 10]} intensity={0.8} />
      <pointLight position={[-10, -5, -10]} intensity={0.35} color="#4466ff" />
      <pointLight position={[0, -8, 5]} intensity={0.2} color="#44ffaa" />

      {/* Controls */}
      <OrbitControls
        ref={setOrbitControlsRef}
        autoRotate={autoRotate}
        autoRotateSpeed={1.5}
        enableDamping
        dampingFactor={0.05}
        minDistance={2}
        maxDistance={40}
        makeDefault
      />

      {/* Nodes */}
      {visibleNodes.map((node) => (
        <AgentNode
          key={node.id}
          node={node}
          isSelected={selectedNode?.id === node.id}
          isHovered={false}
          wireframe={wireframe}
          onClick={handleNodeClick}
          onPointerEnter={handleNodeEnter}
          onPointerLeave={handleNodeLeave}
        />
      ))}

      {/* Edges */}
      {visibleEdges.map((edge) => {
        const srcPos = positionMap.get(edge.source);
        const tgtPos = positionMap.get(edge.target);
        if (!srcPos || !tgtPos) return null;
        return (
          <HyphalEdge
            key={edge.id}
            edge={edge}
            sourcePos={srcPos}
            targetPos={tgtPos}
          />
        );
      })}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Legend overlay rendered outside the Canvas                        */
/* ------------------------------------------------------------------ */

const SPECIALTIES: AgentSpecialty[] = ['regime', 'strategy', 'indicator', 'tactical', 'risk'];

function LegendOverlay() {
  return (
    <div className="rounded-lg border border-[#1e1e3a] bg-[#0a0a0f]/85 px-3 py-2.5 backdrop-blur-sm">
      <span className="mb-1.5 block text-[10px] font-semibold uppercase tracking-wider text-[#666688]">
        Specialties
      </span>
      <div className="flex flex-col gap-1">
        {SPECIALTIES.map((spec) => (
          <div key={spec} className="flex items-center gap-2 text-xs text-[#c8c8d0]">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: SPECIALTY_COLORS[spec] }}
            />
            {SPECIALTY_LABELS[spec]}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Phase indicator badge                                             */
/* ------------------------------------------------------------------ */

const PHASE_COLORS: Record<string, string> = {
  pre_critical: '#666688',
  critical: '#ffaa44',
  supercritical: '#ff4466',
  degenerate: '#7c3aed',
};

function PhaseBadge({ phase }: { phase: string }) {
  const color = PHASE_COLORS[phase] ?? '#666688';
  const label = phase.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div
      className="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-medium backdrop-blur-sm"
      style={{
        borderColor: `${color}44`,
        backgroundColor: `${color}15`,
        color,
      }}
    >
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Empty state                                                       */
/* ------------------------------------------------------------------ */

function EmptyState() {
  return (
    <div className="flex h-full w-full items-center justify-center">
      <div className="flex flex-col items-center gap-2 text-[#666688]">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 6v6l4 2" />
        </svg>
        <span className="text-xs">No agents in network</span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main export — MycelialNetwork                                     */
/* ------------------------------------------------------------------ */

interface MycelialNetworkProps {
  showStats?: boolean;
  className?: string;
}

/**
 * Main 3D mycelial agent network component.
 *
 * Renders a full-screen R3F Canvas with agent nodes, hyphal edges,
 * orbital controls, and overlay UI for legend / phase / display toggles.
 */
export function MycelialNetwork({ showStats = false, className = '' }: MycelialNetworkProps) {
  const controlsRef = useRef<OrbitControlsType | null>(null);
  const [autoRotate, setAutoRotate] = useState(false);
  const [wireframe, setWireframe] = useState(false);

  const network = useAgentStore((s) => s.network);
  const selectedNode = useAgentStore((s) => s.selectedNode);

  const handleToggleAutoRotate = useCallback(() => {
    setAutoRotate((p) => !p);
  }, []);

  const handleToggleWireframe = useCallback(() => {
    setWireframe((p) => !p);
  }, []);

  const handleResetCamera = useCallback(() => {
    if (controlsRef.current) {
      controlsRef.current.reset();
    }
  }, []);

  return (
    <div className={`relative h-full w-full overflow-hidden ${className}`}>
      {network && network.nodes.length > 0 ? (
        <>
          <Canvas
            camera={{ position: [0, 5, 14], fov: 50, near: 0.1, far: 100 }}
            dpr={[1, 2]}
            gl={{
              antialias: true,
              alpha: false,
              powerPreference: 'high-performance',
            }}
          >
            <color attach="background" args={['#0a0a0f']} />
            <fog attach="fog" args={['#0a0a0f', 20, 45]} />

            <SceneContent
              wireframe={wireframe}
              autoRotate={autoRotate}
              controlsRef={controlsRef}
            />

            {showStats && <Stats />}
          </Canvas>

          {/* Overlay — Legend */}
          <div className="pointer-events-none absolute left-4 top-4 z-10">
            <LegendOverlay />
          </div>

          {/* Overlay — Phase badge + selected node info */}
          <div className="pointer-events-none absolute right-4 top-4 z-10 flex flex-col items-end gap-2">
            <PhaseBadge phase={network.phase} />
            {selectedNode && (
              <div
                className="rounded-lg border border-[#1e1e3a] bg-[#0a0a0f]/85 px-3 py-2 text-xs backdrop-blur-sm"
                style={{
                  borderColor: `${SPECIALTY_COLORS[selectedNode.specialty]}44`,
                }}
              >
                <div className="flex items-center gap-2 font-medium text-[#e2e8f0]">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: SPECIALTY_COLORS[selectedNode.specialty] }}
                  />
                  {selectedNode.name}
                </div>
                <div className="mt-1 flex gap-3 text-[#888899]">
                  <span>Score: {(selectedNode.performance_score * 100).toFixed(0)}%</span>
                  <span>Tasks: {selectedNode.task_count}</span>
                  <span>Latency: {selectedNode.avg_latency_ms.toFixed(1)}ms</span>
                </div>
              </div>
            )}
          </div>

          {/* Overlay — Controls */}
          <NetworkControls
            autoRotate={autoRotate}
            onToggleAutoRotate={handleToggleAutoRotate}
            wireframe={wireframe}
            onToggleWireframe={handleToggleWireframe}
            onResetCamera={handleResetCamera}
          />

        </>
      ) : (
        <EmptyState />
      )}
    </div>
  );
}
