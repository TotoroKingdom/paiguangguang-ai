import Link from "next/link";

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
      <section className="grid gap-8 md:grid-cols-[1.15fr_0.85fr] md:items-center">
        <div className="space-y-6">
          <p className="text-sm font-semibold uppercase text-clay">AI Engineer Portfolio</p>
          <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-ink md:text-6xl">
            Interactive AI systems, explained through working product surfaces.
          </h1>
          <p className="max-w-2xl text-lg leading-8 text-ink/70">
            A staged portfolio platform for Portfolio Chat, RAG, tool-calling agents, and architecture visualization.
          </p>
        </div>
        <div className="border border-ink/10 bg-white/65 p-5 shadow-sm">
          <p className="mb-4 text-sm font-semibold text-tide">V1 Frontend Skeleton</p>
          <div className="space-y-3 text-sm text-ink/70">
            <div className="border-l-4 border-brass bg-paper px-4 py-3">User Input</div>
            <div className="border-l-4 border-tide bg-paper px-4 py-3">Portfolio Chat</div>
            <div className="border-l-4 border-clay bg-paper px-4 py-3">Visible AI Workflow</div>
          </div>
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
