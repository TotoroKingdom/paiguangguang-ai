import { HomepageContact } from "./homepage-contact";
import { HomepageHero } from "./homepage-hero";
import { HomepageOverview } from "./homepage-overview";
import { HomepageProjects } from "./homepage-projects";
import { HomepageRoadmap } from "./homepage-roadmap";
import { HomepageTechStack } from "./homepage-tech-stack";
import { RagFlowVisual } from "./rag-flow-visual";
import { ragIngestionSteps, ragQuerySteps } from "./homepage-data";

const navigation = [
  { label: "关于", href: "#overview" },
  { label: "系统", href: "#rag-flow" },
  { label: "项目", href: "#projects" },
  { label: "路线", href: "#roadmap" },
  { label: "联系", href: "#contact" }
];

function SiteNavigation() {
  return (
    <header className="site-header">
      <div className="site-header__inner">
        <a href="#hero" className="brand" aria-label="回到首页">
          <span className="brand-mark">TG</span>
          <span className="brand-copy">
            <span className="brand-wordmark">TOTOROKINGDOM</span>
            <span className="brand-caption">/ AI systems</span>
          </span>
        </a>

        <nav className="site-nav" aria-label="主导航">
          {navigation.map((item) => (
            <a key={item.href} href={item.href}>
              {item.label}
            </a>
          ))}
        </nav>

        <div className="status-inline">
          <span className="status-dot" />
          Open to meaningful work
        </div>
      </div>
    </header>
  );
}

function SectionHeading() {
  return (
    <div className="section-intro section-intro--center">
      <p className="eyebrow">Retrieval · Reasoning · Delivery</p>
      <h2 className="section-title">把复杂的 AI，做成简单的体验</h2>
      <p className="section-description">
        从知识入库到 Agent 执行，把模型能力收束成稳定、可观测、能真正落地的产品体验。
      </p>
    </div>
  );
}

export function Homepage() {
  return (
    <div className="home-page">
      <div className="pointer-events-none fixed inset-0 z-0 page-grid opacity-55" />

      <div className="relative z-10">
        <SiteNavigation />

        <main className="home-main">
          <HomepageHero />

          <section id="overview" className="home-section home-section--overview scroll-mt-24">
            <SectionHeading />
            <HomepageOverview />
          </section>

          <HomepageTechStack />

          <section id="rag-flow" className="home-section scroll-mt-24">
            <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
              <div className="section-intro">
                <p className="eyebrow">System map / 01</p>
                <h2 className="section-title">让每一次回答，都有迹可循</h2>
              </div>
              <p className="section-description mt-0 max-w-md sm:text-right">
                入库、召回、重排、生成和引用，每一步都可以被看见，也可以被验证。
              </p>
            </div>
            <RagFlowVisual ingestionSteps={ragIngestionSteps} querySteps={ragQuerySteps} />
          </section>

          <HomepageProjects />
          <HomepageRoadmap />
          <HomepageContact />
        </main>

        <footer className="home-footer">
          <span className="font-mono">TG / AI SYSTEMS</span>
          <span>Built with clarity, shipped with intent.</span>
        </footer>
      </div>
    </div>
  );
}
