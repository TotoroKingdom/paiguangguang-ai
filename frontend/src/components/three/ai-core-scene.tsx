"use client";

import { useEffect, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import type { MutableRefObject } from "react";
import type { Group, Mesh } from "three";
import { aiCoreNodes, AI_CORE_CAMERA } from "./ai-core-data";
import { AgentOrbit } from "./agent-orbit";
import { FloatingNode } from "./floating-node";

const TARGET_FRAME_MS = 1000 / 24;

export type AICorePointer = {
  x: number;
  y: number;
};

export type AICoreSceneProps = {
  active: boolean;
  reducedMotion: boolean;
  pointerRef: MutableRefObject<AICorePointer>;
  scrollRef: MutableRefObject<number>;
  onReady?: () => void;
  onContextLost?: () => void;
};

// Fit the existing perspective camera to a square footprint at every breakpoint.
function SceneFraming() {
  const { camera, size, invalidate } = useThree();
  useEffect(() => {
    camera.position.z = AI_CORE_CAMERA.distance * Math.max(1, size.height / Math.max(1, size.width));
    camera.updateProjectionMatrix();
    invalidate();
  }, [camera, size.width, size.height, invalidate]);
  return null;
}

function DemandFrameLoop({ active, reducedMotion }: Pick<AICoreSceneProps, "active" | "reducedMotion">) {
  const invalidate = useThree((state) => state.invalidate);

  useEffect(() => {
    if (!active || reducedMotion) {
      invalidate();
      return;
    }

    const interval = window.setInterval(() => invalidate(), TARGET_FRAME_MS);
    return () => window.clearInterval(interval);
  }, [active, invalidate, reducedMotion]);

  return null;
}

type CoreModelProps = Pick<AICoreSceneProps, "active" | "reducedMotion" | "pointerRef" | "scrollRef">;

function CoreModel({ active, reducedMotion, pointerRef, scrollRef }: CoreModelProps) {
  const modelRef = useRef<Group>(null);
  const shellRef = useRef<Mesh>(null);
  const coreRef = useRef<Mesh>(null);

  useFrame((state, delta) => {
    if (!active || !modelRef.current) {
      return;
    }

    const elapsed = state.clock.elapsedTime;
    const pointerX = reducedMotion ? 0 : pointerRef.current.x;
    const pointerY = reducedMotion ? 0 : pointerRef.current.y;
    const scrollOffset = reducedMotion ? 0 : Math.max(-0.35, Math.min(0.35, scrollRef.current / 1400));
    const targetX = pointerY * -0.035 + scrollOffset * 0.025;
    // Keep the outer group still in ambient mode so the HTML labels remain aligned.
    // The core and the two orbital paths provide the slow internal movement instead.
    const targetY = pointerX * 0.045;
    const easing = Math.min(1, delta * 2.7);

    modelRef.current.rotation.x += (targetX - modelRef.current.rotation.x) * easing;
    modelRef.current.rotation.y += (targetY - modelRef.current.rotation.y) * easing;
    modelRef.current.position.y += (scrollOffset * 0.08 - modelRef.current.position.y) * easing;

    if (!reducedMotion && shellRef.current) {
      shellRef.current.rotation.z = elapsed * 0.025;
    }
    if (!reducedMotion && coreRef.current) {
      coreRef.current.rotation.x = Math.sin(elapsed * 0.19) * 0.035;
      coreRef.current.rotation.y = elapsed * 0.075;
    }
  });

  return (
    <group ref={modelRef}>
      <mesh scale={1.48}>
        <sphereGeometry args={[1, 40, 28]} />
        <meshBasicMaterial color="#b3c2e8" transparent opacity={0.045} depthWrite={false} />
      </mesh>

      <mesh ref={shellRef} scale={1.18}>
        <sphereGeometry args={[1, 48, 32]} />
        <meshStandardMaterial
          color="#c8d4f0"
          roughness={0.22}
          metalness={0.03}
          transparent
          opacity={0.16}
          depthWrite={false}
        />
      </mesh>

      <mesh ref={coreRef} rotation={[0.12, 0.22, 0]}>
        <sphereGeometry args={[0.62, 48, 32]} />
        <meshStandardMaterial
          color="#edf2ff"
          emissive="#8b9be1"
          emissiveIntensity={0.16}
          roughness={0.3}
          metalness={0.08}
          flatShading={false}
          transparent
          opacity={0.95}
        />
      </mesh>

      <mesh scale={0.73}>
        <sphereGeometry args={[0.58, 20, 14]} />
        <meshStandardMaterial color="#dbe4fb" roughness={0.25} metalness={0.02} transparent opacity={0.58} />
      </mesh>

      <AgentOrbit active={active} reducedMotion={reducedMotion} />

      {aiCoreNodes.map((node) => (
        <FloatingNode key={node.id} label={node.label} position={node.position} color={node.color} radius={node.radius} reducedMotion={reducedMotion} />
      ))}
    </group>
  );
}

export default function AICoreScene({ active, reducedMotion, pointerRef, scrollRef, onReady, onContextLost }: AICoreSceneProps) {
  return (
    <Canvas
      className="ai-core-canvas"
      dpr={[1, 1.5]}
      frameloop="demand"
      camera={{ position: [0, 0, AI_CORE_CAMERA.distance], fov: AI_CORE_CAMERA.fov }}
      gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}
      onCreated={({ gl }) => {
        gl.setClearColor(0x000000, 0);
        gl.domElement.addEventListener("webglcontextlost", (event) => {
          event.preventDefault();
          onContextLost?.();
        });
        onReady?.();
      }}
    >
      <ambientLight intensity={1.55} color="#e9efff" />
      <directionalLight position={[3.5, 4, 5]} intensity={2.15} color="#ffffff" />
      <directionalLight position={[-3, -1, 2]} intensity={0.9} color="#b9c7ed" />
      <SceneFraming />
      <DemandFrameLoop active={active} reducedMotion={reducedMotion} />
      <CoreModel active={active} reducedMotion={reducedMotion} pointerRef={pointerRef} scrollRef={scrollRef} />
    </Canvas>
  );
}
