"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth-provider";

type AuthGateProps = {
  children: ReactNode;
  title: string;
  description: string;
};

export function AuthGate({ children, title, description }: AuthGateProps) {
  const { status, user, logout } = useAuth();
  const pathname = usePathname();
  const loginHref = `/login?next=${encodeURIComponent(pathname || "/")}`;

  if (status === "loading") {
    return (
      <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-wide text-clay">Authentication</p>
        <h2 className="mt-2 text-2xl font-semibold text-ink">{title}</h2>
        <p className="mt-2 max-w-2xl text-sm leading-7 text-ink/70">{description}</p>
        <div className="mt-6 animate-pulse rounded-2xl border border-dashed border-ink/15 bg-paper/70 p-5 text-sm text-ink/55">
          Checking your session...
        </div>
      </div>
    );
  }

  if (status === "anonymous" || status === "expired") {
    return (
      <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-wide text-clay">Authentication</p>
        <h2 className="mt-2 text-2xl font-semibold text-ink">{title}</h2>
        <p className="mt-2 max-w-2xl text-sm leading-7 text-ink/70">{description}</p>
        <div
          className={[
            "mt-6 border px-4 py-4 text-sm leading-7",
            status === "expired" ? "border-clay/25 bg-clay/10" : "border-brass/20 bg-brass/10"
          ].join(" ")}
        >
          <p className="font-semibold text-ink">
            {status === "expired" ? "Your session expired." : "Sign in required."}
          </p>
          <p className="mt-1 text-ink/75">
            {status === "expired"
              ? "Refresh your session to continue using this area."
              : "Sign in to access the Knowledge Agent or admin workspace."}
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              href={loginHref}
              className="border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-tide/90"
            >
              Go to login
            </Link>
            {status === "expired" ? (
              <button
                type="button"
                onClick={logout}
                className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-ink/25 hover:bg-paper"
              >
                Clear session
              </button>
            ) : null}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-clay">Authenticated</p>
            <h2 className="mt-2 text-2xl font-semibold text-ink">{title}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-7 text-ink/70">{description}</p>
          </div>
          <div className="space-y-2 text-right">
            <div className="rounded-full border border-tide/20 bg-tide/10 px-3 py-1 text-xs font-semibold text-tide">
              {user?.email}
            </div>
            <button
              type="button"
              onClick={logout}
              className="border border-ink/15 bg-white px-3 py-2 text-xs font-semibold text-ink transition hover:border-ink/25 hover:bg-paper"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
      {children}
    </div>
  );
}
