'use client';

import { useRef, useMemo } from 'react';
import { useFrame, ThreeEvent } from '@react-three/fiber';
import * as THREE from 'three';
import type { AgentNode as AgentNodeType } from '@/types/agent';
import { SPECIALTY_COLORS } from '@/types/agent';

interface AgentNodeProps {
  node: AgentNodeType;
  isSelected: boolean;
  isHovered: boolean;
  wireframe?: boolean;
  onClick?: (node: AgentNodeType) => void;
  onPointerEnter?: (node: AgentNodeType) => void;
  onPointerLeave?: () => void;
}

/** 3D representation of a single agent in the mycelial network. */
export function AgentNode({
  node,
  isSelected,
  isHovered,
  wireframe = false,
  onClick,
  onPointerEnter,
  onPointerLeave,
}: AgentNodeProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);
  const scaleRef = useRef(1);

  const basePos = useMemo(
    () => new THREE.Vector3(node.x, node.y, node.z),
    [node.x, node.y, node.z],
  );

  const color = SPECIALTY_COLORS[node.specialty];
  const size = 0.3 + node.performance_score * 0.9;
  const isEmissive = (node.status as string) === 'active' || node.status === 'busy';
  const isSpawning = node.lifecycle === 'spawning';
  const isDead = node.lifecycle === 'dead';

  // Hover / selection target scale
  const targetScale = isHovered ? 1.3 : isSelected ? 1.15 : 1;

  useFrame((state) => {
    const t = state.clock.elapsedTime;

    if (meshRef.current) {
      // Gentle floating bob
      const floatY = Math.sin(t * 0.8 + node.x * 0.5 + node.z * 0.3) * 0.06;
      meshRef.current.position.y = basePos.y + floatY;

      // Smooth scale lerp toward target
      scaleRef.current += (targetScale - scaleRef.current) * 0.06;
      meshRef.current.scale.setScalar(scaleRef.current);
    }

    // Spawning ring pulse
    if (ringRef.current && isSpawning) {
      const pulse = Math.sin(t * 3.0) * 0.5 + 0.5;
      const s = 1 + pulse * 0.6;
      ringRef.current.scale.set(s, s, s);
      (ringRef.current.material as THREE.MeshBasicMaterial).opacity =
        0.5 - pulse * 0.4;
    }

    // Selection glow pulse
    if (glowRef.current) {
      const pulse = Math.sin(t * 1.5) * 0.2 + 0.8;
      glowRef.current.scale.setScalar(1 + pulse * 0.1);
    }
  });

  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    onClick?.(node);
  };

  const handlePointerEnter = (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    onPointerEnter?.(node);
  };

  const handlePointerLeave = () => {
    onPointerLeave?.();
  };

  if (isDead) return null;

  return (
    <group>
      {/* Ambient glow for emissive (active/busy) agents */}
      {isEmissive && (
        <mesh position={basePos}>
          <sphereGeometry args={[size * 1.8, 16, 16]} />
          <meshBasicMaterial color={color} transparent opacity={0.06} />
        </mesh>
      )}

      {/* Selection highlight ring */}
      {isSelected && (
        <mesh ref={glowRef} position={basePos}>
          <sphereGeometry args={[size * 1.35, 24, 24]} />
          <meshBasicMaterial color={color} transparent opacity={0.18} />
        </mesh>
      )}

      {/* Main agent sphere */}
      <mesh
        ref={meshRef}
        position={basePos}
        onClick={handleClick}
        onPointerEnter={handlePointerEnter}
        onPointerLeave={handlePointerLeave}
      >
        <sphereGeometry args={[size, 24, 24]} />
        <meshStandardMaterial
          color={color}
          emissive={isEmissive ? color : '#000000'}
          emissiveIntensity={isEmissive ? (node.status === 'busy' ? 0.55 : 0.3) : 0}
          roughness={0.3}
          metalness={0.15}
          wireframe={wireframe}
        />
      </mesh>

      {/* Spawning lifecycle pulse ring */}
      {isSpawning && (
        <mesh
          ref={ringRef}
          position={basePos}
          rotation={[-Math.PI / 2, 0, 0]}
        >
          <ringGeometry args={[size * 1.1, size * 1.45, 48]} />
          <meshBasicMaterial
            color={color}
            transparent
            opacity={0.5}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}
    </group>
  );
}
