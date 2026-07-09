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
              className="group relative w-full max-w-[320px] overflow-hidden rounded-[26px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.96),rgba(2,6,23,0.98))] p-5 transition duration-500 hover:-translate-y-1 hover:scale-[1.01] hover:border-cyan-300/65 hover:shadow-[0_32px_90px_rgba(34,211,238,0.24)]"
            >
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.04),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(236,72,153,0.04),transparent_32%),linear-gradient(135deg,rgba(56,189,248,0.05),rgba(217,70,239,0.05))] opacity-0 transition duration-500 group-hover:opacity-100" />
              <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(34,211,238,0.46),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(236,72,153,0.38),transparent_32%),linear-gradient(135deg,rgba(56,189,248,0.24),rgba(217,70,239,0.2))] opacity-0 blur-[1.5px] mix-blend-screen transition duration-500 group-hover:opacity-100" />
              <div className="absolute right-0 top-0 h-24 w-24 rounded-full bg-cyan-400/10 blur-2xl" />
              <div className="relative z-10">
                <p className="text-sm font-semibold uppercase tracking-[0.4em] text-cyan-200/70">{stage.stage}</p>
                <h3 className="mt-4 text-2xl font-semibold text-white">{stage.title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-300">{stage.description}</p>
                <div className="mt-6 h-px w-full bg-gradient-to-r from-cyan-300/60 via-fuchsia-300/50 to-transparent" />
                {/*<div className="mt-4 text-xs uppercase tracking-[0.28em] text-slate-400">Hover-ready milestone</div>*/}
              </div>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
