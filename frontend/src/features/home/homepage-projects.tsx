import Image from "next/image";
import { NeumorphicCard } from "@/components/ui/neumorphic-card";
import { activeProjects, completedProjects, explorationProjects } from "./homepage-data";
import type { ActiveProject, CompletedProject } from "./homepage-data";

function ProjectCard({ project }: { project: CompletedProject | ActiveProject }) {
  const image = "image" in project ? project.image : undefined;
  const external = project.href?.startsWith("https://");

  return (
    <NeumorphicCard className={`brand-project${image ? " brand-project--featured" : " brand-project--text"}`}>
      {image && (
        <div className="brand-project__image">
          <Image src={image.src} width={image.width} height={image.height} alt={image.alt} unoptimized />
        </div>
      )}
      <div className="brand-project__body">
        <div className="brand-project__meta">
          <p className="brand-project__number">{project.category}</p>
          <span className={`brand-status brand-status--${project.status.toLowerCase()}`}>
            {project.status} · {project.status === "BUILT" ? "阶段已完成" : "在建"}
          </span>
        </div>
        <h3>{project.name}</h3>
        <p className="brand-project__description">{project.description}</p>
        <ul aria-label={project.status === "BUILT" ? "已完成的工程能力" : "当前投入方向"}>
          {project.items.map((item) => <li key={item}>{item}</li>)}
        </ul>
        {project.href && (
          <a className="brand-project__link" href={project.href} target={external ? "_blank" : undefined} rel={external ? "noopener noreferrer" : undefined}>
            {project.linkText ?? "查看项目"} <span aria-hidden="true">{external ? "↗" : "→"}</span>
            {external && <span className="sr-only">（新标签页打开）</span>}
          </a>
        )}
      </div>
    </NeumorphicCard>
  );
}

export function HomepageProjects() {
  return (
    <section id="projects" className="brand-projects" aria-labelledby="built-title">
      <div className="brand-projects__heading">
        <p className="brand-eyebrow">03 / 已完成项目</p>
        <h2 id="built-title">从知识，到对话，再到行动</h2>
        <p>这些系统已完成明确的工程阶段，呈现我如何把能力落到完整流程中。</p>
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
        <p className="brand-eyebrow">04 / 在建项目</p>
        <div>
          <h2 id="building-title" className="brand-section-title">我正在构建什么</h2>
          <p className="brand-section-description">当前投入的工程方向，持续推进知识治理、企业任务执行与智能体运行框架。</p>
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
        <p className="brand-eyebrow">05 / 开源研究</p>
        <div>
          <h2 id="exploring-title" className="brand-section-title">哪些系统正在启发我</h2>
          <p className="brand-section-description">我正在研究的外部开源项目与学习资料。它们由各自的组织或作者维护。</p>
        </div>
      </div>
      <div className="brand-exploration-grid">
        {explorationProjects.map((project) => (
          <NeumorphicCard key={project.id} className="brand-exploration">
            <a className="brand-exploration__link" href={project.href} target="_blank" rel="noopener noreferrer" aria-labelledby={`exploration-${project.id}-title exploration-${project.id}-destination`} aria-describedby={`exploration-${project.id}-source exploration-${project.id}-description`}>
              <div className="brand-exploration__meta">
                <span className="brand-status brand-status--exploring">{project.status} · 研究中</span>
                <span className="brand-exploration__arrow" aria-hidden="true">↗</span>
              </div>
              <h3 id={`exploration-${project.id}-title`}>{project.name}</h3>
              <p id={`exploration-${project.id}-source`} className="brand-exploration__source">来源 · {project.source}</p>
              <p id={`exploration-${project.id}-description`} className="brand-exploration__description">{project.description}</p>
              <ul aria-label="研究主题">{project.items.map((item) => <li key={item}>{item}</li>)}</ul>
              <span id={`exploration-${project.id}-destination`} className="brand-exploration__destination">GitHub · 外部仓库<span className="sr-only">（新标签页打开）</span></span>
            </a>
          </NeumorphicCard>
        ))}
      </div>
    </section>
  );
}
