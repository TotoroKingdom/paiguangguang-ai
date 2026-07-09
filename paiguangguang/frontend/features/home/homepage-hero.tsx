"use client";

import Link from "next/link";
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
          RAG Control Plane
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
      </motion.div>
      <div className="lg:pl-0">
        <RagFlowVisual ingestionSteps={ragIngestionSteps} querySteps={ragQuerySteps} />
      </div>
    </section>
  );
}
