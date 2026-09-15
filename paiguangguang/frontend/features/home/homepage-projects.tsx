"use client";

import { motion } from "framer-motion";

import { projectCards } from "./homepage-data";

const accentColors = ["bg-sky-200", "bg-emerald-200", "bg-violet-200", "bg-amber-100", "bg-rose-200", "bg-cyan-200", "bg-fuchsia-200"];

function ProjectCard({ project, index, featured = false }: { project: (typeof projectCards)[number]; index: number; featured?: boolean }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.45, delay: index * 0.05 }}
      className={`group relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.035] p-5 transition duration-500 hover:-translate-y-1 hover:border-emerald-100/30 hover:bg-white/[0.06] ${featured ? "min-h-[270px] sm:p-7" : "min-h-[220px]"}`}
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-emerald-200/70 to-transparent opacity-50 transition duration-500 group-hover:opacity-100" />
      <div className="relative flex h-full flex-col">
        <div className="flex items-center justify-between gap-3">
          <span className="font-mono text-xs text-white/30">{String(index + 1).padStart(2, "0")}</span>
          <span className="rounded-full border border-white/10 px-2.5 py-1 text-[10px] uppercase tracking-[0.14em] text-white/40">{project.status}</span>
        </div>
        <div className="mt-auto">
          <span className={`mb-4 block h-1.5 w-8 rounded-full ${accentColors[index % accentColors.length]} opacity-70 transition-all duration-500 group-hover:w-14`} />
          <h3 className={`${featured ? "text-2xl" : "text-xl"} font-medium tracking-[-0.025em] text-white`}>{project.name}</h3>
          <p className="mt-3 max-w-md text-sm leading-6 text-white/45">{project.description}</p>
          <div className="mt-5 flex flex-wrap gap-1.5">
            {project.tags.map((tag) => (
              <span key={tag} className="rounded-full bg-white/[0.06] px-2.5 py-1 text-[10px] text-white/45">{tag}</span>
            ))}
          </div>
        </div>
      </div>
    </motion.article>
  );
}

export function HomepageProjects() {
  return (
    <section id="projects" className="scroll-mt-10 space-y-8">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-200/65">Selected work / 02</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-white sm:text-4xl">把想法交付成产品</h2>
        </div>
        <p className="max-w-md text-sm leading-7 text-white/45 sm:text-right">从对话、知识库到企业自动化，关注每个系统真正被使用的瞬间。</p>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        {projectCards.slice(0, 3).map((project, index) => (
          <ProjectCard key={project.name} project={project} index={index} featured />
        ))}
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {projectCards.slice(3).map((project, index) => (
          <ProjectCard key={project.name} project={project} index={index + 3} />
        ))}
      </div>
    </section>
  );
}
