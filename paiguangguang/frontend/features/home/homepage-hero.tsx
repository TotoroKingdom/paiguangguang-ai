"use client";

import { motion } from "framer-motion";

import { ArrowUpRightIcon, ActivityIcon, LayersIcon } from "@/components/icons";

const stats = [
  { value: "RAG", label: "可靠的知识" },
  { value: "AGENT", label: "可执行的流程" },
  { value: "FULL-STACK", label: "完整的交付" }
];

const pipeline = ["RETRIEVE", "REASON", "DELIVER"];

export function HomepageHero() {
  return (
    <section id="hero" className="hero-section scroll-mt-24">
      <div className="hero-section__glow hero-section__glow--one" />
      <div className="hero-section__glow hero-section__glow--two" />

      <div className="hero-layout">
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="hero-copy-column"
        >
          <div className="hero-kicker">
            <span className="hero-kicker__dot" />
            <span>AI APPLICATION ENGINEER</span>
            <span className="hero-kicker__year">/ 2026</span>
          </div>

          <h1 className="hero-title">
            让 <span>AI</span> 获得
            <br />
            <em>可以被使用的形状。</em>
          </h1>

          <p className="hero-copy">
            我是 TotoroKingdom，专注 RAG Engineering、Agent Workflow 和 Vibe Coding，把模型能力做成可靠、可用、可持续迭代的产品。
          </p>

          <div className="hero-actions">
            <a href="#projects" className="home-button home-button--solid">
              查看项目
              <ArrowUpRightIcon size={15} />
            </a>
            <a href="#rag-flow" className="home-button home-button--glass">
              探索系统
            </a>
            <a href="#contact" className="home-button home-button--text">
              联系我 <span aria-hidden="true">→</span>
            </a>
          </div>

          <div className="hero-stats" aria-label="核心方向">
            {stats.map((stat) => (
              <div key={stat.value} className="hero-stat">
                <p className="hero-stat__value">{stat.value}</p>
                <p className="hero-stat__label">{stat.label}</p>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.1, ease: "easeOut" }}
          className="hero-stage"
          aria-label="AI 系统运行状态"
        >
          <div className="hero-stage__grid" />
          <div className="hero-stage__scanline" />
          <div className="hero-stage__halo hero-stage__halo--outer" />
          <div className="hero-stage__halo hero-stage__halo--inner" />
          <div className="hero-stage__orbit hero-stage__orbit--one" />
          <div className="hero-stage__orbit hero-stage__orbit--two" />

          <div className="hero-stage__core">
            <div className="hero-stage__core-light" />
            <LayersIcon size={44} />
          </div>

          <div className="hero-stage__topline">
            <span>RUNTIME / 001</span>
            <span className="hero-stage__online">
              <span className="status-dot" />
              OPERATIONAL
            </span>
          </div>

          <div className="hero-stage__card hero-stage__card--left">
            <span className="hero-stage__card-label">INPUT</span>
            <strong>knowledge</strong>
            <small>structured context</small>
          </div>

          <div className="hero-stage__card hero-stage__card--right">
            <span className="hero-stage__card-label">OUTPUT</span>
            <strong>useful answer</strong>
            <small>traceable delivery</small>
          </div>

          <div className="hero-stage__footer">
            <span className="inline-flex items-center gap-2">
              <ActivityIcon size={13} />
              retrieval → context → action
            </span>
            <span>health 98.4%</span>
          </div>

          <div className="hero-pipeline" aria-label="系统处理流程">
            {pipeline.map((step, index) => (
              <div key={step} className="hero-pipeline__step">
                <span>0{index + 1}</span>
                <strong>{step}</strong>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      <a className="hero-scroll" href="#overview" aria-label="滚动到关于区域">
        <span>SCROLL TO EXPLORE</span>
        <span className="hero-scroll__line" />
      </a>
    </section>
  );
}
