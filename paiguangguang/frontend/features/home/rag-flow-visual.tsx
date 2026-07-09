"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";

import type { RagFlowStep } from "./homepage-data";

type RagFlowVisualProps = {
  ingestionSteps: RagFlowStep[];
  querySteps: RagFlowStep[];
};

const kindStyles: Record<RagFlowStep["kind"], string> = {
  ingestion: "border-emerald-400/30 bg-emerald-400/10 text-emerald-100",
  query: "border-sky-400/30 bg-sky-400/10 text-sky-100",
  branch: "border-fuchsia-400/30 bg-fuchsia-400/10 text-fuchsia-100",
  system: "border-amber-400/30 bg-amber-400/10 text-amber-100",
  ai: "border-violet-400/30 bg-violet-400/10 text-violet-100",
  storage: "border-slate-200/30 bg-slate-200/10 text-slate-100"
};

type Point = {
  x: number;
  y: number;
  row: number;
};

export function RagFlowVisual({ ingestionSteps, querySteps }: RagFlowVisualProps) {
  const steps = useMemo(() => [...ingestionSteps, ...querySteps], [ingestionSteps, querySteps]);
  const containerRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef<Array<HTMLDivElement | null>>([]);
  const [points, setPoints] = useState<Point[]>([]);

  useEffect(() => {
    const measure = () => {
      const container = containerRef.current;
      if (!container) {
        return;
      }

      const containerRect = container.getBoundingClientRect();
      const nextPoints = cardRefs.current
        .map((node) => {
          if (!node) {
            return null;
          }

          const rect = node.getBoundingClientRect();
          return {
            x: rect.left - containerRect.left + rect.width / 2,
            y: rect.top - containerRect.top + rect.height / 2,
            row: Math.round((rect.top - containerRect.top) / 8)
          };
        })
        .filter((point): point is Point => point !== null);

      setPoints(nextPoints);
    };

    measure();
    window.addEventListener("resize", measure);

    return () => window.removeEventListener("resize", measure);
  }, [steps.length]);

  const paths = useMemo(() => {
    const lines: string[] = [];

    for (let index = 0; index < points.length - 1; index += 1) {
      const current = points[index];
      const next = points[index + 1];
      const midX = (current.x + next.x) / 2;

      if (current.row === next.row) {
        lines.push(`M ${current.x} ${current.y} H ${next.x}`);
      } else {
        const elbowY = current.y + 22;
        const startX = current.x;
        const endX = next.x;
        lines.push(`M ${startX} ${current.y} V ${elbowY} H ${midX} V ${next.y - 22} H ${endX}`);
      }
    }

    return lines;
  }, [points]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97, y: 24 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.7, ease: "easeOut" }}
      className="relative overflow-hidden rounded-[32px] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.16),transparent_32%),radial-gradient(circle_at_right,rgba(217,70,239,0.16),transparent_36%),linear-gradient(180deg,rgba(15,23,42,0.95),rgba(2,6,23,0.98))] p-5 shadow-[0_30px_80px_rgba(2,6,23,0.45)]"
    >
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:24px_24px] opacity-20" />
      <div className="relative space-y-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.4em] text-cyan-200/80">RAG Control Plane</p>
            <h3 className="mt-2 text-2xl font-black text-white">可视化入库链路与问答链路</h3>
          </div>
          <div className="rounded-full border border-fuchsia-400/25 bg-fuchsia-400/10 px-3 py-1 text-xs font-medium text-fuchsia-100">
            Excalidraw-inspired
          </div>
        </div>
        <div ref={containerRef} className="relative">
          <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full overflow-visible">
            <defs>
              <linearGradient id="rag-line" x1="0%" x2="100%" y1="0%" y2="0%">
                <stop offset="0%" stopColor="rgba(103,232,249,0.05)" />
                <stop offset="50%" stopColor="rgba(103,232,249,0.75)" />
                <stop offset="100%" stopColor="rgba(217,70,239,0.6)" />
              </linearGradient>
            </defs>
            {paths.map((path, index) => (
              <path key={`${index}-${path}`} d={path} fill="none" stroke="url(#rag-line)" strokeWidth="2" strokeLinecap="round" />
            ))}
          </svg>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {steps.map((step, index) => (
              <motion.div
                key={step.id}
                ref={(node) => {
                  cardRefs.current[index] = node;
                }}
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.45, delay: index * 0.03 }}
                className="relative z-10 rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${kindStyles[step.kind]}`}>
                    {step.kind}
                  </span>
                  <span className="text-[11px] font-medium uppercase tracking-[0.28em] text-slate-400">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                </div>
                <h4 className="mt-4 text-base font-semibold text-white">{step.title}</h4>
                <p className="mt-2 text-sm leading-6 text-slate-300">{step.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {["Milvus", "Redis", "DeepSeek", "Guardrails", "Trace"].map((tag) => (
            <span key={tag} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-slate-200">
              {tag}
            </span>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
