"use client";

import { motion } from "framer-motion";

import { roadmapStages } from "./homepage-data";

export function HomepageRoadmap() {
  return (
    <section id="roadmap" className="scroll-mt-10 space-y-8">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-200/65">Roadmap / 03</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-white sm:text-4xl">下一步，继续把边界推远</h2>
        </div>
        <p className="max-w-md text-sm leading-7 text-white/45 sm:text-right">每个阶段都不是头衔，而是一种更稳定地解决问题的方式。</p>
      </div>

      <div className="relative grid gap-3 lg:grid-cols-3">
        <div className="pointer-events-none absolute left-[16%] right-[16%] top-8 hidden h-px bg-gradient-to-r from-emerald-200/10 via-emerald-200/50 to-sky-200/10 lg:block" />
        {roadmapStages.map((stage, index) => (
          <motion.article
            key={stage.stage}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.45, delay: index * 0.06 }}
            className="group relative rounded-2xl border border-white/10 bg-white/[0.035] p-5 transition duration-500 hover:-translate-y-1 hover:border-emerald-100/30 hover:bg-white/[0.06] sm:p-6"
          >
            <div className="relative z-10 flex items-center justify-between">
              <span className="grid h-6 w-6 place-items-center rounded-full border border-emerald-200/30 bg-[#0a0d0f] font-mono text-[10px] text-emerald-100">{stage.stage}</span>
              <span className="text-[10px] uppercase tracking-[0.18em] text-white/25">next chapter</span>
            </div>
            <div className="mt-16 h-px w-10 bg-gradient-to-r from-emerald-200/70 to-sky-200/20 transition-all duration-500 group-hover:w-16" />
            <h3 className="mt-4 text-xl font-medium tracking-[-0.02em] text-white">{stage.title}</h3>
            <p className="mt-3 text-sm leading-6 text-white/45">{stage.description}</p>
          </motion.article>
        ))}
      </div>
    </section>
  );
}
