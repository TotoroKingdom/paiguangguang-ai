"use client";

import { useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import type { Mesh } from "three";

export type FloatingNodeProps = {
  label: string;
  position: [number, number, number];
  color?: string;
  radius?: number;
  reducedMotion?: boolean;
};

/** A small, soft node used to give the core a readable spatial vocabulary. */
export function FloatingNode({ label, position, color = "#93a5d9", radius = 0.12, reducedMotion = false }: FloatingNodeProps) {
  const meshRef = useRef<Mesh>(null);
  const [hovered, setHovered] = useState(false);

  useFrame((_, delta) => {
    if (!meshRef.current) {
      return;
    }

    if (reducedMotion) {
      meshRef.current.scale.setScalar(1);
      return;
    }

    const targetScale = hovered ? 1.16 : 1;
    const nextScale = meshRef.current.scale.x + (targetScale - meshRef.current.scale.x) * Math.min(1, delta * 7);
    meshRef.current.scale.setScalar(nextScale);
  });

  return (
    <mesh
      ref={meshRef}
      name={`ai-node-${label.toLowerCase()}`}
      position={position}
      onPointerOver={(event) => {
        if (reducedMotion) {
          return;
        }
        event.stopPropagation();
        setHovered(true);
      }}
      onPointerOut={() => setHovered(false)}
    >
      <sphereGeometry args={[radius, 32, 24]} />
      <meshStandardMaterial
        color={color}
        roughness={0.32}
        emissive={color}
        emissiveIntensity={0.06}
        metalness={0.04}
        transparent
        opacity={0.9}
      />
    </mesh>
  );
}
