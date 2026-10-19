"use client";

import { useEffect, useMemo, useRef } from "react";
import {
  AdditiveBlending,
  CanvasTexture,
  RepeatWrapping,
  SRGBColorSpace,
  type Group,
  type Mesh,
  type MeshBasicMaterial,
  type MeshPhysicalMaterial
} from "three";
import type { AICoreNode, AICoreNodeId } from "./ai-core-data";

export type PlanetHandles = {
  id: AICoreNodeId;
  group: Group;
  mesh: Mesh;
  material: MeshPhysicalMaterial;
  halo: Mesh;
  haloMaterial: MeshBasicMaterial;
  ringMaterial: MeshPhysicalMaterial | null;
};

export type PlanetNodeProps = {
  node: AICoreNode;
  simplified?: boolean;
  onReady: (handles: PlanetHandles) => void;
  onRemove: (id: AICoreNodeId) => void;
};

/** A tiny procedural albedo map: enough banding and mottling to make spin legible. */
function createPlanetTexture(seed: number): CanvasTexture | null {
  if (typeof document === "undefined") {
    return null;
  }

  const width = 256;
  const height = 128;
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) {
    return null;
  }

  let state = seed || 1;
  const random = () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 4294967296;
  };

  context.fillStyle = "#f3f3f3";
  context.fillRect(0, 0, width, height);

  for (let index = 0; index < 11; index += 1) {
    const y = random() * height;
    const bandHeight = 2 + random() * 9;
    context.fillStyle = `rgba(30,38,58,${0.035 + random() * 0.06})`;
    context.fillRect(0, y, width, bandHeight);
  }

  for (let index = 0; index < 15; index += 1) {
    const x = random() * width;
    const y = random() * height;
    const radius = 2 + random() * 13;
    const gradient = context.createRadialGradient(x, y, 0, x, y, radius);
    gradient.addColorStop(0, `rgba(24,32,50,${0.04 + random() * 0.055})`);
    gradient.addColorStop(1, "rgba(24,32,50,0)");
    context.fillStyle = gradient;
    context.fillRect(x - radius, y - radius, radius * 2, radius * 2);
  }

  const poles = context.createLinearGradient(0, 0, 0, height);
  poles.addColorStop(0, "rgba(255,255,255,0.2)");
  poles.addColorStop(0.45, "rgba(255,255,255,0)");
  poles.addColorStop(1, "rgba(24,32,50,0.16)");
  context.fillStyle = poles;
  context.fillRect(0, 0, width, height);

  const texture = new CanvasTexture(canvas);
  texture.wrapS = RepeatWrapping;
  texture.colorSpace = SRGBColorSpace;
  return texture;
}

/**
 * A planet is deliberately built from a small number of physical materials:
 * a pearl-like body, an optional ring, and a very quiet additive aura used for
 * hover/focus. The scene owns every transform; this component only publishes refs.
 */
export function PlanetNode({ node, simplified = false, onReady, onRemove }: PlanetNodeProps) {
  const groupRef = useRef<Group>(null);
  const meshRef = useRef<Mesh>(null);
  const materialRef = useRef<MeshPhysicalMaterial>(null);
  const haloRef = useRef<Mesh>(null);
  const haloMaterialRef = useRef<MeshBasicMaterial>(null);
  const ringMaterialRef = useRef<MeshPhysicalMaterial>(null);

  const seed = useMemo(
    () => node.id.split("").reduce((value, character) => value * 31 + character.charCodeAt(0), 7),
    [node.id]
  );
  const texture = useMemo(() => createPlanetTexture(seed), [seed]);
  useEffect(() => () => texture?.dispose(), [texture]);

  useEffect(() => {
    const group = groupRef.current;
    const mesh = meshRef.current;
    const material = materialRef.current;
    const halo = haloRef.current;
    const haloMaterial = haloMaterialRef.current;
    if (!group || !mesh || !material || !halo || !haloMaterial) {
      return;
    }

    onReady({
      id: node.id,
      group,
      mesh,
      material,
      halo,
      haloMaterial,
      ringMaterial: ringMaterialRef.current
    });

    return () => onRemove(node.id);
  }, [node.id, onReady, onRemove]);

  const segments = simplified ? 22 : 40;

  return (
    <group ref={groupRef} name={`ai-node-${node.id}`}>
      <mesh ref={meshRef} name={`ai-node-body-${node.id}`}>
        <sphereGeometry args={[node.radius, segments, Math.max(14, Math.round(segments * 0.7))]} />
        <meshPhysicalMaterial
          ref={materialRef}
          map={texture ?? undefined}
          color={node.color}
          roughness={0.32}
          metalness={0.02}
          clearcoat={0.55}
          clearcoatRoughness={0.24}
          envMapIntensity={1.08}
          sheen={0.24}
          sheenRoughness={0.5}
          sheenColor={node.glow}
          emissive={node.color}
          emissiveIntensity={0.018}
        />
      </mesh>

      {node.ring ? (
        <mesh rotation={[Math.PI * 0.42, 0.22, 0]} name={`ai-node-ring-${node.id}`}>
          <torusGeometry args={[node.radius * 1.62, node.radius * 0.035, 8, simplified ? 40 : 72]} />
          <meshPhysicalMaterial
            ref={ringMaterialRef}
            color={node.glow}
            roughness={0.26}
            metalness={0.12}
            transparent
            opacity={0.62}
            depthWrite={false}
            envMapIntensity={1.1}
          />
        </mesh>
      ) : null}

      <mesh ref={haloRef} scale={1.5} name={`ai-node-halo-${node.id}`}>
        <sphereGeometry args={[node.radius, 18, 12]} />
        <meshBasicMaterial
          ref={haloMaterialRef}
          color={node.glow}
          transparent
          opacity={0}
          depthWrite={false}
          blending={AdditiveBlending}
          toneMapped={false}
        />
      </mesh>
    </group>
  );
}
