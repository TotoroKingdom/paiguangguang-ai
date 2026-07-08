"use client";

import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Bloom, EffectComposer } from "@react-three/postprocessing";
import type { Group, Mesh } from "three";

function SunCore() {
  const coreRef = useRef<Mesh>(null);
  const haloRef = useRef<Mesh>(null);
  const ringRef = useRef<Group>(null);

  useFrame((state, delta) => {
    if (coreRef.current) {
      coreRef.current.rotation.y += delta * 0.25;
      coreRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.35) * 0.08;
    }
    if (haloRef.current) {
      haloRef.current.rotation.z -= delta * 0.15;
    }
    if (ringRef.current) {
      ringRef.current.rotation.z += delta * 0.12;
      ringRef.current.rotation.x = 0.45 + Math.sin(state.clock.elapsedTime * 0.25) * 0.05;
    }
  });

  const particles = useMemo(
    () =>
      Array.from({ length: 28 }, (_, index) => {
        const angle = (index / 28) * Math.PI * 2;
        const radius = 1.8 + (index % 4) * 0.15;
        return {
          key: index,
          position: [Math.cos(angle) * radius, Math.sin(angle * 1.5) * 0.7, Math.sin(angle) * radius] as [
            number,
            number,
            number
          ],
          scale: 0.04 + (index % 3) * 0.012
        };
      }),
    []
  );

  return (
    <>
      <group ref={ringRef}>
        <mesh>
          <torusGeometry args={[2.2, 0.02, 16, 120]} />
          <meshStandardMaterial color="#7dd3fc" emissive="#38bdf8" emissiveIntensity={2.4} transparent opacity={0.65} />
        </mesh>
        <mesh rotation={[0, 0.55, 0]}>
          <torusGeometry args={[1.7, 0.015, 16, 100]} />
          <meshStandardMaterial color="#f472b6" emissive="#d946ef" emissiveIntensity={1.8} transparent opacity={0.55} />
        </mesh>
      </group>

      <mesh ref={haloRef} scale={2.45}>
        <sphereGeometry args={[1, 64, 64]} />
        <meshBasicMaterial color="#60a5fa" transparent opacity={0.08} />
      </mesh>

      <mesh ref={coreRef}>
        <sphereGeometry args={[1, 64, 64]} />
        <meshStandardMaterial
          color="#facc15"
          emissive="#fb923c"
          emissiveIntensity={2.2}
          roughness={0.2}
          metalness={0.06}
        />
      </mesh>

      {particles.map((particle) => (
        <mesh key={particle.key} position={particle.position} scale={particle.scale}>
          <sphereGeometry args={[1, 16, 16]} />
          <meshStandardMaterial color="#e0f2fe" emissive="#7dd3fc" emissiveIntensity={1.4} transparent opacity={0.9} />
        </mesh>
      ))}
    </>
  );
}

export function SunCanvas() {
  return (
    <Canvas
      className="absolute inset-0"
      dpr={[1, 2]}
      camera={{ position: [0, 0, 5.2], fov: 45 }}
      gl={{ antialias: true, alpha: true }}
    >
      <color attach="background" args={["#020617"]} />
      <fog attach="fog" args={["#020617", 7, 12]} />
      <ambientLight intensity={0.55} />
      <pointLight position={[4, 4, 5]} intensity={28} color="#f59e0b" />
      <pointLight position={[-4, -2, 3]} intensity={10} color="#38bdf8" />
      <SunCore />
      <EffectComposer>
        <Bloom intensity={1.1} luminanceThreshold={0.15} luminanceSmoothing={0.85} />
      </EffectComposer>
    </Canvas>
  );
}
