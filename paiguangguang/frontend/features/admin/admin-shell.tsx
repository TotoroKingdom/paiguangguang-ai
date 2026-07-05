"use client";

import Link from "next/link";

import { AuthGate } from "@/components/auth-gate";

export function AdminShell() {
  return (
    <AuthGate
      title="Admin Workspace"
      description="The knowledge base admin surface is reserved for authenticated staff users."
    >
      <section className="grid gap-4 md:grid-cols-2">
        <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-wide text-clay">Admin shell</p>
          <h2 className="mt-2 text-2xl font-semibold text-ink">Ready for management tools</h2>
          <p className="mt-3 leading-7 text-ink/70">
            Task 27 only adds the auth shell. The CRUD interfaces arrive in the next admin tasks.
          </p>
        </div>
        <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-wide text-clay">Entry points</p>
          <div className="mt-3 flex flex-wrap gap-3">
            <Link
              href="/agents/knowledge"
              className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-tide/35 hover:bg-paper"
            >
              Knowledge Agent
            </Link>
            <Link
              href="/"
              className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-tide/35 hover:bg-paper"
            >
              Home
            </Link>
          </div>
        </div>
      </section>
    </AuthGate>
  );
}
