"use client";

import Link from "next/link";
import { motion } from "framer-motion";

import { projectCards } from "./homepage-data";

export function HomepageProjects() {
  return (
    <section id="projects" className="space-y-6">
      <div className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-[0.32em] text-cyan-200/80">Projects</p>
        <h2 className="mt-3 text-3xl font-black text-white sm:text-4xl">四个模块卡片，直接连接到现有路由</h2>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {projectCards.map((project, index) => (
          <motion.article
            key={project.name}
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.45, delay: index * 0.05 }}
            className="group flex min-h-[18rem] flex-col rounded-[26px] border border-white/10 bg-white/5 p-5 transition hover:border-cyan-300/25 hover:bg-white/[0.07]"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-2xl font-semibold text-white">{project.name}</h3>
                <p className="mt-2 text-sm leading-7 text-slate-300">{project.description}</p>
              </div>
              <span className="shrink-0 rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-xs font-semibold text-cyan-100">
                {project.status}
              </span>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              {project.tags.map((tag) => (
                <span key={tag} className="rounded-full border border-white/10 bg-slate-950/70 px-3 py-1 text-xs font-medium text-slate-200">
                  {tag}
                </span>
              ))}
            </div>
            <div className="mt-auto pt-6">
              <Link
                href={project.href}
                className="inline-flex items-center gap-2 text-sm font-semibold text-cyan-100 transition group-hover:translate-x-1"
              >
                Open module
                <span aria-hidden="true">→</span>
              </Link>
            </div>
          </motion.article>
        ))}
      </div>
    </section>
  );
}
