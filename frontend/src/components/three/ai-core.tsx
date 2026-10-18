import type { CSSProperties } from "react";

const visuallyHiddenStyle: CSSProperties = {
  position: "absolute",
  width: 1,
  height: 1,
  padding: 0,
  margin: -1,
  overflow: "hidden",
  clip: "rect(0, 0, 0, 0)",
  whiteSpace: "nowrap",
  border: 0
};

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

/**
 * The hero landmark for the persistent 3D layer. It reserves the visual column
 * and provides a static, server-rendered fallback until WebGL is ready. The
 * actual model lives in the single page-level canvas (see AICoreExperience).
 */
export function AICore({ className = "" }: AICoreProps) {
  return (
    <figure
      className={`ai-core-stage ${className}`.trim()}
      data-ai-scene-anchor="hero"
      aria-labelledby="ai-core-stage-caption"
      aria-describedby="ai-core-stage-description"
    >
      <AICoreFallback />
      <figcaption id="ai-core-stage-caption" className="ai-core-caption">
        LLM / RAG / TOOL / MEMORY / AGENT
        <span className="ai-core-caption__hint"> · 点击节点查看能力</span>
      </figcaption>
      <span id="ai-core-stage-description" style={visuallyHiddenStyle}>
        An interactive spatial AI system core. Five capability nodes — LLM for reasoning, RAG for
        retrieval, Tool for actions, Memory for context, and Agent for orchestration — orbit a
        pearl-like central core. Use the node labels or click the planets to inspect each capability.
      </span>
    </figure>
  );
}

export default AICore;
