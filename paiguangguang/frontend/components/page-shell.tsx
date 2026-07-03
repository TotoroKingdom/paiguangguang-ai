import type { ReactNode } from "react";

type PageShellProps = {
  eyebrow: string;
  title: string;
  description: string;
  status: string;
  children: ReactNode;
};

export function PageShell({ eyebrow, title, description, status, children }: PageShellProps) {
  return (
    <div className="space-y-8">
      <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-stretch">
        <div className="space-y-4">
          <p className="text-sm font-semibold uppercase tracking-wide text-clay">{eyebrow}</p>
          <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-ink md:text-5xl">{title}</h1>
          <p className="max-w-2xl text-lg leading-8 text-ink/70">{description}</p>
        </div>
        <aside className="border border-ink/10 bg-white/65 p-5 shadow-sm">
          <p className="mb-4 text-sm font-semibold text-tide">{status}</p>
          <div className="space-y-3 text-sm text-ink/75">{children}</div>
        </aside>
      </section>
    </div>
  );
}
