"use client";

import type { MemoryData } from "../types/memory";

type MemoryListProps = {
  items: MemoryData[];
  loading: boolean;
  loadingMore: boolean;
  error: string | null;
  hasMore: boolean;
  selectedMemoryId: string | null;
  currentConversationId: string | null;
  onSelectMemory: (memoryId: string) => void | Promise<void>;
  onLoadMore: () => void | Promise<void>;
};

function formatTimestamp(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Unknown time";
  }
  return date.toLocaleString();
}

function summarizeContent(content: string) {
  const summary = content.replace(/\s+/g, " ").trim();
  if (summary.length <= 96) {
    return summary;
  }
  return `${summary.slice(0, 96)}...`;
}

export function MemoryList({
  items,
  loading,
  loadingMore,
  error,
  hasMore,
  selectedMemoryId,
  currentConversationId,
  onSelectMemory,
  onLoadMore,
}: MemoryListProps) {
  return (
    <section className="flex min-h-0 flex-col rounded-2xl border border-ink/10 bg-white/80 shadow-sm">
      <div className="border-b border-ink/10 px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm font-semibold text-ink">Memory list</p>
          <div className="text-xs text-ink/55">{loading ? "Loading memories..." : `${items.length} memories`}</div>
        </div>
      </div>

      <div className="min-h-0 flex-1 overscroll-contain overflow-y-auto p-2">
        {error ? (
          <div className="m-2 rounded-2xl border border-clay/30 bg-clay/10 p-4 text-sm text-ink">
            <p className="font-semibold text-clay">Unable to load memories</p>
            <p className="mt-2 leading-6">{error}</p>
          </div>
        ) : null}

        {!error && !loading && items.length === 0 ? (
          <div className="m-2 rounded-2xl border border-dashed border-ink/15 bg-paper/55 p-5 text-sm leading-7 text-ink/65">
            <p className="font-semibold text-ink">No memories yet</p>
            <p className="mt-2">Adjust the filters or select a different conversation scope.</p>
          </div>
        ) : null}

        {loadingMore ? (
          <div className="m-2 rounded-2xl border border-ink/10 bg-paper/55 p-4 text-sm text-ink/60">
            Loading more memories...
          </div>
        ) : null}

        <div className="space-y-2">
          {items.map((memory) => {
            const selected = selectedMemoryId === memory.id;
            const scopeLabel =
              memory.conversation_id && currentConversationId && memory.conversation_id === currentConversationId
                ? "Current conversation"
                : memory.conversation_id
                  ? "Conversation memory"
                  : "Global memory";

            return (
              <button
                key={memory.id}
                type="button"
                aria-pressed={selected}
                aria-label={summarizeContent(memory.content)}
                onClick={() => void onSelectMemory(memory.id)}
                className={[
                  "w-full rounded-2xl border p-4 text-left transition",
                  selected
                    ? "border-tide/45 bg-tide/5 shadow-sm"
                    : "border-ink/10 bg-white hover:border-tide/30 hover:bg-paper/40",
                ].join(" ")}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="truncate text-sm font-semibold text-ink">{summarizeContent(memory.content)}</h3>
                    <p className="mt-1 text-xs text-ink/55">{memory.memory_type}</p>
                  </div>
                  <span className="shrink-0 rounded-full border border-ink/10 bg-paper px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-ink/60">
                    {memory.status}
                  </span>
                </div>

                <p className="mt-3 text-sm leading-6 text-ink/70">{memory.content}</p>

                <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-semibold uppercase tracking-wide text-ink/50">
                  <span className="rounded-full border border-ink/10 bg-paper px-2 py-1">{scopeLabel}</span>
                  <span className="rounded-full border border-ink/10 bg-paper px-2 py-1">
                    Confidence {memory.confidence.toFixed(2)}
                  </span>
                  <span className="rounded-full border border-ink/10 bg-paper px-2 py-1">
                    Updated {formatTimestamp(memory.updated_at)}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {hasMore ? (
        <div className="border-t border-ink/10 p-4">
          <button
            type="button"
            onClick={() => void onLoadMore()}
            className="w-full rounded-full border border-ink/10 bg-paper px-4 py-2.5 text-sm font-semibold text-ink transition hover:border-tide/35 hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loadingMore ? "Loading..." : "Load more"}
          </button>
        </div>
      ) : null}
    </section>
  );
}
