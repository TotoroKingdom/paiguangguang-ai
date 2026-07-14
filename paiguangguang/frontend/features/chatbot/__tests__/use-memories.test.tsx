import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useMemories } from "../hooks/use-memories";
import type { MemoryData } from "../types/memory";

function makeMemory(id: string, overrides: Partial<MemoryData> = {}): MemoryData {
  return {
    id,
    conversation_id: null,
    memory_type: "project_context",
    content: "project memory",
    importance: 0.8,
    confidence: 0.9,
    source_message_ids: [],
    status: "active",
    last_accessed_at: null,
    expires_at: null,
    created_at: "2026-07-14T00:00:00.000Z",
    updated_at: "2026-07-14T00:00:00.000Z",
    ...overrides,
  };
}

describe("useMemories", () => {
  it("loads, updates, and removes memories", async () => {
    const client = {
      listMemories: vi.fn().mockResolvedValue({
        items: [makeMemory("memory-1")],
        next_cursor: null,
        has_more: false,
      }),
      updateMemory: vi
        .fn()
        .mockResolvedValue(makeMemory("memory-1", { content: "updated" })),
      deleteMemory: vi.fn().mockResolvedValue({
        id: "memory-1",
        status: "deleted",
        cleanup_status: "pending",
      }),
    };

    const { result } = renderHook(() => useMemories({ token: "token", client }));
    await waitFor(() => expect(result.current.items).toHaveLength(1));
    expect(client.listMemories).toHaveBeenCalledWith({
      token: "token",
      status: "active",
      cursor: null,
      limit: 20,
    });

    await act(async () => {
      await result.current.updateMemory("memory-1", { content: "updated" });
    });
    expect(result.current.items[0].content).toBe("updated");

    await act(async () => {
      await result.current.deleteMemory("memory-1");
    });
    expect(result.current.items).toEqual([]);
  });
});
