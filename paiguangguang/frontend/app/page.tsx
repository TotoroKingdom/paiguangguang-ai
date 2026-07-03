import Link from "next/link";

import { PortfolioChatPanel } from "@/features/portfolio-chat/portfolio-chat-panel";

const modules = [
  {
    title: "Knowledge Agent",
    href: "/agents/knowledge",
    description: "RAG workspace placeholder for document upload, retrieval, and citations."
  },
  {
    title: "Browser Agent",
    href: "/agents/browser",
    description: "Research workflow placeholder for planning, mock search, and synthesis."
  },
  {
    title: "Office Agent",
    href: "/agents/office",
    description: "Automation workflow placeholder for reports, summaries, and structured outputs."
  },
  {
    title: "Architecture",
    href: "/architecture",
    description: "System visualization placeholder for the frontend, backend, and AI layers."
  }
];

export default function HomePage() {
  return (
    <div className="space-y-10">
      <section className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
        <div className="space-y-6">
          <p className="text-sm font-semibold uppercase text-clay">AI Engineer Portfolio</p>
          <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-ink md:text-6xl">
            Interactive AI systems, explained through working product surfaces.
          </h1>
          <p className="max-w-2xl text-lg leading-8 text-ink/70">
            A staged portfolio platform for Portfolio Chat, RAG, tool-calling agents, and architecture visualization.
          </p>
          <div className="flex flex-wrap gap-3 text-sm font-medium text-ink/70">
            <span className="border border-ink/10 bg-white/60 px-3 py-2">V1 Chat live</span>
            <span className="border border-ink/10 bg-white/60 px-3 py-2">V2 RAG ready</span>
            <span className="border border-ink/10 bg-white/60 px-3 py-2">V3 agents planned</span>
          </div>
        </div>
        <div className="border border-ink/10 bg-white/65 p-5 shadow-sm">
          <p className="mb-4 text-sm font-semibold text-tide">Portfolio Chat Workflow</p>
          <div className="space-y-3 text-sm text-ink/70">
            <div className="border-l-4 border-brass bg-paper px-4 py-3">User asks about the portfolio</div>
            <div className="border-l-4 border-tide bg-paper px-4 py-3">Backend keeps session memory</div>
            <div className="border-l-4 border-clay bg-paper px-4 py-3">DeepSeek returns a project-aware reply</div>
          </div>
        </div>
      </section>

      <PortfolioChatPanel />

      <section className="grid gap-4 md:grid-cols-3">
        <div className="border border-ink/10 bg-white/60 p-5">
          <p className="text-sm font-semibold uppercase text-clay">V1</p>
          <h2 className="mt-2 text-xl font-semibold text-ink">Portfolio Chat</h2>
          <p className="mt-3 leading-7 text-ink/70">A lightweight assistant surface for your personal and project story.</p>
        </div>
        <div className="border border-ink/10 bg-white/60 p-5">
          <p className="text-sm font-semibold uppercase text-clay">V2</p>
          <h2 className="mt-2 text-xl font-semibold text-ink">Knowledge Agent</h2>
          <p className="mt-3 leading-7 text-ink/70">A future RAG workspace for retrieval, citations, and knowledge exploration.</p>
        </div>
        <div className="border border-ink/10 bg-white/60 p-5">
          <p className="text-sm font-semibold uppercase text-clay">V3</p>
          <h2 className="mt-2 text-xl font-semibold text-ink">Agent Workflows</h2>
          <p className="mt-3 leading-7 text-ink/70">Mock browser and office agents that reveal planning and execution.</p>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        {modules.map((module) => (
          <Link
            key={module.href}
            href={module.href}
            className="border border-ink/10 bg-white/60 p-5 transition hover:border-tide/40 hover:bg-white"
          >
            <h2 className="text-xl font-semibold text-ink">{module.title}</h2>
            <p className="mt-3 leading-7 text-ink/70">{module.description}</p>
          </Link>
        ))}
      </section>
    </div>
  );
}
