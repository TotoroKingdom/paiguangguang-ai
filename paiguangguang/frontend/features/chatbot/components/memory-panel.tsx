"use client";

import { useCallback } from "react";

import { useMemories } from "../hooks/use-memories";
import { MemoryDetailEditor } from "./memory-detail-editor";
import { MemoryFilters } from "./memory-filters";
import { MemoryList } from "./memory-list";

type MemoryPanelProps = {
  token: string | null;
  conversationId?: string | null;
};

export function MemoryPanel({ token, conversationId = null }: MemoryPanelProps) {
  const memories = useMemories({ token, conversationId });

  const handleRefresh = useCallback(() => {
    void memories.refresh();
  }, [memories.refresh]);

  const handleSelectMemory = useCallback(
    (memoryId: string) => {
      void memories.selectMemory(memoryId);
    },
    [memories.selectMemory]
  );

  const handleSaveMemory = useCallback(
    (memoryId: string, request: Parameters<typeof memories.updateMemory>[1]) => {
      void memories.updateMemory(memoryId, request);
    },
    [memories.updateMemory]
  );

  const handleDeleteMemory = useCallback(
    (memoryId: string) => {
      void memories.deleteMemory(memoryId);
    },
    [memories.deleteMemory]
  );

  return (
    <section aria-label="Memories" className="flex h-full min-h-0 flex-col gap-4">
      <div className="rounded-2xl border border-ink/10 bg-white/80 p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-clay">Memory workspace</p>
            <h2 className="mt-1 text-2xl font-semibold text-ink">Memories</h2>
            <p className="mt-2 text-sm leading-6 text-ink/60">
              Manage active knowledge, candidate notes, and superseded records.
            </p>
          </div>

          <button
            type="button"
            onClick={handleRefresh}
            className="rounded-full border border-tide/40 bg-tide px-4 py-2.5 text-sm font-semibold text-paper transition hover:bg-tide/90"
          >
            Refresh
          </button>
        </div>
      </div>

      <MemoryFilters
        status={memories.status}
        memoryType={memories.memoryType}
        scope={memories.scope}
        conversationScopeAvailable={Boolean(conversationId)}
        onChangeStatus={memories.setStatus}
        onChangeMemoryType={memories.setMemoryType}
        onChangeScope={memories.setScope}
      />

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <MemoryList
          items={memories.items}
          loading={memories.loading}
          loadingMore={memories.loadingMore}
          error={memories.error}
          hasMore={memories.hasMore}
          selectedMemoryId={memories.selectedMemoryId}
          currentConversationId={conversationId}
          onSelectMemory={handleSelectMemory}
          onLoadMore={() => void memories.loadMore()}
        />

        <MemoryDetailEditor
          memory={memories.selectedMemory}
          loading={memories.detailLoading}
          error={memories.detailError}
          saving={Boolean(memories.savingMemoryId)}
          deleting={Boolean(memories.deletingMemoryId)}
          onSave={handleSaveMemory}
          onDelete={handleDeleteMemory}
        />
      </div>
    </section>
  );
}
