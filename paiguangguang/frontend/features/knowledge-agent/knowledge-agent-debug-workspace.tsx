"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";

import { AuthGate } from "@/components/auth-gate";
import { ApiError } from "@/lib/api";
import { listAdminDocuments } from "@/lib/admin";
import { getDefaultKnowledgeCollection, queryKnowledgeAgent } from "@/lib/knowledge-agent";
import type {
  KnowledgeQueryData,
  KnowledgeQueryDebugData,
  KnowledgeQueryRewriteData,
  KnowledgeSourceData,
} from "@/types/knowledge-agent";

const defaultQuestion = "What does the knowledge base show about retrieval and citations?";
const defaultCollection = getDefaultKnowledgeCollection();

type AccessState = "checking" | "authorized" | "forbidden" | "error";

function formatScore(value: number) {
  return value.toFixed(3);
}

function formatCount(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatObjectValue(value: unknown) {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (value === null || value === undefined) {
    return "null";
  }
  return JSON.stringify(value);
}

function formatPromptPreview(text: string, limit = 140) {
  const normalized = text.trim().replace(/\s+/g, " ");
  if (normalized.length <= limit) {
    return normalized;
  }
  return `${normalized.slice(0, limit).trimEnd()}...`;
}

function isAuthError(error: unknown) {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}

function sortRouteScores(routeScores: Record<string, number>) {
  return Object.entries(routeScores)
    .filter(([, value]) => Number.isFinite(value))
    .sort(([leftKey], [rightKey]) => {
      const order = new Map([
        ["fusion", 0],
        ["vector", 1],
        ["keyword", 2],
      ]);
      return (order.get(leftKey) ?? 10) - (order.get(rightKey) ?? 10) || leftKey.localeCompare(rightKey);
    });
}

function scoreLabel(score: number | null | undefined) {
  return score === null || score === undefined ? "n/a" : formatScore(score);
}

function formatModelUsage(modelUsage: Record<string, unknown>) {
  const entries = Object.entries(modelUsage);
  if (!entries.length) {
    return ["No token usage reported."];
  }

  return entries
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => `${key}: ${formatObjectValue(value)}`);
}

function getCacheStatus(debug: KnowledgeQueryDebugData | null) {
  if (!debug) {
    return "Cache status is not available until a query runs.";
  }
  if (typeof debug.cache_status === "string" && debug.cache_status.trim()) {
    return debug.cache_status.trim();
  }
  return "Bypassed for debug inspection. The backend skips answer and retrieval caches when include_debug is enabled.";
}

function ScoreBadge({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded-full border border-ink/10 bg-paper px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-ink/65">
      {label}: {value}
    </span>
  );
}

function SummaryTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-ink/10 bg-paper/80 px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-clay">{label}</p>
      <p className="mt-1 break-words text-sm font-semibold leading-6 text-ink">{value}</p>
    </div>
  );
}

function TraceSourceCard({ source, index }: { source: KnowledgeSourceData; index: number }) {
  const routeScores = sortRouteScores(source.route_scores);

  return (
    <li className="rounded-2xl border border-ink/10 bg-white/80 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-ink">#{index + 1}</p>
            <ScoreBadge label="Score" value={formatScore(source.score)} />
            <ScoreBadge label="Rerank" value={scoreLabel(source.rerank_score)} />
          </div>
          <p className="truncate text-xs uppercase tracking-wide text-ink/55">{source.doc_id}</p>
          <p className="text-sm font-medium leading-6 text-ink/85">{source.title ?? "Untitled source"}</p>
          <p className="text-xs leading-5 text-ink/55">
            page {source.page_number ?? "n/a"} | chunk {source.chunk_index} | {source.chunk_id}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {routeScores.map(([label, value]) => (
            <ScoreBadge key={label} label={label} value={formatScore(value)} />
          ))}
        </div>
      </div>

      <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-ink/75">{source.text}</p>

      <details className="mt-4 rounded-xl border border-ink/10 bg-paper/70 p-3">
        <summary className="cursor-pointer list-none text-xs font-semibold uppercase tracking-wide text-clay">
          Metadata
        </summary>
        <dl className="mt-3 grid gap-2 text-xs leading-6 text-ink/70 sm:grid-cols-2">
          {Object.entries(source.metadata).length ? (
            Object.entries(source.metadata)
              .sort(([left], [right]) => left.localeCompare(right))
              .map(([key, value]) => (
                <div key={key} className="rounded-lg border border-ink/10 bg-white/80 px-3 py-2">
                  <dt className="font-semibold uppercase tracking-wide text-clay">{key}</dt>
                  <dd className="mt-1 break-words text-ink/75">{formatObjectValue(value)}</dd>
                </div>
              ))
          ) : (
            <div className="rounded-lg border border-ink/10 bg-white/80 px-3 py-2">No metadata</div>
          )}
        </dl>
      </details>
    </li>
  );
}

function TraceSection({
  title,
  description,
  count,
  children,
}: {
  title: string;
  description: string;
  count: number;
  children: ReactNode;
}) {
  return (
    <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-clay">{title}</p>
          <p className="mt-2 max-w-2xl text-sm leading-7 text-ink/70">{description}</p>
        </div>
        <span className="rounded-full border border-ink/10 bg-paper px-3 py-1 text-xs font-semibold text-ink/65">
          {formatCount(count)}
        </span>
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function RewritePanel({ rewrite }: { rewrite: KnowledgeQueryRewriteData | null }) {
  if (!rewrite) {
    return (
      <div className="rounded-2xl border border-ink/10 bg-paper/70 p-4 text-sm leading-7 text-ink/60">
        Query rewrite data is not available.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2">
        <SummaryTile label="Original question" value={rewrite.original_question} />
        <SummaryTile label="Rewrite status" value={rewrite.metadata.status} />
        <SummaryTile
          label="Rewrite model"
          value={rewrite.metadata.model ?? "Disabled or unavailable"}
        />
        <SummaryTile
          label="Fallback"
          value={rewrite.metadata.fallback_reason ?? "No fallback used"}
        />
      </div>
      <div className="rounded-2xl border border-ink/10 bg-paper/70 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-clay">Rewritten queries</p>
        <ul className="mt-3 space-y-2 text-sm leading-7 text-ink/80">
          {rewrite.rewritten_queries.length ? (
            rewrite.rewritten_queries.map((query, index) => (
              <li key={`${query}-${index}`} className="rounded-xl border border-ink/10 bg-white/80 px-4 py-3">
                <span className="mr-2 text-xs font-semibold uppercase tracking-wide text-clay">
                  {index + 1}
                </span>
                {query}
              </li>
            ))
          ) : (
            <li className="rounded-xl border border-ink/10 bg-white/80 px-4 py-3 text-ink/60">
              No rewritten queries were produced.
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}

export function KnowledgeAgentDebugWorkspace() {
  const [accessState, setAccessState] = useState<AccessState>("checking");
  const [accessError, setAccessError] = useState<string | null>(null);
  const [question, setQuestion] = useState(defaultQuestion);
  const [collection, setCollection] = useState(defaultCollection);
  const [topK, setTopK] = useState(5);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [hasQueried, setHasQueried] = useState(false);
  const [result, setResult] = useState<KnowledgeQueryData | null>(null);

  useEffect(() => {
    let active = true;
    setAccessState("checking");
    setAccessError(null);

    void listAdminDocuments()
      .then(() => {
        if (active) {
          setAccessState("authorized");
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }

        if (isAuthError(error)) {
          setAccessState("forbidden");
          return;
        }

        setAccessState("error");
        setAccessError(error instanceof ApiError ? error.message : "Unable to verify debug access.");
      });

    return () => {
      active = false;
    };
  }, []);

  async function handleQuery() {
    const trimmedQuestion = question.trim();
    const trimmedCollection = collection.trim() || defaultCollection;

    if (!trimmedQuestion) {
      setQueryError("Enter a question before running the trace.");
      setResult(null);
      setHasQueried(false);
      return;
    }

    setQueryLoading(true);
    setQueryError(null);

    try {
      const response = await queryKnowledgeAgent({
        question: trimmedQuestion,
        collection: trimmedCollection,
        top_k: topK,
        include_debug: true,
      });

      setResult(response);
      setHasQueried(true);
    } catch (error) {
      if (isAuthError(error)) {
        setAccessState("forbidden");
        setAccessError(
          error instanceof ApiError && error.status === 401
            ? "Your session expired or is invalid."
            : "This account does not have permission to inspect debug traces."
        );
      } else {
        setQueryError(error instanceof ApiError ? error.message : "Unable to run the debug query.");
      }
    } finally {
      setQueryLoading(false);
    }
  }

  function resetQuery() {
    setQuestion(defaultQuestion);
    setCollection(defaultCollection);
    setTopK(5);
    setResult(null);
    setHasQueried(false);
    setQueryError(null);
  }

  const debug = result?.debug ?? null;
  const promptSummary = {
    question: question.trim() || "Empty question",
    collection: collection.trim() || defaultCollection,
    topK: formatCount(topK),
    includeDebug: "enabled",
    cache: getCacheStatus(debug),
  };

  return (
    <AuthGate
      title="RAG Debug Page"
      description="Inspect retrieval and answer traces for the Knowledge Agent."
    >
      <section className="space-y-6">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="border border-ink/10 bg-white/70 px-4 py-3 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Trace</p>
            <p className="mt-1 text-sm leading-7 text-ink/75">
              Run a live debug query with rewrite, retrieval, fusion, rerank, context, and citation details.
            </p>
          </div>
          <div className="border border-ink/10 bg-white/70 px-4 py-3 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Access</p>
            <p className="mt-1 text-sm leading-7 text-ink/75">
              Only document-admin or admin users can inspect this page.
            </p>
          </div>
          <div className="border border-ink/10 bg-white/70 px-4 py-3 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Cache</p>
            <p className="mt-1 text-sm leading-7 text-ink/75">
              Debug queries bypass caches so the trace reflects the live pipeline.
            </p>
          </div>
        </div>

        <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-clay">Navigation</p>
              <h2 className="mt-2 text-2xl font-semibold text-ink">Knowledge Agent debug inspector</h2>
              <p className="mt-2 max-w-2xl text-sm leading-7 text-ink/70">
                Use this page to inspect the complete retrieval trace without leaving the authenticated UI.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                href="/agents/knowledge"
                className="border border-ink/15 bg-paper px-3 py-2 text-xs font-semibold text-ink transition hover:border-ink/25 hover:bg-white"
              >
                Back to Knowledge Agent
              </Link>
              <Link
                href="/admin"
                className="border border-tide/40 bg-tide px-3 py-2 text-xs font-semibold text-paper transition hover:bg-tide/90"
              >
                Open Admin
              </Link>
            </div>
          </div>
        </div>

        {accessState === "checking" ? (
          <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-clay">Authorization</p>
            <h2 className="mt-2 text-2xl font-semibold text-ink">Checking debug permissions</h2>
            <div className="mt-5 animate-pulse rounded-2xl border border-dashed border-ink/15 bg-paper/70 p-5 text-sm text-ink/55">
              Verifying whether this account can access admin or document-admin traces...
            </div>
          </section>
        ) : null}

        {accessState === "forbidden" ? (
          <section className="border border-clay/25 bg-clay/10 p-5 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-clay">Forbidden</p>
            <h2 className="mt-2 text-2xl font-semibold text-ink">You do not have debug access</h2>
            <p className="mt-2 max-w-2xl text-sm leading-7 text-ink/75">
              This page is limited to users with admin or document-admin permissions.
            </p>
            <div className="mt-4">
              <Link
                href="/agents/knowledge"
                className="inline-flex border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-ink/25 hover:bg-paper"
              >
                Return to Knowledge Agent
              </Link>
            </div>
          </section>
        ) : null}

        {accessState === "error" ? (
          <section className="border border-clay/25 bg-clay/10 p-5 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-clay">Error</p>
            <h2 className="mt-2 text-2xl font-semibold text-ink">Unable to verify access</h2>
            <p className="mt-2 max-w-2xl text-sm leading-7 text-ink/75">
              {accessError ?? "The access check failed before the trace page could load."}
            </p>
          </section>
        ) : null}

        {accessState === "authorized" ? (
          <div className="space-y-6">
            <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-clay">Query</p>
                  <h2 className="mt-2 text-2xl font-semibold text-ink">Run a traced question</h2>
                  <p className="mt-2 max-w-2xl text-sm leading-7 text-ink/70">
                    The query runs with `include_debug` enabled so the page can display rewrite output, retrieval
                    candidates, fusion order, rerank scores, selected context, citations, latency, and usage data.
                  </p>
                </div>
                <div className="rounded-full border border-ink/10 bg-paper px-3 py-1 text-xs font-semibold text-ink/65">
                  {hasQueried ? "Trace loaded" : "Awaiting query"}
                </div>
              </div>

              <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_0.42fr]">
                <label className="block">
                  <span className="mb-2 block text-sm font-semibold text-ink">Question</span>
                  <textarea
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    rows={6}
                    className="w-full resize-none border border-ink/15 bg-white px-4 py-3 text-sm leading-7 text-ink outline-none transition placeholder:text-ink/40 focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
                    placeholder="Ask a question about retrieval behavior, citations, or trace details."
                  />
                </label>

                <div className="space-y-4">
                  <label className="block">
                    <span className="mb-2 block text-sm font-semibold text-ink">Collection</span>
                    <input
                      value={collection}
                      onChange={(event) => setCollection(event.target.value)}
                      className="w-full border border-ink/15 bg-white px-4 py-3 text-sm text-ink outline-none transition placeholder:text-ink/40 focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
                    />
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-sm font-semibold text-ink">Top K</span>
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={topK}
                      onChange={(event) => {
                        const parsed = Number(event.target.value);
                        setTopK(Number.isFinite(parsed) ? Math.max(1, Math.min(20, Math.round(parsed))) : 5);
                      }}
                      className="w-full border border-ink/15 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
                    />
                  </label>
                  <div className="rounded-2xl border border-ink/10 bg-paper/70 p-4 text-sm leading-7 text-ink/75">
                    <p className="font-semibold text-ink">Prompt summary</p>
                    <p className="mt-2 text-xs uppercase tracking-wide text-clay">Cache</p>
                    <p>{promptSummary.cache}</p>
                  </div>
                </div>
              </div>

              {queryError ? (
                <div className="mt-4 border border-clay/25 bg-clay/10 px-4 py-3 text-sm leading-7 text-ink">
                  {queryError}
                </div>
              ) : null}

              <div className="mt-5 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => void handleQuery()}
                  disabled={queryLoading}
                  className="border border-tide/40 bg-ink px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-ink/90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {queryLoading ? "Running trace..." : "Inspect trace"}
                </button>
                <button
                  type="button"
                  onClick={resetQuery}
                  className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-ink/25 hover:bg-paper"
                >
                  Reset
                </button>
              </div>
            </section>

            {hasQueried && result ? (
              <div className="space-y-6">
                <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold uppercase tracking-wide text-clay">Prompt input summary</p>
                      <h2 className="mt-2 text-2xl font-semibold text-ink">Live trace request</h2>
                      <p className="mt-2 max-w-2xl text-sm leading-7 text-ink/70">
                        This summary mirrors the prompt inputs used for the trace so you can correlate the query with
                        retrieval and answer behavior.
                      </p>
                    </div>
                    <div className="rounded-full border border-tide/20 bg-tide/10 px-3 py-1 text-xs font-semibold text-tide">
                      {result.debug ? `${formatCount(result.debug.latency_ms)} ms` : "Latency n/a"}
                    </div>
                  </div>

                  <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                    <SummaryTile label="Question" value={formatPromptPreview(promptSummary.question, 160)} />
                    <SummaryTile label="Collection" value={promptSummary.collection} />
                    <SummaryTile label="Top K" value={promptSummary.topK} />
                    <SummaryTile label="Include debug" value={promptSummary.includeDebug} />
                  </div>
                </section>

                <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
                  <div className="space-y-6">
                    <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold uppercase tracking-wide text-clay">Answer</p>
                          <h2 className="mt-2 text-2xl font-semibold text-ink">Model response</h2>
                        </div>
                        <span className="rounded-full border border-ink/10 bg-paper px-3 py-1 text-xs font-semibold text-ink/65">
                          {result.sources.length} citations
                        </span>
                      </div>
                      <div className="mt-5 rounded-2xl border border-ink/10 bg-paper/80 p-4">
                        <p className="whitespace-pre-wrap text-sm leading-8 text-ink">{result.answer}</p>
                      </div>
                    </section>

                    <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
                      <p className="text-sm font-semibold uppercase tracking-wide text-clay">Cache status</p>
                      <h2 className="mt-2 text-2xl font-semibold text-ink">Debug request cache view</h2>
                      <p className="mt-2 max-w-2xl text-sm leading-7 text-ink/70">{getCacheStatus(debug)}</p>
                    </section>
                  </div>

                  <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold uppercase tracking-wide text-clay">Rewrite</p>
                        <h2 className="mt-2 text-2xl font-semibold text-ink">Query rewrite output</h2>
                      </div>
                      <span className="rounded-full border border-ink/10 bg-paper px-3 py-1 text-xs font-semibold text-ink/65">
                        {result.rewrite?.metadata.rewritten_query_count ?? 0} rewrites
                      </span>
                    </div>
                    <div className="mt-5">
                      <RewritePanel rewrite={result.rewrite ?? debug?.rewrites ?? null} />
                    </div>
                  </section>
                </section>

                <TraceSection
                  title="Vector hits"
                  description="Raw vector candidates before fusion."
                  count={debug?.vector_hits.length ?? 0}
                >
                  {debug?.vector_hits.length ? (
                    <ul className="space-y-3">
                      {debug.vector_hits.map((source, index) => (
                        <TraceSourceCard key={`${source.doc_id}-${source.chunk_id}-vector`} source={source} index={index} />
                      ))}
                    </ul>
                  ) : (
                    <div className="rounded-2xl border border-ink/10 bg-paper/70 p-4 text-sm leading-7 text-ink/60">
                      No vector hits were returned.
                    </div>
                  )}
                </TraceSection>

                <TraceSection
                  title="Keyword hits"
                  description="Exact-term candidates that supplement vector retrieval."
                  count={debug?.keyword_hits.length ?? 0}
                >
                  {debug?.keyword_hits.length ? (
                    <ul className="space-y-3">
                      {debug.keyword_hits.map((source, index) => (
                        <TraceSourceCard key={`${source.doc_id}-${source.chunk_id}-keyword`} source={source} index={index} />
                      ))}
                    </ul>
                  ) : (
                    <div className="rounded-2xl border border-ink/10 bg-paper/70 p-4 text-sm leading-7 text-ink/60">
                      No keyword hits were returned.
                    </div>
                  )}
                </TraceSection>

                <TraceSection
                  title="Fusion"
                  description="Reciprocal Rank Fusion output before reranking."
                  count={debug?.fusion.length ?? 0}
                >
                  {debug?.fusion.length ? (
                    <ul className="space-y-3">
                      {debug.fusion.map((source, index) => (
                        <TraceSourceCard key={`${source.doc_id}-${source.chunk_id}-fusion`} source={source} index={index} />
                      ))}
                    </ul>
                  ) : (
                    <div className="rounded-2xl border border-ink/10 bg-paper/70 p-4 text-sm leading-7 text-ink/60">
                      No fusion candidates were returned.
                    </div>
                  )}
                </TraceSection>

                <TraceSection
                  title="Rerank"
                  description="Post-rerank ordering and scores when the rerank layer is available."
                  count={debug?.rerank.length ?? 0}
                >
                  {debug?.rerank.length ? (
                    <ul className="space-y-3">
                      {debug.rerank.map((source, index) => (
                        <TraceSourceCard key={`${source.doc_id}-${source.chunk_id}-rerank`} source={source} index={index} />
                      ))}
                    </ul>
                  ) : (
                    <div className="rounded-2xl border border-ink/10 bg-paper/70 p-4 text-sm leading-7 text-ink/60">
                      No rerank results were returned.
                    </div>
                  )}
                </TraceSection>

                <TraceSection
                  title="Selected context"
                  description="Chunks assembled into the model prompt."
                  count={debug?.selected_context.length ?? 0}
                >
                  {debug?.selected_context.length ? (
                    <ul className="space-y-3">
                      {debug.selected_context.map((source, index) => (
                        <TraceSourceCard key={`${source.doc_id}-${source.chunk_id}-context`} source={source} index={index} />
                      ))}
                    </ul>
                  ) : (
                    <div className="rounded-2xl border border-ink/10 bg-paper/70 p-4 text-sm leading-7 text-ink/60">
                      No context was selected for the prompt.
                    </div>
                  )}
                </TraceSection>

                <TraceSection
                  title="Citations"
                  description="Final sources surfaced to the user."
                  count={result.sources.length}
                >
                  {result.sources.length ? (
                    <ul className="space-y-3">
                      {result.sources.map((source, index) => (
                        <TraceSourceCard key={`${source.doc_id}-${source.chunk_id}-citation`} source={source} index={index} />
                      ))}
                    </ul>
                  ) : (
                    <div className="rounded-2xl border border-ink/10 bg-paper/70 p-4 text-sm leading-7 text-ink/60">
                      The answer returned no citations.
                    </div>
                  )}
                </TraceSection>

                <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold uppercase tracking-wide text-clay">Usage</p>
                      <h2 className="mt-2 text-2xl font-semibold text-ink">Latency and token usage</h2>
                    </div>
                    <span className="rounded-full border border-ink/10 bg-paper px-3 py-1 text-xs font-semibold text-ink/65">
                      {result.debug ? formatCount(result.debug.latency_ms) : "0"} ms
                    </span>
                  </div>

                  <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                    <SummaryTile
                      label="Latency"
                      value={result.debug ? `${formatCount(result.debug.latency_ms)} ms` : "Unavailable"}
                    />
                    <SummaryTile label="Token usage" value={result.debug ? "Available below" : "Unavailable"} />
                    <SummaryTile
                      label="Sources"
                      value={`${formatCount(result.sources.length)} citations`}
                    />
                  </div>

                  <div className="mt-5 rounded-2xl border border-ink/10 bg-paper/80 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-clay">Model usage</p>
                    <ul className="mt-3 space-y-2 text-sm leading-7 text-ink/80">
                      {formatModelUsage(debug?.model_usage ?? {}).map((entry) => (
                        <li key={entry} className="rounded-xl border border-ink/10 bg-white/80 px-4 py-3">
                          {entry}
                        </li>
                      ))}
                    </ul>
                  </div>
                </section>
              </div>
            ) : (
              <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
                <p className="text-sm font-semibold uppercase tracking-wide text-clay">Empty state</p>
                <h2 className="mt-2 text-2xl font-semibold text-ink">No trace yet</h2>
                <p className="mt-2 max-w-2xl text-sm leading-7 text-ink/70">
                  Submit a question to inspect retrieval and answer decisions. The page will show loading,
                  empty, forbidden, and error states as the trace progresses.
                </p>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <SummaryTile label="Rewrite" value="Waiting for a query" />
                  <SummaryTile label="Retrieval" value="Waiting for a query" />
                  <SummaryTile label="Answer" value="Waiting for a query" />
                </div>
              </section>
            )}
          </div>
        ) : null}
      </section>
    </AuthGate>
  );
}
