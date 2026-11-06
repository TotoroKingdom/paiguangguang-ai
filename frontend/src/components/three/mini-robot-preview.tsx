"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import styles from "./mini-robot-preview.module.css";

type MiniRobotPreviewProps = {
  poster: string;
  alt: string;
  sizes: string;
};

/** Reuses the full robot.js geometry/animation in mini mode once the poster enters view. */
export function MiniRobotPreview({ poster, alt, sizes }: MiniRobotPreviewProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const root = rootRef.current;
    if (!root || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches || !("WebGLRenderingContext" in window)) {
      return;
    }

    if (!("IntersectionObserver" in window)) {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(([entry]) => {
      setVisible(entry.isIntersecting);
    }, { rootMargin: "160px" });
    observer.observe(root);
    return () => observer.disconnect();
  }, []);

  return (
    <div className={styles.preview} ref={rootRef}>
      <Image src={poster} fill alt={alt} sizes={sizes} unoptimized />
      {visible && (
        <iframe
          title="Three.js 智能机器人 mini 预览"
          src="/threejs-lab/mini.html"
          loading="lazy"
          tabIndex={-1}
          aria-hidden="true"
          className={styles.frame}
        />
      )}
      <span className={styles.liveLabel} aria-hidden="true">● LIVE 3D</span>
    </div>
  );
}
