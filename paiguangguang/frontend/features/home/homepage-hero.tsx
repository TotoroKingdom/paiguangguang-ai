"use client";

import { motion } from "framer-motion";

import { ragIngestionSteps, ragQuerySteps } from "./homepage-data";
import { RagFlowVisual } from "./rag-flow-visual";

export function HomepageHero() {
  return (
    <section id="hero" className="grid gap-8 lg:grid-cols-[0.42fr_1fr] lg:items-start">
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="space-y-7 pt-2 lg:sticky lg:top-6"
      >
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-300/20 bg-cyan-300/8 px-4 py-2 text-sm font-medium text-cyan-100">
          <span className="h-2 w-2 rounded-full bg-cyan-300" />
          Overview
        </div>
        <motion.article
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut", delay: 0.08 }}
          className="rounded-[28px] border border-white/10 bg-white/5 p-5 backdrop-blur-sm"
        >
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-cyan-200/80">Self Introduction</p>
          <h2 className="mt-3 text-2xl font-black text-white">RAG / Agent / AI 应用工程</h2>
          <p className="mt-4 text-sm leading-7 text-slate-300">
            我专注于把知识库、检索链路、工具编排和交付流程做成可见、可调试、可落地的产品界面。
          </p>
          <p className="mt-3 text-sm leading-7 text-slate-300">
            这张卡片保留个人简介，但只放在首页左侧，不再用路由按钮占据首屏。
          </p>
        </motion.article>
      </motion.div>
      <div className="lg:pl-0">
        <RagFlowVisual ingestionSteps={ragIngestionSteps} querySteps={ragQuerySteps} />
      </div>
    </section>
  );
}
