import type { ReactNode } from "react";

import { projectCards } from "./homepage-data";

function ProjectField({ label, children, accent = false }: { label: string; children: ReactNode; accent?: boolean }) {
  return (
    <div className={`brand-project-field ${accent ? "brand-project-field--accent" : ""}`}>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function ProjectCard({ project, index }: { project: (typeof projectCards)[number]; index: number }) {
  return (
    <article className={`brand-project-card brand-project-card--${project.accent}`}>
      <div className="brand-project-card__top">
        <span className="brand-mono">0{index + 1}</span>
        <span className="brand-project-card__focus">{project.focus}</span>
      </div>

      <h3 className="brand-project-card__title">{project.name}</h3>
      <p className="brand-project-card__context">{project.context}</p>

      <dl className="brand-project-fields">
        <ProjectField label="Problem">{project.problem}</ProjectField>
        <ProjectField label="Architecture">
          <div className="brand-project-architecture">
            {project.architecture.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
        </ProjectField>
        <ProjectField label="Contribution">{project.contribution}</ProjectField>
        <ProjectField label="Outcome" accent>
          {project.outcome}
        </ProjectField>
      </dl>

      <span className="brand-project-card__action">
        查看详情 <span aria-hidden="true">↗</span>
      </span>
    </article>
  );
}

export function HomepageProjects() {
  return (
    <section id="projects" className="brand-section brand-projects scroll-mt-24">
      <div className="brand-section-heading">
        <p className="brand-eyebrow">Work</p>
        <div>
          <h2 className="brand-section-title">Projects framed as engineering evidence.</h2>
          <p className="brand-section-description">
            三个核心项目，记录我如何从问题出发，设计系统边界，并把模型能力交付到真实工作流里。
          </p>
        </div>
      </div>

      <div className="brand-project-grid">
        {projectCards.map((project, index) => (
          <ProjectCard key={project.name} project={project} index={index} />
        ))}
      </div>
    </section>
  );
}
