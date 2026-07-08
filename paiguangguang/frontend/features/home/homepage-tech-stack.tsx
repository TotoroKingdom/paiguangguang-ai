"use client";

import { motion } from "framer-motion";

import type { TechStackItem } from "./homepage-data";
import { techStack } from "./homepage-data";

const categoryLabels: Record<TechStackItem["category"], string> = {
  frontend: "Frontend",
  backend: "Backend",
  ai: "AI",
  storage: "Storage",
  workflow: "Workflow",
  delivery: "Delivery"
};

const categoryStyles: Record<TechStackItem["category"], string> = {
  frontend: "from-sky-400/20 via-cyan-300/10 to-white/5 text-sky-100 border-sky-300/20",
  backend: "from-emerald-400/20 via-teal-300/10 to-white/5 text-emerald-100 border-emerald-300/20",
  ai: "from-fuchsia-400/20 via-pink-300/10 to-white/5 text-fuchsia-100 border-fuchsia-300/20",
  storage: "from-amber-400/20 via-orange-300/10 to-white/5 text-amber-100 border-amber-300/20",
  workflow: "from-violet-400/20 via-purple-300/10 to-white/5 text-violet-100 border-violet-300/20",
  delivery: "from-slate-200/15 via-slate-300/10 to-white/5 text-slate-100 border-white/10"
};

export function HomepageTechStack() {
  return (
    <section id="tech-stack" className="space-y-6">
      <div className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-[0.32em] text-cyan-200/80">Tech Stack</p>
        <h2 className="mt-3 text-3xl font-black text-white sm:text-4xl">漂浮式技术墙，强调能力而不是装饰图标</h2>
      </div>
      <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(14,165,233,0.15),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(217,70,239,0.13),transparent_30%),linear-gradient(180deg,rgba(15,23,42,0.95),rgba(2,6,23,0.95))] p-4 sm:p-6">
        <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px)] bg-[size:28px_28px] opacity-20" />
        <div className="relative grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {techStack.map((item, index) => (
            <motion.div
              key={`${item.category}-${item.name}`}
              initial={{ opacity: 0, scale: 0.95, y: 18 }}
              whileInView={{ opacity: 1, scale: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.45, delay: index * 0.035 }}
              whileHover={{ y: -6, rotate: index % 2 === 0 ? -1 : 1 }}
              className={`rounded-[22px] border bg-gradient-to-br p-4 backdrop-blur-sm ${categoryStyles[item.category]}`}
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-white/60">
                {categoryLabels[item.category]}
              </p>
              <div className="mt-4 flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/10 text-sm font-black text-white shadow-[0_0_35px_rgba(255,255,255,0.08)]">
                  {item.name.slice(0, 1)}
                </div>
                <div>
                  <p className="text-base font-semibold text-white">{item.name}</p>
                  <p className="mt-1 text-xs text-white/55">Capability marker</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
