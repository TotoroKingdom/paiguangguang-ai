"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

import { ArrowUpRightIcon, GithubIcon, MailIcon } from "@/components/icons";

const SunCanvas = dynamic(() => import("./sun-canvas").then((module) => module.SunCanvas), {
  ssr: false,
  loading: () => <div className="absolute inset-0 bg-[#101827]" />
});

function SunCanvasFallback() {
  return (
    <div
      aria-hidden="true"
      className="absolute inset-0 bg-[radial-gradient(circle_at_58%_42%,rgba(125,211,252,0.34),transparent_11%),radial-gradient(circle_at_58%_42%,rgba(37,99,235,0.18),transparent_28%),#101827]"
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

export function HomepageContact() {
  return (
    <section id="contact" className="home-section scroll-mt-24 pb-2">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div className="section-intro">
          <p className="eyebrow">Contact / 04</p>
          <h2 className="section-title">一起做点有用的东西</h2>
        </div>
        <p className="section-description mt-0 max-w-md sm:text-right">如果你也在构建 AI 产品，欢迎聊聊你的问题、想法或下一次合作。</p>
      </div>

      <div className="grid gap-3 lg:grid-cols-[0.9fr_1.1fr]">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.35 }}
          className="surface contact-card flex flex-col justify-between"
        >
          <div>
            <span className="contact-card__label">hello@totoro</span>
            <h3 className="contact-card__title">让好的想法先从一封邮件开始。</h3>
          </div>

          <div className="contact-card__actions">
            <a href="mailto:totorokingdom@foxmail.com" className="home-button home-button--solid">
              <MailIcon size={16} />
              发邮件
              <ArrowUpRightIcon size={15} />
            </a>
            <a
              aria-label="GitHub profile"
              className="icon-button"
              href="https://github.com/TotoroKingdom"
              rel="noreferrer"
              target="_blank"
            >
              <GithubIcon size={18} />
            </a>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.45, delay: 0.05 }}
          className="artifact-card"
        >
          <div className="artifact-card__grid" />
          <LazySunCanvas />
          <div className="artifact-card__badge">
            <span className="status-dot" />
            Interactive artifact
          </div>
          <div className="artifact-card__footer">
            <span>drag to explore</span>
            <span>three.js / canvas</span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
