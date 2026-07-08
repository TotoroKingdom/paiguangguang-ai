import Link from "next/link";

import { moduleLinks } from "./homepage-data";

export function HomepageModuleLinks() {
  return (
    <section className="space-y-5">
      <div>
        <p className="text-sm font-semibold uppercase tracking-normal text-clay">Existing modules</p>
        <h2 className="mt-2 text-3xl font-semibold text-ink">Explore the AI system surfaces</h2>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {moduleLinks.map((module) => (
          <Link
            key={module.href}
            href={module.href}
            className="border border-ink/10 bg-white/65 p-5 transition hover:border-tide/45 hover:bg-white"
          >
            <div className="flex items-start justify-between gap-4">
              <h3 className="text-xl font-semibold text-ink">{module.title}</h3>
              <span className="border border-tide/20 bg-tide/10 px-2.5 py-1 text-xs font-semibold text-tide">
                {module.status}
              </span>
            </div>
            <p className="mt-3 text-sm leading-7 text-ink/70">{module.description}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
