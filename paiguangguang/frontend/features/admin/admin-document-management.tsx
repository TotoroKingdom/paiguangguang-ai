"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AuthGate } from "@/components/auth-gate";
import { ApiError } from "@/lib/api";
import {
  deleteAdminDocument,
  getAdminDocument,
  listAdminDocuments,
  listAdminIngestionJobs,
  reindexAdminDocument,
} from "@/lib/admin";
import { AdminDataTable, type AdminDataTableColumn } from "@/features/admin/admin-data-table";
import { AdminPagination } from "@/features/admin/admin-pagination";
import type { AdminDocumentData, AdminIngestionJobData } from "@/types/admin";

type PageState = "loading" | "ready" | "empty" | "forbidden" | "error";
type DetailState = "idle" | "loading" | "ready" | "error";

type ChunkPreview = {
  chunk_index: number;
  start_char: number;
  end_char: number;
};

function formatDateTime(value: string | null) {
  if (!value) {
    return "Unknown";
  }
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatCount(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function buildChunkPreview(document: AdminDocumentData | null, job: AdminIngestionJobData | null) {
  if (!document || !job) {
    return [];
  }

  const chunkSize = Math.max(job.chunk_size ?? 800, 1);
  const overlap = Math.min(Math.max(job.chunk_overlap ?? 120, 0), chunkSize - 1);
  const totalLength = Math.max(document.text_length, 0);
  const previews: ChunkPreview[] = [];

  let start = 0;
  let index = 0;

  while (start < totalLength && index < 12) {
    const end = Math.min(totalLength, start + chunkSize);
    previews.push({
      chunk_index: index,
      start_char: start,
      end_char: end,
    });
    if (end >= totalLength) {
      break;
    }
    const nextStart = end - overlap;
    start = nextStart > start ? nextStart : start + 1;
    index += 1;
  }

  return previews;
}

function statusTone(status: string) {
  if (["indexed", "completed", "active"].includes(status)) {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (["failed", "deleted", "inactive"].includes(status)) {
    return "border-clay/25 bg-clay/10 text-ink";
  }
  return "border-brass/25 bg-brass/10 text-ink";
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1">
      <dt className="text-xs font-semibold uppercase tracking-wide text-clay">{label}</dt>
      <dd className="text-sm leading-6 text-ink">{value}</dd>
    </div>
  );
}

function StatePill({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-2">
      <span className="text-xs font-semibold uppercase tracking-wide text-clay">{label}</span>
      <span className={`inline-flex w-fit border px-3 py-1 text-xs font-semibold ${statusTone(value)}`}>{value}</span>
    </div>
  );
}

export function AdminDocumentManagement() {
  const [pageState, setPageState] = useState<PageState>("loading");
  const [detailState, setDetailState] = useState<DetailState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [documents, setDocuments] = useState<AdminDocumentData[]>([]);
  const [jobs, setJobs] = useState<AdminIngestionJobData[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<AdminDocumentData | null>(null);
  const [mutationState, setMutationState] = useState<{ action: "delete" | "reindex" | null; docId: string | null }>({
    action: null,
    docId: null,
  });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [sortBy, setSortBy] = useState("updated_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [total, setTotal] = useState(0);

  async function loadData(preferredDocumentId?: string | null) {
    setPageState("loading");
    setErrorMessage(null);

    try {
      const [nextDocuments, nextJobs] = await Promise.all([
        listAdminDocuments({
          page,
          pageSize,
          sortBy,
          sortOrder,
        }),
        listAdminIngestionJobs(),
      ]);
      setDocuments(nextDocuments);
      setJobs(nextJobs);
      setTotal(nextDocuments.total);
      setPage(nextDocuments.page);
      setPageSize(nextDocuments.page_size);

      const fallbackId =
        preferredDocumentId && nextDocuments.some((document) => document.doc_id === preferredDocumentId)
          ? preferredDocumentId
          : nextDocuments[0]?.doc_id ?? null;

      setSelectedDocumentId(fallbackId);
      setPageState(nextDocuments.length === 0 ? "empty" : "ready");
    } catch (caughtError) {
      const message = caughtError instanceof ApiError ? caughtError.message : "Unable to load admin documents.";
      setErrorMessage(message);
      setPageState(caughtError instanceof ApiError && caughtError.status === 403 ? "forbidden" : "error");
    }
  }

  useEffect(() => {
    void loadData();
  }, [page, pageSize, sortBy, sortOrder]);

  useEffect(() => {
    if (!selectedDocumentId) {
      setSelectedDocument(null);
      setDetailState("idle");
      return;
    }

    const currentDocumentId = selectedDocumentId;
    let cancelled = false;

    async function loadSelectedDocument() {
      setDetailState("loading");
      try {
        const document = await getAdminDocument(currentDocumentId);
        if (cancelled) {
          return;
        }
        setSelectedDocument(document);
        setDetailState("ready");
      } catch (caughtError) {
        if (cancelled) {
          return;
        }
        setSelectedDocument(null);
        setDetailState("error");
        setErrorMessage(caughtError instanceof ApiError ? caughtError.message : "Unable to load document details.");
      }
    }

    void loadSelectedDocument();

    return () => {
      cancelled = true;
    };
  }, [selectedDocumentId]);

  const visibleDocuments = documents;
  const selectedDocumentSummary =
    selectedDocument ?? visibleDocuments.find((document) => document.doc_id === selectedDocumentId) ?? null;
  const selectedJobs = selectedDocumentId ? jobs.filter((job) => job.document_id === selectedDocumentId) : [];
  const selectedJob = selectedJobs[0] ?? null;
  const chunkPreview = buildChunkPreview(selectedDocumentSummary, selectedJob);
  const documentColumns: AdminDataTableColumn<AdminDocumentData>[] = [
    {
      key: "title",
      header: "Document",
      sortable: true,
      sortKey: "title",
      render: (document) => (
        <div className="grid gap-1">
          <span className="font-semibold text-ink">{document.title ?? document.doc_id}</span>
          <span className="text-xs text-ink/55">{document.doc_id}</span>
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      sortable: true,
      sortKey: "status",
      render: (document) => (
        <span className={`border px-2.5 py-1 text-xs font-semibold ${statusTone(document.status)}`}>{document.status}</span>
      ),
    },
    {
      key: "owner",
      header: "Owner",
      sortable: true,
      sortKey: "owner_user_id",
      render: (document) => <span className="text-sm text-ink/70">{document.owner_user_id ?? "Unassigned"}</span>,
    },
    {
      key: "workspace",
      header: "Workspace",
      sortable: true,
      sortKey: "workspace_id",
      render: (document) => <span className="text-sm text-ink/70">{document.workspace_id ?? "Unassigned"}</span>,
    },
    {
      key: "updated_at",
      header: "Updated",
      sortable: true,
      sortKey: "updated_at",
      render: (document) => <span className="text-sm text-ink/70">{formatDateTime(document.updated_at)}</span>,
    },
  ];
  const jobColumns: AdminDataTableColumn<AdminIngestionJobData>[] = [
    {
      key: "job_id",
      header: "Job",
      render: (job) => <span className="font-semibold text-ink">{job.job_id}</span>,
    },
    {
      key: "status",
      header: "Status",
      render: (job) => (
        <span className={`border px-2.5 py-1 text-xs font-semibold ${statusTone(job.status)}`}>{job.status}</span>
      ),
    },
    {
      key: "retry_count",
      header: "Retries",
      render: (job) => <span className="text-sm text-ink/70">{formatCount(job.retry_count)}</span>,
    },
    {
      key: "updated_at",
      header: "Updated",
      render: (job) => <span className="text-sm text-ink/70">{formatDateTime(job.updated_at)}</span>,
    },
  ];

  function handleDocumentSort(nextSortBy: string) {
    setPage(1);
    if (sortBy === nextSortBy) {
      setSortOrder((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortBy(nextSortBy);
    setSortOrder(nextSortBy === "updated_at" ? "desc" : "asc");
  }

  function handleDocumentPageChange(nextPage: number) {
    setPage(nextPage);
  }

  function handleDocumentPageSizeChange(nextPageSize: number) {
    setPage(1);
    setPageSize(nextPageSize);
  }

  async function handleReload() {
    await loadData(selectedDocumentId);
  }

  async function handleDelete(documentId: string) {
    const confirmed = window.confirm("Delete this document record?");
    if (!confirmed) {
      return;
    }

    setMutationState({ action: "delete", docId: documentId });
    setErrorMessage(null);
    try {
      await deleteAdminDocument(documentId);
      await loadData(documentId);
    } catch (caughtError) {
      setErrorMessage(caughtError instanceof ApiError ? caughtError.message : "Unable to delete the document.");
    } finally {
      setMutationState({ action: null, docId: null });
    }
  }

  async function handleReindex(documentId: string) {
    setMutationState({ action: "reindex", docId: documentId });
    setErrorMessage(null);
    try {
      await reindexAdminDocument(documentId);
      await loadData(documentId);
    } catch (caughtError) {
      setErrorMessage(caughtError instanceof ApiError ? caughtError.message : "Unable to reindex the document.");
    } finally {
      setMutationState({ action: null, docId: null });
    }
  }

  return (
    <AuthGate
      title="Admin Document Management"
      description="Inspect document lifecycle state, review ingestion jobs, and trigger delete or reindex actions."
    >
      <section className="grid gap-5 lg:grid-cols-[minmax(0,0.38fr)_minmax(0,0.62fr)]">
        <div className="space-y-4">
          <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-clay">Documents</p>
                <h2 className="mt-2 text-2xl font-semibold text-ink">Lifecycle records</h2>
              </div>
              <button
                type="button"
                onClick={() => void handleReload()}
                className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:border-tide/30 hover:bg-paper"
              >
                Refresh
              </button>
            </div>

            <div className="mt-4 text-sm leading-7 text-ink/70">
              Status, owner, workspace, permission scope, update time, and failure reasons are shown for each record.
            </div>

            <div className="mt-5 space-y-3">
              <AdminDataTable
                columns={documentColumns}
                rows={visibleDocuments}
                state={pageState}
                loadingMessage="Loading documents..."
                emptyMessage="No documents are registered yet."
                forbiddenMessage="You do not have permission to view document management. This page requires the document admin scope."
                errorMessage={errorMessage}
                getRowKey={(document) => document.doc_id}
                activeRowKey={selectedDocumentId}
                onRowClick={(document) => setSelectedDocumentId(document.doc_id)}
                sortBy={sortBy}
                sortOrder={sortOrder}
                onSort={handleDocumentSort}
              />
              {pageState === "ready" ? (
                <AdminPagination
                  page={page}
                  pageSize={pageSize}
                  total={total}
                  onPageChange={handleDocumentPageChange}
                  onPageSizeChange={handleDocumentPageSizeChange}
                />
              ) : null}
            </div>
          </div>

          <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-wide text-clay">Summary</p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div className="border border-ink/10 bg-paper/75 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-clay">Documents</div>
                <div className="mt-2 text-2xl font-semibold text-ink">{formatCount(total)}</div>
              </div>
              <div className="border border-ink/10 bg-paper/75 p-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-clay">Ingestion jobs</div>
                <div className="mt-2 text-2xl font-semibold text-ink">{formatCount(jobs.length)}</div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-clay">Document detail</p>
                <h2 className="mt-2 text-2xl font-semibold text-ink">
                  {selectedDocumentSummary?.title ?? selectedDocumentSummary?.doc_id ?? "Select a document"}
                </h2>
                <p className="mt-2 max-w-2xl text-sm leading-7 text-ink/70">
                  Source metadata, lifecycle states, and ingestion jobs are presented together for admin inspection.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {selectedDocumentSummary ? (
                  <>
                    <button
                      type="button"
                      onClick={() => void handleReindex(selectedDocumentSummary.doc_id)}
                      disabled={mutationState.docId === selectedDocumentSummary.doc_id}
                      className="border border-tide/40 bg-tide px-3 py-2 text-sm font-semibold text-paper transition hover:bg-tide/90 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {mutationState.action === "reindex" && mutationState.docId === selectedDocumentSummary.doc_id
                        ? "Reindexing..."
                        : "Reindex"}
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDelete(selectedDocumentSummary.doc_id)}
                      disabled={mutationState.docId === selectedDocumentSummary.doc_id}
                      className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:border-clay/30 hover:bg-paper disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {mutationState.action === "delete" && mutationState.docId === selectedDocumentSummary.doc_id
                        ? "Deleting..."
                        : "Delete"}
                    </button>
                  </>
                ) : null}
              </div>
            </div>

            {detailState === "loading" ? (
              <div className="mt-5 animate-pulse border border-dashed border-ink/15 bg-paper/70 p-6 text-sm text-ink/55">
                Loading document details...
              </div>
            ) : null}

            {detailState === "error" ? (
              <div className="mt-5 border border-clay/25 bg-clay/10 p-4 text-sm leading-7 text-ink">
                {errorMessage ?? "Unable to load the selected document."}
              </div>
            ) : null}

            {selectedDocumentSummary ? (
              <dl className="mt-5 grid gap-4 sm:grid-cols-2">
                <MetaRow label="Document ID" value={selectedDocumentSummary.doc_id} />
                <MetaRow label="Content hash" value={selectedDocumentSummary.content_hash} />
                <MetaRow label="Owner user" value={selectedDocumentSummary.owner_user_id ?? "Unassigned"} />
                <MetaRow label="Workspace" value={selectedDocumentSummary.workspace_id ?? "Unassigned"} />
                <MetaRow label="Permission scope" value={selectedDocumentSummary.permission_scope ?? "Unscoped"} />
                <MetaRow label="Text length" value={`${formatCount(selectedDocumentSummary.text_length)} characters`} />
                <StatePill label="Status" value={selectedDocumentSummary.status} />
                <StatePill label="Parse" value={selectedDocumentSummary.parse_status} />
                <StatePill label="Chunk" value={selectedDocumentSummary.chunk_status} />
                <StatePill label="Embedding" value={selectedDocumentSummary.embedding_status} />
                <StatePill label="Index" value={selectedDocumentSummary.index_status} />
                <MetaRow label="Updated" value={formatDateTime(selectedDocumentSummary.updated_at)} />
              </dl>
            ) : null}

            {selectedDocumentSummary?.error_message ? (
              <div className="mt-5 border border-clay/20 bg-clay/10 p-4 text-sm leading-7 text-ink">
                Failure reason: {selectedDocumentSummary.error_message}
              </div>
            ) : null}
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-wide text-clay">Ingestion jobs</p>
              <div className="mt-4">
                <AdminDataTable
                  columns={jobColumns}
                  rows={selectedJobs}
                  state={selectedJobs.length === 0 ? "empty" : "ready"}
                  loadingMessage="Loading ingestion jobs..."
                  emptyMessage="No ingestion jobs found for the selected document."
                  forbiddenMessage="You do not have permission to view document jobs."
                  errorMessage={null}
                  getRowKey={(job) => job.job_id}
                />
              </div>
            </div>

            <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-wide text-clay">Chunk metadata</p>
              <p className="mt-2 text-sm leading-7 text-ink/70">
                The backend admin API does not expose chunk text directly, so this section previews chunk boundaries and
                metadata derived from the selected document and its latest ingestion settings.
              </p>
              <div className="mt-4">
                {!selectedDocumentSummary ? (
                  <div className="border border-ink/10 bg-paper/70 p-4 text-sm leading-7 text-ink/70">
                    Choose a document to inspect its chunk layout.
                  </div>
                ) : chunkPreview.length === 0 ? (
                  <div className="border border-ink/10 bg-paper/70 p-4 text-sm leading-7 text-ink/70">
                    No chunk preview available for the selected document.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {chunkPreview.map((chunk) => (
                      <div key={chunk.chunk_index} className="border border-ink/10 bg-paper/75 p-3 text-sm leading-6 text-ink">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-semibold">Chunk {chunk.chunk_index}</span>
                          <span className="text-xs font-medium uppercase tracking-wide text-clay">
                            chars {formatCount(chunk.start_char)} to {formatCount(chunk.end_char)}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-ink/60">
                          Chunk layout preview based on text length and the latest chunk configuration.
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-clay">Navigation</p>
            <p className="mt-1 text-sm leading-6 text-ink/70">Return to the Knowledge Agent or the home page when needed.</p>
          </div>
          <div className="flex flex-wrap gap-3">
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
      </div>
    </AuthGate>
  );
}
