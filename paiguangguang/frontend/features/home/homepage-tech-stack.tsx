"use client";

import { motion } from "framer-motion";

import type { TechStackItem } from "./homepage-data";
import { techStack } from "./homepage-data";

const categoryOrder: TechStackItem["category"][] = ["ai", "backend", "frontend", "storage", "workflow", "delivery"];

const categoryLabels: Record<TechStackItem["category"], string> = {
  frontend: "Frontend",
  backend: "Backend",
  ai: "AI / RAG",
  storage: "Storage",
  workflow: "Workflow",
  delivery: "Delivery",
  response: "Response"
};

export function HomepageTechStack() {
  return (
    <section id="tech-stack" className="home-section scroll-mt-24">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div className="section-intro">
          <p className="eyebrow">Stack / 2026</p>
          <h2 className="section-title">工具是手，系统才是作品</h2>
        </div>
        <p className="section-description mt-0 max-w-md sm:text-right">用熟悉的工程基础，连接模型、数据和真实业务。</p>
      </div>

      <div className="surface stack-surface">
        <div className="stack-summary">
          <div>
            <span className="stack-summary__count">13 core tools</span>
            <span className="stack-summary__copy"> / a focused stack for shipping AI applications</span>
          </div>
          <span className="stack-summary__signal">SYSTEM READY</span>
        </div>

        <div className="stack-list">
          {categoryOrder.map((category, categoryIndex) => {
            const items = techStack.filter((item) => item.category === category);

            return (
              <div key={category} className="stack-row">
                <span className="stack-row__label">{categoryLabels[category]}</span>
                <div className="stack-items">
                  {items.map((item, itemIndex) => (
                    <motion.span
                      key={item.name}
                      initial={{ opacity: 0, y: 5 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true, amount: 0.2 }}
                      transition={{ duration: 0.25, delay: categoryIndex * 0.025 + itemIndex * 0.018 }}
                      className="tech-pill"
                    >
                      {item.name}
                    </motion.span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
