"use client";

import { motion } from "framer-motion";

import { overviewCards } from "./homepage-data";

const cardMeta = [
  { index: "01", label: "RETRIEVE", color: "text-emerald-200" },
  { index: "02", label: "ORCHESTRATE", color: "text-violet-200" },
  { index: "03", label: "SHIP", color: "text-sky-200" },
  { index: "04", label: "ITERATE", color: "text-amber-100" }
];

export function HomepageOverview() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {overviewCards.map((card, index) => {
        const meta = cardMeta[index] ?? cardMeta[0];

        return (
          <motion.article
            key={card.title}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.45, delay: index * 0.06 }}
            className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.035] p-5 transition duration-500 hover:-translate-y-1 hover:border-emerald-100/30 hover:bg-white/[0.06]"
          >
            <div className="pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full bg-emerald-200/[0.08] blur-3xl opacity-0 transition duration-500 group-hover:opacity-100" />
            <div className="relative">
              <div className="flex items-center justify-between">
                <span className={`font-mono text-xs ${meta.color}`}>{meta.index}</span>
                <span className="text-[10px] uppercase tracking-[0.18em] text-white/30">{meta.label}</span>
              </div>
              <div className="mt-14 h-px w-10 bg-emerald-200/60 transition-all duration-500 group-hover:w-16" />
              <h3 className="mt-4 text-xl font-medium tracking-[-0.02em] text-white">{card.title}</h3>
              <p className="mt-3 min-h-14 text-sm leading-6 text-white/45">{card.description}</p>
            </div>
          </motion.article>
        );
      })}
    </div>
  );
}
