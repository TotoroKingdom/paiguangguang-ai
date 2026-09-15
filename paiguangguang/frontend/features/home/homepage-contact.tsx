"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

const SunCanvas = dynamic(() => import("./sun-canvas").then((module) => module.SunCanvas), {
  ssr: false,
  loading: () => <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(110,231,183,0.16),transparent_32%),#101618" />
});

function SunCanvasFallback() {
  return (
    <div
      aria-hidden="true"
      className="absolute inset-0 bg-[radial-gradient(circle_at_58%_42%,rgba(186,230,253,0.55),transparent_10%),radial-gradient(circle_at_58%_42%,rgba(110,231,183,0.2),transparent_24%),radial-gradient(circle_at_45%_55%,rgba(56,189,248,0.12),transparent_36%),#101618]"
    />
  );
}

function LazySunCanvas() {
  const hostRef = useRef<HTMLDivElement>(null);
  const [shouldMountCanvas, setShouldMountCanvas] = useState(false);
  const [isCanvasActive, setIsCanvasActive] = useState(false);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const isSmallViewport = window.matchMedia("(max-width: 767px)").matches;

    if (prefersReducedMotion || isSmallViewport || !("IntersectionObserver" in window)) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setShouldMountCanvas(true);
        setIsCanvasActive(entry.isIntersecting);
      },
      { rootMargin: "280px 0px" }
    );

    observer.observe(host);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={hostRef} className="absolute inset-0">
      <SunCanvasFallback />
      {shouldMountCanvas ? <SunCanvas active={isCanvasActive} /> : null}
    </div>
  );
}

function GitHubIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5 fill-current">
      <path d="M12 2C6.48 2 2 6.58 2 12.26c0 4.54 2.87 8.39 6.84 9.75.5.1.68-.22.68-.49 0-.24-.01-.87-.01-1.71-2.78.62-3.37-1.37-3.37-1.37-.46-1.2-1.13-1.52-1.13-1.52-.92-.65.07-.64.07-.64 1.02.07 1.55 1.07 1.55 1.07.9 1.58 2.36 1.12 2.94.86.09-.67.35-1.12.63-1.38-2.22-.26-4.56-1.14-4.56-5.06 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.31.1-2.72 0 0 .84-.28 2.75 1.05.8-.23 1.66-.35 2.52-.35.86 0 1.72.12 2.52.35 1.91-1.33 2.75-1.05 2.75-1.05.55 1.41.2 2.46.1 2.72.64.72 1.03 1.63 1.03 2.75 0 3.93-2.35 4.8-4.58 5.05.36.32.69.96.69 1.94 0 1.4-.01 2.53-.01 2.87 0 .27.18.6.69.49A10.28 10.28 0 0 0 22 12.26C22 6.58 17.52 2 12 2Z" />
    </svg>
  );
}

export function HomepageContact() {
  return (
    <section id="contact" className="scroll-mt-10 space-y-8 pb-6">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-200/65">Contact / 04</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-white sm:text-4xl">一起做点有用的东西</h2>
        </div>
        <p className="max-w-md text-sm leading-7 text-white/45 sm:text-right">如果你也在构建 AI 产品，欢迎聊聊你的问题、想法或下一次合作。</p>
      </div>

      <div className="grid gap-3 lg:grid-cols-[0.9fr_1.1fr]">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.45 }}
          className="flex min-h-[360px] flex-col justify-between rounded-2xl border border-white/10 bg-white/[0.035] p-6 sm:p-8"
        >
          <div>
            <span className="font-mono text-xs text-emerald-200/70">hello@totoro</span>
            <h3 className="mt-12 max-w-sm text-3xl font-medium leading-tight tracking-[-0.04em] text-white sm:text-4xl">让好的想法先从一封邮件开始。</h3>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <a href="mailto:totorokingdom@foxmail.com" className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2.5 text-sm font-medium text-[#0a0d0f] transition hover:-translate-y-0.5 hover:bg-emerald-100">
              发邮件 <span aria-hidden="true">↗</span>
            </a>
            <a
              aria-label="GitHub profile"
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/15 text-white/70 transition hover:-translate-y-0.5 hover:border-emerald-200/50 hover:text-white"
              href="https://github.com/TotoroKingdom"
              rel="noreferrer"
              target="_blank"
            >
              <GitHubIcon />
            </a>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.97, y: 18 }}
          whileInView={{ opacity: 1, scale: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.55 }}
          className="relative min-h-[360px] overflow-hidden rounded-2xl border border-white/10 bg-[#101618] sm:min-h-[420px]"
        >
          <div className="pointer-events-none absolute inset-0 page-grid opacity-35" />
          <LazySunCanvas />
          <div className="absolute left-5 top-5 flex items-center gap-2 rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-[10px] uppercase tracking-[0.18em] text-white/50 backdrop-blur-md sm:left-7 sm:top-7">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-300" />
            Interactive artifact
          </div>
          <div className="absolute bottom-5 left-5 right-5 flex items-end justify-between text-[10px] text-white/35 sm:bottom-7 sm:left-7 sm:right-7">
            <span>drag to explore</span>
            <span>three.js / canvas</span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
