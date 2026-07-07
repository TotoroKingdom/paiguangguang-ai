"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { AuthGate } from "@/components/auth-gate";
import { ApiError } from "@/lib/api";
import {
  clearAdminEntityDetailCache,
  clearAdminEntityListCache,
  deleteAdminDocument,
  getAdminDocument,
  listAdminDocuments,
  listAdminIngestionJobs,
  reindexAdminDocument,
  uploadAdminDocument,
} from "@/lib/admin";
import { AdminDataTable, type AdminDataTableColumn } from "@/features/admin/admin-data-table";
import { AdminPagination } from "@/features/admin/admin-pagination";
import type { AdminDocumentData, AdminIngestionJobData } from "@/types/admin";

type PageState = "loading" | "ready" | "empty" | "forbidden" | "error";
type DetailState = "idle" | "loading" | "ready" | "error";
type UploadState = "idle" | "uploading";

type ChunkPreview = {
  chunk_index: number;
  start_char: number;
  end_char: number;
};

type UploadFormState = {
  title: string;
  ownerUserId: string;
  workspaceId: string;
  permissionScope: string;
};

const DEFAULT_UPLOAD_FORM: UploadFormState = {
  title: "",
  ownerUserId: "",
  workspaceId: "",
  permissionScope: "workspace",
};

function formatDateTime(value: string | null) {
  if (!value) {
    return "未知";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatCount(value: number) {
  return new Intl.NumberFormat("zh-CN").format(value);
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
  if (["indexed", "completed", "active", "registered"].includes(status)) {
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
      <dt className="text-xs font-semibold tracking-wide text-clay">{label}</dt>
      <dd className="text-sm leading-6 text-ink">{value}</dd>
    </div>
  );
}

function StatePill({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-2">
      <span className="text-xs font-semibold tracking-wide text-clay">{label}</span>
      <span className={`inline-flex w-fit border px-3 py-1 text-xs font-semibold ${statusTone(value)}`}>{value}</span>
    </div>
  );
}

export function AdminDocumentManagement() {
  const [pageState, setPageState] = useState<PageState>("loading");
  const [detailState, setDetailState] = useState<DetailState>("idle");
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
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
  const [reloadToken, setReloadToken] = useState(0);
  const [uploadForm, setUploadForm] = useState<UploadFormState>(DEFAULT_UPLOAD_FORM);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadFileKey, setUploadFileKey] = useState(0);

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
      const message = caughtError instanceof ApiError ? caughtError.message : "无法加载文档列表。";
      setErrorMessage(message);
      setPageState(caughtError instanceof ApiError && caughtError.status === 403 ? "forbidden" : "error");
    }
  }

  useEffect(() => {
    void loadData();
  }, [page, pageSize, sortBy, sortOrder, reloadToken]);

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
        setErrorMessage(caughtError instanceof ApiError ? caughtError.message : "无法加载当前文档详情。");
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
      key: "original_filename",
      header: "原始文件名",
      sortable: true,
      sortKey: "original_filename",
      render: (document) => (
        <div className="grid gap-1">
          <span className="font-semibold text-ink">{document.original_filename ?? "未提供"}</span>
          <span className="text-xs text-ink/55">{document.doc_id}</span>
        </div>
      ),
    },
    {
      key: "title",
      header: "标题",
      sortable: true,
      sortKey: "title",
      render: (document) => <span className="font-semibold text-ink">{document.title ?? "未命名文档"}</span>,
    },
    {
      key: "status",
      header: "状态",
      sortable: true,
      sortKey: "status",
      render: (document) => (
        <span className={`border px-2.5 py-1 text-xs font-semibold ${statusTone(document.status)}`}>{document.status}</span>
      ),
    },
    {
      key: "owner",
      header: "负责人",
      sortable: true,
      sortKey: "owner_user_id",
      render: (document) => <span className="text-sm text-ink/70">{document.owner_user_id ?? "未分配"}</span>,
    },
    {
      key: "workspace",
      header: "工作区",
      sortable: true,
      sortKey: "workspace_id",
      render: (document) => <span className="text-sm text-ink/70">{document.workspace_id ?? "未分配"}</span>,
    },
    {
      key: "updated_at",
      header: "更新时间",
      sortable: true,
      sortKey: "updated_at",
      render: (document) => <span className="text-sm text-ink/70">{formatDateTime(document.updated_at)}</span>,
    },
  ];
  const jobColumns: AdminDataTableColumn<AdminIngestionJobData>[] = [
    {
      key: "job_id",
      header: "任务",
      render: (job) => <span className="font-semibold text-ink">{job.job_id}</span>,
    },
    {
      key: "status",
      header: "状态",
      render: (job) => (
        <span className={`border px-2.5 py-1 text-xs font-semibold ${statusTone(job.status)}`}>{job.status}</span>
      ),
    },
    {
      key: "retry_count",
      header: "重试",
      render: (job) => <span className="text-sm text-ink/70">{formatCount(job.retry_count)}</span>,
    },
    {
      key: "updated_at",
      header: "更新时间",
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

  async function handleClearDocumentListCache() {
    await clearAdminEntityListCache({
      entity: "documents",
      page,
      pageSize,
      sortBy,
      sortOrder,
    });
    await loadData(selectedDocumentId);
  }

  async function handleClearDocumentDetailCache(documentId: string) {
    await clearAdminEntityDetailCache({
      entity: "documents",
      entityId: documentId,
    });
    await loadData(documentId);
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUploadError(null);

    if (!uploadFile) {
      setUploadError("请选择要上传的文件。");
      return;
    }

    setUploadState("uploading");
    try {
      const formData = new FormData();
      formData.set("file", uploadFile);
      if (uploadForm.title.trim()) {
        formData.set("title", uploadForm.title.trim());
      }
      if (uploadForm.ownerUserId.trim()) {
        formData.set("owner_user_id", uploadForm.ownerUserId.trim());
      }
      if (uploadForm.workspaceId.trim()) {
        formData.set("workspace_id", uploadForm.workspaceId.trim());
      }
      if (uploadForm.permissionScope.trim()) {
        formData.set("permission_scope", uploadForm.permissionScope.trim());
      }

      const created = await uploadAdminDocument(formData);
      setUploadForm(DEFAULT_UPLOAD_FORM);
      setUploadFile(null);
      setUploadFileKey((current) => current + 1);
      setSelectedDocumentId(created.doc_id);
      setPage(1);
      setReloadToken((current) => current + 1);
    } catch (caughtError) {
      setUploadError(caughtError instanceof ApiError ? caughtError.message : "上传文档失败。");
    } finally {
      setUploadState("idle");
    }
  }

  async function handleDelete(documentId: string) {
    const confirmed = window.confirm("确定要永久删除这份文档吗？");
    if (!confirmed) {
      return;
    }

    setMutationState({ action: "delete", docId: documentId });
    setErrorMessage(null);
    try {
      await deleteAdminDocument(documentId);
      await loadData(documentId);
    } catch (caughtError) {
      setErrorMessage(caughtError instanceof ApiError ? caughtError.message : "无法删除该文档。");
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
      setErrorMessage(caughtError instanceof ApiError ? caughtError.message : "无法重新入库该文档。");
    } finally {
      setMutationState({ action: null, docId: null });
    }
  }

  return (
    <AuthGate
      title="文档管理"
      description="上传文档、查看原始文件名、检查入库状态，并执行删除或重新入库。"
    >
      <section className="space-y-6">
        <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-clay">上传文档</p>
              <h2 className="mt-2 text-2xl font-semibold text-ink">导入新的知识文档</h2>
              <p className="mt-2 max-w-3xl text-sm leading-7 text-ink/70">
                支持 `txt`、`md`、`markdown` 和 `pdf`。文件名会保留为原始文件名，标题可以单独填写。
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => void handleReload()}
                className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:border-tide/30 hover:bg-paper"
              >
                刷新
              </button>
            </div>
          </div>

          <form className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]" onSubmit={handleUpload}>
            <div className="grid gap-4">
              <label className="grid gap-2 text-sm font-medium text-ink">
                <span>选择文件</span>
                <input
                  key={uploadFileKey}
                  type="file"
                  accept=".txt,.md,.markdown,.pdf"
                  onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                  className="border border-ink/15 bg-white px-3 py-2 text-sm text-ink file:mr-4 file:border-0 file:bg-tide file:px-3 file:py-2 file:text-sm file:font-semibold file:text-paper"
                />
              </label>
              <label className="grid gap-2 text-sm font-medium text-ink">
                <span>标题</span>
                <input
                  type="text"
                  value={uploadForm.title}
                  onChange={(event) => setUploadForm((current) => ({ ...current, title: event.target.value }))}
                  placeholder="可留空，默认使用文件名"
                  className="border border-ink/15 bg-white px-3 py-2 text-sm text-ink outline-none placeholder:text-ink/35 focus:border-tide/50"
                />
              </label>
            </div>

            <div className="grid gap-4">
              <label className="grid gap-2 text-sm font-medium text-ink">
                <span>负责人用户 ID</span>
                <input
                  type="text"
                  value={uploadForm.ownerUserId}
                  onChange={(event) => setUploadForm((current) => ({ ...current, ownerUserId: event.target.value }))}
                  placeholder="可选"
                  className="border border-ink/15 bg-white px-3 py-2 text-sm text-ink outline-none placeholder:text-ink/35 focus:border-tide/50"
                />
              </label>
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="grid gap-2 text-sm font-medium text-ink">
                  <span>工作区 ID</span>
                  <input
                    type="text"
                    value={uploadForm.workspaceId}
                    onChange={(event) => setUploadForm((current) => ({ ...current, workspaceId: event.target.value }))}
                    placeholder="可选"
                    className="border border-ink/15 bg-white px-3 py-2 text-sm text-ink outline-none placeholder:text-ink/35 focus:border-tide/50"
                  />
                </label>
                <label className="grid gap-2 text-sm font-medium text-ink">
                  <span>权限范围</span>
                  <select
                    value={uploadForm.permissionScope}
                    onChange={(event) =>
                      setUploadForm((current) => ({ ...current, permissionScope: event.target.value }))
                    }
                    className="border border-ink/15 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-tide/50"
                  >
                    <option value="workspace">workspace</option>
                    <option value="admin">admin</option>
                  </select>
                </label>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 lg:col-span-2">
              <div className="text-sm leading-6 text-ink/70">
                上传后会自动创建文档记录，并在成功时刷新到第一页以便立即查看。
              </div>
              <button
                type="submit"
                disabled={uploadState === "uploading"}
                className="border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-tide/90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {uploadState === "uploading" ? "上传中..." : "上传文档"}
              </button>
            </div>

            {uploadError ? (
              <div className="rounded-none border border-clay/25 bg-clay/10 px-4 py-3 text-sm leading-7 text-ink lg:col-span-2">
                {uploadError}
              </div>
            ) : null}
          </form>
        </div>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,0.38fr)_minmax(0,0.62fr)]">
          <div className="space-y-4">
            <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-clay">文档列表</p>
                  <h2 className="mt-2 text-2xl font-semibold text-ink">文档与入库状态</h2>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => void handleClearDocumentListCache()}
                    className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:border-tide/30 hover:bg-paper"
                    title="清理当前列表 Redis 缓存"
                  >
                    Redis 清理
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleReload()}
                    className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:border-tide/30 hover:bg-paper"
                  >
                    刷新
                  </button>
                </div>
              </div>

              <div className="mt-4 text-sm leading-7 text-ink/70">
                一览原始文件名、显示标题、负责人、工作区、更新时间以及失败原因。
              </div>

              <div className="mt-5 space-y-3">
                <AdminDataTable
                  columns={documentColumns}
                  rows={visibleDocuments}
                  state={pageState}
                  loadingMessage="正在加载文档..."
                  emptyMessage="当前还没有文档。"
                  forbiddenMessage="你没有查看文档管理的权限。"
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
              <p className="text-sm font-semibold uppercase tracking-wide text-clay">统计概览</p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div className="border border-ink/10 bg-paper/75 p-4">
                  <div className="text-xs font-semibold uppercase tracking-wide text-clay">文档数</div>
                  <div className="mt-2 text-2xl font-semibold text-ink">{formatCount(total)}</div>
                </div>
                <div className="border border-ink/10 bg-paper/75 p-4">
                  <div className="text-xs font-semibold uppercase tracking-wide text-clay">入库任务</div>
                  <div className="mt-2 text-2xl font-semibold text-ink">{formatCount(jobs.length)}</div>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-wide text-clay">文档详情</p>
                  <h2 className="mt-2 text-2xl font-semibold text-ink">
                    {selectedDocumentSummary?.title ?? selectedDocumentSummary?.original_filename ?? "请选择文档"}
                  </h2>
                  <p className="mt-2 max-w-2xl text-sm leading-7 text-ink/70">
                    原始文件名、生命周期状态和入库任务会在这里一起展示。
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {selectedDocumentSummary ? (
                    <>
                      <button
                        type="button"
                        onClick={() => void handleClearDocumentDetailCache(selectedDocumentSummary.doc_id)}
                        className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:border-tide/30 hover:bg-paper"
                        title="清理当前文档 Redis 缓存"
                      >
                        Redis
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleReindex(selectedDocumentSummary.doc_id)}
                        disabled={mutationState.docId === selectedDocumentSummary.doc_id}
                        className="border border-tide/40 bg-tide px-3 py-2 text-sm font-semibold text-paper transition hover:bg-tide/90 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {mutationState.action === "reindex" && mutationState.docId === selectedDocumentSummary.doc_id
                          ? "重新入库中..."
                          : "重新入库"}
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleDelete(selectedDocumentSummary.doc_id)}
                        disabled={mutationState.docId === selectedDocumentSummary.doc_id}
                        className="border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:border-clay/30 hover:bg-paper disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {mutationState.action === "delete" && mutationState.docId === selectedDocumentSummary.doc_id
                          ? "删除中..."
                          : "永久删除"}
                      </button>
                    </>
                  ) : null}
                </div>
              </div>

              {detailState === "loading" ? (
                <div className="mt-5 animate-pulse border border-dashed border-ink/15 bg-paper/70 p-6 text-sm text-ink/55">
                  正在加载文档详情...
                </div>
              ) : null}

              {detailState === "error" ? (
                <div className="mt-5 border border-clay/25 bg-clay/10 p-4 text-sm leading-7 text-ink">
                  {errorMessage ?? "无法加载当前文档。"}
                </div>
              ) : null}

              {selectedDocumentSummary ? (
                <dl className="mt-5 grid gap-4 sm:grid-cols-2">
                  <MetaRow label="文档 ID" value={selectedDocumentSummary.doc_id} />
                  <MetaRow label="内容哈希" value={selectedDocumentSummary.content_hash} />
                  <MetaRow label="原始文件名" value={selectedDocumentSummary.original_filename ?? "未提供"} />
                  <MetaRow label="负责人" value={selectedDocumentSummary.owner_user_id ?? "未分配"} />
                  <MetaRow label="工作区" value={selectedDocumentSummary.workspace_id ?? "未分配"} />
                  <MetaRow label="权限范围" value={selectedDocumentSummary.permission_scope ?? "未设置"} />
                  <MetaRow label="文本长度" value={`${formatCount(selectedDocumentSummary.text_length)} 字符`} />
                  <StatePill label="状态" value={selectedDocumentSummary.status} />
                  <StatePill label="解析" value={selectedDocumentSummary.parse_status} />
                  <StatePill label="切块" value={selectedDocumentSummary.chunk_status} />
                  <StatePill label="向量化" value={selectedDocumentSummary.embedding_status} />
                  <StatePill label="索引" value={selectedDocumentSummary.index_status} />
                  <MetaRow label="更新时间" value={formatDateTime(selectedDocumentSummary.updated_at)} />
                </dl>
              ) : null}

              {selectedDocumentSummary?.error_message ? (
                <div className="mt-5 border border-clay/20 bg-clay/10 p-4 text-sm leading-7 text-ink">
                  失败原因：{selectedDocumentSummary.error_message}
                </div>
              ) : null}
            </div>

            <div className="grid gap-4 xl:grid-cols-2">
              <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
                <p className="text-sm font-semibold uppercase tracking-wide text-clay">入库任务</p>
                <div className="mt-4">
                  <AdminDataTable
                    columns={jobColumns}
                    rows={selectedJobs}
                    state={selectedJobs.length === 0 ? "empty" : "ready"}
                    loadingMessage="正在加载入库任务..."
                    emptyMessage="当前文档没有入库任务。"
                    forbiddenMessage="你没有查看入库任务的权限。"
                    errorMessage={null}
                    getRowKey={(job) => job.job_id}
                  />
                </div>
              </div>

              <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
                <p className="text-sm font-semibold uppercase tracking-wide text-clay">切块预览</p>
                <p className="mt-2 text-sm leading-7 text-ink/70">
                  后端不会直接返回 chunk 文本，这里根据文档长度和最近一次入库配置预览切块边界。
                </p>
                <div className="mt-4">
                  {!selectedDocumentSummary ? (
                    <div className="border border-ink/10 bg-paper/70 p-4 text-sm leading-7 text-ink/70">
                      请选择一个文档查看切块布局。
                    </div>
                  ) : chunkPreview.length === 0 ? (
                    <div className="border border-ink/10 bg-paper/70 p-4 text-sm leading-7 text-ink/70">
                      当前文档暂无切块预览。
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {chunkPreview.map((chunk) => (
                        <div
                          key={chunk.chunk_index}
                          className="border border-ink/10 bg-paper/75 p-3 text-sm leading-6 text-ink"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="font-semibold">切块 {chunk.chunk_index}</span>
                            <span className="text-xs font-medium uppercase tracking-wide text-clay">
                              字符 {formatCount(chunk.start_char)} 到 {formatCount(chunk.end_char)}
                            </span>
                          </div>
                          <p className="mt-1 text-xs text-ink/60">预览基于文本长度和最近一次切块参数生成。</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="border border-ink/10 bg-white/72 p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wide text-clay">导航</p>
              <p className="mt-1 text-sm leading-6 text-ink/70">需要时可以返回知识问答或首页。</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/agents/knowledge"
                className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-tide/35 hover:bg-paper"
              >
                知识问答
              </Link>
              <Link
                href="/"
                className="border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-tide/35 hover:bg-paper"
              >
                首页
              </Link>
            </div>
          </div>
        </div>
      </section>
    </AuthGate>
  );
}
