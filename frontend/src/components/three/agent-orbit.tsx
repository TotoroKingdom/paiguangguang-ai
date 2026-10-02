"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import type { Group } from "three";
import { AI_CORE_ORBIT_RADIUS } from "./ai-core-data";

export type AgentOrbitProps = {
  active: boolean;
  reducedMotion: boolean;
};

/** Two quiet orbital paths provide depth without turning the core into a neon wireframe. */
export function AgentOrbit({ active, reducedMotion }: AgentOrbitProps) {
  const orbitRef = useRef<Group>(null);

  useFrame((state) => {
    if (!active || reducedMotion || !orbitRef.current) {
      return;
    }

    const elapsed = state.clock.elapsedTime;
    orbitRef.current.rotation.z = elapsed * 0.035;
  });

  return (
    <group ref={orbitRef} rotation={[0, 0, 0]}>
      <mesh>
        <torusGeometry args={[AI_CORE_ORBIT_RADIUS, 0.012, 12, 128]} />
        <meshBasicMaterial color="#9baad3" transparent opacity={0.34} depthWrite={false} />
      </mesh>
      <mesh rotation={[0.22, 0.16, 0]}>
        <torusGeometry args={[1.32, 0.01, 12, 128]} />
        <meshBasicMaterial color="#b6a8d5" transparent opacity={0.25} depthWrite={false} />
      </mesh>
    </group>
  );
}
