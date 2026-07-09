"use client";

import { useEffect, useMemo, useRef, useState, type PointerEvent } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import type { Group, Mesh } from "three";

const TARGET_FRAME_MS = 1000 / 18;

function DemandFrameLoop({ active }: { active: boolean }) {
  const invalidate = useThree((state) => state.invalidate);

  useEffect(() => {
    if (!active) {
      invalidate();
      return;
    }

    const interval = window.setInterval(() => {
      invalidate();
    }, TARGET_FRAME_MS);

    return () => window.clearInterval(interval);
  }, [active, invalidate]);

  return null;
}

type RotationOffset = {
  x: number;
  y: number;
};

function SunCore({ active, rotationOffset }: { active: boolean; rotationOffset: RotationOffset }) {
  const modelRef = useRef<Group>(null);
  const coreRef = useRef<Mesh>(null);
  const haloRef = useRef<Mesh>(null);
  const ringRef = useRef<Group>(null);

  useFrame((state) => {
    if (!active) {
      return;
    }

    const elapsedTime = state.clock.elapsedTime;

    if (modelRef.current) {
      const targetX = rotationOffset.x + Math.sin(elapsedTime * 0.25) * 0.04;
      const targetY = rotationOffset.y + elapsedTime * 0.16;

      modelRef.current.rotation.x += (targetX - modelRef.current.rotation.x) * 0.14;
      modelRef.current.rotation.y += (targetY - modelRef.current.rotation.y) * 0.14;
    }
    if (coreRef.current) {
      coreRef.current.rotation.y = elapsedTime * 0.32;
      coreRef.current.rotation.x = Math.sin(elapsedTime * 0.35) * 0.08;
    }
    if (haloRef.current) {
      haloRef.current.rotation.z = -0.16 - elapsedTime * 0.08;
    }
    if (ringRef.current) {
      ringRef.current.rotation.z = 0.18 + elapsedTime * 0.1;
      ringRef.current.rotation.x = 0.45 + Math.sin(elapsedTime * 0.25) * 0.05;
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
    <group ref={modelRef}>
      <group ref={ringRef} rotation={[0.45, 0, 0.18]}>
        <mesh>
          <torusGeometry args={[2.2, 0.024, 24, 180]} />
          <meshStandardMaterial color="#7dd3fc" emissive="#38bdf8" emissiveIntensity={2.4} transparent opacity={0.65} />
        </mesh>
        <mesh rotation={[0, 0.55, 0]}>
          <torusGeometry args={[1.7, 0.018, 24, 160]} />
          <meshStandardMaterial color="#f472b6" emissive="#d946ef" emissiveIntensity={1.8} transparent opacity={0.55} />
        </mesh>
      </group>

      <mesh ref={haloRef} scale={2.45} rotation={[0, 0, -0.16]}>
        <sphereGeometry args={[1, 96, 96]} />
        <meshBasicMaterial color="#60a5fa" transparent opacity={0.1} />
      </mesh>

      <mesh ref={coreRef} rotation={[0.08, 0.32, 0]}>
        <sphereGeometry args={[1, 112, 112]} />
        <meshStandardMaterial
          color="#facc15"
          emissive="#fb923c"
          emissiveIntensity={2.55}
          roughness={0.16}
          metalness={0.06}
        />
      </mesh>

      {particles.map((particle) => (
        <mesh key={particle.key} position={particle.position} scale={particle.scale}>
          <sphereGeometry args={[1, 20, 20]} />
          <meshStandardMaterial color="#e0f2fe" emissive="#7dd3fc" emissiveIntensity={1.4} transparent opacity={0.9} />
        </mesh>
      ))}
    </group>
  );
}

export function SunCanvas({ active = true }: { active?: boolean }) {
  const [rotationOffset, setRotationOffset] = useState<RotationOffset>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef({ startX: 0, startY: 0, startRotationX: 0, startRotationY: 0 });

  function updateHoverRotation(event: PointerEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const normalizedX = (event.clientX - rect.left) / rect.width - 0.5;
    const normalizedY = (event.clientY - rect.top) / rect.height - 0.5;

    setRotationOffset({
      x: -normalizedY * 0.28,
      y: normalizedX * 0.42
    });
  }

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      startRotationX: rotationOffset.x,
      startRotationY: rotationOffset.y
    };
    setIsDragging(true);
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!isDragging) {
      updateHoverRotation(event);
      return;
    }

    const deltaX = event.clientX - dragRef.current.startX;
    const deltaY = event.clientY - dragRef.current.startY;

    setRotationOffset({
      x: dragRef.current.startRotationX + deltaY / 150,
      y: dragRef.current.startRotationY + deltaX / 130
    });
  }

  function handlePointerUp(event: PointerEvent<HTMLDivElement>) {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    setIsDragging(false);
  }

  return (
    <Canvas
      className={`absolute inset-0 ${isDragging ? "cursor-grabbing" : "cursor-grab"}`}
      dpr={[1, 1.5]}
      frameloop="demand"
      camera={{ position: [0, 0, 5.2], fov: 45 }}
      gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}
      onPointerDown={handlePointerDown}
      onPointerLeave={() => {
        setIsDragging(false);
      }}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
    >
      <color attach="background" args={["#020617"]} />
      <fog attach="fog" args={["#020617", 7, 12]} />
      <ambientLight intensity={0.55} />
      <pointLight position={[4, 4, 5]} intensity={28} color="#f59e0b" />
      <pointLight position={[-4, -2, 3]} intensity={10} color="#38bdf8" />
      <DemandFrameLoop active={active} />
      <SunCore active={active} rotationOffset={rotationOffset} />
    </Canvas>
  );
}
