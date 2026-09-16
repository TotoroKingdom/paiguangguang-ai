"use client";

import { motion } from "framer-motion";

import { BotIcon, CodeIcon, DatabaseIcon, WorkflowIcon } from "@/components/icons";
import { overviewCards } from "./homepage-data";

const capabilityMeta = [
  { index: "01", label: "RETRIEVE", icon: DatabaseIcon },
  { index: "02", label: "ORCHESTRATE", icon: WorkflowIcon },
  { index: "03", label: "SHIP", icon: CodeIcon },
  { index: "04", label: "ITERATE", icon: BotIcon }
];

export function HomepageOverview() {
  return (
    <div className="capability-grid">
      {overviewCards.map((card, index) => {
        const meta = capabilityMeta[index] ?? capabilityMeta[0];
        const Icon = meta.icon;

        return (
          <motion.article
            key={card.title}
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.35, delay: index * 0.04 }}
            className="capability-item group"
          >
            <div className="capability-item__meta">
              <span>{meta.index}</span>
              <span>{meta.label}</span>
            </div>
            <div className="capability-item__icon">
              <Icon size={18} />
            </div>
            <h3 className="capability-item__title">{card.title}</h3>
            <p className="capability-item__description">{card.description}</p>
          </motion.article>
        );
      })}
    </div>
  );
}
