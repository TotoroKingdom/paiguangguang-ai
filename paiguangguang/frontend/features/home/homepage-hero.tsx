"use client";

import { motion } from "framer-motion";

import { ActivityIcon, ArrowUpRightIcon, LayersIcon } from "@/components/icons";

const stats = [
  { value: "RAG", label: "核心方向" },
  { value: "Agent", label: "工作流" },
  { value: "Full-stack", label: "交付能力" }
];

const pipeline = [
  { value: "01", name: "Retrieve" },
  { value: "02", name: "Reason" },
  { value: "03", name: "Deliver" }
];

export function HomepageHero() {
  return (
    <section id="hero" className="scroll-mt-24 pt-6 sm:pt-10 lg:pt-14">
      <div className="grid items-center gap-14 lg:grid-cols-[1.04fr_0.96fr] lg:gap-20">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        >
          <p className="eyebrow">AI application engineer / 2026</p>

          <h1 className="hero-title">
            把模型能力，变成
            <span className="block hero-title__accent">可信的系统。</span>
          </h1>

          <p className="hero-copy">
            我是 TotoroKingdom，专注 RAG Engineering、Agent Workflow 和 Vibe Coding，把模型能力变成可靠、可用、可持续迭代的产品。
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <a href="#projects" className="btn btn-primary">
              查看项目
              <ArrowUpRightIcon size={16} />
            </a>
            <a href="#contact" className="btn btn-secondary">
              联系我
            </a>
          </div>

          <div className="hero-stats">
            {stats.map((stat) => (
              <div key={stat.value} className="hero-stat">
                <p className="hero-stat__value">{stat.value}</p>
                <p className="hero-stat__label">{stat.label}</p>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.aside
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.08, ease: "easeOut" }}
          className="hero-panel surface--dark"
          aria-label="AI 系统能力概览"
        >
          <div className="hero-panel__top">
            <span>System / 001</span>
            <span className="hero-panel__state">
              <span className="status-dot" />
              Operational
            </span>
          </div>

          <div className="hero-panel__content">
            <div className="hero-system-mark">
              <LayersIcon size={34} />
            </div>
            <h2 className="hero-panel__headline">AI system runtime</h2>
            <p className="hero-panel__copy">
              从知识、模型到动作，把复杂链路整理成可理解、可观测的产品体验。
            </p>

            <div className="pipeline" aria-label="系统处理流程">
              {pipeline.map((step) => (
                <div key={step.value} className="pipeline__step">
                  <p className="pipeline__index">{step.value}</p>
                  <p className="pipeline__name">{step.name}</p>
                </div>
              ))}
            </div>

            <div className="hero-panel__footer">
              <span className="inline-flex items-center gap-2">
                <ActivityIcon size={14} />
                retrieval → context → answer
              </span>
              <span className="hero-panel__metric">98.4% health</span>
            </div>
          </div>
        </motion.aside>
      </div>
    </section>
  );
}
