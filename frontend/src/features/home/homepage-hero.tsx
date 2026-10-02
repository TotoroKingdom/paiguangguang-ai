import { NeumorphicButton } from "@/components/ui/neumorphic-button";
import { AICore } from "@/components/three/ai-core";

export function HomepageHero() {
  return (
    <section id="hero" className="brand-hero">
      <div className="brand-hero__layout">
        <div className="brand-hero__copy">
          <p className="brand-hero__identity">AI APPLICATION ENGINEER <span>/</span> RAG · AGENTS · AI SYSTEMS</p>
          <h1>I build AI systems<br />that actually <em>ship.</em></h1>
          <p className="brand-hero__zh">把 AI 从 Demo 做成真正可交付的产品。</p>
          <p className="brand-hero__description">从 Agent 工作台到模型配置与知识系统，我关注产品体验，也负责让背后的工程真正运转。</p>
          <div className="brand-hero__actions">
            <NeumorphicButton href="#projects">View selected work <span aria-hidden="true">↗</span></NeumorphicButton>
            <NeumorphicButton href="#about" variant="soft">About me <span aria-hidden="true">↗</span></NeumorphicButton>
          </div>
        </div>
        <div className="brand-hero__visual">
          <div className="brand-hero__visual-index">FIG. 01 — SPATIAL AI SYSTEM</div>
          <AICore />
          <div className="brand-hero__visual-note">Five primitives, one system core.</div>
        </div>
      </div>
      <div className="brand-hero__bottom"><span>INDEPENDENT ENGINEERING PRACTICE</span><span>SCROLL TO EXPLORE ↓</span></div>
    </section>
  );
}
