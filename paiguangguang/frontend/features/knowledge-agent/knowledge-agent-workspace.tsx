"use client";

import { useRef, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { useAuth } from "@/components/auth-provider";
import { ApiError } from "@/lib/api";
import {
  getDefaultKnowledgeCollection,
  ingestKnowledgeDocument,
  ingestKnowledgeText,
  queryKnowledgeAgent,
} from "@/lib/knowledge-agent";
import type { KnowledgeDocumentData, KnowledgeIngestData, KnowledgeSourceData } from "@/types/knowledge-agent";

const sampleQuestions = [
  "What does this document say about the project goals?",
  "What key capabilities are described here?",
  "Summarize the most important details from this text.",
];

const defaultQuestion = "What is the document about?";
const defaultCollection = getDefaultKnowledgeCollection();

function makeNoticePrefix(kind: "success" | "error" | "info") {
  if (kind === "success") {
    return "Success";
  }
  if (kind === "error") {
    return "Error";
  }
  return "Info";
}

function formatScore(score: number) {
  return `${Math.round(score * 100)}%`;
}

function formatNullableScore(score: number | null) {
  return score === null ? "n/a" : formatScore(score);
}

function truncateText(text: string, limit = 220) {
  if (text.length <= limit) {
    return text;
  }

  return `${text.slice(0, limit).trimEnd()}...`;
}

function formatCount(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatDateTime(value: string | null) {
  if (!value) {
    return "Unknown";
  }
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function isAuthError(error: unknown) {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}

function toAuthMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Your session expired or is invalid. Sign in again to continue.";
    }
    if (error.status === 403) {
      return "You are signed in, but this account does not have access to the Knowledge Agent.";
    }
    return error.message;
  }

  return "You do not have access to this Knowledge Agent action.";
}

function formatMetadata(metadata: Record<string, unknown>) {
  const entries = Object.entries(metadata);
  if (entries.length === 0) {
    return "No metadata";
  }

  return entries
    .map(([key, value]) => `${key}: ${typeof value === "string" ? value : JSON.stringify(value)}`)
    .join("\n");
}

function SourceCard({ source, index }: { source: KnowledgeSourceData; index: number }) {
  return (
    <li className="rounded-2xl border border-ink/10 bg-paper/80 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="text-sm font-semibold text-ink">
            Source {index + 1} <span className="text-ink/45">-</span> {formatScore(source.score)}
          </p>
          <p className="text-xs uppercase tracking-wide text-ink/55">{source.doc_id}</p>
          <p className="text-sm font-medium text-ink/80">{source.title ?? "Untitled source"}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full border border-tide/20 bg-tide/10 px-3 py-1 text-xs font-semibold text-tide">
            {source.chunk_id}
          </span>
          <span className="rounded-full border border-ink/10 bg-white px-3 py-1 text-xs font-semibold text-ink">
            page {source.page_number ?? "n/a"}
          </span>
        </div>
      </div>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-clay">Chunk index</dt>
          <dd className="text-sm text-ink">{source.chunk_index}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-clay">Rerank</dt>
          <dd className="text-sm text-ink">{formatNullableScore(source.rerank_score)}</dd>
        </div>
      </dl>
      <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-ink/75">{truncateText(source.text)}</p>
      <pre className="mt-4 overflow-x-auto rounded-xl border border-ink/10 bg-white/70 p-3 text-xs leading-6 text-ink/65">
        {formatMetadata(source.metadata)}
      </pre>
    </li>
  );
}

function LifecycleChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-ink/10 bg-white/70 px-3 py-2">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-clay">{label}</p>
      <p className="mt-1 text-sm font-semibold text-ink">{value}</p>
    </div>
  );
}

function IngestionStatusCard({
  document,
  ingestion,
}: {
  document: KnowledgeDocumentData;
  ingestion: KnowledgeIngestData;
}) {
  const job = ingestion.job;

  return (
    <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-clay">Ingestion status</p>
          <h2 className="mt-2 text-2xl font-semibold text-ink">{document.title ?? document.doc_id}</h2>
          <p className="mt-2 max-w-xl text-sm leading-7 text-ink/70">
            The latest document lifecycle, chunking, and job state after upload or reindex.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full border border-tide/20 bg-tide/10 px-3 py-1 text-xs font-semibold text-tide">
            {document.status}
          </span>
          <span className="rounded-full border border-ink/10 bg-paper px-3 py-1 text-xs font-semibold text-ink">
            job {job.status}
          </span>
        </div>
      </div>

      <dl className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <LifecycleChip label="Parse" value={document.parse_status} />
        <LifecycleChip label="Chunk" value={document.chunk_status} />
        <LifecycleChip label="Embedding" value={document.embedding_status} />
        <LifecycleChip label="Index" value={document.index_status} />
        <LifecycleChip label="Retry count" value={formatCount(job.retry_count)} />
        <LifecycleChip label="Reindex" value={job.is_reindex ? "Yes" : "No"} />
        <LifecycleChip
          label="Chunk size"
          value={job.chunk_size === null ? "Unknown" : formatCount(job.chunk_size)}
        />
        <LifecycleChip
          label="Chunk overlap"
          value={job.chunk_overlap === null ? "Unknown" : formatCount(job.chunk_overlap)}
        />
      </dl>

      <div className="mt-5 grid gap-3 lg:grid-cols-2">
        <div className="border border-ink/10 bg-paper/80 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-clay">Document metadata</p>
          <dl className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-clay">Owner</dt>
              <dd className="text-sm text-ink">{document.owner_user_id ?? "Unassigned"}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-clay">Workspace</dt>
              <dd className="text-sm text-ink">{document.workspace_id ?? "Unassigned"}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-clay">Permission</dt>
              <dd className="text-sm text-ink">{document.permission_scope ?? "Unscoped"}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-clay">Error</dt>
              <dd className="text-sm text-ink">{document.error_message ?? "None"}</dd>
            </div>
          </dl>
        </div>
        <div className="border border-ink/10 bg-paper/80 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-clay">Job metadata</p>
          <dl className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-clay">Started</dt>
              <dd className="text-sm text-ink">{formatDateTime(job.started_at)}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-clay">Completed</dt>
              <dd className="text-sm text-ink">{formatDateTime(job.completed_at)}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-clay">Failure reason</dt>
              <dd className="text-sm text-ink">{job.failure_reason ?? "None"}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-clay">Document ID</dt>
              <dd className="text-sm text-ink">{job.document_id}</dd>
            </div>
          </dl>
        </div>
      </div>
    </section>
  );
}

export function KnowledgeAgentWorkspace() {
  const { status } = useAuth();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [documentTitle, setDocumentTitle] = useState("");
  const [documentText, setDocumentText] = useState("");
  const [documentFileName, setDocumentFileName] = useState<string | null>(null);
  const [question, setQuestion] = useState(defaultQuestion);
  const [collection, setCollection] = useState(defaultCollection);
  const [topK, setTopK] = useState(5);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [chunkCount, setChunkCount] = useState<number | null>(null);
  const [latestIngestion, setLatestIngestion] = useState<{
    document: KnowledgeDocumentData;
    ingestion: KnowledgeIngestData;
  } | null>(null);
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<KnowledgeSourceData[]>([]);
  const [notice, setNotice] = useState<{ kind: "success" | "error" | "info"; text: string } | null>({
    kind: "info",
    text: "Load a document, index it into Chroma, and then ask a question.",
  });
  const [authError, setAuthError] = useState<string | null>(null);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [queryLoading, setQueryLoading] = useState(false);
  const [ingestError, setIngestError] = useState<string | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);

  async function handleFileChange(file: File | null) {
    if (!file) {
      return;
    }

    try {
      const text = await file.text();
      setDocumentText(text);
      setDocumentFileName(file.name);
      setNotice({
        kind: "info",
        text: `Loaded ${file.name}. Review the text and ingest it when ready.`,
      });
      setIngestError(null);
      setAuthError(null);
    } catch {
      setNotice({
        kind: "error",
        text: "The selected file could not be read as text.",
      });
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  function handleAuthFailure(error: unknown) {
    const message = toAuthMessage(error);
    setAuthError(message);
    setIngestError(null);
    setQueryError(null);
    setNotice(null);
  }

  async function handleIngest(reindex = false) {
    const text = documentText.trim();
    const title = documentTitle.trim();

    if (reindex && !documentId) {
      setIngestError("Index a document first before reindexing it.");
      setNotice({
        kind: "error",
        text: "Reindex failed because no document is available yet.",
      });
      return;
    }

    if (!reindex && !text) {
      setIngestError("Paste or upload text before ingesting.");
      setNotice({
        kind: "error",
        text: "Ingestion failed because the document text is empty.",
      });
      return;
    }

    if (status !== "authenticated") {
      handleAuthFailure(new ApiError("Sign in required before ingesting.", 401, "UNAUTHORIZED"));
      return;
    }

    setIngestLoading(true);
    setIngestError(null);
    setAuthError(null);
    setNotice(null);

    try {
      if (reindex && documentId) {
        const ingestion = await ingestKnowledgeDocument({
          doc_id: documentId,
          reindex: true,
          chunk_size: 800,
          chunk_overlap: 120,
        });

        setDocumentId(ingestion.document.doc_id);
        setChunkCount(ingestion.chunk_count);
        setLatestIngestion({
          document: ingestion.document,
          ingestion,
        });
        setNotice({
          kind: "success",
          text: `Reindexed ${ingestion.chunk_count} chunks for ${ingestion.document.doc_id}.`,
        });
      } else {
        const result = await ingestKnowledgeText({
          title: title || undefined,
          text,
          chunk_size: 800,
          chunk_overlap: 120,
        });

        setDocumentId(result.document.doc_id);
        setChunkCount(result.ingestion.chunk_count);
        setLatestIngestion(result);
        setNotice({
          kind: "success",
          text: `Indexed ${result.ingestion.chunk_count} chunks for ${result.document.doc_id}.`,
        });
      }
    } catch (error) {
      if (isAuthError(error)) {
        handleAuthFailure(error);
      } else {
        const message = error instanceof ApiError ? error.message : "Unable to index the document.";
        setIngestError(message);
        setNotice({
          kind: "error",
          text: message,
        });
      }
    } finally {
      setIngestLoading(false);
    }
  }

  async function handleQuery() {
    const trimmedQuestion = question.trim();
    const trimmedCollection = collection.trim() || defaultCollection;

    if (!trimmedQuestion) {
      setQueryError("Ask a question before querying.");
      setNotice({
        kind: "error",
        text: "Query failed because the question is empty.",
      });
      return;
    }

    if (status !== "authenticated") {
      handleAuthFailure(new ApiError("Sign in required before querying.", 401, "UNAUTHORIZED"));
      return;
    }

    setQueryLoading(true);
    setQueryError(null);
    setAuthError(null);
    setNotice(null);

    try {
      const result = await queryKnowledgeAgent({
        question: trimmedQuestion,
        collection: trimmedCollection,
        top_k: topK,
      });

      setAnswer(result.answer);
      setSources(result.sources);
      setNotice({
        kind: "success",
        text: result.sources.length
          ? `Retrieved ${result.sources.length} supporting chunk${result.sources.length === 1 ? "" : "s"}.`
          : "The model answered without matching retrieval sources.",
      });
    } catch (error) {
      if (isAuthError(error)) {
        handleAuthFailure(error);
      } else {
        const message = error instanceof ApiError ? error.message : "Unable to query the knowledge agent.";
        setQueryError(message);
        setNotice({
          kind: "error",
          text: message,
        });
      }
    } finally {
      setQueryLoading(false);
    }
  }

  function resetDocument() {
    setDocumentTitle("");
    setDocumentText("");
    setDocumentFileName(null);
    setDocumentId(null);
    setChunkCount(null);
    setLatestIngestion(null);
    setIngestError(null);
    setAuthError(null);
    setNotice({
      kind: "info",
      text: "Document fields cleared. You can load a new source text now.",
    });
  }

  function resetAnswer() {
    setQuestion(defaultQuestion);
    setAnswer("");
    setSources([]);
    setQueryError(null);
    setNotice({
      kind: "info",
      text: "Question cleared. Ask another question when you are ready.",
    });
  }

  function applySampleQuestion(text: string) {
    if (!queryLoading) {
      setQuestion(text);
    }
  }

  const canInteract = status === "authenticated";

  return (
    <AuthGate
      title="Knowledge Agent"
      description="Upload or paste reference text, index it into Chroma, and ask questions with visible sources and citations."
    >
      <section className="space-y-6">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="border border-ink/10 bg-white/70 px-4 py-3 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Pipeline</p>
            <p className="mt-1 text-sm text-ink/75">Paste text or upload a file, then index it into Chroma.</p>
          </div>
          <div className="border border-ink/10 bg-white/70 px-4 py-3 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Retrieval</p>
            <p className="mt-1 text-sm text-ink/75">Questions search the configured collection with top-k similarity.</p>
          </div>
          <div className="border border-ink/10 bg-white/70 px-4 py-3 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Citations</p>
            <p className="mt-1 text-sm text-ink/75">Answers render source title, page, chunk, score, rerank, and metadata.</p>
          </div>
        </div>

        {notice ? (
          <div
            aria-live="polite"
            className={[
              "border px-4 py-3 text-sm leading-7 shadow-sm",
              notice.kind === "success"
                ? "border-tide/20 bg-tide/10 text-ink"
                : notice.kind === "error"
                  ? "border-clay/25 bg-clay/10 text-ink"
                  : "border-brass/20 bg-brass/10 text-ink",
            ].join(" ")}
          >
            <span className="font-semibold">{makeNoticePrefix(notice.kind)}.</span> {notice.text}
          </div>
        ) : null}

        {authError ? (
          <div className="border border-clay/25 bg-clay/10 px-4 py-3 text-sm leading-7 text-ink">
            <div className="font-semibold">Authorization error</div>
            <div className="mt-1">{authError}</div>
          </div>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-[1.02fr_0.98fr]">
          <div className="space-y-6">
            <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-clay">Ingestion</p>
                  <h2 className="mt-2 text-2xl font-semibold text-ink">Document loader</h2>
                  <p className="mt-2 max-w-xl text-sm leading-7 text-ink/70">
                    Upload text or paste notes into the workspace, then send them to the backend for registration,
                    chunking, and Chroma indexing.
                  </p>
                </div>
                <div className="rounded-full border border-ink/10 bg-paper px-3 py-1 text-xs font-semibold text-ink/65">
                  {documentId ? documentId : "No document indexed yet"}
                </div>
              </div>

              <div className="mt-5 space-y-4">
                <label className="block">
                  <span className="mb-2 block text-sm font-semibold text-ink">Document title</span>
                  <input
                    value={documentTitle}
                    onChange={(event) => setDocumentTitle(event.target.value)}
                    placeholder="Optional title for the ingested text"
                    className="w-full border border-ink/15 bg-white px-4 py-3 text-sm text-ink outline-none transition placeholder:text-ink/40 focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
                  />
                </label>

                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-ink">Upload source text</p>
                    <p className="text-sm text-ink/60">
                      Accepts plain text, markdown, or any file that can be read as UTF-8 text.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="border border-ink/15 bg-paper px-3 py-2 text-sm font-semibold text-ink transition hover:border-tide/35 hover:bg-white"
                  >
                    Choose file
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".txt,.md,.markdown,.json,.csv,.log,text/plain"
                    onChange={(event) => void handleFileChange(event.target.files?.[0] ?? null)}
                    className="hidden"
                  />
                </div>

                <div className="rounded-2xl border border-dashed border-ink/15 bg-paper/70 p-4">
                  <textarea
                    value={documentText}
                    onChange={(event) => setDocumentText(event.target.value)}
                    rows={12}
                    placeholder="Paste the text you want to ingest here."
                    className="w-full resize-none border-0 bg-transparent text-sm leading-7 text-ink outline-none placeholder:text-ink/40"
                  />
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-ink/55">
                  <span>{documentFileName ? `Loaded file: ${documentFileName}` : "No file selected"}</span>
                  <span>{documentText.length.toLocaleString()} characters</span>
                </div>

                {ingestError ? (
                  <div className="border border-clay/25 bg-clay/10 px-4 py-3 text-sm leading-7 text-ink">
                    {ingestError}
                  </div>
                ) : null}

                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => void handleIngest(false)}
                    disabled={ingestLoading || !canInteract || !documentText.trim()}
                    className="border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-tide/90 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {ingestLoading ? "Indexing..." : "Ingest into Chroma"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleIngest(true)}
                    disabled={ingestLoading || !canInteract || !documentId}
                    className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-ink/25 hover:bg-paper disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {ingestLoading ? "Reindexing..." : "Reindex current document"}
                  </button>
                  <button
                    type="button"
                    onClick={resetDocument}
                    className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-ink/25 hover:bg-paper"
                  >
                    Clear document
                  </button>
                </div>
              </div>
            </section>

            {latestIngestion ? (
              <IngestionStatusCard document={latestIngestion.document} ingestion={latestIngestion.ingestion} />
            ) : null}

            <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-clay">Query</p>
                  <h2 className="mt-2 text-2xl font-semibold text-ink">Ask the knowledge base</h2>
                  <p className="mt-2 max-w-xl text-sm leading-7 text-ink/70">
                    The backend retrieves relevant chunks from the selected collection, assembles context, and sends
                    it to DeepSeek with citation-friendly instructions.
                  </p>
                </div>
                <div className="rounded-full border border-ink/10 bg-paper px-3 py-1 text-xs font-semibold text-ink/65">
                  {chunkCount !== null ? `${chunkCount} chunks indexed` : "Awaiting indexed content"}
                </div>
              </div>

              <div className="mt-5 space-y-4">
                <label className="block">
                  <span className="mb-2 block text-sm font-semibold text-ink">Question</span>
                  <textarea
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    rows={5}
                    placeholder="Ask about the text you ingested or any other content already stored in the collection."
                    className="w-full resize-none border border-ink/15 bg-white px-4 py-3 text-sm leading-7 text-ink outline-none transition placeholder:text-ink/40 focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
                  />
                </label>

                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="block">
                    <span className="mb-2 block text-sm font-semibold text-ink">Collection</span>
                    <input
                      value={collection}
                      onChange={(event) => setCollection(event.target.value)}
                      placeholder={defaultCollection}
                      className="w-full border border-ink/15 bg-white px-4 py-3 text-sm text-ink outline-none transition placeholder:text-ink/40 focus:border-tide/50 focus:ring-2 focus:ring-tide/10"
                    />
                    <span className="mt-2 block text-xs leading-5 text-ink/55">
                      Ingest writes to the configured default collection. This field controls which collection the
                      query endpoint searches.
                    </span>
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
                </div>

                <div className="flex flex-wrap gap-2">
                  {sampleQuestions.map((sampleQuestion) => (
                    <button
                      key={sampleQuestion}
                      type="button"
                      onClick={() => applySampleQuestion(sampleQuestion)}
                      className="border border-ink/10 bg-paper px-3 py-2 text-left text-sm leading-6 text-ink transition hover:border-tide/35 hover:bg-white"
                    >
                      {sampleQuestion}
                    </button>
                  ))}
                </div>

                {queryError ? (
                  <div className="border border-clay/25 bg-clay/10 px-4 py-3 text-sm leading-7 text-ink">
                    {queryError}
                  </div>
                ) : null}

                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => void handleQuery()}
                    disabled={queryLoading || !canInteract}
                    className="border border-tide/40 bg-ink px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-ink/90 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {queryLoading ? "Searching..." : "Ask question"}
                  </button>
                  <button
                    type="button"
                    onClick={resetAnswer}
                    className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-ink/25 hover:bg-paper"
                  >
                    Clear answer
                  </button>
                </div>
              </div>
            </section>
          </div>

          <aside className="space-y-6">
            <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-clay">Answer</p>
                  <h2 className="mt-2 text-2xl font-semibold text-ink">DeepSeek response</h2>
                </div>
                <div className="rounded-full border border-tide/20 bg-tide/10 px-3 py-1 text-xs font-semibold text-tide">
                  {sources.length ? `${sources.length} sources` : "No sources yet"}
                </div>
              </div>

              <div className="mt-5 min-h-[14rem] rounded-2xl border border-ink/10 bg-paper/80 p-4">
                {answer ? (
                  <p className="whitespace-pre-wrap text-sm leading-8 text-ink">{answer}</p>
                ) : (
                  <div className="flex h-full min-h-[12rem] items-center justify-center text-center">
                    <p className="max-w-sm text-sm leading-7 text-ink/55">
                      Your answer will appear here after a query. The UI keeps retrieval sources visible so you can
                      inspect what the model used.
                    </p>
                  </div>
                )}
              </div>
            </section>

            <section className="border border-ink/10 bg-white/72 p-5 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-clay">Sources</p>
                  <h2 className="mt-2 text-2xl font-semibold text-ink">Citations and chunks</h2>
                </div>
                <div className="rounded-full border border-ink/10 bg-paper px-3 py-1 text-xs font-semibold text-ink/65">
                  {collection || defaultCollection}
                </div>
              </div>

              <div className="mt-5">
                {sources.length ? (
                  <ul className="space-y-3">
                    {sources.map((source, index) => (
                      <SourceCard key={`${source.doc_id}-${source.chunk_id}`} source={source} index={index} />
                    ))}
                  </ul>
                ) : (
                  <div className="rounded-2xl border border-dashed border-ink/15 bg-paper/70 p-5 text-sm leading-7 text-ink/60">
                    No citations yet. Run a query to show the supporting chunks returned by the retrieval layer.
                  </div>
                )}
              </div>
            </section>
          </aside>
        </div>
      </section>
    </AuthGate>
  );
}
