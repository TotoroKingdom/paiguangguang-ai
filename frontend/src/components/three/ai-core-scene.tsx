"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  ACESFilmicToneMapping,
  AdditiveBlending,
  CanvasTexture,
  Color,
  EquirectangularReflectionMapping,
  MeshPhysicalMaterial,
  PMREMGenerator,
  SRGBColorSpace,
  Vector3,
  type BufferAttribute,
  type Group,
  type LineBasicMaterial,
  type LineSegments,
  type Mesh,
  type MeshBasicMaterial,
  type PerspectiveCamera,
  type PointLight
} from "three";

import {
  AI_CORE_FOV,
  aiCoreNodes,
  aiCoreScenes,
  type AICoreNodeId,
  type AICoreScenePose
} from "./ai-core-data";
import { ConnectionLine, OrbitRing } from "./agent-orbit";
import { PlanetNode, type PlanetHandles } from "./floating-node";
import {
  clamp,
  createPoseBuffer,
  fadeForScroll,
  interpolatePoseInto,
  sampleScrollTimeline
} from "./ai-core-scroll";
import type { AICoreSceneProps } from "./ai-core-types";

const FRESNEL_VERTEX = `
  varying vec3 vWorldNormal;
  varying vec3 vWorldPosition;

  void main() {
    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vWorldPosition = worldPosition.xyz;
    vWorldNormal = normalize(mat3(modelMatrix) * normal);
    gl_Position = projectionMatrix * viewMatrix * worldPosition;
  }
`;

const FRESNEL_FRAGMENT = `
  uniform vec3 uColor;
  uniform float uPower;
  uniform float uOpacity;
  varying vec3 vWorldNormal;
  varying vec3 vWorldPosition;

  void main() {
    vec3 viewDirection = normalize(cameraPosition - vWorldPosition);
    float edge = pow(1.0 - clamp(dot(normalize(vWorldNormal), viewDirection), 0.0, 1.0), uPower);
    gl_FragColor = vec4(uColor, edge * uOpacity);
  }
`;

function createGlowTexture(): CanvasTexture | null {
  if (typeof document === "undefined") {
    return null;
  }

  const size = 256;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const context = canvas.getContext("2d");
  if (!context) {
    return null;
  }

  const gradient = context.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  gradient.addColorStop(0, "rgba(255,255,255,0.85)");
  gradient.addColorStop(0.2, "rgba(238,243,255,0.42)");
  gradient.addColorStop(0.52, "rgba(211,221,248,0.12)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, size, size);

  const texture = new CanvasTexture(canvas);
  texture.colorSpace = SRGBColorSpace;
  return texture;
}

function createStudioTexture(): CanvasTexture | null {
  if (typeof document === "undefined") {
    return null;
  }

  const width = 1024;
  const height = 512;
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) {
    return null;
  }

  const base = context.createLinearGradient(0, 0, 0, height);
  base.addColorStop(0, "#fafbff");
  base.addColorStop(0.42, "#dde3f0");
  base.addColorStop(0.76, "#aeb9ce");
  base.addColorStop(1, "#68748c");
  context.fillStyle = base;
  context.fillRect(0, 0, width, height);

  const spot = (x: number, y: number, radius: number, inner: string) => {
    const gradient = context.createRadialGradient(x, y, 0, x, y, radius);
    gradient.addColorStop(0, inner);
    gradient.addColorStop(1, "rgba(255,255,255,0)");
    context.fillStyle = gradient;
    context.fillRect(x - radius, y - radius, radius * 2, radius * 2);
  };

  spot(250, 128, 260, "rgba(255,252,248,0.92)");
  spot(760, 104, 230, "rgba(226,234,255,0.78)");
  spot(520, 396, 280, "rgba(86,100,130,0.36)");
  spot(960, 300, 190, "rgba(176,192,224,0.42)");

  const texture = new CanvasTexture(canvas);
  texture.mapping = EquirectangularReflectionMapping;
  texture.colorSpace = SRGBColorSpace;
  return texture;
}

/**
 * The core is a pearl ceramic material. A per-fragment local-height gradient is
 * injected into the physical material instead of a UV texture: no mipmap
 * aliasing, no vertex-colour banding, and a much richer light-to-shadow falloff
 * than a flat colour.
 */
function createCoreMaterial(): MeshPhysicalMaterial {
  return new MeshPhysicalMaterial({
    color: 0xd2daea,
    roughness: 0.31,
    metalness: 0.05,
    clearcoat: 1,
    clearcoatRoughness: 0.18,
    envMapIntensity: 0.82,
    iridescence: 0.35,
    iridescenceIOR: 1.3,
    iridescenceThicknessRange: [120, 520],
    sheen: 0.4,
    sheenRoughness: 0.58,
    sheenColor: new Color("#d3daf6"),
    emissive: new Color("#5d6cab"),
    emissiveIntensity: 0.025
  });
}

function StudioEnvironment({ simplified }: { simplified: boolean }) {
  const gl = useThree((state) => state.gl);
  const scene = useThree((state) => state.scene);

  useEffect(() => {
    const texture = createStudioTexture();
    if (!texture) {
      return;
    }

    const generator = new PMREMGenerator(gl);
    generator.compileEquirectangularShader();
    const target = generator.fromEquirectangular(texture);
    scene.environment = target.texture;
    scene.environmentIntensity = simplified ? 0.38 : 0.46;

    return () => {
      scene.environment = null;
      target.dispose();
      texture.dispose();
      generator.dispose();
    };
  }, [gl, scene, simplified]);

  return null;
}

function SceneLights({ simplified }: { simplified: boolean }) {
  return (
    <>
      <ambientLight intensity={simplified ? 0.1 : 0.06} color="#e9eeff" />
      <hemisphereLight args={["#f8faff", "#9da9bd", simplified ? 0.2 : 0.18]} />
      <directionalLight position={[4.5, 5.5, 6]} intensity={simplified ? 2.15 : 2.3} color="#fff7f1" />
      <directionalLight position={[-5, 1.5, 3]} intensity={simplified ? 0.24 : 0.28} color="#b9caff" />
      <directionalLight position={[-1.5, 3.2, -6]} intensity={simplified ? 0.95 : 1.2} color="#d6e0ff" />
    </>
  );
}

type LabelPlacement = {
  id: AICoreNodeId;
  x: number;
  y: number;
  radius: number;
  width: number;
  height: number;
  distance: number;
  visible: boolean;
};

function CoreSystem({
  active,
  reducedMotion,
  simplified,
  focusedId,
  hoveredId,
  interactionRef,
  projectedRef,
  timelineRef,
  labelRefs,
  labelSizesRef,
  occlusionRef,
  canvasOpacityRef,
  haloRef
}: AICoreSceneProps) {
  const camera = useThree((state) => state.camera);
  const size = useThree((state) => state.size);

  const rigRef = useRef<Group>(null);
  const coreGroupRef = useRef<Group>(null);
  const coreMeshRef = useRef<Mesh>(null);
  const shellRef = useRef<Mesh>(null);
  const fresnelRef = useRef<Mesh>(null);
  const coreRingARef = useRef<Mesh>(null);
  const coreRingBRef = useRef<Mesh>(null);
  const coreLightRef = useRef<PointLight>(null);
  const haloMeshRef = useRef<Mesh>(null);
  const haloMaterialRef = useRef<MeshBasicMaterial>(null);

  const planetHandlesRef = useRef<Partial<Record<AICoreNodeId, PlanetHandles>>>({});
  const orbitRingRefs = useRef<Partial<Record<AICoreNodeId, Group | null>>>({});
  const connectionRefs = useRef<Partial<Record<AICoreNodeId, LineSegments | null>>>({});

  const pose = useRef<AICoreScenePose>(createPoseBuffer());
  const initialised = useRef(false);
  const smoothScroll = useRef<number | null>(null);
  const orbitClock = useRef(0);
  const coreClock = useRef(0);
  const selfClock = useRef(0);
  const focusAmount = useRef(0);
  const lastFade = useRef(-1);

  const glowTexture = useMemo(() => createGlowTexture(), []);
  useEffect(() => () => glowTexture?.dispose(), [glowTexture]);
  const coreMaterial = useMemo(() => createCoreMaterial(), []);
  useEffect(() => () => coreMaterial.dispose(), [coreMaterial]);

  const fresnelUniforms = useMemo(
    () => ({
      uColor: { value: new Color("#d4ddff") },
      uPower: { value: 2.8 },
      uOpacity: { value: 0.32 }
    }),
    []
  );

  const placements = useMemo<LabelPlacement[]>(
    () =>
      aiCoreNodes.map((node) => ({
        id: node.id,
        x: 0,
        y: 0,
        radius: 0,
        width: 74,
        height: 26,
        distance: 0,
        visible: false
      })),
    []
  );

  const temps = useMemo(
    () => ({
      forward: new Vector3(),
      right: new Vector3(),
      up: new Vector3(),
      world: new Vector3(),
      coreWorld: new Vector3(),
      projected: new Vector3(),
      coreProjected: new Vector3()
    }),
    []
  );

  const handlePlanetReady = useCallback((handles: PlanetHandles) => {
    planetHandlesRef.current[handles.id] = handles;
  }, []);

  const handlePlanetRemove = useCallback((id: AICoreNodeId) => {
    delete planetHandlesRef.current[id];
  }, []);

  useEffect(() => {
    if (active) {
      smoothScroll.current = null;
    }
  }, [active]);

  useFrame((_state, rawDelta) => {
    const rig = rigRef.current;
    if (!rig) {
      return;
    }

    const delta = active ? Math.min(rawDelta, 0.05) : 0;
    const dampDelta = reducedMotion ? 1 : delta;
    const now = performance.now();
    const rawScroll = window.scrollY;
    const timeline = timelineRef.current;
    const layoutScale = size.width < 768 ? 0.64 : size.width < 1050 ? 0.88 : 1;

    if (!initialised.current) {
      smoothScroll.current = rawScroll;
      initialised.current = true;
    }

    const currentScroll = smoothScroll.current ?? rawScroll;
    const followScroll = reducedMotion ? 1 : 1 - Math.exp(-delta * 14);
    const nextScroll = reducedMotion || !active ? rawScroll : currentScroll + (rawScroll - currentScroll) * followScroll;
    smoothScroll.current = nextScroll;

    const sample = timeline
      ? sampleScrollTimeline(timeline, nextScroll, reducedMotion)
      : {
          from: 0,
          to: 0,
          t: 0,
          progress: 0,
          anchorX: 0.5,
          anchorY: 0.5,
          sceneIndex: 0
        };

    interpolatePoseInto(pose.current, aiCoreScenes[sample.from], aiCoreScenes[sample.to], sample.t);
    const currentPose = pose.current;
    const fade = timeline ? fadeForScroll(timeline, rawScroll) : 1;

    if (fade < 0.005 && lastFade.current >= 0.005) {
      rig.visible = false;
    } else {
      rig.visible = true;
    }
    lastFade.current = fade;

    if (canvasOpacityRef.current && Math.abs(Number(canvasOpacityRef.current.style.opacity || 1) - fade) > 0.004) {
      canvasOpacityRef.current.style.opacity = fade.toFixed(3);
    }

    // ---- camera rig -------------------------------------------------------
    const drift = reducedMotion ? 0 : 1;
    const cameraYaw = currentPose.yaw + Math.sin(coreClock.current * 0.34) * 0.018 * drift;
    const cameraPitch = currentPose.pitch + Math.cos(coreClock.current * 0.27) * 0.012 * drift;
    const cameraDistance = currentPose.distance + Math.sin(coreClock.current * 0.5) * 0.06 * drift;

    const focusTarget = focusedId ? 1 : 0;
    focusAmount.current += (focusTarget - focusAmount.current) * (1 - Math.exp(-dampDelta * 6));
    const effectiveDistance = cameraDistance * (1 - focusAmount.current * 0.055);

    camera.position.set(
      Math.sin(cameraYaw) * Math.cos(cameraPitch) * cameraDistance,
      Math.sin(cameraPitch) * cameraDistance,
      Math.cos(cameraYaw) * Math.cos(cameraPitch) * cameraDistance
    );
    camera.lookAt(0, 0, 0);
    camera.updateMatrixWorld();

    const cameraFov = (camera as PerspectiveCamera).fov ?? AI_CORE_FOV;
    const aspect = size.width / Math.max(1, size.height);
    const halfHeight = Math.tan((cameraFov * Math.PI) / 360) * effectiveDistance;
    const halfWidth = halfHeight * aspect;
    const anchorX = clamp(sample.anchorX, 0, 1);
    const anchorY = clamp(sample.anchorY, 0, 1);

    temps.forward.set(0, 0, -1).applyQuaternion(camera.quaternion);
    temps.right.set(1, 0, 0).applyQuaternion(camera.quaternion);
    temps.up.set(0, 1, 0).applyQuaternion(camera.quaternion);

    rig.position
      .copy(camera.position)
      .addScaledVector(temps.forward, effectiveDistance)
      .addScaledVector(temps.right, (anchorX - 0.5) * 2 * halfWidth)
      .addScaledVector(temps.up, -(anchorY - 0.5) * 2 * halfHeight);

    // ---- drag + parallax --------------------------------------------------
    const interaction = interactionRef.current;
    const drag = interaction.drag;
    if (!reducedMotion) {
      if (!drag.active) {
        drag.targetYaw += drag.velocityYaw * delta;
        drag.targetPitch += drag.velocityPitch * delta;
        const friction = Math.exp(-delta * 3.6);
        drag.velocityYaw *= friction;
        drag.velocityPitch *= friction;
        if (Math.abs(drag.velocityYaw) < 0.0008) {
          drag.velocityYaw = 0;
        }
        if (Math.abs(drag.velocityPitch) < 0.0008) {
          drag.velocityPitch = 0;
        }

        if (drag.recenterAt) {
          drag.targetYaw *= Math.exp(-delta * 3.4);
          drag.targetPitch *= Math.exp(-delta * 3.4);
          if (Math.abs(drag.targetYaw) < 0.002 && Math.abs(drag.targetPitch) < 0.002) {
            drag.targetYaw = 0;
            drag.targetPitch = 0;
            drag.recenterAt = 0;
          }
        }

        if (now - interaction.lastActivity > 7000) {
          drag.targetYaw *= Math.exp(-delta * 0.75);
          drag.targetPitch *= Math.exp(-delta * 0.75);
        }
      }

      drag.targetYaw = clamp(drag.targetYaw, -1.15, 1.15);
      drag.targetPitch = clamp(drag.targetPitch, -0.5, 0.5);
      const follow = 1 - Math.exp(-delta * 11);
      drag.currentYaw += (drag.targetYaw - drag.currentYaw) * follow;
      drag.currentPitch += (drag.targetPitch - drag.currentPitch) * follow;
    } else {
      drag.currentYaw = 0;
      drag.currentPitch = 0;
    }

    const scrollingRecently = now - interaction.lastScrollAt < 220;
    const parallaxStrength = drag.active || reducedMotion ? 0 : scrollingRecently ? 0.42 : 1;
    const parallaxX = interaction.pointer.x * 0.032 * parallaxStrength;
    const parallaxY = interaction.pointer.y * 0.022 * parallaxStrength;

    rig.rotation.set(
      currentPose.rotation[0] + drag.currentPitch + parallaxY,
      currentPose.rotation[1] + drag.currentYaw + parallaxX,
      currentPose.rotation[2]
    );

    const breathe = reducedMotion ? 1 : 1 + Math.sin(coreClock.current * 0.82) * 0.006;
    const modelScale = currentPose.scale * layoutScale * (1 + focusAmount.current * 0.035) * breathe;
    rig.scale.setScalar(modelScale);

    // ---- clocks -----------------------------------------------------------
    if (!reducedMotion && active) {
      const speed = currentPose.orbitSpeed * (focusedId ? 0.18 : 1) * (drag.active ? 0.62 : 1);
      orbitClock.current += delta * speed;
      coreClock.current += delta * (0.32 + currentPose.energy * 0.55) * (focusedId ? 0.5 : 1);
      selfClock.current += delta;
    }

    // ---- core -------------------------------------------------------------
    if (coreGroupRef.current) {
      coreGroupRef.current.rotation.y = coreClock.current * 0.22;
      coreGroupRef.current.rotation.x = Math.sin(coreClock.current * 0.29) * 0.05;
    }
    if (shellRef.current) {
      shellRef.current.rotation.y = -coreClock.current * 0.14;
      shellRef.current.rotation.z = coreClock.current * 0.06;
    }
    if (fresnelRef.current) {
      fresnelRef.current.rotation.y = coreClock.current * 0.08;
    }
    if (coreRingARef.current) {
      coreRingARef.current.rotation.z = 0.4 + coreClock.current * 0.1;
    }
    if (coreRingBRef.current) {
      coreRingBRef.current.rotation.y = 0.6 - coreClock.current * 0.07;
    }
    if (coreLightRef.current) {
      coreLightRef.current.intensity = 1.7 + Math.sin(coreClock.current * 1.3) * 0.28;
    }

    // ---- planets + connections -------------------------------------------
    for (const node of aiCoreNodes) {
      const handles = planetHandlesRef.current[node.id];
      if (!handles) {
        continue;
      }

      const angle = node.orbit.phase + orbitClock.current * node.orbit.speed;
      const radius = node.orbit.radius * currentPose.orbitSpread + currentPose.separation;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;

      handles.group.position.set(x, 0, z);
      const ringGroup = orbitRingRefs.current[node.id];
      if (ringGroup) {
        ringGroup.scale.setScalar(radius / node.orbit.radius);
      }

      const isHovered = hoveredId === node.id;
      const isFocused = focusedId === node.id;
      const targetScale = isFocused ? 1.32 : isHovered ? 1.16 : focusedId ? 0.92 : 1;
      const nextScale = handles.mesh.scale.x + (targetScale - handles.mesh.scale.x) * (1 - Math.exp(-dampDelta * 8));
      handles.mesh.scale.setScalar(nextScale);
      handles.mesh.rotation.y = selfClock.current * node.spin + node.orbit.phase;
      handles.mesh.rotation.x = Math.sin(selfClock.current * 0.3 + node.orbit.phase) * 0.12;

      const haloScaleTarget = 1.5 + (isFocused ? 0.42 : isHovered ? 0.22 : 0);
      const haloScale = handles.halo.scale.x + (haloScaleTarget - handles.halo.scale.x) * (1 - Math.exp(-dampDelta * 8));
      handles.halo.scale.setScalar(haloScale);
      const haloOpacityTarget = isFocused ? 0.24 : isHovered ? 0.15 : 0;
      handles.haloMaterial.opacity +=
        (haloOpacityTarget - handles.haloMaterial.opacity) * (1 - Math.exp(-dampDelta * 9));

      const emissiveTarget = isFocused ? 0.13 : isHovered ? 0.075 : 0.025;
      handles.material.emissiveIntensity +=
        (emissiveTarget - handles.material.emissiveIntensity) * (1 - Math.exp(-dampDelta * 7));
      if (handles.ringMaterial) {
        const ringTarget = isFocused ? 0.8 : isHovered ? 0.7 : 0.58;
        handles.ringMaterial.opacity +=
          (ringTarget - handles.ringMaterial.opacity) * (1 - Math.exp(-dampDelta * 6));
      }

      const connection = connectionRefs.current[node.id];
      if (connection) {
        const attribute = connection.geometry.getAttribute("position") as BufferAttribute;
        attribute.setXYZ(0, 0, 0, 0);
        attribute.setXYZ(1, x, 0, z);
        attribute.needsUpdate = true;
        const material = connection.material as LineBasicMaterial;
        const connectionBase = currentPose.connections * (isFocused ? 0.72 : isHovered ? 0.55 : 0.44);
        material.opacity += (connectionBase - material.opacity) * (1 - Math.exp(-dampDelta * 6));
        connection.visible = currentPose.connections > 0.01 && fade > 0.01;
      }
    }

    rig.updateWorldMatrix(true, true);

    // ---- billboard halo ---------------------------------------------------
    if (haloMeshRef.current && haloMaterialRef.current) {
      haloMeshRef.current.position.copy(rig.position);
      haloMeshRef.current.quaternion.copy(camera.quaternion);
      haloMeshRef.current.scale.setScalar(modelScale * 5.6);
      haloMaterialRef.current.opacity = fade * currentPose.halo * 0.1;
      haloMeshRef.current.visible = fade > 0.01;
    }

    // ---- projection: world -> screen labels ------------------------------
    const core = coreMeshRef.current;
    let coreX = size.width / 2;
    let coreY = size.height / 2;
    let coreDistance = effectiveDistance;
    let coreRadius = 0;

    if (core) {
      core.getWorldPosition(temps.coreWorld);
      coreDistance = temps.coreWorld.distanceTo(camera.position);
      temps.coreProjected.copy(temps.coreWorld).project(camera);
      coreX = (temps.coreProjected.x * 0.5 + 0.5) * size.width;
      coreY = (-temps.coreProjected.y * 0.5 + 0.5) * size.height;
      coreRadius =
        ((0.9 * modelScale) / (2 * Math.tan((cameraFov * Math.PI) / 360) * coreDistance)) * size.height;
    }

    projectedRef.current.coreX = coreX;
    projectedRef.current.coreY = coreY;
    projectedRef.current.coreRadius = coreRadius;
    projectedRef.current.fade = fade;
    projectedRef.current.sceneIndex = sample.sceneIndex;

    const rawScrollForOcclusion = rawScroll;
    let placementIndex = 0;
    for (const node of aiCoreNodes) {
      const handles = planetHandlesRef.current[node.id];
      const placement = placements[placementIndex];
      placementIndex += 1;
      if (!handles) {
        placement.visible = false;
        continue;
      }

      handles.group.getWorldPosition(temps.world);
      const distance = temps.world.distanceTo(camera.position);
      temps.projected.copy(temps.world).project(camera);
      const screenX = (temps.projected.x * 0.5 + 0.5) * size.width;
      const screenY = (-temps.projected.y * 0.5 + 0.5) * size.height;
      const nodeRadius =
        ((node.radius * handles.mesh.scale.x * modelScale) /
          (2 * Math.tan((cameraFov * Math.PI) / 360) * distance)) *
        size.height;

      const behindCore =
        distance > coreDistance + 0.12 && Math.hypot(screenX - coreX, screenY - coreY) < coreRadius * 0.88;
      const onScreen =
        temps.projected.z > -1 &&
        temps.projected.z < 1 &&
        screenX >= 0 &&
        screenX <= size.width &&
        screenY >= 0 &&
        screenY <= size.height;

      const visible = onScreen && !behindCore && fade > 0.01;
      placement.distance = distance;
      placement.visible = visible;
      placement.x = screenX;
      placement.y = screenY;
      placement.radius = nodeRadius;
      const labelSize = labelSizesRef.current[node.id];
      placement.width = labelSize?.width ?? 74;
      placement.height = labelSize?.height ?? 26;

      const existing = projectedRef.current.nodes[node.id];
      if (existing) {
        existing.x = screenX;
        existing.y = screenY;
        existing.radius = nodeRadius;
        existing.distance = distance;
        existing.visible = visible;
      } else {
        projectedRef.current.nodes[node.id] = {
          id: node.id,
          x: screenX,
          y: screenY,
          radius: nodeRadius,
          distance,
          visible
        };
      }
    }

    updateLabels({
      placements,
      viewportWidth: size.width,
      viewportHeight: size.height,
      scrollY: rawScrollForOcclusion,
      fade,
      labelOpacity: currentPose.labelOpacity,
      focusedId,
      hoveredId,
      coreX,
      coreY,
      coreRadius,
      coreDistance,
      labelRefs,
      occlusionRef
    });

    if (haloRef.current) {
      const haloScale = clamp((coreRadius * 2.1) / 260, 0.35, 1.45);
      haloRef.current.style.transform = `translate3d(${coreX.toFixed(1)}px, ${coreY.toFixed(1)}px, 0) scale(${haloScale.toFixed(3)})`;
      haloRef.current.style.opacity = (fade * currentPose.halo * 0.95).toFixed(3);
    }
  });

  return (
    <>
      <mesh ref={haloMeshRef} renderOrder={-1}>
        <planeGeometry args={[1, 1]} />
        <meshBasicMaterial
          ref={haloMaterialRef}
          map={glowTexture ?? undefined}
          color="#e8edff"
          transparent
          opacity={0}
          depthWrite={false}
          depthTest
          blending={AdditiveBlending}
          toneMapped={false}
        />
      </mesh>

      <group ref={rigRef}>
        <group ref={coreGroupRef}>
          <mesh ref={coreMeshRef} name="ai-core-inner">
            <sphereGeometry args={[0.58, simplified ? 64 : 128, simplified ? 44 : 96]} />
            <primitive object={coreMaterial} attach="material" />
          </mesh>

          <mesh ref={shellRef} scale={1.0} name="ai-core-glass">
            <sphereGeometry args={[0.9, simplified ? 56 : 96, simplified ? 36 : 64]} />
            <meshPhysicalMaterial
              color="#cfdaf4"
              roughness={0.07}
              metalness={0}
              clearcoat={1}
              clearcoatRoughness={0.05}
              envMapIntensity={1.0}
              transparent
              opacity={0.06}
              depthWrite={false}
            />
          </mesh>

          <mesh ref={fresnelRef} scale={1.012} name="ai-core-rim">
            <sphereGeometry args={[0.9, 48, 32]} />
            <shaderMaterial
              uniforms={fresnelUniforms}
              vertexShader={FRESNEL_VERTEX}
              fragmentShader={FRESNEL_FRAGMENT}
              transparent
              depthWrite={false}
              blending={AdditiveBlending}
              toneMapped={false}
            />
          </mesh>
        </group>

        <mesh ref={coreRingARef} rotation={[0.92, 0.2, 0.4]} renderOrder={4}>
          <torusGeometry args={[1.08, 0.006, 8, simplified ? 80 : 128]} />
          <meshBasicMaterial color="#aebcdd" transparent opacity={0.24} depthWrite={false} toneMapped={false} />
        </mesh>
        <mesh ref={coreRingBRef} rotation={[0.4, 0.6, -0.3]} renderOrder={4}>
          <torusGeometry args={[1.22, 0.005, 8, simplified ? 72 : 120]} />
          <meshBasicMaterial color="#b9aed8" transparent opacity={0.17} depthWrite={false} toneMapped={false} />
        </mesh>

        <pointLight ref={coreLightRef} color="#dfe7ff" intensity={2.1} distance={5.5} decay={2} />

        {aiCoreNodes.map((node) => (
          <group key={node.id} rotation={[node.orbit.tiltX, 0, node.orbit.tiltZ]}>
            <group
              ref={(ringGroup) => {
                orbitRingRefs.current[node.id] = ringGroup;
              }}
            >
              <OrbitRing
                radius={node.orbit.radius}
                color={node.color}
                opacity={node.id === "agent" ? 0.18 : node.id === "llm" ? 0.12 : 0.07}
                simplified={simplified}
              />
            </group>
            <ConnectionLine
              color={node.color}
              ref={(line) => {
                connectionRefs.current[node.id] = line;
              }}
            />
            <PlanetNode
              node={node}
              simplified={simplified}
              onReady={handlePlanetReady}
              onRemove={handlePlanetRemove}
            />
          </group>
        ))}
      </group>
    </>
  );
}

type LabelUpdateInput = {
  placements: LabelPlacement[];
  viewportWidth: number;
  viewportHeight: number;
  scrollY: number;
  fade: number;
  labelOpacity: number;
  focusedId: AICoreNodeId | null;
  hoveredId: AICoreNodeId | null;
  coreX: number;
  coreY: number;
  coreRadius: number;
  coreDistance: number;
  labelRefs: AICoreSceneProps["labelRefs"];
  occlusionRef: AICoreSceneProps["occlusionRef"];
};

function rectsOverlap(
  a: { left: number; top: number; right: number; bottom: number },
  b: { left: number; top: number; right: number; bottom: number },
  padding: number
): boolean {
  return (
    a.right > b.left - padding &&
    a.left < b.right + padding &&
    a.bottom > b.top - padding &&
    a.top < b.bottom + padding
  );
}

function updateLabels({
  placements,
  viewportWidth,
  viewportHeight,
  scrollY,
  fade,
  labelOpacity,
  focusedId,
  hoveredId,
  coreX,
  coreY,
  coreRadius,
  coreDistance,
  labelRefs,
  occlusionRef
}: LabelUpdateInput) {
  const placed: { left: number; top: number; right: number; bottom: number }[] = [];
  const sorted = [...placements].sort((a, b) => a.distance - b.distance);

  for (const placement of sorted) {
    const label = labelRefs.current[placement.id];
    if (!label) {
      continue;
    }

    const width = placement.width;
    const height = placement.height;
    const nearNodeX = Math.hypot(placement.x - coreX, placement.y - coreY) < coreRadius * 0.88;
    const hiddenBehindCore = placement.distance > coreDistance + 0.12 && nearNodeX;
    const depthOpacity = clamp(1 - Math.max(0, placement.distance - coreDistance) / 3.6, 0.42, 1);
    const emphasis = focusedId === placement.id ? 1 : hoveredId === placement.id ? 1 : 0.92;
    let targetOpacity = placement.visible && !hiddenBehindCore ? fade * labelOpacity * depthOpacity * emphasis : 0;

    let x = clamp(placement.x - width / 2, 8, Math.max(8, viewportWidth - width - 8));
    let y = clamp(
      placement.y - placement.radius - 12 - height,
      8,
      Math.max(8, viewportHeight - height - 8)
    );

    if (targetOpacity > 0.02) {
      let resolved = false;
      for (let attempt = 0; attempt < 7; attempt += 1) {
        const candidate = { left: x, top: y, right: x + width, bottom: y + height };
        if (!placed.some((rect) => rectsOverlap(candidate, rect, 4))) {
          resolved = true;
          break;
        }
        const direction = attempt % 2 === 0 ? -1 : 1;
        const step = Math.ceil((attempt + 1) / 2) * (height + 6);
        y = clamp(placement.y - placement.radius - 12 - height + direction * step, 8, Math.max(8, viewportHeight - height - 8));
      }
      if (!resolved) {
        targetOpacity = 0;
      }
    }

    if (targetOpacity > 0.02) {
      const candidate = { left: x, top: y, right: x + width, bottom: y + height };
      const occluded = occlusionRef.current.some((rect) =>
        rectsOverlap(
          candidate,
          {
            left: rect.left,
            top: rect.fixed ? rect.top : rect.top - scrollY,
            right: rect.right,
            bottom: rect.fixed ? rect.bottom : rect.bottom - scrollY
          },
          3
        )
      );
      if (occluded) {
        targetOpacity = 0;
      }
    }

    if (targetOpacity > 0.02) {
      placed.push({ left: x, top: y, right: x + width, bottom: y + height });
    }

    label.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0)`;
    label.style.opacity = targetOpacity.toFixed(3);
    label.style.pointerEvents = targetOpacity > 0.22 ? "auto" : "none";
    label.tabIndex = targetOpacity > 0.22 ? 0 : -1;
    label.style.zIndex = String(10 + Math.round(depthOpacity * 10));
    label.dataset.depth = depthOpacity < 0.62 ? "far" : "near";
  }
}

function FrameScheduler({
  active,
  reducedMotion,
  interactionRef
}: Pick<AICoreSceneProps, "active" | "reducedMotion" | "interactionRef">) {
  const invalidate = useThree((state) => state.invalidate);

  useEffect(() => {
    invalidate();
    if (!active || reducedMotion) {
      return;
    }

    let frame = 0;
    let last = 0;
    const tick = (now: number) => {
      const idle = now - interactionRef.current.lastActivity > 1400;
      const interval = idle ? 1000 / 30 : 1000 / 60;
      if (now - last >= interval - 1) {
        last = now;
        invalidate();
      }
      frame = window.requestAnimationFrame(tick);
    };
    frame = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frame);
  }, [active, invalidate, interactionRef, reducedMotion]);

  return null;
}

function SceneBridge({ onBridge }: Pick<AICoreSceneProps, "onBridge">) {
  const invalidate = useThree((state) => state.invalidate);
  useEffect(() => {
    onBridge?.({ invalidate });
    return () => onBridge?.(null);
  }, [invalidate, onBridge]);
  return null;
}

function ReadySignal({
  onReady,
  timelineRef
}: Pick<AICoreSceneProps, "onReady" | "timelineRef">) {
  const done = useRef(false);
  useFrame(() => {
    if (!done.current && timelineRef.current) {
      done.current = true;
      onReady?.();
    }
  });
  return null;
}

function ContextGuard({ onContextLost }: Pick<AICoreSceneProps, "onContextLost">) {
  const gl = useThree((state) => state.gl);

  useEffect(() => {
    const canvas = gl.domElement;
    const handler = (event: Event) => {
      event.preventDefault();
      onContextLost?.();
    };
    canvas.addEventListener("webglcontextlost", handler, false);
    return () => canvas.removeEventListener("webglcontextlost", handler, false);
  }, [gl, onContextLost]);

  return null;
}

export default function AICoreScene(props: AICoreSceneProps) {
  const { quality, simplified } = props;

  return (
    <Canvas
      className="ai-core-canvas"
      dpr={[1, quality]}
      frameloop="demand"
      camera={{ position: [0, 0, 9.2], fov: AI_CORE_FOV, near: 0.1, far: 60 }}
      gl={{
        antialias: !simplified,
        alpha: true,
        depth: true,
        stencil: false,
        powerPreference: simplified ? "low-power" : "high-performance"
      }}
      onCreated={({ gl }) => {
        gl.setClearColor(0x000000, 0);
        gl.toneMapping = ACESFilmicToneMapping;
        gl.toneMappingExposure = 0.94;
      }}
    >
      <StudioEnvironment simplified={simplified} />
      <SceneLights simplified={simplified} />
      <CoreSystem {...props} />
      <FrameScheduler active={props.active} reducedMotion={props.reducedMotion} interactionRef={props.interactionRef} />
      <SceneBridge onBridge={props.onBridge} />
      <ReadySignal onReady={props.onReady} timelineRef={props.timelineRef} />
      <ContextGuard onContextLost={props.onContextLost} />
    </Canvas>
  );
}
