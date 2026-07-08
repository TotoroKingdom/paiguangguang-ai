import Image from "next/image";
import Link from "next/link";

import { portfolioProjects } from "./homepage-data";

export function HomepageProjects() {
  return (
    <section className="space-y-5">
      <div>
        <p className="text-sm font-semibold uppercase tracking-normal text-clay">Portfolio proof</p>
        <h2 className="mt-2 text-3xl font-semibold text-ink">Projects framed as engineering evidence</h2>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        {portfolioProjects.map((project) => (
          <article key={project.name} className="flex min-h-[18rem] flex-col border border-ink/10 bg-white/65 p-5">
            {project.imageSrc ? (
              <div className="relative mb-4 aspect-[16/9] overflow-hidden border border-ink/10 bg-paper">
                <Image src={project.imageSrc} alt={project.name} fill className="object-cover" />
              </div>
            ) : null}
            <div className="flex-1">
              <h3 className="text-xl font-semibold text-ink">{project.name}</h3>
              <p className="mt-3 text-sm leading-7 text-ink/70">{project.description}</p>
              <p className="mt-4 border-l-4 border-brass bg-paper px-4 py-3 text-sm leading-6 text-ink/75">
                {project.proof}
              </p>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              {project.tags.map((tag) => (
                <span key={tag} className="border border-ink/10 bg-paper px-2.5 py-1 text-xs font-semibold text-ink/65">
                  {tag}
                </span>
              ))}
            </div>
            <Link href={project.href} className="mt-5 text-sm font-semibold text-tide hover:text-tide/80">
              Open project
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}
