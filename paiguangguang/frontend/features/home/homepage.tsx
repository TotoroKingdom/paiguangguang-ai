import { HomepageContact } from "./homepage-contact";
import { HomepageHero } from "./homepage-hero";
import { HomepageOverview } from "./homepage-overview";
import { HomepageProjects } from "./homepage-projects";
import { HomepageRoadmap } from "./homepage-roadmap";
import { HomepageTechStack } from "./homepage-tech-stack";
import { RagFlowVisual } from "./rag-flow-visual";
import { ragIngestionSteps, ragQuerySteps } from "./homepage-data";

const navigation = [
  { label: "能力", href: "#overview" },
  { label: "链路", href: "#rag-flow" },
  { label: "项目", href: "#projects" },
  { label: "联系", href: "#contact" }
];

function SiteNavigation() {
  return (
    <header className="site-header">
      <div className="site-header__inner">
        <a href="#hero" className="brand" aria-label="回到首页">
          <span className="brand-mark">TG</span>
          <span className="brand-wordmark">AI SYSTEMS</span>
          <span className="brand-caption">/ portfolio</span>
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
          Available for work
        </div>
      </div>
    </header>
  );
}

function SectionHeading() {
  return (
    <div className="section-intro section-intro--center">
      <p className="eyebrow">Retrieval · Reasoning · Delivery</p>
      <h2 className="section-title">让复杂的 AI 链路变得可理解</h2>
      <p className="section-description">
        从知识入库到 Agent 执行，把模型能力收束成稳定、可观测、能真正落地的产品体验。
      </p>
    </div>
  );
}

export function Homepage() {
  return (
    <div className="min-h-screen overflow-hidden text-ink">
      <div className="pointer-events-none fixed inset-0 z-0 page-grid opacity-55" />

      <div className="relative z-10">
        <SiteNavigation />

        <main className="mx-auto flex w-full max-w-[1240px] flex-col gap-28 px-5 pb-16 pt-8 sm:gap-36 sm:px-8 sm:pt-12 lg:gap-40 lg:px-10">
          <HomepageHero />

          <section id="overview" className="scroll-mt-24 space-y-10">
            <SectionHeading />
            <HomepageOverview />
          </section>

          <HomepageTechStack />

          <section id="rag-flow" className="scroll-mt-24 space-y-8">
            <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
              <div className="section-intro">
                <p className="eyebrow">System map / 01</p>
                <h2 className="section-title">一条可追踪的 RAG 链路</h2>
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

        <footer className="mx-auto flex w-full max-w-[1240px] items-center justify-between border-t border-line px-5 py-6 text-xs text-subtle sm:px-8 lg:px-10">
          <span className="font-mono">TG / AI SYSTEMS</span>
          <span>Built with clarity, shipped with intent.</span>
        </footer>
      </div>
    </div>
  );
}
