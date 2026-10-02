import { NeumorphicButton } from "@/components/ui/neumorphic-button";
import { AICore } from "@/components/three/ai-core";
import { githubProfileHref, homepageIdentity } from "./homepage-data";

export function HomepageHero() {
  return (
    <section id="hero" className="brand-hero" aria-labelledby="identity-title">
      <div className="brand-hero__layout">
        <div className="brand-hero__copy">
          <p className="brand-hero__identity">01 / {homepageIdentity.title} <span>·</span> {homepageIdentity.titleZh}</p>
          <h1 id="identity-title">{homepageIdentity.headline.lead}<br /><em>{homepageIdentity.headline.accent}</em></h1>
          <p className="brand-hero__zh">{homepageIdentity.statement}</p>
          <p className="brand-hero__description">{homepageIdentity.description}</p>
          <p className="brand-hero__secondary">{homepageIdentity.secondary} · 从界面到服务，连接体验与工程。</p>
          <div className="brand-hero__actions">
            <NeumorphicButton href="#projects">查看作品 <span aria-hidden="true">↓</span></NeumorphicButton>
            <NeumorphicButton href={githubProfileHref} target="_blank" rel="noopener noreferrer" variant="soft">GitHub <span aria-hidden="true">↗</span><span className="sr-only">（新标签页打开）</span></NeumorphicButton>
          </div>
        </div>
        <div className="brand-hero__visual">
          <div className="brand-hero__visual-index">图 01 · 空间 AI 系统</div>
          <AICore />
          <div className="brand-hero__visual-note">五种能力，一个系统核心。</div>
        </div>
      </div>
      <div className="brand-hero__bottom"><span>独立工程实践 · TotoroKingdom</span><span>向下了解我的工作 ↓</span></div>
    </section>
  );
}
