"use client";

import { useEffect, useRef, useState } from "react";

import styles from "./mini-scene-preview.module.css";

export type MiniSceneKind = "robot" | "gears";

const scenes: Record<MiniSceneKind, string> = {
  robot: "/threejs-lab/mini.html",
  gears: "/threejs-gears/mini.html"
};

/** The poster stays abstract until the real WebGL scene sends its first-frame signal. */
export function MiniScenePreview({ scene }: { scene: MiniSceneKind }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [visible, setVisible] = useState(false);
  const [ready, setReady] = useState(false);
  const [available, setAvailable] = useState(true);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches || !("WebGLRenderingContext" in window)) {
      setAvailable(false);
      return;
    }
    if (!("IntersectionObserver" in window)) {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) setReady(false);
      setVisible(entry.isIntersecting);
    }, { rootMargin: "160px" });
    observer.observe(root);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!visible) return;
    function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin || event.source !== frameRef.current?.contentWindow) return;
      if (event.data?.type === "mini-scene-ready") setReady(true);
      if (event.data?.type === "mini-scene-error") setAvailable(false);
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [visible]);

  return (
    <div className={styles.preview} ref={rootRef} aria-hidden="true" data-mini-scene={scene}>
      <span className={styles.orbit} />
      {available && visible && (
        <iframe
          ref={frameRef}
          title={`${scene} mini 3D preview`}
          src={scenes[scene]}
          loading="lazy"
          tabIndex={-1}
          onLoad={() => frameRef.current?.contentWindow?.postMessage({ type: "mini-scene-status-request" }, window.location.origin)}
          className={`${styles.frame}${ready ? ` ${styles.frameReady}` : ""}`}
        />
      )}
      <span className={styles.liveLabel}>
        {ready ? "● LIVE 3D" : available ? "3D LOADING" : "3D PREVIEW"}
      </span>
    </div>
  );
}
