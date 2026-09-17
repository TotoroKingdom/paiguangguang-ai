"use client";

import { motion } from "framer-motion";

import { roadmapStages } from "./homepage-data";

export function HomepageRoadmap() {
  return (
    <section id="roadmap" className="home-section scroll-mt-24">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div className="section-intro">
          <p className="eyebrow">Roadmap / 03</p>
          <h2 className="section-title">下一步，继续把边界推远</h2>
        </div>
        <p className="section-description mt-0 max-w-md sm:text-right">每个阶段都不是头衔，而是一种更稳定地解决问题的方式。</p>
      </div>

      <div className="roadmap-grid">
        {roadmapStages.map((stage, index) => (
          <motion.article
            key={stage.stage}
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.35, delay: index * 0.045 }}
            className="roadmap-step"
          >
            <div className="roadmap-step__top">
              <span className="roadmap-step__index">{stage.stage}</span>
              <span className="roadmap-step__label">Next chapter</span>
            </div>
            <h3 className="roadmap-step__title">{stage.title}</h3>
            <p className="roadmap-step__description">{stage.description}</p>
          </motion.article>
        ))}
      </div>
    </section>
  );
}
