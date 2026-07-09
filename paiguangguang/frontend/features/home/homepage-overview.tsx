"use client";

import { motion } from "framer-motion";

import { overviewCards } from "./homepage-data";

const glyphStyles: Record<(typeof overviewCards)[number]["accent"], string> = {
  green: "from-emerald-400 to-lime-300",
  purple: "from-fuchsia-400 to-violet-300",
  blue: "from-sky-400 to-cyan-300",
  pink: "from-rose-400 to-pink-300"
};

export function HomepageOverview() {
  return (
    <section id="overview" className="space-y-6">
      <div className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-[0.32em] text-cyan-200/80">Core Competencies</p>
        <h2 className="mt-3 text-3xl font-black text-white sm:text-4xl">我的核心能力</h2>
      </div>
      <div className="grid gap-4 lg:grid-cols-4 md:grid-cols-2">
        {overviewCards.map((card, index) => (
          <motion.article
            key={card.title}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.45, delay: index * 0.05 }}
            className="group relative overflow-hidden rounded-[24px] border border-white/10 bg-white/5 p-[1px] transition hover:-translate-y-1 hover:border-white/20"
          >
            <div className="relative h-full rounded-[23px] bg-slate-950/80 p-5">
              <div className={`h-12 w-12 rounded-2xl bg-gradient-to-br ${glyphStyles[card.accent]} opacity-90 shadow-[0_0_35px_rgba(56,189,248,0.15)]`} />
              <h3 className="mt-5 text-xl font-semibold text-white transition group-hover:text-cyan-100">
                {card.title}
              </h3>
              <p className="mt-3 text-sm leading-7 text-slate-300">{card.description}</p>
              <div className="mt-6 h-px w-full bg-gradient-to-r from-white/10 via-white/30 to-white/10" />
              <div className="mt-4 flex items-center gap-2 text-xs uppercase tracking-[0.24em] text-slate-400">
                <span className="h-1.5 w-1.5 rounded-full bg-current" />
                Hover reveals glow
              </div>
            </div>
          </motion.article>
        ))}
      </div>
    </section>
  );
}
