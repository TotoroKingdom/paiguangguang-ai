import Image from "next/image";

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
            <a href="#projects">View selected work <span aria-hidden="true">↗</span></a>
            <a href="#about">About me <span aria-hidden="true">↗</span></a>
          </div>
        </div>
        <div className="brand-hero__visual" aria-label="真实项目界面拼贴：Mini-Codex 和 DeepSeek Harness">
          <div className="brand-hero__visual-index">FIG. 01 — SOFTWARE, IN USE</div>
          <figure className="brand-hero__shot brand-hero__shot--main">
            <Image src="/work/mini-codex.png" width={1603} height={978} alt="Mini-Codex 桌面 Agent 工作台真实界面" priority unoptimized />
            <figcaption>01 / MINI-CODEX</figcaption>
          </figure>
          <figure className="brand-hero__shot brand-hero__shot--secondary">
            <Image src="/work/deepseek-harness.png" width={1600} height={866} alt="DeepSeek Harness 模型配置真实界面" priority unoptimized />
            <figcaption>02 / DEEPSEEK HARNESS</figcaption>
          </figure>
          <div className="brand-hero__visual-note">Selected interfaces from public project repositories.</div>
        </div>
      </div>
      <div className="brand-hero__bottom"><span>INDEPENDENT ENGINEERING PRACTICE</span><span>SCROLL TO EXPLORE ↓</span></div>
    </section>
  );
}
