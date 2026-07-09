"use client";

import { motion } from "framer-motion";

import { roadmapStages } from "./homepage-data";

export function HomepageRoadmap() {
  return (
    <section id="roadmap" className="space-y-6">
      <div className="mx-auto max-w-3xl text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.32em] text-cyan-200/80">Roadmap</p>
        <h2 className="mt-3 text-3xl font-black text-white sm:text-4xl">职业规划</h2>
      </div>
      <div className="relative mx-auto max-w-5xl">
        <div className="pointer-events-none absolute left-[12%] right-[12%] top-1/2 hidden h-px -translate-y-1/2 bg-gradient-to-r from-cyan-300/10 via-cyan-200/60 to-fuchsia-300/10 lg:block" />
        <div className="relative z-10 grid justify-center justify-items-center gap-6 lg:grid-cols-3">
        {roadmapStages.map((stage, index) => (
          <motion.article
            key={stage.stage}
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.45, delay: index * 0.06 }}
            className="relative w-full max-w-[320px] overflow-hidden rounded-[26px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.96),rgba(2,6,23,0.98))] p-5"
          >
            <div className="absolute right-0 top-0 h-24 w-24 rounded-full bg-cyan-400/10 blur-2xl" />
            <p className="text-sm font-semibold uppercase tracking-[0.4em] text-cyan-200/70">{stage.stage}</p>
            <h3 className="mt-4 text-2xl font-semibold text-white">{stage.title}</h3>
            <p className="mt-3 text-sm leading-7 text-slate-300">{stage.description}</p>
            <div className="mt-6 h-px w-full bg-gradient-to-r from-cyan-300/60 via-fuchsia-300/50 to-transparent" />
            {/*<div className="mt-4 text-xs uppercase tracking-[0.28em] text-slate-400">Hover-ready milestone</div>*/}
          </motion.article>
        ))}
        </div>
      </div>
    </section>
  );
}
