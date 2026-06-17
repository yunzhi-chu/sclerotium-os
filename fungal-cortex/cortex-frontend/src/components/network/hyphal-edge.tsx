'use client';

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { HyphalEdge as HyphalEdgeType } from '@/types/agent';

interface HyphalEdgeProps {
  edge: HyphalEdgeType;
  sourcePos: [number, number, number];
  targetPos: [number, number, number];
}

const EDGE_COLORS: Record<string, string> = {
  signal: '#ff4466',
  nutrient: '#44ff66',
  damage: '#888899',
  catalysis: '#ffaa44',
  data: '#44aaff',
};

const DASH_VERTEX = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const DASH_FRAGMENT = `
  uniform vec3 uColor;
  uniform float uOpacity;
  uniform float uTime;
  uniform float uDashes;
  uniform float uDashRatio;
  uniform float uIsActive;

  varying vec2 vUv;

  void main() {
    float alpha = uOpacity;

    if (uIsActive > 0.5) {
      float dash = fract(vUv.x * uDashes + uTime);
      float dashOn = step(dash, uDashRatio);
      alpha *= dashOn;
    }

    // Soft edge glow toward the tube surface
    float edgeGlow = 1.0 - abs(vUv.y - 0.5) * 2.0;
    alpha *= (0.55 + edgeGlow * 0.45);

    gl_FragColor = vec4(uColor, alpha);
  }
`;

/** Build a cubic bezier curve with an upward arc between two 3D positions. */
function buildCurve(
  source: [number, number, number],
  target: [number, number, number],
): THREE.CubicBezierCurve3 {
  const [sx, sy, sz] = source;
  const [tx, ty, tz] = target;

  const dx = tx - sx;
  const dz = tz - sz;
  const dist = Math.sqrt(dx * dx + dz * dz);
  const midY = (sy + ty) / 2;
  const arcHeight = Math.max(dist * 0.3, 0.5);

  return new THREE.CubicBezierCurve3(
    new THREE.Vector3(sx, sy, sz),
    new THREE.Vector3(sx + dx * 0.25, midY + arcHeight, sz + dz * 0.25),
    new THREE.Vector3(tx - dx * 0.25, midY + arcHeight, tz - dz * 0.25),
    new THREE.Vector3(tx, ty, tz),
  );
}

/** Animated 3D tube edge connecting two agent nodes in the mycelial network. */
export function HyphalEdge({ edge, sourcePos, targetPos }: HyphalEdgeProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const matRef = useRef<THREE.ShaderMaterial>(null);

  const curve = useMemo(
    () => buildCurve(sourcePos, targetPos),
    [sourcePos, targetPos],
  );

  const color = EDGE_COLORS[edge.edge_type] ?? '#888899';
  const opacity = edge.flow_rate;
  const radius = 0.02 + edge.weight * 0.04;

  const geometry = useMemo(
    () => new THREE.TubeGeometry(curve, 24, radius, 6, false),
    [curve, radius],
  );

  // When the edge type / style props change, recreate the uniforms object
  // so the shader material picks up new values
  useFrame((state) => {
    if (matRef.current) {
      matRef.current.uniforms.uTime.value =
        state.clock.elapsedTime * 0.4;
    }
  });

  return (
    <mesh ref={meshRef} geometry={geometry}>
      <shaderMaterial
        ref={matRef}
        transparent
        depthWrite={false}
        uniforms={{
          uColor: { value: new THREE.Color(color) },
          uOpacity: { value: opacity },
          uTime: { value: 0 },
          uDashes: { value: 16 },
          uDashRatio: { value: edge.is_active ? 0.5 : 1.0 },
          uIsActive: { value: edge.is_active ? 1.0 : 0.0 },
        }}
        vertexShader={DASH_VERTEX}
        fragmentShader={DASH_FRAGMENT}
      />
    </mesh>
  );
}
