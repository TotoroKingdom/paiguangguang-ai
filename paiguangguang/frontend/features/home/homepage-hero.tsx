"use client";

import { motion } from "framer-motion";

const stats = [
  { value: "RAG", label: "核心方向" },
  { value: "Agent", label: "工作流" },
  { value: "Full-stack", label: "交付能力" }
];

const pipeline = ["retrieve", "reason", "act"];

export function HomepageHero() {
  return (
    <section id="hero" className="scroll-mt-10 pt-10 sm:pt-16 lg:pt-20">
      <div className="grid items-center gap-14 lg:grid-cols-[1.03fr_0.97fr] lg:gap-16">
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.65, ease: "easeOut" }}
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200/20 bg-emerald-200/[0.06] px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-emerald-100/80">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 shadow-[0_0_12px_rgba(110,231,183,0.9)]" />
            AI application engineer
          </div>

          <h1 className="mt-7 max-w-3xl text-[clamp(3.25rem,8vw,6.9rem)] font-semibold leading-[0.96] tracking-[-0.075em] text-white">
            构建能被
            <span className="block bg-gradient-to-r from-emerald-100 via-sky-200 to-white bg-clip-text text-transparent">信任的 AI 系统。</span>
          </h1>

          <p className="mt-7 max-w-xl text-base leading-8 text-white/55 sm:text-lg">
            我是 TotoroKingdom，专注 RAG Engineering、Agent Workflow 和 Vibe Coding，把模型能力变成可靠、可用、可持续迭代的产品。
          </p>

          <div className="mt-9 flex flex-wrap items-center gap-3">
            <a
              href="#projects"
              className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-5 py-3 text-sm font-semibold text-[#0a0d0f] transition hover:-translate-y-0.5 hover:bg-white"
            >
              查看项目 <span aria-hidden="true">↗</span>
            </a>
            <a
              href="#contact"
              className="inline-flex items-center gap-2 rounded-full border border-white/15 px-5 py-3 text-sm font-medium text-white/75 transition hover:-translate-y-0.5 hover:border-white/35 hover:text-white"
            >
              联系我
            </a>
          </div>

          <div className="mt-12 grid max-w-xl grid-cols-3 border-y border-white/10 py-4">
            {stats.map((stat, index) => (
              <div key={stat.value} className={`pr-3 ${index > 0 ? "border-l border-white/10 pl-4" : ""}`}>
                <p className="font-mono text-sm text-emerald-100/85">{stat.value}</p>
                <p className="mt-1 text-xs text-white/35">{stat.label}</p>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.12, ease: "easeOut" }}
          className="relative min-h-[460px] overflow-hidden rounded-[2rem] border border-white/10 bg-[#101618] p-5 shadow-[0_30px_100px_rgba(0,0,0,0.24)] sm:min-h-[540px] sm:p-7"
        >
          <div className="pointer-events-none absolute inset-0 page-grid opacity-40" />
          <div className="pointer-events-none absolute -right-16 top-8 h-64 w-64 rounded-full bg-sky-300/[0.12] blur-3xl" />
          <div className="pointer-events-none absolute -bottom-20 left-0 h-64 w-64 rounded-full bg-emerald-300/[0.1] blur-3xl" />

          <div className="relative flex items-center justify-between text-[10px] uppercase tracking-[0.2em] text-white/35">
            <span>System / 001</span>
            <span className="inline-flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-emerald-300" /> Live</span>
          </div>

          <div className="absolute inset-0 grid place-items-center">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 28, repeat: Infinity, ease: "linear" }}
              className="absolute h-64 w-64 rounded-full border border-dashed border-emerald-100/25 sm:h-80 sm:w-80"
            />
            <motion.div
              animate={{ rotate: -360 }}
              transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
              className="absolute h-44 w-44 rounded-full border border-sky-200/25 sm:h-56 sm:w-56"
            />
            <div className="relative grid h-32 w-32 place-items-center rounded-full border border-emerald-100/40 bg-emerald-100/[0.08] shadow-[0_0_90px_rgba(110,231,183,0.2)] sm:h-40 sm:w-40">
              <div className="absolute inset-3 rounded-full border border-white/10" />
              <div className="h-14 w-14 rounded-full bg-gradient-to-br from-emerald-100 via-sky-200 to-white shadow-[0_0_48px_rgba(186,230,253,0.7)] sm:h-20 sm:w-20" />
            </div>
          </div>

          <div className="absolute left-5 top-20 rounded-2xl border border-white/10 bg-black/20 p-3 backdrop-blur-md sm:left-7">
            <p className="text-[10px] uppercase tracking-[0.18em] text-white/35">Current focus</p>
            <p className="mt-2 text-sm font-medium text-white/85">RAG + Agent Systems</p>
            <div className="mt-3 flex items-center gap-1.5">
              {pipeline.map((item, index) => (
                <span key={item} className="flex items-center gap-1.5 text-[10px] text-emerald-100/65">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-300/80" />
                  {item}
                  {index < pipeline.length - 1 ? <span className="ml-0.5 text-white/20">/</span> : null}
                </span>
              ))}
            </div>
          </div>

          <motion.div
            animate={{ y: [0, -7, 0] }}
            transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
            className="absolute bottom-6 right-5 w-48 rounded-2xl border border-white/10 bg-[#0a0d0f]/80 p-4 backdrop-blur-md sm:bottom-8 sm:right-7"
          >
            <div className="flex items-center justify-between text-[10px] text-white/35">
              <span>pipeline health</span>
              <span className="text-emerald-200/80">98.4%</span>
            </div>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10">
              <motion.div
                animate={{ width: ["72%", "94%", "82%"] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                className="h-full rounded-full bg-gradient-to-r from-emerald-300 to-sky-200"
              />
            </div>
            <p className="mt-3 font-mono text-[10px] text-white/35">retrieval → context → answer</p>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
