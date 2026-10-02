"use client";

import type { HTMLAttributes, PointerEvent } from "react";

export function NeumorphicCard({ className = "", ...props }: HTMLAttributes<HTMLElement>) {
  function tilt(event: PointerEvent<HTMLElement>) {
    if (event.pointerType !== "mouse" || !window.matchMedia("(min-width: 768px) and (hover: hover) and (prefers-reduced-motion: no-preference)").matches) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = Math.max(-1, Math.min(1, (event.clientX - rect.left) / rect.width * 2 - 1));
    const y = Math.max(-1, Math.min(1, (event.clientY - rect.top) / rect.height * 2 - 1));
    event.currentTarget.style.setProperty("--card-x", `${-y * 3}deg`);
    event.currentTarget.style.setProperty("--card-y", `${x * 4}deg`);
  }
  function reset(event: PointerEvent<HTMLElement>) {
    event.currentTarget.style.setProperty("--card-x", "0deg");
    event.currentTarget.style.setProperty("--card-y", "0deg");
  }
  return <article {...props} className={`neu-surface neu-card ${className}`} onPointerMove={tilt} onPointerLeave={reset} />;
}
