"use client";

import { useCallback, useEffect, useState } from "react";

import { memoryApiClient, type MemoryApiClient } from "../api/memories";
import type { MemoryData, MemoryStatus, MemoryUpdateRequest } from "../types/memory";

type Options = {
  token: string | null;
  client?: MemoryApiClient;
  pageSize?: number;
};

export function useMemories({ token, client = memoryApiClient, pageSize = 20 }: Options) {
  const [status, setStatusState] = useState<MemoryStatus>("active");
  const [items, setItems] = useState<MemoryData[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (cursor: string | null = null, append = false) => {
      if (!token) {
        return null;
      }
      setLoading(true);
      setError(null);
      try {
        const page = await client.listMemories({ token, status, cursor, limit: pageSize });
        setItems((current) => (append ? [...current, ...page.items] : page.items));
        setNextCursor(page.next_cursor);
        setHasMore(page.has_more);
        return page;
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Unable to load memories.");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [client, pageSize, status, token]
  );

  useEffect(() => {
    void load(null, false);
  }, [load]);

  const setStatus = useCallback((next: MemoryStatus) => {
    setStatusState(next);
    setItems([]);
    setNextCursor(null);
    setHasMore(false);
  }, []);

  const updateMemory = useCallback(
    async (memoryId: string, request: MemoryUpdateRequest) => {
      if (!token) {
        return null;
      }
      setError(null);
      try {
        const updated = await client.updateMemory({ token, memoryId }, request);
        setItems((current) =>
          updated.status === status
            ? current.map((item) => (item.id === memoryId ? updated : item))
            : current.filter((item) => item.id !== memoryId)
        );
        return updated;
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Unable to update memory.");
        return null;
      }
    },
    [client, status, token]
  );

  const deleteMemory = useCallback(
    async (memoryId: string) => {
      if (!token) {
        return false;
      }
      setError(null);
      try {
        await client.deleteMemory({ token, memoryId });
        setItems((current) => current.filter((item) => item.id !== memoryId));
        return true;
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Unable to delete memory.");
        return false;
      }
    },
    [client, token]
  );

  const loadMore = useCallback(() => {
    if (!hasMore || !nextCursor) {
      return Promise.resolve(null);
    }
    return load(nextCursor, true);
  }, [hasMore, load, nextCursor]);

  return {
    status,
    setStatus,
    items,
    loading,
    error,
    hasMore,
    loadMore,
    updateMemory,
    deleteMemory,
    refresh: () => load(null, false),
  };
}
