"use client";

import dynamic from "next/dynamic";
import { AnimatePresence, motion } from "framer-motion";
import {
  Component,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ErrorInfo,
  type ReactNode
} from "react";

import {
  AI_CORE_SCENE_IDS,
  aiCoreNodeIndex,
  aiCoreNodes,
  aiCoreScenes,
  type AICoreNodeId
} from "./ai-core-data";
import {
  computeSceneComposition,
  type ContentBlock,
  type ContentRole
} from "./ai-core-composition";
import {
  applySceneCompositions,
  buildScrollTimeline,
  clamp,
  fadeForScroll,
  sampleScrollTimeline,
  type MeasuredSceneAnchor,
  type ScrollTimeline
} from "./ai-core-scroll";
import { deviceDprLimit } from "./ai-core-runtime";
import {
  createInteractionState,
  createProjectionState,
  type AICoreInteractionStatus,
  type AICoreSceneBridge,
  type AICoreSceneProps,
  type LabelSize,
  type OcclusionRect
} from "./ai-core-types";

const AICoreScene = dynamic<AICoreSceneProps>(() => import("./ai-core-scene"), {
  ssr: false,
  loading: () => null
});

type SupportState = "pending" | "webgl" | "fallback";

type LabelStyle = CSSProperties & {
  "--node-color": string;
  "--node-accent": string;
};

const OCCLUSION_SELECTOR = [
  ".brand-header__inner",
  ".brand-footer",
  "main h1",
  "main h2",
  "main h3",
  "main p",
  "main a",
  "main li",
  "main button",
  ".brand-capability",
  ".brand-project",
  ".brand-exploration",
  ".brand-contact",
  ".ai-core-caption",
  ".brand-hero__bottom"
].join(",");

// Containers used for composition, not label collision. A block represents the
// real screen estate of a copy column, card, nav rail or caption.
const CONTENT_BLOCK_SELECTOR = [
  ".brand-header__inner",
  ".brand-footer",
  ".brand-hero__copy",
  ".brand-hero__bottom",
  ".brand-section-heading__copy",
  ".brand-projects__heading-copy",
  ".brand-capability",
  ".brand-project",
  ".brand-exploration",
  ".brand-approach-item",
  ".brand-contact",
  ".ai-core-caption"
].join(",");

// A drag may start on empty visual space, but never on copy, links, cards or controls.
const INTERACTION_IGNORE_SELECTOR = [
  "a",
  "button",
  "input",
  "textarea",
  "select",
  "label",
  "[role='button']",
  "[data-ai-core-ui]",
  ".ai-core-panel",
  ".ai-core-label",
  ".brand-header",
  ".brand-footer",
  ".brand-hero__copy",
  ".brand-hero__bottom",
  ".ai-core-caption",
  ".brand-section-heading__copy",
  ".brand-projects__heading-copy",
  ".brand-capability",
  ".brand-project",
  ".brand-exploration",
  ".brand-contact",
  "p",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "li",
  "blockquote"
].join(",");

function safeMatchMedia(query: string): MediaQueryList | null {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return null;
  }
  try {
    return window.matchMedia(query);
  } catch {
    return null;
  }
}

function useMediaPreference(query: string): boolean {
  const [matches, setMatches] = useState(() => safeMatchMedia(query)?.matches ?? false);

  useEffect(() => {
    const media = safeMatchMedia(query);
    if (!media) {
      return;
    }

    const update = () => setMatches(media.matches);
    update();
    if (typeof media.addEventListener === "function") {
      media.addEventListener("change", update);
      return () => media.removeEventListener("change", update);
    }
    media.addListener?.(update);
    return () => media.removeListener?.(update);
  }, [query]);

  return matches;
}

function detectWebGL(): boolean {
  if (typeof window === "undefined" || typeof window.WebGLRenderingContext === "undefined") {
    return false;
  }

  try {
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("webgl2") ?? canvas.getContext("webgl");
    const extension = context?.getExtension("WEBGL_lose_context");
    extension?.loseContext();
    return Boolean(context);
  } catch {
    return false;
  }
}

function collectOcclusionRects(page: HTMLElement, scrollY: number): OcclusionRect[] {
  const rects: OcclusionRect[] = [];
  page.querySelectorAll<HTMLElement>(OCCLUSION_SELECTOR).forEach((element) => {
    if (element.closest("[data-ai-core-ui]")) {
      return;
    }
    const rect = element.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) {
      return;
    }
    if (element.closest(".brand-header")) {
      rects.push({
        left: rect.left,
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom,
        fixed: true
      });
      return;
    }
    rects.push({
      left: rect.left,
      top: rect.top + scrollY,
      right: rect.right,
      bottom: rect.bottom + scrollY
    });
  });
  return rects;
}

function collectContentBlocks(page: HTMLElement, scrollY: number): ContentBlock[] {
  const blocks: ContentBlock[] = [];
  page.querySelectorAll<HTMLElement>(CONTENT_BLOCK_SELECTOR).forEach((element) => {
    if (element.closest("[data-ai-core-ui]")) {
      return;
    }
    const rect = element.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) {
      return;
    }

    const inHeader = Boolean(element.closest(".brand-header"));
    let role: ContentRole = "copy";
    if (inHeader) {
      role = "nav";
    } else if (element.classList.contains("brand-footer")) {
      role = "footer";
    } else if (element.classList.contains("ai-core-caption")) {
      role = "caption";
    } else if (
      element.classList.contains("brand-capability") ||
      element.classList.contains("brand-project") ||
      element.classList.contains("brand-exploration") ||
      element.classList.contains("brand-approach-item") ||
      element.classList.contains("brand-contact")
    ) {
      role = "card";
    }

    blocks.push({
      left: rect.left,
      top: inHeader ? rect.top : rect.top + scrollY,
      right: rect.right,
      bottom: inHeader ? rect.bottom : rect.bottom + scrollY,
      role,
      fixed: inHeader || undefined
    });
  });
  return blocks;
}

type SceneErrorBoundaryProps = {
  children: ReactNode;
  fallback: ReactNode;
  onError: (error: Error) => void;
};

type SceneErrorBoundaryState = {
  hasError: boolean;
};

class SceneErrorBoundary extends Component<SceneErrorBoundaryProps, SceneErrorBoundaryState> {
  state: SceneErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): SceneErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, _errorInfo: ErrorInfo) {
    this.props.onError(error);
  }

  render() {
    return this.state.hasError ? this.props.fallback : this.props.children;
  }
}

export function AICoreExperience() {
  const prefersReducedMotion = useMediaPreference("(prefers-reduced-motion: reduce)");
  const coarsePointer = useMediaPreference("(pointer: coarse)");
  const narrowViewport = useMediaPreference("(max-width: 767px)");

  const lowPowerDevice = useMemo(() => {
    if (typeof navigator === "undefined") {
      return false;
    }
    const cores = navigator.hardwareConcurrency ?? 8;
    const memory = (navigator as Navigator & { deviceMemory?: number }).deviceMemory ?? 8;
    return cores <= 4 || memory <= 4;
  }, []);

  const simplified = coarsePointer || narrowViewport || lowPowerDevice;
  const quality = deviceDprLimit(coarsePointer || narrowViewport, lowPowerDevice);

  const [support, setSupport] = useState<SupportState>("pending");
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [pageVisible, setPageVisible] = useState(true);
  const [inRange, setInRange] = useState(true);
  const [hoveredId, setHoveredId] = useState<AICoreNodeId | null>(null);
  const [focusedId, setFocusedId] = useState<AICoreNodeId | null>(null);
  const [dragging, setDragging] = useState(false);
  const [scrolling, setScrolling] = useState(false);
  const [panelSide, setPanelSide] = useState<"left" | "right">("left");

  const timelineRef = useRef<ScrollTimeline | null>(null);
  const interactionRef = useRef(createInteractionState());
  const projectedRef = useRef(createProjectionState());
  const labelRefs = useRef<Partial<Record<AICoreNodeId, HTMLButtonElement | null>>>({});
  const labelSizesRef = useRef<Partial<Record<AICoreNodeId, LabelSize>>>({});
  const occlusionRef = useRef<OcclusionRect[]>([]);
  const contentBlocksRef = useRef<ContentBlock[]>([]);
  const canvasSlotRef = useRef<HTMLDivElement>(null);
  const haloRef = useRef<HTMLDivElement>(null);
  const bridgeRef = useRef<AICoreSceneBridge | null>(null);
  const hoveredRef = useRef<AICoreNodeId | null>(null);
  const focusedRef = useRef<AICoreNodeId | null>(null);
  const inRangeRef = useRef(true);
  const lastSceneRef = useRef(0);
  const pressRef = useRef({ x: 0, y: 0, moved: false, pointerId: null as number | null });
  const measureFrame = useRef(0);
  const scrollTimer = useRef<number | null>(null);

  const showExperience = support === "webgl" && !failed;
  const status: AICoreInteractionStatus = dragging
    ? "dragging"
    : focusedId
      ? "focused"
      : hoveredId
        ? "hover"
        : scrolling
          ? "scrolling"
          : "idle";

  const focusedNode = focusedId ? aiCoreNodes.find((node) => node.id === focusedId) ?? null : null;

  const measure = useCallback(() => {
    if (typeof window === "undefined") {
      return;
    }
    const page = document.querySelector<HTMLElement>(".home-page");
    if (!page) {
      return;
    }

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const scrollY = window.scrollY;
    const documentHeight = Math.max(
      document.documentElement.scrollHeight,
      document.body?.scrollHeight ?? 0
    );
    const maxScroll = Math.max(0, documentHeight - viewportHeight);
    const anchors: MeasuredSceneAnchor[] = [];

    AI_CORE_SCENE_IDS.forEach((id, index) => {
      const landmark = page.querySelector<HTMLElement>(`[data-ai-scene-anchor="${id}"]`);
      const section = document.getElementById(id);
      const element = landmark ?? section;
      if (element) {
        const rect = element.getBoundingClientRect();
        anchors.push({
          index,
          centerX: rect.left + rect.width / 2,
          centerY: rect.top + scrollY + rect.height / 2
        });
      } else {
        anchors.push({
          index,
          centerX: viewportWidth / 2,
          centerY: viewportHeight / 2 + index * viewportHeight * 0.9
        });
      }
    });

    const journey = document.getElementById("journey");
    const journeyBottom = journey ? journey.getBoundingClientRect().bottom + scrollY : documentHeight;
    const baseTimeline = buildScrollTimeline({
      viewportWidth,
      viewportHeight,
      maxScroll,
      anchors,
      // Let the core make a deliberate exit across the final section instead of
      // snapping off at max scroll when the footer sits below the viewport.
      fadeStart: Math.min(maxScroll, journeyBottom - viewportHeight * 0.9),
      fadeEnd: Math.min(maxScroll, journeyBottom - viewportHeight * 0.1),
      reducedMotion: prefersReducedMotion
    });

    const blocks = collectContentBlocks(page, scrollY);
    contentBlocksRef.current = blocks;

    const compositions = baseTimeline.stops.map((stop) =>
      computeSceneComposition({
        index: stop.index,
        anchorX: stop.anchorX,
        anchorY: stop.anchorY,
        scrollY: stop.scrollY,
        pose: aiCoreScenes[stop.index],
        blocks,
        viewportWidth,
        viewportHeight
      })
    );
    const timeline = applySceneCompositions(baseTimeline, compositions);

    timelineRef.current = timeline;

    for (const node of aiCoreNodes) {
      const label = labelRefs.current[node.id];
      if (label) {
        labelSizesRef.current[node.id] = {
          width: label.offsetWidth,
          height: label.offsetHeight
        };
      }
    }

    occlusionRef.current = collectOcclusionRects(page, scrollY);

    const initialFade = fadeForScroll(timeline, scrollY);
    const nextInRange = initialFade > 0.005;
    if (nextInRange !== inRangeRef.current) {
      inRangeRef.current = nextInRange;
      setInRange(nextInRange);
    }
    lastSceneRef.current = sampleScrollTimeline(timeline, scrollY, prefersReducedMotion).sceneIndex;

    bridgeRef.current?.invalidate();
  }, [prefersReducedMotion]);

  const scheduleMeasure = useCallback(() => {
    if (measureFrame.current) {
      window.cancelAnimationFrame(measureFrame.current);
    }
    measureFrame.current = window.requestAnimationFrame(() => {
      measureFrame.current = 0;
      measure();
    });
  }, [measure]);

  const updateHover = useCallback((id: AICoreNodeId | null) => {
    if (hoveredRef.current === id) {
      return;
    }
    hoveredRef.current = id;
    setHoveredId(id);
    interactionRef.current.lastActivity = performance.now();
  }, []);

  const findNodeAt = useCallback((x: number, y: number): AICoreNodeId | null => {
    let nearest: AICoreNodeId | null = null;
    let nearestDistance = Infinity;
    for (const node of aiCoreNodes) {
      const projected = projectedRef.current.nodes[node.id];
      if (!projected?.visible) {
        continue;
      }
      const distance = Math.hypot(projected.x - x, projected.y - y);
      const hitRadius = Math.max(30, projected.radius * 1.8 + 8);
      if (distance < hitRadius && distance < nearestDistance) {
        nearest = node.id;
        nearestDistance = distance;
      }
    }
    return nearest;
  }, []);

  const clearFocus = useCallback(() => {
    focusedRef.current = null;
    setFocusedId(null);
    updateHover(null);
    interactionRef.current.drag.recenterAt = 1;
  }, [updateHover]);

  const selectNode = useCallback(
    (id: AICoreNodeId) => {
      const next = focusedRef.current === id ? null : id;
      focusedRef.current = next;
      setFocusedId(next);
      if (next) {
        updateHover(id);
        interactionRef.current.drag.recenterAt = 1;
        const coreX = projectedRef.current.coreX;
        setPanelSide(coreX > window.innerWidth * 0.55 ? "left" : "right");
      } else {
        updateHover(null);
      }
    },
    [updateHover]
  );

  useEffect(() => {
    setSupport(detectWebGL() ? "webgl" : "fallback");
    interactionRef.current.lastActivity = performance.now();
  }, []);

  useEffect(() => {
    const update = () => {
      const visible = document.visibilityState !== "hidden";
      setPageVisible(visible);
      if (!visible) {
        interactionRef.current.drag.active = false;
        hoveredRef.current = null;
        setDragging(false);
        setHoveredId(null);
      }
    };
    update();
    document.addEventListener("visibilitychange", update);
    return () => document.removeEventListener("visibilitychange", update);
  }, []);

  useEffect(() => {
    const page = document.querySelector<HTMLElement>(".home-page");
    if (!page) {
      return;
    }
    const state = failed || support === "fallback" ? "fallback" : ready ? "ready" : "loading";
    page.setAttribute("data-ai-core", state);
    return () => {
      if (page.getAttribute("data-ai-core") === state) {
        page.removeAttribute("data-ai-core");
      }
    };
  }, [failed, ready, support]);

  useEffect(() => {
    scheduleMeasure();
    let active = true;
    const handleResize = () => scheduleMeasure();
    window.addEventListener("resize", handleResize, { passive: true });

    let observer: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      const main = document.querySelector("main");
      if (main) {
        observer = new ResizeObserver(() => scheduleMeasure());
        observer.observe(main);
        const header = document.querySelector(".brand-header");
        if (header) {
          observer.observe(header);
        }
      }
    }

    if (document.fonts?.ready) {
      document.fonts.ready
        .then(() => {
          if (active) {
            scheduleMeasure();
          }
        })
        .catch(() => undefined);
    }

    return () => {
      active = false;
      window.removeEventListener("resize", handleResize);
      observer?.disconnect();
      if (measureFrame.current) {
        window.cancelAnimationFrame(measureFrame.current);
      }
    };
  }, [scheduleMeasure]);

  useEffect(() => {
    const onScroll = () => {
      const now = performance.now();
      const interaction = interactionRef.current;
      interaction.lastActivity = now;
      interaction.lastScrollAt = now;
      interaction.drag.recenterAt = 1;

      setScrolling((previous) => (previous ? previous : true));
      if (scrollTimer.current) {
        window.clearTimeout(scrollTimer.current);
      }
      scrollTimer.current = window.setTimeout(() => {
        scrollTimer.current = null;
        setScrolling(false);
      }, 220);

      const timeline = timelineRef.current;
      if (!timeline) {
        return;
      }

      const scrollY = window.scrollY;
      const nextInRange = fadeForScroll(timeline, scrollY) > 0.005;
      if (nextInRange !== inRangeRef.current) {
        inRangeRef.current = nextInRange;
        setInRange(nextInRange);
        if (!nextInRange && focusedRef.current) {
          focusedRef.current = null;
          setFocusedId(null);
        }
      }

      const scene = sampleScrollTimeline(timeline, scrollY, prefersReducedMotion);
      if (scene.sceneIndex !== lastSceneRef.current) {
        lastSceneRef.current = scene.sceneIndex;
        if (focusedRef.current) {
          focusedRef.current = null;
          setFocusedId(null);
        }
      }

      if (prefersReducedMotion) {
        bridgeRef.current?.invalidate();
      }
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (scrollTimer.current) {
        window.clearTimeout(scrollTimer.current);
        scrollTimer.current = null;
      }
    };
  }, [prefersReducedMotion]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        clearFocus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [clearFocus]);

  useEffect(() => {
    if (focusedId) {
      focusedRef.current = focusedId;
    }
  }, [focusedId]);

  useEffect(() => {
    if (showExperience) {
      scheduleMeasure();
    }
  }, [scheduleMeasure, showExperience]);

  useEffect(() => {
    bridgeRef.current?.invalidate();
  }, [focusedId, hoveredId]);

  useEffect(() => {
    document.body.style.cursor = dragging ? "grabbing" : "";
    return () => {
      document.body.style.cursor = "";
    };
  }, [dragging]);

  useEffect(() => {
    if (!showExperience) {
      return;
    }

    const onPointerDown = (event: PointerEvent) => {
      if (event.pointerType === "mouse" && event.button !== 0) {
        return;
      }
      const target = event.target;
      if (!(target instanceof Element) || target.closest(INTERACTION_IGNORE_SELECTOR)) {
        return;
      }

      const interaction = interactionRef.current;
      interaction.lastActivity = performance.now();
      pressRef.current = {
        x: event.clientX,
        y: event.clientY,
        moved: false,
        pointerId: event.pointerId
      };

      if (prefersReducedMotion || coarsePointer || event.pointerType === "touch") {
        return;
      }

      interaction.drag.active = true;
      interaction.drag.lastX = event.clientX;
      interaction.drag.lastY = event.clientY;
      interaction.drag.lastMoveAt = performance.now();
      interaction.drag.velocityYaw = 0;
      interaction.drag.velocityPitch = 0;
      interaction.drag.recenterAt = 0;
      setDragging(true);
      event.preventDefault();
    };

    const onPointerMove = (event: PointerEvent) => {
      const interaction = interactionRef.current;
      interaction.pointer.x = clamp((event.clientX / window.innerWidth - 0.5) * 2, -1, 1);
      interaction.pointer.y = clamp((event.clientY / window.innerHeight - 0.5) * 2, -1, 1);
      interaction.pointerScreen.x = event.clientX;
      interaction.pointerScreen.y = event.clientY;
      interaction.pointerNdc.x = (event.clientX / window.innerWidth) * 2 - 1;
      interaction.pointerNdc.y = -(event.clientY / window.innerHeight) * 2 + 1;
      interaction.lastActivity = performance.now();

      const target = event.target;
      const overContent =
        target instanceof Element && Boolean(target.closest(INTERACTION_IGNORE_SELECTOR));
      const overLabel =
        target instanceof Element && Boolean(target.closest("[data-ai-core-label]"));
      if (!overLabel) {
        if (!overContent) {
          updateHover(findNodeAt(event.clientX, event.clientY));
        } else if (hoveredRef.current) {
          updateHover(null);
        }
      }

      const press = pressRef.current;
      if (Math.hypot(event.clientX - press.x, event.clientY - press.y) > 6) {
        press.moved = true;
      }

      if (prefersReducedMotion || !interaction.drag.active) {
        return;
      }

      const dx = event.clientX - interaction.drag.lastX;
      const dy = event.clientY - interaction.drag.lastY;
      const now = performance.now();
      const elapsed = Math.max(8, now - interaction.drag.lastMoveAt);
      interaction.drag.targetYaw = clamp(interaction.drag.targetYaw + dx * 0.006, -1.15, 1.15);
      interaction.drag.targetPitch = clamp(interaction.drag.targetPitch + dy * 0.0045, -0.5, 0.5);
      interaction.drag.velocityYaw = clamp((dx * 0.006 * 1000) / elapsed, -2.4, 2.4);
      interaction.drag.velocityPitch = clamp((dy * 0.0045 * 1000) / elapsed, -1.6, 1.6);
      interaction.drag.lastX = event.clientX;
      interaction.drag.lastY = event.clientY;
      interaction.drag.lastMoveAt = now;
      updateHover(null);
      event.preventDefault();
    };

    const onPointerUp = (event: PointerEvent) => {
      const interaction = interactionRef.current;
      if (interaction.drag.active) {
        interaction.drag.active = false;
        setDragging(false);
      }

      const press = pressRef.current;
      if (press.pointerId === event.pointerId && !press.moved) {
        const hit = findNodeAt(event.clientX, event.clientY);
        if (hit) {
          selectNode(hit);
        } else {
          clearFocus();
        }
      }

      pressRef.current = { x: 0, y: 0, moved: false, pointerId: null };
    };

    const onPointerCancel = () => {
      const interaction = interactionRef.current;
      interaction.drag.active = false;
      interaction.drag.velocityYaw = 0;
      interaction.drag.velocityPitch = 0;
      setDragging(false);
      pressRef.current = { x: 0, y: 0, moved: false, pointerId: null };
    };

    window.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove, { passive: false });
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerCancel);
    window.addEventListener("blur", onPointerCancel);
    return () => {
      window.removeEventListener("pointerdown", onPointerDown);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("pointercancel", onPointerCancel);
      window.removeEventListener("blur", onPointerCancel);
    };
  }, [
    clearFocus,
    coarsePointer,
    findNodeAt,
    prefersReducedMotion,
    selectNode,
    showExperience,
    updateHover
  ]);

  const handleBridge = useCallback((bridge: AICoreSceneBridge | null) => {
    bridgeRef.current = bridge;
  }, []);

  const handleReady = useCallback(() => setReady(true), []);
  const handleContextLost = useCallback(() => {
    setReady(false);
    setFailed(true);
  }, []);
  const handleSceneError = useCallback(() => {
    setReady(false);
    setFailed(true);
  }, []);

  const sceneActive = pageVisible && inRange && support === "webgl" && !failed;

  return (
    <>
      <div className="ai-core-visual-layer" data-state={status} data-ai-core-ui="true" aria-hidden="true">
        <div ref={haloRef} className="ai-core-ambient-halo" aria-hidden="true" />
        <div ref={canvasSlotRef} className="ai-core-canvas-slot">
          {showExperience ? (
            <SceneErrorBoundary fallback={null} onError={handleSceneError}>
              <AICoreScene
                active={sceneActive}
                reducedMotion={prefersReducedMotion}
                simplified={simplified}
                quality={quality}
                focusedId={focusedId}
                hoveredId={hoveredId}
                interactionRef={interactionRef}
                projectedRef={projectedRef}
                timelineRef={timelineRef}
                labelRefs={labelRefs}
                labelSizesRef={labelSizesRef}
                occlusionRef={occlusionRef}
                contentBlocksRef={contentBlocksRef}
                canvasOpacityRef={canvasSlotRef}
                haloRef={haloRef}
                onBridge={handleBridge}
                onReady={handleReady}
                onContextLost={handleContextLost}
              />
            </SceneErrorBoundary>
          ) : null}
        </div>

      </div>

      <div className="ai-core-overlay" data-state={status} data-ai-core-ui="true">
        <div className="ai-core-labels" role="group" aria-label="AI 系统能力节点">
          {showExperience
            ? aiCoreNodes.map((node) => (
                <button
                  key={node.id}
                  type="button"
                  ref={(element) => {
                    labelRefs.current[node.id] = element;
                  }}
                  className="ai-core-label"
                  data-ai-core-label="true"
                  data-state={
                    focusedId === node.id ? "focused" : hoveredId === node.id ? "hovered" : "idle"
                  }
                  aria-pressed={focusedId === node.id}
                  aria-label={`聚焦 ${node.label}：${node.title}`}
                  style={
                    {
                      "--node-color": node.color,
                      "--node-accent": node.accent
                    } as LabelStyle
                  }
                  onPointerEnter={() => updateHover(node.id)}
                  onPointerLeave={() => {
                    if (focusedRef.current !== node.id) {
                      updateHover(null);
                    }
                  }}
                  onFocus={() => updateHover(node.id)}
                  onBlur={() => {
                    if (focusedRef.current !== node.id) {
                      updateHover(null);
                    }
                  }}
                  onClick={() => selectNode(node.id)}
                >
                  <span className="ai-core-label__leader" aria-hidden="true" />
                  <span className="ai-core-label__inner">
                    <span className="ai-core-label__dot" aria-hidden="true" />
                    <span>{node.label}</span>
                  </span>
                </button>
              ))
            : null}
        </div>

        <AnimatePresence mode="wait">
          {focusedNode ? (
            <motion.aside
              key={focusedNode.id}
              className={`ai-core-panel ai-core-panel--${panelSide}`}
              role="region"
              aria-label={`${focusedNode.title} 能力说明`}
              aria-live="polite"
              initial={{ opacity: 0, y: 18, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 12, scale: 0.98 }}
              transition={{ duration: prefersReducedMotion ? 0 : 0.3, ease: "easeOut" }}
            >
              <div className="ai-core-panel__top">
                <span className="ai-core-panel__kicker">
                  NODE 0{(aiCoreNodeIndex.get(focusedNode.id) ?? 0) + 1} · {focusedNode.label}
                </span>
                <button
                  type="button"
                  className="ai-core-panel__close"
                  onClick={clearFocus}
                  aria-label="关闭能力说明"
                >
                  ×
                </button>
              </div>
              <h2 className="ai-core-panel__title">{focusedNode.title}</h2>
              <p className="ai-core-panel__description">{focusedNode.description}</p>
              <ul className="ai-core-panel__items">
                {focusedNode.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <p className="ai-core-panel__hint">点击空白或按 Esc 返回整体视角</p>
            </motion.aside>
          ) : null}
        </AnimatePresence>
      </div>
    </>
  );
}
