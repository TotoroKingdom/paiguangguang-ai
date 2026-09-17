"use client";

import { motion } from "framer-motion";

import { ArrowUpRightIcon } from "@/components/icons";

const systemSteps = [
  { label: "Knowledge", detail: "trusted sources", tone: "purple" },
  { label: "Retrieve", detail: "relevant context", tone: "cyan" },
  { label: "Reason", detail: "grounded decisions", tone: "purple" },
  { label: "Action", detail: "tool-backed work", tone: "cyan" },
  { label: "Citation", detail: "verifiable output", tone: "green" }
] as const;

export function HomepageHero() {
  return (
    <section id="hero" className="brand-hero scroll-mt-24">
      <div className="brand-hero__layout">
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="brand-hero__copy"
        >
          <p className="brand-eyebrow brand-hero__eyebrow">
            <span className="brand-eyebrow__dot" />
            AI AGENT ENGINEER
          </p>

          <h1 className="brand-hero__title">
            构建可检索、可执行、
            <br />
            <span>可验证</span>的 AI Agent 系统。
          </h1>

          <p className="brand-hero__description">RAG · Agent Workflow · Knowledge Infrastructure</p>

          <div className="brand-hero__actions">
            <a href="#projects" className="brand-button brand-button--primary">
              View Projects
              <ArrowUpRightIcon size={15} />
            </a>
            <a href="#systems" className="brand-button brand-button--secondary">
              Explore Systems
            </a>
          </div>

          <div className="brand-hero__signal" aria-label="核心工作方向">
            <span>Knowledge-first</span>
            <span>Workflow-native</span>
            <span>Production-minded</span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.97, y: 14 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.08, ease: "easeOut" }}
          className="brand-system-visual"
          aria-label="Knowledge 到 Citation 的 AI Agent 系统流程"
        >
          <div className="brand-system-visual__grid" aria-hidden="true" />
          <div className="brand-system-visual__header">
            <span className="brand-mono">SYSTEM / KNOWLEDGE PIPELINE</span>
            <span className="brand-system-visual__caption">traceable by design</span>
          </div>

          <div className="brand-system-flow">
            {systemSteps.map((step, index) => (
              <div key={step.label} className="brand-system-flow__item">
                <span className="brand-system-flow__index">0{index + 1}</span>
                <div className={`brand-system-flow__node brand-system-flow__node--${step.tone}`}>
                  <span className="brand-system-flow__node-label">{step.label}</span>
                  <span className="brand-system-flow__node-detail">{step.detail}</span>
                </div>
                {index < systemSteps.length - 1 ? (
                  <div className="brand-system-flow__connector" aria-hidden="true">
                    <span />
                  </div>
                ) : null}
              </div>
            ))}
          </div>

          <div className="brand-system-visual__footer">
            <span>retrieval → reasoning → action</span>
            <span>source-linked output</span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
