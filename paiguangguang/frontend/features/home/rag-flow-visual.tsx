"use client";

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

function FlowColumn({
  title,
  steps
}: {
  title: string;
  steps: RagFlowStep[];
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-[0.28em] text-slate-300">{title}</h3>
        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-medium text-slate-300">
          {steps.length} steps
        </span>
      </div>
      <div className="relative space-y-3 pl-5 before:absolute before:bottom-3 before:left-[0.6rem] before:top-3 before:w-px before:bg-gradient-to-b before:from-cyan-300/80 before:via-fuchsia-400/70 before:to-transparent">
        {steps.map((step, index) => (
          <motion.div
            key={step.id}
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.45, delay: index * 0.04 }}
            className="relative rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-sm"
          >
            <span className={`absolute -left-5 top-5 h-3 w-3 rounded-full border ${kindStyles[step.kind]}`} />
            <div className="flex items-center gap-2">
              <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${kindStyles[step.kind]}`}>
                {step.kind}
              </span>
            </div>
            <h4 className="mt-3 text-base font-semibold text-white">{step.title}</h4>
            <p className="mt-2 text-sm leading-6 text-slate-300">{step.description}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

export function RagFlowVisual({ ingestionSteps, querySteps }: RagFlowVisualProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97, y: 24 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.7, ease: "easeOut" }}
      className="relative overflow-hidden rounded-[32px] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.16),transparent_32%),radial-gradient(circle_at_right,rgba(217,70,239,0.16),transparent_36%),linear-gradient(180deg,rgba(15,23,42,0.95),rgba(2,6,23,0.98))] p-5 shadow-[0_30px_80px_rgba(2,6,23,0.45)]"
    >
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:24px_24px] opacity-20" />
      <div className="relative">
        <div className="mb-5 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.4em] text-cyan-200/80">RAG Control Plane</p>
            <h3 className="mt-2 text-2xl font-black text-white">可视化入库链路与问答链路</h3>
          </div>
          <div className="rounded-full border border-fuchsia-400/25 bg-fuchsia-400/10 px-3 py-1 text-xs font-medium text-fuchsia-100">
            Excalidraw-inspired
          </div>
        </div>
        <div className="grid gap-6 lg:grid-cols-[1fr_auto_1fr] lg:items-start">
          <FlowColumn title="Ingestion" steps={ingestionSteps} />
          <div className="flex items-center justify-center lg:h-full">
            <motion.div
              initial={{ opacity: 0, scale: 0.85 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true, amount: 0.25 }}
              transition={{ duration: 0.55 }}
              className="relative flex h-20 w-20 items-center justify-center rounded-full border border-cyan-300/30 bg-[radial-gradient(circle,rgba(125,211,252,0.26),rgba(14,165,233,0.08)_60%,transparent_72%)]"
            >
              <div className="absolute inset-2 rounded-full border border-white/10" />
              <div className="absolute h-px w-32 bg-gradient-to-r from-transparent via-cyan-200/70 to-transparent" />
              <div className="absolute h-32 w-px bg-gradient-to-b from-transparent via-fuchsia-200/70 to-transparent" />
              <span className="text-xs font-semibold uppercase tracking-[0.35em] text-cyan-50">Flow</span>
            </motion.div>
          </div>
          <FlowColumn title="Query" steps={querySteps} />
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          {["Milvus", "Redis", "DeepSeek", "Guardrails", "Trace"].map((tag) => (
            <span
              key={tag}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-slate-200"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
