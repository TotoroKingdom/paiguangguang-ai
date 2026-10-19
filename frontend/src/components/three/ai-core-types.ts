import type { MutableRefObject, RefObject } from "react";
import type { AICoreNodeId } from "./ai-core-data";
import type { ContentBlock } from "./ai-core-composition";
import type { ScrollTimeline } from "./ai-core-scroll";

export type AICoreInteractionStatus = "idle" | "hover" | "dragging" | "focused" | "scrolling";

export type AICoreDragState = {
  active: boolean;
  targetYaw: number;
  targetPitch: number;
  currentYaw: number;
  currentPitch: number;
  velocityYaw: number;
  velocityPitch: number;
  lastX: number;
  lastY: number;
  lastMoveAt: number;
  pressX: number;
  pressY: number;
  recenterAt: number;
};

export type AICoreInteractionState = {
  pointer: { x: number; y: number };
  pointerScreen: { x: number; y: number };
  pointerNdc: { x: number; y: number };
  lastActivity: number;
  lastScrollAt: number;
  drag: AICoreDragState;
};

export type AICoreProjectedNode = {
  id: AICoreNodeId;
  x: number;
  y: number;
  radius: number;
  distance: number;
  visible: boolean;
};

export type AICoreProjectionState = {
  nodes: Partial<Record<AICoreNodeId, AICoreProjectedNode>>;
  coreX: number;
  coreY: number;
  coreRadius: number;
  fade: number;
  sceneIndex: number;
};

export type OcclusionRect = {
  left: number;
  top: number;
  right: number;
  bottom: number;
  /** Sticky/fixed UI (the floating nav) is stored in viewport coordinates. */
  fixed?: boolean;
};

export type AICoreSceneBridge = {
  invalidate: () => void;
};

export type LabelSize = {
  width: number;
  height: number;
};

export type AICoreSceneProps = {
  active: boolean;
  reducedMotion: boolean;
  simplified: boolean;
  quality: number;
  focusedId: AICoreNodeId | null;
  hoveredId: AICoreNodeId | null;
  interactionRef: MutableRefObject<AICoreInteractionState>;
  projectedRef: MutableRefObject<AICoreProjectionState>;
  timelineRef: MutableRefObject<ScrollTimeline | null>;
  labelRefs: MutableRefObject<Partial<Record<AICoreNodeId, HTMLButtonElement | null>>>;
  labelSizesRef: MutableRefObject<Partial<Record<AICoreNodeId, LabelSize>>>;
  occlusionRef: MutableRefObject<OcclusionRect[]>;
  contentBlocksRef: MutableRefObject<ContentBlock[]>;
  canvasOpacityRef: RefObject<HTMLElement>;
  haloRef: RefObject<HTMLElement>;
  onBridge?: (bridge: AICoreSceneBridge | null) => void;
  onReady?: () => void;
  onContextLost?: () => void;
};

export function createInteractionState(): AICoreInteractionState {
  return {
    pointer: { x: 0, y: 0 },
    pointerScreen: { x: 0, y: 0 },
    pointerNdc: { x: 0, y: 0 },
    lastActivity: 0,
    lastScrollAt: 0,
    drag: {
      active: false,
      targetYaw: 0,
      targetPitch: 0,
      currentYaw: 0,
      currentPitch: 0,
      velocityYaw: 0,
      velocityPitch: 0,
      lastX: 0,
      lastY: 0,
      lastMoveAt: 0,
      pressX: 0,
      pressY: 0,
      recenterAt: 0
    }
  };
}

export function createProjectionState(): AICoreProjectionState {
  return {
    nodes: {},
    coreX: 0,
    coreY: 0,
    coreRadius: 0,
    fade: 0,
    sceneIndex: 0
  };
}
