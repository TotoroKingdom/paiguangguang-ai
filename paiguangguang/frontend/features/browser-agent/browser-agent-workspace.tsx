"use client";

import { FormEvent, useState } from "react";

import { ApiError } from "@/lib/api";
import { runBrowserAgent } from "@/lib/browser-agent";
import type { BrowserAgentRunData, BrowserAgentStepData, BrowserSearchResultData } from "@/types/browser-agent";

const starterPrompt = "How does the portfolio use React Flow to explain the system architecture?";
const suggestedPrompts = [
  "How does the portfolio use React Flow to explain the system architecture?",
  "What mock research workflow does the Browser Agent demonstrate?",
  "Which portfolio pages show workflow state instead of just final answers?",
];

function badgeClass(kind: BrowserAgentStepData["kind"]) {
  if (kind === "plan") return "border-brass/30 bg-brass/10 text-ink";
  if (kind === "tool_call") return "border-tide/30 bg-tide/10 text-ink";
  if (kind === "observation") return "border-clay/30 bg-clay/10 text-ink";
  return "border-moss/30 bg-moss/10 text-ink";
}

function kindLabel(kind: BrowserAgentStepData["kind"]) {
  if (kind === "tool_call") return "Tool";
  if (kind === "observation") return "Observation";
  if (kind === "synthesis") return "Synthesis";
  return "Plan";
}

function formatData(value: Record<string, unknown>) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function SearchResultCard({ result, index }: { result: BrowserSearchResultData; index: number }) {
  return (
    <li className="rounded-2xl border border-ink/10 bg-paper/80 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-ink">
            Result {index + 1} <span className="text-ink/45">·</span> {Math.round(result.score * 100)}%
          </p>
          <a
            href={result.url}
            target="_blank"
            rel="noreferrer"
            className="mt-1 block text-xs uppercase tracking-wide text-tide underline decoration-tide/40 underline-offset-2"
          >
            {result.url}
          </a>
        </div>
        <span className="rounded-full border border-ink/10 bg-white/70 px-3 py-1 text-xs font-semibold text-ink/70">
          {result.title}
        </span>
      </div>
      <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-ink/75">{result.snippet}</p>
    </li>
  );
}

function StepCard({ step }: { step: BrowserAgentStepData }) {
  return (
    <li className="rounded-2xl border border-ink/10 bg-white/70 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-ink">{step.title}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.2em] text-ink/55">{step.step_id}</p>
        </div>
        <span className={["rounded-full border px-3 py-1 text-xs font-semibold", badgeClass(step.kind)].join(" ")}>
          {kindLabel(step.kind)}
        </span>
      </div>
      <p className="mt-3 text-sm leading-7 text-ink/75">{step.detail}</p>
      <pre className="mt-4 overflow-x-auto rounded-xl border border-ink/10 bg-paper/80 p-3 text-xs leading-6 text-ink/75">
        {formatData(step.data)}
      </pre>
    </li>
  );
}

export function BrowserAgentWorkspace() {
  const [prompt, setPrompt] = useState(starterPrompt);
  const [topK, setTopK] = useState(3);
  const [result, setResult] = useState<BrowserAgentRunData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt || isLoading) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await runBrowserAgent({
        prompt: trimmedPrompt,
        top_k: topK,
      });
      setResult(data);
    } catch (caughtError) {
      const message = caughtError instanceof ApiError ? caughtError.message : "Unable to run the browser agent.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  function usePrompt(samplePrompt: string) {
    if (!isLoading) {
      setPrompt(samplePrompt);
    }
  }

  return (
    <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <div className="space-y-6">
        <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-clay">Browser Research</p>
              <h2 className="mt-2 text-2xl font-semibold text-ink">Mock research workflow</h2>
              <p className="mt-2 max-w-xl text-sm leading-7 text-ink/70">
                This demo shows the visible plan, deterministic mock search, intermediate observations, and the
                synthesized answer.
              </p>
            </div>
            <div className="rounded-full border border-ink/10 bg-paper px-3 py-1 text-xs font-semibold text-ink/65">
              {isLoading ? "Running" : "Ready"}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="mt-5 space-y-4">
            <label className="block">
              <span className="mb-2 block text-sm font-semibold text-ink">Research prompt</span>
              <textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                rows={6}
                placeholder="Ask about a workflow, page, system concept, or architecture detail."
                className="w-full resize-none border border-ink/15 bg-white px-4 py-3 text-sm leading-7 text-ink outline-none transition placeholder:text-ink/40 focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
              />
            </label>

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="mb-2 block text-sm font-semibold text-ink">Top K</span>
                <input
                  type="number"
                  min={1}
                  max={5}
                  value={topK}
                  onChange={(event) => {
                    const parsed = Number(event.target.value);
                    setTopK(Number.isFinite(parsed) ? Math.max(1, Math.min(5, Math.round(parsed))) : 3);
                  }}
                  className="w-full border border-ink/15 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
                />
              </label>
              <div className="rounded-2xl border border-dashed border-ink/15 bg-paper/70 px-4 py-3 text-sm leading-7 text-ink/65">
                The mock search is deterministic and stays offline so the workflow is easy to inspect.
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {suggestedPrompts.map((samplePrompt) => (
                <button
                  key={samplePrompt}
                  type="button"
                  onClick={() => usePrompt(samplePrompt)}
                  className="border border-ink/10 bg-paper px-3 py-2 text-left text-sm leading-6 text-ink transition hover:border-tide/35 hover:bg-white"
                >
                  {samplePrompt}
                </button>
              ))}
            </div>

            {error ? (
              <div className="border border-clay/25 bg-clay/10 px-4 py-3 text-sm leading-7 text-ink">{error}</div>
            ) : null}

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={isLoading}
                className="border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-tide/90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isLoading ? "Running..." : "Run research"}
              </button>
              <button
                type="button"
                onClick={() => setResult(null)}
                className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-ink/25 hover:bg-paper"
              >
                Clear result
              </button>
            </div>
          </form>
        </section>

        <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-wide text-clay">Execution Steps</p>
          {result ? (
            <ul className="mt-4 space-y-3">
              {result.steps.map((step) => (
                <StepCard key={step.step_id} step={step} />
              ))}
            </ul>
          ) : (
            <div className="mt-4 rounded-2xl border border-dashed border-ink/15 bg-paper/70 p-5 text-sm leading-7 text-ink/60">
              Run the browser workflow to reveal the plan, tool call, intermediate observations, and synthesis.
            </div>
          )}
        </section>
      </div>

      <aside className="space-y-6">
        <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-wide text-clay">Final Answer</p>
          <div className="mt-4 rounded-2xl border border-ink/10 bg-paper/80 p-4">
            {result ? (
              <p className="whitespace-pre-wrap text-sm leading-8 text-ink">{result.final_answer}</p>
            ) : (
              <p className="text-sm leading-7 text-ink/60">
                The synthesized answer appears here after the workflow completes.
              </p>
            )}
          </div>
          {result ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="border border-ink/10 bg-paper/80 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-clay">Search Query</p>
                <p className="mt-1 text-sm leading-7 text-ink">{result.search_query}</p>
              </div>
              <div className="border border-ink/10 bg-paper/80 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-clay">Results</p>
                <p className="mt-1 text-sm leading-7 text-ink">{result.search_results.length}</p>
              </div>
            </div>
          ) : null}
        </section>

        <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
          <p className="text-sm font-semibold uppercase tracking-wide text-clay">Search Results</p>
          {result?.search_results.length ? (
            <ul className="mt-4 space-y-3">
              {result.search_results.map((searchResult, index) => (
                <SearchResultCard key={`${searchResult.title}-${index}`} result={searchResult} index={index} />
              ))}
            </ul>
          ) : (
            <div className="mt-4 rounded-2xl border border-dashed border-ink/15 bg-paper/70 p-5 text-sm leading-7 text-ink/60">
              Search results are shown here after the mock tool runs.
            </div>
          )}
        </section>
      </aside>
    </section>
  );
}
