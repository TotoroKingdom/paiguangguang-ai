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
    <header className="mx-auto flex w-full max-w-[1240px] items-center justify-between px-5 py-5 sm:px-8 lg:px-10">
      <a href="#hero" className="group inline-flex items-center gap-3" aria-label="回到首页">
        <span className="grid h-9 w-9 place-items-center rounded-xl border border-emerald-200/20 bg-emerald-200/[0.06] font-mono text-xs font-bold text-emerald-100 transition group-hover:border-emerald-200/50 group-hover:bg-emerald-200/10">
          TG
        </span>
        <span className="hidden text-sm font-medium tracking-[0.18em] text-white/75 sm:block">AI SYSTEMS</span>
      </a>

      <nav className="hidden items-center gap-7 text-sm text-white/50 md:flex" aria-label="主导航">
        {navigation.map((item) => (
          <a key={item.href} href={item.href} className="transition hover:text-white">
            {item.label}
          </a>
        ))}
      </nav>

      <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs text-white/60">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 shadow-[0_0_12px_rgba(110,231,183,0.85)]" />
        Available for work
      </div>
    </header>
  );
}

function SectionHeading() {
  return (
    <div className="mx-auto max-w-3xl text-center">
      <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-200/65">Retrieval · Reasoning · Delivery</p>
      <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-white sm:text-4xl">让复杂的 AI 链路变得可理解</h2>
      <p className="mt-4 text-sm leading-7 text-white/50 sm:text-base">
        从知识入库到 Agent 执行，把模型能力收束成稳定、可观测、能真正落地的产品体验。
      </p>
    </div>
  );
}

export function Homepage() {
  return (
    <div className="min-h-screen overflow-hidden bg-[#0a0d0f] text-[#edf4ee]">
      <div className="pointer-events-none fixed inset-0 z-0 page-grid opacity-70" />
      <div className="pointer-events-none fixed -left-40 top-20 z-0 h-96 w-96 rounded-full bg-emerald-300/[0.06] blur-3xl" />
      <div className="pointer-events-none fixed -right-40 top-[34%] z-0 h-[28rem] w-[28rem] rounded-full bg-sky-300/[0.05] blur-3xl" />

      <div className="relative z-10">
        <SiteNavigation />

        <main className="mx-auto flex w-full max-w-[1240px] flex-col gap-28 px-5 pb-10 sm:gap-36 sm:px-8 lg:gap-44 lg:px-10">
          <HomepageHero />

          <section id="overview" className="scroll-mt-10 space-y-10">
            <SectionHeading />
            <HomepageOverview />
          </section>

          <HomepageTechStack />

          <section id="rag-flow" className="scroll-mt-10 space-y-8">
            <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-200/65">System map / 01</p>
                <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-white sm:text-4xl">一条可追踪的 RAG 链路</h2>
              </div>
              <p className="max-w-md text-sm leading-7 text-white/45 sm:text-right">
                入库、召回、重排、生成和引用，每一步都可以被看见，也可以被验证。
              </p>
            </div>
            <RagFlowVisual ingestionSteps={ragIngestionSteps} querySteps={ragQuerySteps} />
          </section>

          <HomepageProjects />
          <HomepageRoadmap />
          <HomepageContact />
        </main>
      </div>
    </div>
  );
}
