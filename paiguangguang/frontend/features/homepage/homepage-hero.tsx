import Link from "next/link";

import { heroProofPoints } from "./homepage-data";

export function HomepageHero() {
  return (
    <section className="grid min-h-[calc(100vh-9rem)] gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
      <div className="space-y-6">
        <p className="text-sm font-semibold uppercase tracking-normal text-clay">AI Engineer Portfolio</p>
        <h1 className="max-w-4xl text-4xl font-semibold leading-tight text-ink md:text-6xl">
          Pai Guangguang builds visible AI systems, not black-box demos.
        </h1>
        <p className="max-w-2xl text-lg leading-8 text-ink/70">
          A full-stack portfolio for RAG, agent workflows, backend orchestration, and product-grade AI interfaces.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link
            href="#portfolio-chat"
            className="border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-tide/90"
          >
            Try Portfolio Chat
          </Link>
          <Link
            href="/architecture"
            className="border border-ink/15 bg-white/70 px-4 py-2.5 text-sm font-semibold text-ink transition hover:bg-white"
          >
            View Architecture
          </Link>
        </div>
        <div className="flex flex-wrap gap-2">
          {heroProofPoints.map((point) => (
            <span key={point} className="border border-ink/10 bg-white/65 px-3 py-2 text-sm font-medium text-ink/70">
              {point}
            </span>
          ))}
        </div>
      </div>
      <div className="border border-ink/10 bg-ink p-5 text-paper shadow-sm">
        <p className="text-sm font-semibold uppercase text-brass">System proof</p>
        <div className="mt-5 space-y-3 text-sm leading-6">
          <div className="border border-paper/10 bg-paper/10 p-4">Frontend surfaces explain each workflow step.</div>
          <div className="border border-paper/10 bg-paper/10 p-4">Backend services isolate prompts, retrieval, tools, and providers.</div>
          <div className="border border-paper/10 bg-paper/10 p-4">RAG and agent pages remain available through stable routes.</div>
        </div>
      </div>
    </section>
  );
}
