"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { memoryApiClient, type MemoryApiClient } from "../api/memories";
import type { MemoryData, MemoryStatus, MemoryType, MemoryUpdateRequest } from "../types/memory";

export type MemoryScope = "all" | "current";
export type MemoryTypeFilter = MemoryType | "all";

type Options = {
  token: string | null;
  conversationId?: string | null;
  client?: MemoryApiClient;
  pageSize?: number;
};

function normalizeError(error: unknown, fallback: string) {
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
}

export function useMemories({ token, conversationId = null, client = memoryApiClient, pageSize = 20 }: Options) {
  const [status, setStatusState] = useState<MemoryStatus>("active");
  const [memoryType, setMemoryTypeState] = useState<MemoryTypeFilter>("all");
  const [scope, setScopeState] = useState<MemoryScope>("all");
  const [items, setItems] = useState<MemoryData[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMemoryId, setSelectedMemoryId] = useState<string | null>(null);
  const [selectedMemory, setSelectedMemory] = useState<MemoryData | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [savingMemoryId, setSavingMemoryId] = useState<string | null>(null);
  const [deletingMemoryId, setDeletingMemoryId] = useState<string | null>(null);

  const listRequestRef = useRef(0);
  const detailRequestRef = useRef(0);

  const listConversationId = scope === "current" ? conversationId : null;
  const listMemoryType = memoryType === "all" ? null : memoryType;

  const clearListState = useCallback(() => {
    setItems([]);
    setNextCursor(null);
    setHasMore(false);
    setLoadingMore(false);
  }, []);

  const clearDetailState = useCallback(() => {
    setSelectedMemoryId(null);
    setSelectedMemory(null);
    setDetailLoading(false);
    setDetailError(null);
  }, []);

  const loadPage = useCallback(
    async ({
      requestId,
      cursor = null,
      append = false,
    }: {
      requestId: number;
      cursor?: string | null;
      append?: boolean;
    }) => {
      if (!token) {
        return null;
      }

      if (append) {
        setLoadingMore(true);
      } else {
        setLoadingMore(false);
        setLoading(true);
      }
      setError(null);

      try {
        const page = await client.listMemories({
          token,
          status,
          memoryType: listMemoryType,
          conversationId: listConversationId,
          cursor,
          limit: pageSize,
        });

        if (requestId !== listRequestRef.current) {
          return null;
        }

        setItems((current) => (append ? [...current, ...page.items] : page.items));
        setNextCursor(page.next_cursor);
        setHasMore(page.has_more);
        return page;
      } catch (cause) {
        if (requestId !== listRequestRef.current) {
          return null;
        }

        setError(normalizeError(cause, "Unable to load memories."));
        return null;
      } finally {
        if (requestId === listRequestRef.current) {
          if (append) {
            setLoadingMore(false);
          } else {
            setLoading(false);
          }
        }
      }
    },
    [client, listConversationId, listMemoryType, pageSize, status, token]
  );

  const refresh = useCallback(() => {
    if (!token) {
      return Promise.resolve(null);
    }

    const requestId = ++listRequestRef.current;
    return loadPage({ requestId, cursor: null, append: false });
  }, [loadPage, token]);

  const loadMore = useCallback(() => {
    if (!hasMore || !nextCursor || !token) {
      return Promise.resolve(null);
    }

    const requestId = listRequestRef.current;
    return loadPage({ requestId, cursor: nextCursor, append: true });
  }, [hasMore, loadPage, nextCursor, token]);

  useEffect(() => {
    if (!token) {
      listRequestRef.current += 1;
      clearListState();
      clearDetailState();
      setLoading(false);
      setLoadingMore(false);
      setError(null);
      return;
    }

    if (scope === "current" && !conversationId) {
      setScopeState("all");
      return;
    }

    const requestId = ++listRequestRef.current;
    clearListState();
    clearDetailState();
    void loadPage({ requestId, cursor: null, append: false });
  }, [clearDetailState, clearListState, conversationId, loadPage, scope, token]);

  const setStatus = useCallback(
    (next: MemoryStatus) => {
      setStatusState(next);
      clearListState();
      clearDetailState();
    },
    [clearDetailState, clearListState]
  );

  const setMemoryType = useCallback(
    (next: MemoryTypeFilter) => {
      setMemoryTypeState(next);
      clearListState();
      clearDetailState();
    },
    [clearDetailState, clearListState]
  );

  const setScope = useCallback(
    (next: MemoryScope) => {
      if (next === "current" && !conversationId) {
        return;
      }
      setScopeState(next);
      clearListState();
      clearDetailState();
    },
    [conversationId, clearDetailState, clearListState]
  );

  const selectMemory = useCallback(
    async (memoryId: string) => {
      if (!token) {
        return null;
      }

      const requestId = ++detailRequestRef.current;
      setSelectedMemoryId(memoryId);
      setDetailLoading(true);
      setDetailError(null);

      try {
        const memory = await client.getMemory({ token, memoryId });
        if (requestId !== detailRequestRef.current) {
          return null;
        }
        setSelectedMemory(memory);
        return memory;
      } catch (cause) {
        if (requestId !== detailRequestRef.current) {
          return null;
        }
        setSelectedMemory(null);
        setDetailError(normalizeError(cause, "Unable to load memory detail."));
        return null;
      } finally {
        if (requestId === detailRequestRef.current) {
          setDetailLoading(false);
        }
      }
    },
    [client, token]
  );

  const updateMemory = useCallback(
    async (memoryId: string, request: MemoryUpdateRequest) => {
      if (!token) {
        return null;
      }

      setSavingMemoryId(memoryId);
      setDetailError(null);

      try {
        const updated = await client.updateMemory({ token, memoryId }, request);
        setItems((current) =>
          current.some((item) => item.id === memoryId)
            ? updated.status === status
              ? current.map((item) => (item.id === memoryId ? updated : item))
              : current.filter((item) => item.id !== memoryId)
            : current
        );
        setSelectedMemory((current) => (current?.id === memoryId ? updated : current));
        return updated;
      } catch (cause) {
        setDetailError(normalizeError(cause, "Unable to update memory."));
        return null;
      } finally {
        setSavingMemoryId((current) => (current === memoryId ? null : current));
      }
    },
    [client, status, token]
  );

  const deleteMemory = useCallback(
    async (memoryId: string) => {
      if (!token) {
        return false;
      }

      setDeletingMemoryId(memoryId);
      setDetailError(null);

      try {
        await client.deleteMemory({ token, memoryId });
        setItems((current) => current.filter((item) => item.id !== memoryId));
        setSelectedMemoryId((current) => (current === memoryId ? null : current));
        setSelectedMemory((current) => (current?.id === memoryId ? null : current));
        return true;
      } catch (cause) {
        setDetailError(normalizeError(cause, "Unable to delete memory."));
        return false;
      } finally {
        setDeletingMemoryId((current) => (current === memoryId ? null : current));
      }
    },
    [client, token]
  );

  return {
    status,
    setStatus,
    memoryType,
    setMemoryType,
    scope,
    setScope,
    items,
    loading,
    loadingMore,
    error,
    hasMore,
    nextCursor,
    refresh,
    loadMore,
    selectedMemoryId,
    selectedMemory,
    detailLoading,
    detailError,
    selectMemory,
    updateMemory,
    deleteMemory,
    savingMemoryId,
    deletingMemoryId,
  };
}
