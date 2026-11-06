import { NeumorphicCard } from "@/components/ui/neumorphic-card";
import { MiniRobotPreview } from "@/components/three/mini-robot-preview";
import { activeProjects, completedProjects, explorationProjects, homepageSections } from "./homepage-data";
import type { ActiveProject, CompletedProject } from "./homepage-data";

function ProjectCard({ project }: { project: CompletedProject | ActiveProject }) {
  const image = "image" in project ? project.image : undefined;
  const external = project.href?.startsWith("https://");
  const cardLink = "cardLink" in project && project.cardLink;
  const statusLabel = "statusLabel" in project && project.statusLabel
    ? project.statusLabel
    : project.status === "BUILT" ? "阶段已完成" : "在建";

  return (
    <NeumorphicCard className={`brand-project${image ? " brand-project--featured" : " brand-project--text"}${cardLink ? " brand-project--clickable" : ""}`}>
      {image && (
        <div className="brand-project__image">
          <MiniRobotPreview poster={image.src} alt={image.alt} sizes="(max-width: 760px) 100vw, 55vw" />
        </div>
      )}
      <div className="brand-project__body">
        <div className="brand-project__meta">
          <p className="brand-project__number">{project.category}</p>
          <span className={`brand-status brand-status--${project.status.toLowerCase()}`}>
            {project.status} · {statusLabel}
          </span>
        </div>
        <h3 id={cardLink ? `project-${project.id}-title` : undefined}>{project.name}</h3>
        <p className="brand-project__description">{project.description}</p>
        <ul aria-label={project.status === "BUILT" ? "已完成的工程能力" : "当前投入方向"}>
          {project.items.map((item) => <li key={item}>{item}</li>)}
        </ul>
        {cardLink && project.href && (
          <span id={`project-${project.id}-action`} className="brand-project__link">{project.linkText ?? "查看项目"} <span aria-hidden="true">→</span></span>
        )}
        {project.href && !cardLink && (
          <a className="brand-project__link" href={project.href} target={external ? "_blank" : undefined} rel={external ? "noopener noreferrer" : undefined}>
            {project.linkText ?? "查看项目"} <span aria-hidden="true">{external ? "↗" : "→"}</span>
            {external && <span className="sr-only">（新标签页打开）</span>}
          </a>
        )}
      </div>
      {cardLink && project.href && (
        <a className="brand-project__card-link" href={project.href} aria-labelledby={`project-${project.id}-title project-${project.id}-action`} />
      )}
    </NeumorphicCard>
  );
}

export function HomepageProjects() {
  return (
    <section id="projects" className="brand-projects" aria-labelledby="built-title">
      <div className="brand-projects__heading">
        <div className="brand-projects__heading-copy">
          <h2 id="built-title">{homepageSections.projects.title}</h2>
          <p>{homepageSections.projects.description}</p>
        </div>
        <div className="brand-section-visual" aria-hidden="true">
          <span className="ai-scene-anchor" data-ai-scene-anchor="projects" />
        </div>
      </div>
      <div className="brand-projects__list brand-projects__list--built">
        {completedProjects.map((project) => <ProjectCard key={project.id} project={project} />)}
      </div>
    </section>
  );
}

export function HomepageBuilding() {
  return (
    <section id="building" className="brand-section brand-building" aria-labelledby="building-title">
      <div className="brand-section-heading">
        <div className="brand-section-heading__copy">
          <h2 id="building-title" className="brand-section-title">{homepageSections.building.title}</h2>
          <p className="brand-section-description">{homepageSections.building.description}</p>
        </div>
        <div className="brand-section-visual" aria-hidden="true">
          <span className="ai-scene-anchor" data-ai-scene-anchor="building" />
        </div>
      </div>
      <div className="brand-projects__list brand-projects__list--active">
        {activeProjects.map((project) => <ProjectCard key={project.id} project={project} />)}
      </div>
    </section>
  );
}

export function HomepageExploring() {
  return (
    <section id="exploring" className="brand-section brand-exploring" aria-labelledby="exploring-title">
      <div className="brand-section-heading">
        <div className="brand-section-heading__copy">
          <h2 id="exploring-title" className="brand-section-title">{homepageSections.exploring.title}</h2>
          <p className="brand-section-description">{homepageSections.exploring.description}</p>
        </div>
        <div className="brand-section-visual" aria-hidden="true">
          <span className="ai-scene-anchor" data-ai-scene-anchor="exploring" />
        </div>
      </div>
      <div className="brand-exploration-grid">
        {explorationProjects.map((project) => {
          const external = project.href.startsWith("https://");

          return (
            <NeumorphicCard key={project.id} className="brand-exploration">
              <a className="brand-exploration__link" href={project.href} target={external ? "_blank" : undefined} rel={external ? "noopener noreferrer" : undefined} aria-labelledby={`exploration-${project.id}-title exploration-${project.id}-destination`} aria-describedby={`exploration-${project.id}-source exploration-${project.id}-description`}>
                <div className="brand-exploration__meta">
                  <span className="brand-status brand-status--exploring">{project.status} · 研究中</span>
                  <span className="brand-exploration__arrow" aria-hidden="true">{external ? "↗" : "→"}</span>
                </div>
                <h3 id={`exploration-${project.id}-title`}>{project.name}</h3>
                <p id={`exploration-${project.id}-source`} className="brand-exploration__source">来源 · {project.source}</p>
                <p id={`exploration-${project.id}-description`} className="brand-exploration__description">{project.description}</p>
                <ul aria-label="研究主题">{project.items.map((item) => <li key={item}>{item}</li>)}</ul>
                <span id={`exploration-${project.id}-destination`} className="brand-exploration__destination">
                  {external ? "GitHub · 外部仓库" : "查看交互演示 · 站内页面"}
                  {external && <span className="sr-only">（新标签页打开）</span>}
                </span>
              </a>
            </NeumorphicCard>
          );
        })}
      </div>
    </section>
  );
}
