"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import {
  ACESFilmicToneMapping,
  AdditiveBlending,
  BufferAttribute,
  CanvasTexture,
  Color,
  EquirectangularReflectionMapping,
  MeshPhysicalMaterial,
  PMREMGenerator,
  SphereGeometry,
  SRGBColorSpace,
  Vector3,
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
  aiCoreTransitions,
  type AICoreNodeId,
  type AICoreScenePose
} from "./ai-core-data";
import { modelCoverage, type ContentBlock } from "./ai-core-composition";
import { ConnectionLine, OrbitRing } from "./agent-orbit";
import { PlanetNode, type PlanetHandles } from "./floating-node";
import {
  clamp,
  createPoseBuffer,
  fadeForScroll,
  interpolatePoseInto,
  sampleScrollTimeline,
  smoothstep01
} from "./ai-core-scroll";
import { isModelVisible } from "./ai-core-runtime";
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

  // A dark studio cyclorama with a few large, shaped softboxes. The bright
  // surround is deliberately restrained so the shadow side of the pearl can
  // actually go dark and the box reflections stay legible.
  const base = context.createLinearGradient(0, 0, 0, height);
  base.addColorStop(0, "#232b3a");
  base.addColorStop(0.3, "#202734");
  base.addColorStop(0.56, "#171d27");
  base.addColorStop(0.78, "#0e1219");
  base.addColorStop(1, "#07090d");
  context.fillStyle = base;
  context.fillRect(0, 0, width, height);

  const horizon = context.createLinearGradient(0, height * 0.34, 0, height * 0.7);
  horizon.addColorStop(0, "rgba(255,255,255,0)");
  horizon.addColorStop(0.5, "rgba(196,214,244,0.12)");
  horizon.addColorStop(1, "rgba(255,255,255,0)");
  context.fillStyle = horizon;
  context.fillRect(0, height * 0.34, width, height * 0.36);

  const shape = (
    x: number,
    y: number,
    w: number,
    h: number,
    color: string,
    blur: number,
    rotation = 0
  ) => {
    context.save();
    context.translate(x, y);
    context.rotate(rotation);
    context.filter = `blur(${blur}px)`;
    context.fillStyle = color;
    context.fillRect(-w / 2, -h / 2, w, h);
    context.restore();
  };

  // Large warm key softbox, upper left.
  shape(292, 112, 390, 186, "rgba(255,252,246,1)", 10, -0.07);
  // Cool fill strip, upper right.
  shape(746, 104, 138, 272, "rgba(226,238,255,0.96)", 8, 0.05);
  // Narrow highlight bar: creates the crisp vertical reflection on the shell.
  shape(548, 86, 52, 330, "rgba(255,255,255,0.92)", 5);
  // Small rim box and a tight catchlight for the clearcoat.
  shape(910, 292, 104, 76, "rgba(255,255,255,0.72)", 6, -0.12);
  shape(612, 148, 86, 86, "rgba(255,255,255,0.95)", 4, 0.1);

  // Deep floor sweep keeps the lower hemisphere from flattening out.
  const floor = context.createRadialGradient(236, 478, 20, 236, 478, 430);
  floor.addColorStop(0, "rgba(21,26,36,0.6)");
  floor.addColorStop(0.62, "rgba(25,31,43,0.2)");
  floor.addColorStop(1, "rgba(25,31,43,0)");
  context.fillStyle = floor;
  context.fillRect(0, 220, 700, 292);

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
    color: 0xffffff,
    vertexColors: true,
    roughness: 0.145,
    metalness: 0,
    clearcoat: 0.92,
    clearcoatRoughness: 0.04,
    envMapIntensity: 1.6,
    iridescence: 0.16,
    iridescenceIOR: 1.36,
    iridescenceThicknessRange: [150, 480],
    sheen: 0.24,
    sheenRoughness: 0.42,
    sheenColor: new Color("#e9edff"),
    specularIntensity: 1.22,
    specularColor: new Color("#ffffff"),
    emissive: new Color("#43548a"),
    emissiveIntensity: 0.004
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
    scene.environmentIntensity = simplified ? 0.72 : 0.95;

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
      <ambientLight intensity={simplified ? 0.06 : 0.018} color="#e9eeff" />
      <hemisphereLight args={["#fbfcff", "#7b88a3", simplified ? 0.1 : 0.065]} />
      {/* Warm key from the upper left: the terminator lands on the right. */}
      <directionalLight position={[-5.2, 6.6, 5.2]} intensity={simplified ? 3.5 : 3.85} color="#fff3e6" />
      {/* Cool fill keeps the shadow side blue-grey instead of muddy. */}
      <directionalLight position={[5.6, 0.8, 3.8]} intensity={simplified ? 0.26 : 0.3} color="#b4c6ff" />
      {/* Rim from behind picks out the silhouette of the shell. */}
      <directionalLight position={[2.2, 3.1, -6.4]} intensity={simplified ? 1.5 : 1.85} color="#cfdcff" />
      <directionalLight position={[-1.2, -3.8, 3.2]} intensity={simplified ? 0.14 : 0.2} color="#e8e2ff" />
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
  contentBlocksRef,
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
  const travelFade = useRef(1);
  const coverageRef = useRef(0);

  const glowTexture = useMemo(() => createGlowTexture(), []);
  useEffect(() => () => glowTexture?.dispose(), [glowTexture]);
  const coreMaterial = useMemo(() => createCoreMaterial(), []);
  useEffect(() => () => coreMaterial.dispose(), [coreMaterial]);

  /**
   * A pearl body: a soft vertical colour gradient baked into vertex colours.
   * It keeps the top lavender, the equator pearl-blue and the underside
   * blue-grey without adding another shader pass.
   */
  const coreGeometry = useMemo(() => {
    const geometry = new SphereGeometry(
      0.58,
      simplified ? 64 : 128,
      simplified ? 44 : 96
    );
    const position = geometry.getAttribute("position");
    const colors = new Float32Array(position.count * 3);
    const topLavender = new Color("#e7e1f8");
    const topBlue = new Color("#dfe8f7");
    const equator = new Color("#cfd8ee");
    const bottom = new Color("#7c8dbb");
    const sample = new Color();
    const cap = new Color();
    for (let index = 0; index < position.count; index += 1) {
      const x = clamp(position.getX(index) / 0.58, -1, 1);
      const t = clamp(position.getY(index) / 0.58, -1, 1);
      if (t >= 0) {
        cap.copy(topBlue).lerp(topLavender, (x + 1) / 2);
        sample.copy(equator).lerp(cap, t);
      } else {
        sample.copy(equator).lerp(bottom, -t);
      }
      colors[index * 3] = sample.r;
      colors[index * 3 + 1] = sample.g;
      colors[index * 3 + 2] = sample.b;
    }
    geometry.setAttribute("color", new BufferAttribute(colors, 3));
    return geometry;
  }, [simplified]);
  useEffect(() => () => coreGeometry.dispose(), [coreGeometry]);

  const fresnelUniforms = useMemo(
    () => ({
      uColor: { value: new Color("#93a6d6") },
      uPower: { value: 2.35 },
      uOpacity: { value: 0.5 }
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
          fit: 1,
          sceneIndex: 0
        };

    interpolatePoseInto(pose.current, aiCoreScenes[sample.from], aiCoreScenes[sample.to], sample.t);
    const currentPose = pose.current;
    const fade = timeline ? fadeForScroll(timeline, rawScroll) : 1;

    // ---- transition choreography -----------------------------------------
    // The authored arc is zero at both stops, so this path is identical when
    // scrolling forward and backward.
    const transitionIndex = Math.min(sample.from, sample.to);
    const transition = aiCoreTransitions[transitionIndex] ?? {
      arcX: 0,
      arcY: 0,
      dolly: 0,
      spin: 0,
      roll: 0
    };
    const arc = Math.sin(Math.PI * sample.t);

    // The model steps back and fades whenever its silhouette would be cut by a
    // card or copy block. The target comes from the previous frame's measured
    // coverage; a short exponential smooth keeps it from flickering.
    const coverageTarget = clamp(
      1 - smoothstep01((coverageRef.current - 0.12) / 0.22),
      0,
      1
    );
    travelFade.current += (coverageTarget - travelFade.current) * (1 - Math.exp(-dampDelta * 9));
    const travel = reducedMotion ? coverageTarget : travelFade.current;
    const travelScale = 0.74 + 0.26 * travel;
    const travelDistance = 1 + (1 - travel) * 0.22;
    const sceneOpacity = fade * travel;

    rig.visible = isModelVisible(sceneOpacity);

    if (
      canvasOpacityRef.current &&
      Math.abs(Number(canvasOpacityRef.current.style.opacity || 1) - sceneOpacity) > 0.004
    ) {
      canvasOpacityRef.current.style.opacity = sceneOpacity.toFixed(3);
    }

    // ---- camera rig -------------------------------------------------------
    const drift = reducedMotion ? 0 : 1;
    const cameraYaw = currentPose.yaw + Math.sin(coreClock.current * 0.34) * 0.018 * drift;
    const cameraPitch = currentPose.pitch + Math.cos(coreClock.current * 0.27) * 0.012 * drift;
    const cameraDistance =
      (currentPose.distance + Math.sin(coreClock.current * 0.5) * 0.06 * drift) *
      (1 + transition.dolly * arc) *
      travelDistance;

    const focusTarget = focusedId ? 1 : 0;
    focusAmount.current += (focusTarget - focusAmount.current) * (1 - Math.exp(-dampDelta * 6));
    const effectiveDistance = cameraDistance * (1 - focusAmount.current * 0.055);

    const lookX = currentPose.lookX + Math.sin(coreClock.current * 0.21) * 0.02 * drift;
    const lookY = currentPose.lookY + Math.cos(coreClock.current * 0.24) * 0.015 * drift;

    camera.position.set(
      Math.sin(cameraYaw) * Math.cos(cameraPitch) * cameraDistance,
      Math.sin(cameraPitch) * cameraDistance,
      Math.cos(cameraYaw) * Math.cos(cameraPitch) * cameraDistance
    );
    camera.lookAt(lookX, lookY, 0);
    camera.rotateZ(currentPose.roll + transition.roll * arc);
    camera.updateMatrixWorld();

    const cameraFov = (camera as PerspectiveCamera).fov ?? AI_CORE_FOV;
    const aspect = size.width / Math.max(1, size.height);
    const halfHeight = Math.tan((cameraFov * Math.PI) / 360) * effectiveDistance;
    const halfWidth = halfHeight * aspect;
    const anchorX = clamp(sample.anchorX + transition.arcX * arc, 0, 1);
    const anchorY = clamp(sample.anchorY + transition.arcY * arc, 0, 1);

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
      currentPose.rotation[1] + drag.currentYaw + parallaxX + transition.spin * arc,
      currentPose.rotation[2]
    );

    const breathe = reducedMotion ? 1 : 1 + Math.sin(coreClock.current * 0.82) * 0.006;
    const baseModelScale =
      currentPose.scale * sample.fit * layoutScale * (1 + focusAmount.current * 0.035) * breathe;
    const exitScale = 0.92 + 0.08 * fade;
    const modelScale = baseModelScale * travelScale * exitScale;
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
      coreLightRef.current.intensity = 3.9 + Math.sin(coreClock.current * 1.3) * 0.35;
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
        connection.visible = currentPose.connections > 0.01 && sceneOpacity > 0.01;
      }
    }

    rig.updateWorldMatrix(true, true);

    // ---- billboard halo ---------------------------------------------------
    if (haloMeshRef.current && haloMaterialRef.current) {
      haloMeshRef.current.position.copy(rig.position);
      haloMeshRef.current.quaternion.copy(camera.quaternion);
      haloMeshRef.current.scale.setScalar(modelScale * 4.7);
      haloMaterialRef.current.opacity = sceneOpacity * currentPose.halo * 0.055;
      haloMeshRef.current.visible = sceneOpacity > 0.01;
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
    projectedRef.current.fade = sceneOpacity;
    projectedRef.current.sceneIndex = sample.sceneIndex;

    // Measure how much of the authored silhouette would sit behind real
    // content. The next frame uses this to recede or fade instead of letting a
    // half-hidden sphere peek out from under a card.
    const coverageScale = currentPose.scale * sample.fit * layoutScale;
    const coverageDistance = Math.max(1, currentPose.distance * (1 + transition.dolly * arc));
    let maxOrbit = 0;
    for (const node of aiCoreNodes) {
      maxOrbit = Math.max(
        maxOrbit,
        node.orbit.radius * currentPose.orbitSpread + currentPose.separation + node.radius
      );
    }
    const coverageRadius =
      ((maxOrbit * coverageScale * size.height) /
        (2 * Math.tan((cameraFov * Math.PI) / 360) * coverageDistance)) *
      0.94;
    coverageRef.current = modelCoverage(
      contentBlocksRef.current,
      rawScroll,
      coreX,
      coreY,
      coverageRadius
    );

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
        distance > coreDistance + 0.12 &&
        Math.hypot(screenX - coreX, screenY - coreY) < coreRadius * 0.62 + nodeRadius;
      const onScreen =
        temps.projected.z > -1 &&
        temps.projected.z < 1 &&
        screenX >= 0 &&
        screenX <= size.width &&
        screenY >= 0 &&
        screenY <= size.height;

      const visible = onScreen && !behindCore && sceneOpacity > 0.01;
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
      fade: sceneOpacity,
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
      haloRef.current.style.opacity = (sceneOpacity * currentPose.halo * 0.6).toFixed(3);
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
          <mesh ref={coreMeshRef} geometry={coreGeometry} name="ai-core-inner">
            <primitive object={coreMaterial} attach="material" />
          </mesh>

          <mesh ref={shellRef} scale={1.0} name="ai-core-glass">
            <sphereGeometry args={[0.9, simplified ? 56 : 96, simplified ? 36 : 64]} />
            <meshPhysicalMaterial
              color="#cbd8f4"
              roughness={0.07}
              metalness={0}
              clearcoat={1}
              clearcoatRoughness={0.02}
              envMapIntensity={1.45}
              transparent
              opacity={0.072}
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
              toneMapped={false}
            />
          </mesh>
        </group>

        <mesh ref={coreRingARef} rotation={[0.92, 0.2, 0.4]} renderOrder={4}>
          <torusGeometry args={[1.08, 0.006, 8, simplified ? 80 : 128]} />
          <meshBasicMaterial color="#aebcdd" transparent opacity={0.3} depthWrite={false} toneMapped={false} />
        </mesh>
        <mesh ref={coreRingBRef} rotation={[0.4, 0.6, -0.3]} renderOrder={4}>
          <torusGeometry args={[1.22, 0.005, 8, simplified ? 72 : 120]} />
          <meshBasicMaterial color="#b9aed8" transparent opacity={0.2} depthWrite={false} toneMapped={false} />
        </mesh>

        <pointLight
          ref={coreLightRef}
          position={[-1.15, 1.85, 1.55]}
          color="#fff5e9"
          intensity={4.1}
          distance={7}
          decay={2}
        />

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
                opacity={node.id === "agent" ? 0.24 : node.id === "llm" ? 0.18 : 0.12}
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
    const nearNodeX = Math.hypot(placement.x - coreX, placement.y - coreY) < coreRadius * 0.62 + placement.radius;
    const hiddenBehindCore = placement.distance > coreDistance + 0.12 && nearNodeX;
    const depthOpacity = clamp(1 - Math.max(0, placement.distance - coreDistance) / 3.6, 0.42, 1);
    const emphasis = focusedId === placement.id ? 1 : hoveredId === placement.id ? 1 : 0.92;
    let targetOpacity = placement.visible && !hiddenBehindCore ? fade * labelOpacity * depthOpacity * emphasis : 0;

    const minX = 8;
    const maxX = Math.max(8, viewportWidth - width - 8);
    const minY = 8;
    const maxY = Math.max(8, viewportHeight - height - 8);
    const gap = 12;
    const candidates = [
      { x: placement.x - width / 2, y: placement.y - placement.radius - gap - height },
      { x: placement.x - width / 2, y: placement.y + placement.radius + gap },
      { x: placement.x + placement.radius + gap, y: placement.y - height / 2 },
      { x: placement.x - placement.radius - gap - width, y: placement.y - height / 2 }
    ];

    let x = clamp(candidates[0].x, minX, maxX);
    let y = clamp(candidates[0].y, minY, maxY);

    const coreRect = {
      left: coreX - coreRadius * 0.94,
      top: coreY - coreRadius * 0.94,
      right: coreX + coreRadius * 0.94,
      bottom: coreY + coreRadius * 0.94
    };
    const planetRects = placements.map((planet) => ({
      id: planet.id,
      left: planet.x - planet.radius - 3,
      top: planet.y - planet.radius - 3,
      right: planet.x + planet.radius + 3,
      bottom: planet.y + planet.radius + 3
    }));
    const occluderRects = occlusionRef.current.map((occluder) => ({
      left: occluder.left,
      top: occluder.fixed ? occluder.top : occluder.top - scrollY,
      right: occluder.right,
      bottom: occluder.fixed ? occluder.bottom : occluder.bottom - scrollY
    }));

    const fits = (candidateX: number, candidateY: number, id: AICoreNodeId) => {
      const rect = {
        left: candidateX,
        top: candidateY,
        right: candidateX + width,
        bottom: candidateY + height
      };
      if (rectsOverlap(rect, coreRect, 2)) {
        return false;
      }
      if (placed.some((other) => rectsOverlap(rect, other, 4))) {
        return false;
      }
      if (
        planetRects.some(
          (planet) => planet.id !== id && rectsOverlap(rect, planet, 1)
        )
      ) {
        return false;
      }
      if (occluderRects.some((occluder) => rectsOverlap(rect, occluder, 3))) {
        return false;
      }
      return true;
    };

    if (targetOpacity > 0.02) {
      let resolved = false;
      for (const candidate of candidates) {
        const candidateX = clamp(candidate.x, minX, maxX);
        const candidateY = clamp(candidate.y, minY, maxY);
        if (fits(candidateX, candidateY, placement.id)) {
          x = candidateX;
          y = candidateY;
          resolved = true;
          break;
        }
      }

      // Nodes that sit in front of the core cannot use their own edge: every
      // adjacent slot overlaps the sphere. Slide the pill out to the core's
      // silhouette, staying on the node's own radial direction.
      if (!resolved) {
        const ringRadius =
          coreRadius * 1.08 + gap + Math.max(width, height) / 2;
        const baseAngle = Math.atan2(
          placement.y - coreY,
          placement.x - coreX
        );
        const angles = [baseAngle, baseAngle + 0.5, baseAngle - 0.5, baseAngle + 1, baseAngle - 1, baseAngle + 1.55, baseAngle - 1.55, baseAngle + Math.PI];
        for (const angle of angles) {
          const candidateX = clamp(
            coreX + Math.cos(angle) * ringRadius - width / 2,
            minX,
            maxX
          );
          const candidateY = clamp(
            coreY + Math.sin(angle) * ringRadius - height / 2,
            minY,
            maxY
          );
          if (fits(candidateX, candidateY, placement.id)) {
            x = candidateX;
            y = candidateY;
            resolved = true;
            break;
          }
        }
      }
      if (!resolved) {
        targetOpacity = 0;
      }
    }

    if (targetOpacity > 0.02) {
      placed.push({ left: x, top: y, right: x + width, bottom: y + height });
    }

    const labelCenterX = x + width / 2;
    const labelCenterY = y + height / 2;
    const deltaX = placement.x - labelCenterX;
    const deltaY = placement.y - labelCenterY;
    const distance = Math.hypot(deltaX, deltaY);
    const leader = label.querySelector<HTMLElement>(".ai-core-label__leader");
    if (leader) {
      if (targetOpacity > 0.02 && distance > placement.radius + 6) {
        const unitX = deltaX / distance;
        const unitY = deltaY / distance;
        const edgeX = Math.min(
          Math.abs(unitX) < 1e-4 ? Number.POSITIVE_INFINITY : width / 2 / Math.abs(unitX),
          Math.abs(unitY) < 1e-4 ? Number.POSITIVE_INFINITY : height / 2 / Math.abs(unitY)
        );
        const exitX = width / 2 + unitX * edgeX;
        const exitY = height / 2 + unitY * edgeX;
        const leaderLength = Math.max(0, distance - edgeX - placement.radius - 3);
        leader.style.left = `${exitX.toFixed(1)}px`;
        leader.style.top = `${(exitY - 0.5).toFixed(1)}px`;
        leader.style.width = `${leaderLength.toFixed(1)}px`;
        leader.style.transform = `rotate(${(
          (Math.atan2(deltaY, deltaX) * 180) /
          Math.PI
        ).toFixed(2)}deg)`;
        leader.style.opacity = (targetOpacity * 0.82).toFixed(3);
      } else {
        leader.style.opacity = "0";
      }
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
