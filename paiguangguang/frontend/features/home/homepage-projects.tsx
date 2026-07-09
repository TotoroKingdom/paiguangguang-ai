"use client";

import { motion } from "framer-motion";

import { projectCards } from "./homepage-data";

const projectGradients = [
  "from-sky-400/35 via-cyan-300/20 to-blue-500/15",
  "from-emerald-400/35 via-cyan-300/20 to-teal-500/15",
  "from-violet-400/35 via-fuchsia-300/20 to-indigo-500/15",
  "from-amber-300/30 via-rose-300/20 to-fuchsia-500/15"
];

const primaryProjectCards = projectCards.slice(0, 4);
const scenarioProjectCards = projectCards.slice(4);

function ProjectTile({ project, index }: { project: (typeof projectCards)[number]; index: number }) {
  return (
    <motion.article
      key={project.name}
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.25 }}
      transition={{ duration: 0.45, delay: index * 0.05 }}
      className="group relative flex aspect-square w-full max-w-[280px] overflow-hidden rounded-[26px] border border-white/10 bg-white/5 p-6 text-center transition duration-500 hover:-translate-y-2 hover:border-cyan-300/35 hover:bg-white/[0.07]"
    >
      <div className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${projectGradients[index % projectGradients.length]} opacity-0 transition duration-500 group-hover:opacity-100`} />
      <div className="pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full bg-cyan-200/10 blur-3xl opacity-0 transition duration-500 group-hover:opacity-100" />
      <div className="relative z-10 flex h-full flex-col items-center justify-center">
        <h3 className="text-2xl font-semibold text-white">{project.name}</h3>
        <p className="mt-4 text-sm leading-7 text-slate-300">{project.description}</p>
      </div>
    </motion.article>
  );
}

export function HomepageProjects() {
  return (
    <section id="projects" className="space-y-6">
      <div className="mx-auto max-w-3xl text-center">
        <p className="text-sm font-semibold uppercase tracking-[0.32em] text-cyan-200/80">Projects</p>
      </div>

      <div className="space-y-5">
        <div className="mx-auto grid max-w-6xl justify-center justify-items-center gap-5 sm:grid-cols-2 xl:grid-cols-4">
          {primaryProjectCards.map((project, index) => (
            <ProjectTile key={project.name} project={project} index={index} />
          ))}
        </div>

        <div className="mx-auto grid max-w-4xl justify-center justify-items-center gap-5 sm:grid-cols-3">
          {scenarioProjectCards.map((project, index) => (
            <ProjectTile key={project.name} project={project} index={index + primaryProjectCards.length} />
          ))}
        </div>
      </div>
    </section>
  );
}
