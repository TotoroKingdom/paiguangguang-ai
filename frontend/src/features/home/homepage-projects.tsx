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
    <article className={`brand-project-card brand-project-card--${project.accent} ${index === 0 ? "brand-project-card--featured" : ""}`}>
      <div className="brand-project-card__top">
        <span className="brand-mono">{index === 0 ? "FEATURED CASE / 01" : `SELECTED CASE / 0${index + 1}`}</span>
        <span className="brand-project-card__focus">{project.focus}</span>
      </div>

      {index === 0 ? (
        <div className="brand-project-card__preview" aria-label="Knowledge System architecture preview">
          <div className="brand-project-card__preview-top"><span>KNOWLEDGE CONTROL PLANE</span><span>LIVE ARCHITECTURE</span></div>
          <div className="brand-project-card__preview-flow">
            <span>Sources</span><i /><span>Retrieve</span><i /><span>Rerank</span><i /><strong>Answer</strong>
          </div>
          <div className="brand-project-card__preview-footer"><span>permission-aware retrieval</span><span>citation attached</span></div>
        </div>
      ) : null}

      <div className="brand-project-card__body">
        <h3 className="brand-project-card__title">{project.name}</h3>
        <p className="brand-project-card__context">{project.context}</p>

        <dl className="brand-project-fields">
          <ProjectField label="Challenge">{project.problem}</ProjectField>
          <ProjectField label="System">
            <div className="brand-project-architecture">
              {project.architecture.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          </ProjectField>
          <ProjectField label="Role">{project.contribution}</ProjectField>
          <ProjectField label="Result" accent>
            {project.outcome}
          </ProjectField>
        </dl>

        <span className="brand-project-card__action">
          Engineering case study <span aria-hidden="true">↗</span>
        </span>
      </div>
    </article>
  );
}

export function HomepageProjects() {
  return (
    <section id="projects" className="brand-section brand-projects scroll-mt-24">
      <div className="brand-section-heading">
        <p className="brand-eyebrow">Work</p>
        <div>
          <h2 className="brand-section-title">从可用的 AI 能力，到可交付的产品系统。</h2>
          <p className="brand-section-description">
            重点案例先展示完整的系统思考；其余项目则从工程边界、关键决策和交付结果切入。
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
