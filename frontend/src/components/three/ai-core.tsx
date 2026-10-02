"use client";

import dynamic from "next/dynamic";
import { Component, useEffect, useRef, useState, type CSSProperties, type ErrorInfo, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";
import { aiCoreNodes, AI_CORE_VIEW_HEIGHT } from "./ai-core-data";
import type { AICorePointer, AICoreSceneProps } from "./ai-core-scene";

const AICoreScene = dynamic<AICoreSceneProps>(() => import("./ai-core-scene"), {
  ssr: false,
  loading: () => <AICoreFallback />,
});

const visuallyHiddenStyle: CSSProperties = {
  position: "absolute",
  width: 1,
  height: 1,
  padding: 0,
  margin: -1,
  overflow: "hidden",
  clip: "rect(0, 0, 0, 0)",
  whiteSpace: "nowrap",
  border: 0,
};

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

export function AICoreFallback({ error = false }: { error?: boolean }) {
  return (
    <div className="ai-core-fallback" data-error={error || undefined} aria-hidden="true">
      <span className="ai-core-fallback__sphere" />
    </div>
  );
}

type AICoreProps = {
  className?: string;
};

export function AICore({ className = "" }: AICoreProps) {
  const stageRef = useRef<HTMLElement>(null);
  const pointerRef = useRef<AICorePointer>({ x: 0, y: 0 });
  const scrollRef = useRef(0);
  const [isInViewport, setIsInViewport] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [sceneReady, setSceneReady] = useState(false);
  const [sceneFailed, setSceneFailed] = useState(false);
  const [pageHidden, setPageHidden] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const [isCoarsePointer, setIsCoarsePointer] = useState(false);
  const [preferencesReady, setPreferencesReady] = useState(false);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) {
      return;
    }

    if (!("IntersectionObserver" in window)) {
      setIsInViewport(true);
      setHasLoaded(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        const visible = entry?.isIntersecting ?? false;
        setIsInViewport(visible);
        if (visible) {
          setHasLoaded(true);
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(stage);

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const coarsePointerQuery = window.matchMedia("(pointer: coarse), (max-width: 767px)");
    const updatePreferences = () => {
      setPrefersReducedMotion(reducedMotionQuery.matches);
      setIsCoarsePointer(coarsePointerQuery.matches);
      setPreferencesReady(true);
    };

    updatePreferences();
    reducedMotionQuery.addEventListener("change", updatePreferences);
    coarsePointerQuery.addEventListener("change", updatePreferences);

    return () => {
      reducedMotionQuery.removeEventListener("change", updatePreferences);
      coarsePointerQuery.removeEventListener("change", updatePreferences);
    };
  }, []);

  const reducedMotion = !preferencesReady || prefersReducedMotion || isCoarsePointer;
  const active = isInViewport && !pageHidden;
  const isFallbackVisible = !sceneReady || sceneFailed;
  const renderState = sceneFailed ? "error" : sceneReady ? "ready" : hasLoaded ? "loading" : "idle";

  useEffect(() => {
    const updateVisibility = () => setPageHidden(document.visibilityState === "hidden");
    const updateScroll = () => {
      scrollRef.current = window.scrollY;
    };

    updateVisibility();
    document.addEventListener("visibilitychange", updateVisibility);
    if (active && !reducedMotion) {
      updateScroll();
      window.addEventListener("scroll", updateScroll, { passive: true });
    }

    return () => {
      document.removeEventListener("visibilitychange", updateVisibility);
      window.removeEventListener("scroll", updateScroll);
    };
  }, [active, reducedMotion]);

  function handlePointerMove(event: ReactPointerEvent<HTMLElement>) {
    if (reducedMotion || !stageRef.current) {
      return;
    }

    const bounds = stageRef.current.getBoundingClientRect();
    if (!bounds.width || !bounds.height) {
      return;
    }

    pointerRef.current = {
      x: Math.max(-1, Math.min(1, ((event.clientX - bounds.left) / bounds.width - 0.5) * 2)),
      y: Math.max(-1, Math.min(1, ((event.clientY - bounds.top) / bounds.height - 0.5) * 2)),
    };
  }

  function resetPointer() {
    pointerRef.current = { x: 0, y: 0 };
  }

  return (
    <figure
      ref={stageRef}
      className={`ai-core-stage ${className}`.trim()}
      data-render-state={renderState}
      onPointerMove={handlePointerMove}
      onPointerLeave={resetPointer}
      aria-labelledby="ai-core-stage-caption"
      aria-describedby="ai-core-stage-description"
    >
      {isFallbackVisible ? <AICoreFallback error={sceneFailed} /> : null}
      {hasLoaded && !sceneFailed ? (
        <SceneErrorBoundary
          fallback={<AICoreFallback error />}
          onError={() => {
            setSceneFailed(true);
            setSceneReady(false);
          }}
        >
          <AICoreScene
            active={active}
            reducedMotion={reducedMotion}
            pointerRef={pointerRef}
            scrollRef={scrollRef}
            onReady={() => setSceneReady(true)}
            onContextLost={() => {
              setSceneFailed(true);
              setSceneReady(false);
            }}
          />
        </SceneErrorBoundary>
      ) : null}

      <div className="ai-core-node-labels" aria-hidden="true">
        {aiCoreNodes.map((node) => (
          <span key={node.id} className={`ai-core-label ai-core-label--${node.id}`} style={{
            left: `calc(50% + ${node.position[0] / AI_CORE_VIEW_HEIGHT} * var(--ai-core-size))`,
            top: `calc(50% - ${(node.position[1] + node.radius) / AI_CORE_VIEW_HEIGHT} * var(--ai-core-size) - 10px)`,
            transform: "translate(-50%, -100%)",
            color: node.labelColor,
            borderColor: `${node.color}66`,
          }}>
            {node.label}
          </span>
        ))}
      </div>

      <figcaption id="ai-core-stage-caption" className="ai-core-caption">
        LLM / RAG / TOOL / MEMORY / AGENT
      </figcaption>
      <span id="ai-core-stage-description" style={visuallyHiddenStyle}>
        An abstract spatial AI system core connects five nodes: LLM for model reasoning, RAG for retrieval, Tool for actions,
        Memory for context, and Agent for orchestration.
      </span>
    </figure>
  );
}

export default AICore;
