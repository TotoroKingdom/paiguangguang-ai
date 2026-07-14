"use client";

import { useState } from "react";

import { useMemories } from "../hooks/use-memories";
import type { MemoryData, MemoryStatus } from "../types/memory";

const FILTERS: Array<{ status: MemoryStatus; label: string }> = [
  { status: "active", label: "Active" },
  { status: "candidate", label: "Candidate" },
  { status: "superseded", label: "Superseded" },
];

export function MemoryPanel({ token }: { token: string | null }) {
  const memories = useMemories({ token });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState("");

  function beginEdit(memory: MemoryData) {
    setEditingId(memory.id);
    setEditingContent(memory.content);
  }

  async function save(memoryId: string) {
    const content = editingContent.trim();
    if (!content) {
      return;
    }
    const updated = await memories.updateMemory(memoryId, { content });
    if (updated) {
      setEditingId(null);
      setEditingContent("");
    }
  }

  async function remove(memory: MemoryData) {
    if (!window.confirm(`Delete memory "${memory.content.slice(0, 40)}"?`)) {
      return;
    }
    await memories.deleteMemory(memory.id);
  }

  return (
    <section aria-label="Memories" className="border border-ink/10 bg-white/80 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-2xl font-semibold text-ink">Memories</h2>
        <button type="button" onClick={() => void memories.refresh()}>
          Refresh
        </button>
      </div>
      <div className="mt-4 flex gap-2">
        {FILTERS.map((filter) => (
          <button
            key={filter.status}
            type="button"
            aria-pressed={memories.status === filter.status}
            onClick={() => memories.setStatus(filter.status)}
          >
            {filter.label}
          </button>
        ))}
      </div>
      {memories.error ? <p role="alert">{memories.error}</p> : null}
      {!memories.loading && memories.items.length === 0 ? <p>No memories.</p> : null}
      <div className="mt-4 space-y-3">
        {memories.items.map((memory) => (
          <article key={memory.id} className="border border-ink/10 p-4">
            <p className="text-xs uppercase text-ink/60">
              {memory.memory_type} · confidence {memory.confidence.toFixed(2)}
            </p>
            {editingId === memory.id ? (
              <>
                <textarea
                  aria-label="Memory content"
                  value={editingContent}
                  onChange={(event) => setEditingContent(event.target.value)}
                />
                <button type="button" onClick={() => void save(memory.id)}>
                  Save
                </button>
                <button type="button" onClick={() => setEditingId(null)}>
                  Cancel
                </button>
              </>
            ) : (
              <p>{memory.content}</p>
            )}
            <p className="text-xs text-ink/50">Updated {memory.updated_at}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" onClick={() => beginEdit(memory)}>
                Edit
              </button>
              {memory.status === "candidate" ? (
                <button
                  type="button"
                  onClick={() => void memories.updateMemory(memory.id, { status: "active" })}
                >
                  Activate
                </button>
              ) : null}
              {memory.status === "active" ? (
                <button
                  type="button"
                  onClick={() =>
                    void memories.updateMemory(memory.id, { status: "candidate" })
                  }
                >
                  Move to candidate
                </button>
              ) : null}
              <button type="button" onClick={() => void remove(memory)}>
                Delete
              </button>
            </div>
          </article>
        ))}
      </div>
      {memories.hasMore ? (
        <button type="button" onClick={() => void memories.loadMore()}>
          Load more
        </button>
      ) : null}
      {memories.loading ? <p>Loading memories…</p> : null}
    </section>
  );
}
