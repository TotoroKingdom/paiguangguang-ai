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
      <section className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-stretch">
        <div className="section-intro">
          <p className="eyebrow">{eyebrow}</p>
          <h1 className="section-title text-4xl md:text-5xl">{title}</h1>
          <p className="section-description max-w-2xl text-base">{description}</p>
        </div>
        <aside className="surface surface--quiet p-5">
          <p className="mb-4 text-sm font-semibold text-primary">{status}</p>
          <div className="space-y-3 text-sm text-muted">{children}</div>
        </aside>
      </section>
    </div>
  );
}
