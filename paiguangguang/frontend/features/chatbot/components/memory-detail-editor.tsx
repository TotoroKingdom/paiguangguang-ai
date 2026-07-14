"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type { MemoryData, MemoryListStatus, MemoryUpdateRequest } from "../types/memory";

type MemoryDetailEditorProps = {
  memory: MemoryData | null;
  loading: boolean;
  error: string | null;
  saving: boolean;
  deleting: boolean;
  onSave: (memoryId: string, request: MemoryUpdateRequest) => void | Promise<void>;
  onDelete: (memoryId: string) => void | Promise<void>;
};

function formatLocalInputValue(value: string | null) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const offsetMinutes = date.getTimezoneOffset();
  const localDate = new Date(date.getTime() - offsetMinutes * 60_000);
  return localDate.toISOString().slice(0, 16);
}

function parseLocalInputValue(value: string) {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toISOString();
}

export function MemoryDetailEditor({
  memory,
  loading,
  error,
  saving,
  deleting,
  onSave,
  onDelete,
}: MemoryDetailEditorProps) {
  const [content, setContent] = useState("");
  const [status, setStatus] = useState<Extract<MemoryListStatus, "active" | "candidate">>("active");
  const [expiresAt, setExpiresAt] = useState("");

  useEffect(() => {
    if (!memory) {
      setContent("");
      setStatus("active");
      setExpiresAt("");
      return;
    }

    setContent(memory.content);
    setStatus(memory.status === "candidate" || memory.status === "active" ? memory.status : "active");
    setExpiresAt(formatLocalInputValue(memory.expires_at));
  }, [memory]);

  const canEditStatus = memory ? memory.status === "active" || memory.status === "candidate" : false;

  const isDirty = useMemo(() => {
    if (!memory) {
      return false;
    }

    const contentChanged = content !== memory.content;
    const expiresChanged = expiresAt !== formatLocalInputValue(memory.expires_at);
    const statusChanged = canEditStatus ? status !== memory.status : false;
    return contentChanged || expiresChanged || statusChanged;
  }, [canEditStatus, content, expiresAt, memory, status]);

  const handleSave = useCallback(() => {
    if (!memory) {
      return;
    }

    const trimmedContent = content.trim();
    if (!trimmedContent) {
      return;
    }

    const request: MemoryUpdateRequest = {
      content: trimmedContent,
      expires_at: parseLocalInputValue(expiresAt),
    };

    if (canEditStatus) {
      request.status = status;
    }

    void onSave(memory.id, request);
  }, [canEditStatus, content, expiresAt, memory, onSave, status]);

  const handleDelete = useCallback(() => {
    if (!memory) {
      return;
    }

    if (!window.confirm(`Delete memory "${memory.content.slice(0, 40)}"?`)) {
      return;
    }

    void onDelete(memory.id);
  }, [memory, onDelete]);

  const canSave = Boolean(memory) && !loading && !saving && !deleting && content.trim().length > 0 && isDirty;

  if (!memory) {
    return (
      <section className="flex min-h-0 flex-1 flex-col rounded-2xl border border-ink/10 bg-white/80 p-5 shadow-sm">
        <div className="flex h-full min-h-[18rem] flex-1 items-center justify-center rounded-2xl border border-dashed border-ink/15 bg-paper/40 px-6 text-sm leading-7 text-ink/65">
          Select a memory from the list to inspect and edit its content, status, and expiry.
        </div>
      </section>
    );
  }

  return (
    <section className="flex min-h-0 flex-1 flex-col rounded-2xl border border-ink/10 bg-white/80 p-5 shadow-sm">
      <div className="border-b border-ink/10 pb-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Memory detail</p>
            <h2 className="mt-1 text-lg font-semibold text-ink">{memory.memory_type}</h2>
          </div>
          <span className="rounded-full border border-ink/10 bg-paper px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-ink/60">
            {memory.status}
          </span>
        </div>
        <p className="mt-2 text-sm leading-6 text-ink/60">Confidence {memory.confidence.toFixed(2)}</p>
      </div>

      {error ? (
        <p role="alert" className="mt-4 rounded-xl border border-clay/30 bg-clay/10 px-4 py-3 text-sm leading-6 text-ink">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="mt-4 rounded-xl border border-ink/10 bg-paper/50 px-4 py-3 text-sm leading-6 text-ink/60">
          Loading memory detail...
        </p>
      ) : null}

      <div className="mt-4 min-h-0 flex-1 space-y-4">
        <label className="block">
          <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-ink/50">Memory content</span>
          <textarea
            aria-label="Memory content"
            value={content}
            onChange={(event) => setContent(event.target.value)}
            disabled={saving || deleting}
            rows={10}
            className="min-h-[12rem] w-full rounded-2xl border border-ink/15 bg-white px-4 py-3 text-sm leading-7 text-ink outline-none transition placeholder:text-ink/40 focus:border-tide/50 focus:ring-2 focus:ring-tide/10 disabled:cursor-not-allowed disabled:bg-paper"
          />
        </label>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="space-y-4 rounded-2xl border border-ink/10 bg-paper/35 p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-ink/50">Status</p>
              <span className="text-xs text-ink/45">Only active and candidate can be changed</span>
            </div>

            {canEditStatus ? (
              <label className="block">
                <span className="sr-only">Memory status</span>
                <select
                  aria-label="Memory status"
                  value={status}
                  onChange={(event) => setStatus(event.target.value as Extract<MemoryListStatus, "active" | "candidate">)}
                  disabled={saving || deleting}
                  className="w-full rounded-xl border border-ink/15 bg-white px-3 py-2 text-sm text-ink outline-none transition focus:border-tide/50 focus:ring-2 focus:ring-tide/10 disabled:cursor-not-allowed disabled:bg-paper"
                >
                  <option value="candidate">Candidate</option>
                  <option value="active">Active</option>
                </select>
              </label>
            ) : (
              <p className="rounded-xl border border-ink/10 bg-white px-3 py-2 text-sm text-ink/70">
                Status is read-only for {memory.status} memories.
              </p>
            )}

            <label className="block">
              <span className="mb-2 block text-xs font-semibold uppercase tracking-wide text-ink/50">Expires at</span>
              <input
                type="datetime-local"
                value={expiresAt}
                onChange={(event) => setExpiresAt(event.target.value)}
                disabled={saving || deleting}
                className="w-full rounded-xl border border-ink/15 bg-white px-3 py-2 text-sm text-ink outline-none transition focus:border-tide/50 focus:ring-2 focus:ring-tide/10 disabled:cursor-not-allowed disabled:bg-paper"
              />
            </label>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setExpiresAt("")}
                disabled={saving || deleting || expiresAt === ""}
                className="rounded-full border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:border-tide/35 hover:bg-paper disabled:cursor-not-allowed disabled:opacity-60"
              >
                Clear expiry
              </button>
              <button
                type="button"
                onClick={() => {
                  setContent(memory.content);
                  setStatus(memory.status === "candidate" || memory.status === "active" ? memory.status : "active");
                  setExpiresAt(formatLocalInputValue(memory.expires_at));
                }}
                disabled={saving || deleting || !isDirty}
                className="rounded-full border border-ink/15 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:border-tide/35 hover:bg-paper disabled:cursor-not-allowed disabled:opacity-60"
              >
                Reset draft
              </button>
            </div>
          </div>

          <div className="space-y-4 rounded-2xl border border-ink/10 bg-paper/35 p-4">
            <div className="grid gap-2 text-sm text-ink/70">
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs font-semibold uppercase tracking-wide text-ink/50">Conversation</span>
                <span>{memory.conversation_id ?? "Global"}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs font-semibold uppercase tracking-wide text-ink/50">Source messages</span>
                <span>{memory.source_message_ids.length}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs font-semibold uppercase tracking-wide text-ink/50">Updated</span>
                <span>{new Date(memory.updated_at).toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs font-semibold uppercase tracking-wide text-ink/50">Last accessed</span>
                <span>{memory.last_accessed_at ? new Date(memory.last_accessed_at).toLocaleString() : "Never"}</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={handleSave}
                disabled={!canSave}
                className="rounded-full border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-tide/90 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {saving ? "Saving..." : "Save memory"}
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleting || saving}
                className="rounded-full border border-clay/30 bg-white px-4 py-2.5 text-sm font-semibold text-clay transition hover:border-clay/50 hover:bg-clay/5 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {deleting ? "Deleting..." : "Delete memory"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
