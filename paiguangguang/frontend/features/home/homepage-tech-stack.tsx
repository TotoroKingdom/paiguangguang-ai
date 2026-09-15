"use client";

import { motion } from "framer-motion";

import type { TechStackItem } from "./homepage-data";
import { techStack } from "./homepage-data";

const categoryOrder: TechStackItem["category"][] = ["ai", "backend", "frontend", "storage", "workflow", "delivery"];

const categoryLabels: Record<TechStackItem["category"], string> = {
  frontend: "Frontend",
  backend: "Backend",
  ai: "AI / RAG",
  storage: "Storage",
  workflow: "Workflow",
  delivery: "Delivery",
  response: "Response"
};

const categoryAccent: Record<TechStackItem["category"], string> = {
  frontend: "border-sky-200/15 text-sky-100/85 hover:border-sky-200/45",
  backend: "border-violet-200/15 text-violet-100/85 hover:border-violet-200/45",
  ai: "border-emerald-200/15 text-emerald-100/85 hover:border-emerald-200/45",
  storage: "border-amber-100/15 text-amber-100/85 hover:border-amber-100/45",
  workflow: "border-fuchsia-200/15 text-fuchsia-100/85 hover:border-fuchsia-200/45",
  delivery: "border-white/15 text-white/75 hover:border-white/40",
  response: "border-white/15 text-white/75 hover:border-white/40"
};

export function HomepageTechStack() {
  return (
    <section id="tech-stack" className="scroll-mt-10 space-y-8">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-200/65">Stack / 2026</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-white sm:text-4xl">工具是手，系统才是作品</h2>
        </div>
        <p className="max-w-md text-sm leading-7 text-white/45 sm:text-right">用熟悉的工程基础，连接模型、数据和真实业务。</p>
      </div>

      <div className="rounded-3xl border border-white/10 bg-white/[0.025] p-5 sm:p-7">
        <div className="space-y-7">
          {categoryOrder.map((category, categoryIndex) => {
            const items = techStack.filter((item) => item.category === category);

            return (
              <div key={category} className="grid gap-3 sm:grid-cols-[130px_1fr] sm:items-center">
                <div className="flex items-center gap-2 text-xs font-medium text-white/45">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-200/70" />
                  {categoryLabels[category]}
                </div>
                <div className="flex flex-wrap gap-2">
                  {items.map((item, itemIndex) => (
                    <motion.span
                      key={item.name}
                      initial={{ opacity: 0, y: 8 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true, amount: 0.2 }}
                      transition={{ duration: 0.3, delay: categoryIndex * 0.04 + itemIndex * 0.025 }}
                      whileHover={{ y: -2 }}
                      className={`inline-flex items-center gap-2 rounded-full border bg-black/10 px-3 py-2 text-sm transition ${categoryAccent[category]}`}
                    >
                      <span className="font-mono text-[10px] opacity-45">{String(itemIndex + 1).padStart(2, "0")}</span>
                      {item.name}
                    </motion.span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
