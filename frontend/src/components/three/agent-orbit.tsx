"use client";

import { forwardRef, useMemo } from "react";
import type { LineSegments } from "three";

export type OrbitRingProps = {
  radius: number;
  color: string;
  opacity: number;
  simplified?: boolean;
};

/** A thin, tilted guide line. The parent group owns the plane orientation. */
export function OrbitRing({ radius, color, opacity, simplified = false }: OrbitRingProps) {
  const segments = simplified ? 64 : 128;
  const points = useMemo(() => {
    const buffer = new Float32Array(segments * 3);
    for (let index = 0; index < segments; index += 1) {
      const angle = (index / segments) * Math.PI * 2;
      buffer[index * 3] = Math.cos(angle) * radius;
      buffer[index * 3 + 1] = 0;
      buffer[index * 3 + 2] = Math.sin(angle) * radius;
    }
    return buffer;
  }, [radius, segments]);

  return (
    <lineLoop frustumCulled={false} renderOrder={2}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[points, 3]} />
      </bufferGeometry>
      <lineBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        depthWrite={false}
        toneMapped={false}
      />
    </lineLoop>
  );
}

export type ConnectionLineProps = {
  color: string;
};

/** A restrained core-to-node link, used by the "Building" scene. */
export const ConnectionLine = forwardRef<LineSegments, ConnectionLineProps>(function ConnectionLine({ color }, ref) {
  const points = useMemo(() => new Float32Array(6), []);
  return (
    <lineSegments ref={ref} frustumCulled={false} renderOrder={3}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[points, 3]} />
      </bufferGeometry>
      <lineBasicMaterial
        color={color}
        transparent
        opacity={0}
        depthWrite={false}
        toneMapped={false}
      />
    </lineSegments>
  );
});
