"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { ApiError } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";

export function LoginPanel() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const nextPath = next && next.startsWith("/") ? next : "/";
  const { status, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "authenticated") {
      router.replace(nextPath);
    }
  }, [nextPath, router, status]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await login({ email, password });
      router.replace(nextPath);
    } catch (caughtError) {
      const message =
        caughtError instanceof ApiError
          ? caughtError.status === 401
            ? "Invalid email or password."
            : caughtError.message
          : "Unable to sign in.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="grid gap-8 lg:grid-cols-[1fr_0.9fr] lg:items-center">
      <div className="space-y-5">
        <p className="text-sm font-semibold uppercase tracking-wide text-clay">Authentication</p>
        <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-ink md:text-5xl">
          Sign in to access the Knowledge Agent and admin workspace.
        </h1>
        <p className="max-w-2xl text-lg leading-8 text-ink/70">
          The frontend stores your Bearer token locally, validates it against `/api/v1/auth/me`, and
          attaches it to authenticated API calls.
        </p>
        <div className="grid gap-3 md:grid-cols-3">
          <div className="border border-ink/10 bg-white/65 p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Session</p>
            <p className="mt-2 text-sm leading-7 text-ink/75">JWT stored in local browser state.</p>
          </div>
          <div className="border border-ink/10 bg-white/65 p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Validation</p>
            <p className="mt-2 text-sm leading-7 text-ink/75">Me endpoint refreshes the active user.</p>
          </div>
          <div className="border border-ink/10 bg-white/65 p-4 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Routing</p>
            <p className="mt-2 text-sm leading-7 text-ink/75">Protected pages stay hidden without a session.</p>
          </div>
        </div>
      </div>

      <form onSubmit={(event) => void handleSubmit(event)} className="border border-ink/10 bg-white/72 p-6 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-wide text-clay">Login</p>
        <h2 className="mt-2 text-2xl font-semibold text-ink">Enter credentials</h2>
        <div className="mt-6 space-y-4">
          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-ink">Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              className="w-full border border-ink/15 bg-white px-4 py-3 text-sm text-ink outline-none transition placeholder:text-ink/40 focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
              placeholder="admin@example.com"
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-sm font-semibold text-ink">Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              className="w-full border border-ink/15 bg-white px-4 py-3 text-sm text-ink outline-none transition placeholder:text-ink/40 focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
              placeholder="Enter your password"
            />
          </label>

          {error ? (
            <div className="border border-clay/25 bg-clay/10 px-4 py-3 text-sm leading-7 text-ink">
              {error}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={loading}
            className="w-full border border-tide/40 bg-tide px-4 py-3 text-sm font-semibold text-paper transition hover:bg-tide/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
          <p className="text-xs leading-6 text-ink/55">
            After sign-in you&apos;ll be returned to {nextPath}.
          </p>
        </div>
      </form>
    </section>
  );
}
