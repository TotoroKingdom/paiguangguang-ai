import Image from "next/image";

const selectedWork = [
  {
    number: "01", name: "Mini-Codex", type: "AGENT WORKSPACE / DESKTOP APP",
    description: "一个面向真实编码任务的 Agent 工作台：会话、项目与执行过程在同一界面中被组织起来。",
    image: "/work/mini-codex.png", imageAlt: "Mini-Codex 桌面应用的真实工作界面", imageWidth: 1603, imageHeight: 978,
    tags: ["Agent workflow", "Desktop UI", "Tool use"],
    href: "https://github.com/TotoroKingdom/Mini-Codex", linkText: "View project"
  },
  {
    number: "02", name: "DeepSeek Harness", type: "AGENT PLATFORM / WEB INTERFACE",
    description: "围绕模型接入与 Agent 使用体验构建的 Harness。画面来自项目仓库中的模型配置页面。",
    image: "/work/deepseek-harness.png", imageAlt: "DeepSeek Harness 模型配置界面的真实截图", imageWidth: 1600, imageHeight: 866,
    tags: ["Model providers", "Agent platform", "Web UI"],
    href: "https://github.com/TotoroKingdom/deepseek-harness", linkText: "View project"
  },
  {
    number: "03", name: "RAG Control Plane", type: "KNOWLEDGE SYSTEM / SYSTEM EXPLAINER",
    description: "把文档入库、混合召回、重排和引用的链路展开为可浏览的系统说明页。",
    image: "/work/rag-control-plane.png", imageAlt: "本站 RAG Control Plane 页面真实截图", imageWidth: 1440, imageHeight: 900,
    tags: ["RAG", "Retrieval", "Citation"],
    href: "/rag", linkText: "Explore system"
  }
] as const;

export function HomepageProjects() {
  return (
    <section id="projects" className="brand-projects">
      <div className="brand-projects__heading">
        <p className="brand-eyebrow">SELECTED WORK <span> / 01—03</span></p>
        <h2>Selected systems <em>I&apos;ve built.</em></h2>
        <p>真实界面与可访问的项目，呈现产品如何被设计、实现和交付。</p>
      </div>
      <div className="brand-projects__list">
        {selectedWork.map((project) => (
          <article className="brand-project" key={project.number}>
            <a className="brand-project__image" href={project.href} target={project.href.startsWith("http") ? "_blank" : undefined} rel={project.href.startsWith("http") ? "noreferrer" : undefined} aria-label={project.name + " — " + project.linkText}>
              <Image src={project.image} width={project.imageWidth} height={project.imageHeight} alt={project.imageAlt} unoptimized />
            </a>
            <div className="brand-project__body">
              <p className="brand-project__number">{project.number} / {project.type}</p>
              <h3>{project.name}</h3>
              <p className="brand-project__description">{project.description}</p>
              <ul aria-label="项目方向">{project.tags.map((tag) => <li key={tag}>{tag}</li>)}</ul>
              <a className="brand-project__link" href={project.href} target={project.href.startsWith("http") ? "_blank" : undefined} rel={project.href.startsWith("http") ? "noreferrer" : undefined}>{project.linkText} <span aria-hidden="true">↗</span></a>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
