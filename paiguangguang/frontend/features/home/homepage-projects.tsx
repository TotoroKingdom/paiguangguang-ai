"use client";

import { motion } from "framer-motion";

import { projectCards } from "./homepage-data";

function ProjectCard({
  project,
  index,
  featured = false
}: {
  project: (typeof projectCards)[number];
  index: number;
  featured?: boolean;
}) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.35, delay: index * 0.035 }}
      className={`project-card ${featured ? "project-card--featured" : ""}`}
    >
      <div className="project-card__top">
        <span>{String(index + 1).padStart(2, "0")}</span>
        <span className="project-card__status">{project.status}</span>
      </div>

      <div className={`project-card__visual project-card__visual--${(index % 6) + 1}`} aria-hidden="true">
        <span className="project-card__visual-orbit" />
        <span className="project-card__visual-core" />
        <span className="project-card__visual-label">CASE / {String(index + 1).padStart(2, "0")}</span>
      </div>

      <div className="project-card__body">
        <div className="project-card__rule" />
        <h3 className="project-card__title">{project.name}</h3>
        <p className="project-card__description">{project.description}</p>
        <div className="project-card__tags">
          {project.tags.map((tag) => (
            <span key={tag} className="tag">
              {tag}
            </span>
          ))}
        </div>
        <span className="project-card__action">
          Explore case <span aria-hidden="true">↗</span>
        </span>
      </div>
    </motion.article>
  );
}

export function HomepageProjects() {
  return (
    <section id="projects" className="home-section scroll-mt-24">
      <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
        <div className="section-intro">
          <p className="eyebrow">Selected work / 02</p>
          <h2 className="section-title">把想法交付成产品</h2>
        </div>
        <p className="section-description mt-0 max-w-md sm:text-right">从对话、知识库到企业自动化，关注每个系统真正被使用的瞬间。</p>
      </div>

      <div className="project-grid project-grid--featured">
        {projectCards.slice(0, 3).map((project, index) => (
          <ProjectCard key={project.name} project={project} index={index} featured />
        ))}
      </div>

      <div className="project-grid project-grid--secondary">
        {projectCards.slice(3).map((project, index) => (
          <ProjectCard key={project.name} project={project} index={index + 3} />
        ))}
      </div>
    </section>
  );
}
