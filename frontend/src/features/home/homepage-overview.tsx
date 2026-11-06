import { capabilities } from "./homepage-data";

export function HomepageOverview() {
  return (
    <div className="brand-capabilities-grid">
      {capabilities.map((capability, index) => (
        <article key={capability.name} className="brand-capability">
          <div className="brand-capability__top">
            <span className="brand-mono">0{index + 1}</span>
            <span className="brand-capability__line" aria-hidden="true" />
          </div>
          <h3 className="brand-capability__title">{capability.name}</h3>
          <p className="brand-capability__description">{capability.description}</p>
          <ul className="brand-capability__list">
            {capability.items.map((item) => (
              <li key={typeof item === "string" ? item : item.name}>
                <span className="brand-capability__bullet" aria-hidden="true" />
                {typeof item === "string" ? item : (
                  <>
                    {item.name}
                    <ul className="brand-capability__children" aria-label={`${item.name} 工作模式`}>
                      {item.children.map((child) => <li key={child}>{child}</li>)}
                    </ul>
                  </>
                )}
              </li>
            ))}
          </ul>
        </article>
      ))}
    </div>
  );
}
