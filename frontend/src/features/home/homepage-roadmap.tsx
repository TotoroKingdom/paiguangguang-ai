import { careerStages } from "./homepage-data";

export function HomepageRoadmap() {
  return (
    <section id="journey" className="brand-section brand-journey" aria-labelledby="journey-title">
      <div className="brand-section-heading">
        <p className="brand-eyebrow">06 / 成长方向</p>
        <div>
          <h2 id="journey-title" className="brand-section-title">从构建系统，到设计架构</h2>
          <p className="brand-section-description">以工程能力的演进为主线，从可靠应用走向可治理、可评估的智能体系统。</p>
        </div>
      </div>
      <ol className="brand-approach-track brand-journey-track" aria-label="工程能力成长路径">
        {careerStages.map((stage, index) => (
          <li key={stage.id} className={`brand-approach-item brand-journey-item brand-journey-item--${stage.state}`} aria-current={stage.state === "current" ? "step" : undefined}>
            <div className="brand-approach-item__top">
              <span className="brand-mono">0{index + 1} / {stage.state === "current" ? "当前阶段" : stage.state === "future" ? "成长目标" : "能力基础"}</span>
              {index < careerStages.length - 1 && <span className="brand-approach-item__arrow" aria-hidden="true">→</span>}
            </div>
            <h3>{stage.title}</h3>
            <p className="brand-journey-item__label">{stage.label}</p>
            <p>{stage.description}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
