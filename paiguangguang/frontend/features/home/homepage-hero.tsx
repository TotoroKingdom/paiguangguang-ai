"use client";

import Link from "next/link";
import { motion } from "framer-motion";

import { overviewCards, ragIngestionSteps, ragQuerySteps } from "./homepage-data";
import { RagFlowVisual } from "./rag-flow-visual";

export function HomepageHero() {
  return (
    <section id="hero" className="grid gap-8 lg:grid-cols-[1.02fr_0.98fr] lg:items-center">
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="space-y-7"
      >
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-300/20 bg-cyan-300/8 px-4 py-2 text-sm font-medium text-cyan-100">
          <span className="h-2 w-2 rounded-full bg-cyan-300" />
          RAG Control Plane
        </div>
        <div className="space-y-5">
          <h1 className="max-w-4xl text-4xl font-black leading-tight text-white sm:text-5xl lg:text-7xl">
            面向 RAG、Agent 和 AI 应用工程的暗色首页
          </h1>
          <p className="max-w-2xl text-lg leading-8 text-slate-300">
            这个首页不再围绕个人介绍，而是直接展示企业知识库、检索问答、工具编排、技术栈和交付路径。
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/agents/knowledge"
            className="rounded-full bg-gradient-to-r from-cyan-400 to-sky-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110"
          >
            打开 Knowledge Agent
          </Link>
          <Link
            href="#projects"
            className="rounded-full border border-white/15 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:border-cyan-300/40 hover:bg-white/10"
          >
            浏览 Projects
          </Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {overviewCards.map((card, index) => {
            const toneMap: Record<typeof card.accent, string> = {
              green: "from-emerald-400/20 via-emerald-300/10 to-transparent",
              purple: "from-fuchsia-400/20 via-fuchsia-300/10 to-transparent",
              blue: "from-sky-400/20 via-sky-300/10 to-transparent",
              pink: "from-rose-400/20 via-rose-300/10 to-transparent"
            };

            return (
              <motion.article
                key={card.title}
                initial={{ opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.35 }}
                transition={{ duration: 0.45, delay: index * 0.05 }}
                className={`rounded-[22px] border border-white/10 bg-gradient-to-br ${toneMap[card.accent]} p-[1px]`}
              >
                <div className="h-full rounded-[21px] border border-white/10 bg-slate-950/70 p-4">
                  <h3 className="text-lg font-semibold text-white">{card.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-300">{card.description}</p>
                </div>
              </motion.article>
            );
          })}
        </div>
      </motion.div>
      <div className="lg:pl-4">
        <RagFlowVisual ingestionSteps={ragIngestionSteps} querySteps={ragQuerySteps} />
      </div>
    </section>
  );
}
