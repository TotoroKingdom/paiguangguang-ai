import { approachStages } from "./homepage-data";

export function HomepageRoadmap() {
  return (
    <section id="approach" className="brand-section brand-approach scroll-mt-24">
      <div className="brand-section-heading">
        <p className="brand-eyebrow">HOW I BUILD / 04</p>
        <div>
          <h2 className="brand-section-title">From question to shipped system.</h2>
          <p className="brand-section-description">Understand → Design → Build → Evaluate → Ship</p>
        </div>
      </div>

      <div className="brand-approach-track">
        {approachStages.map((stage, index) => (
          <div key={stage.stage} className="brand-approach-item">
            <div className="brand-approach-item__top">
              <span className="brand-mono">{stage.stage}</span>
              {index < approachStages.length - 1 ? <span className="brand-approach-item__arrow" aria-hidden="true">→</span> : null}
            </div>
            <h3>{stage.title}</h3>
            <p>{stage.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
