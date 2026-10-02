"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import type { Group } from "three";

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
    orbitRef.current.rotation.x = 0.5 + Math.sin(elapsed * 0.12) * 0.025;
  });

  return (
    <group ref={orbitRef} rotation={[0.5, 0.12, -0.12]}>
      <mesh>
        <torusGeometry args={[1.54, 0.014, 8, 64]} />
        <meshBasicMaterial color="#9aa9d1" transparent opacity={0.34} depthWrite={false} />
      </mesh>
      <mesh rotation={[0.15, 0.62, 0.16]}>
        <torusGeometry args={[1.31, 0.011, 8, 56]} />
        <meshBasicMaterial color="#b5c0dd" transparent opacity={0.25} depthWrite={false} />
      </mesh>
    </group>
  );
}
