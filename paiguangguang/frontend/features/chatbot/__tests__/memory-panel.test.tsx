import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const setStatus = vi.fn();
const setMemoryType = vi.fn();
const setScope = vi.fn();
const selectMemory = vi.fn();
const updateMemory = vi.fn().mockResolvedValue({ id: "memory-1" });
const deleteMemory = vi.fn().mockResolvedValue(true);

vi.mock("../hooks/use-memories", () => ({
  useMemories: () => ({
    status: "active",
    setStatus,
    memoryType: "all",
    setMemoryType,
    scope: "all",
    setScope,
    items: [
      {
        id: "memory-1",
        conversation_id: "conv-1",
        memory_type: "project_context",
        content: "Project memory",
        importance: 0.8,
        confidence: 0.9,
        source_message_ids: ["msg-1"],
        status: "active",
        last_accessed_at: null,
        expires_at: "2026-07-15T00:00:00.000Z",
        created_at: "2026-07-14T00:00:00.000Z",
        updated_at: "2026-07-14T00:00:00.000Z",
      },
    ],
    loading: false,
    loadingMore: false,
    error: null,
    hasMore: false,
    loadMore: vi.fn(),
    refresh: vi.fn(),
    selectedMemoryId: "memory-1",
    selectedMemory: {
      id: "memory-1",
      conversation_id: "conv-1",
      memory_type: "project_context",
      content: "Project memory",
      importance: 0.8,
      confidence: 0.9,
      source_message_ids: ["msg-1"],
      status: "active",
      last_accessed_at: null,
      expires_at: "2026-07-15T00:00:00.000Z",
      created_at: "2026-07-14T00:00:00.000Z",
      updated_at: "2026-07-14T00:00:00.000Z",
    },
    detailLoading: false,
    detailError: null,
    selectMemory,
    updateMemory,
    deleteMemory,
    savingMemoryId: null,
    deletingMemoryId: null,
  }),
}));

import { MemoryPanel } from "../components/memory-panel";

describe("MemoryPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  it("filters, scopes, edits, and deletes memories", async () => {
    render(<MemoryPanel token="token" conversationId="conv-1" />);

    fireEvent.click(screen.getByRole("button", { name: "Candidate" }));
    expect(setStatus).toHaveBeenCalledWith("candidate");

    fireEvent.change(screen.getByLabelText("Memory type"), {
      target: { value: "goal" },
    });
    expect(setMemoryType).toHaveBeenCalledWith("goal");

    fireEvent.click(screen.getByRole("button", { name: "Current conversation" }));
    expect(setScope).toHaveBeenCalledWith("current");

    fireEvent.click(screen.getByRole("button", { name: "Project memory" }));
    expect(selectMemory).toHaveBeenCalledWith("memory-1");

    fireEvent.change(screen.getByRole("textbox", { name: "Memory content" }), {
      target: { value: "Updated memory" },
    });
    fireEvent.change(screen.getByLabelText("Memory status"), {
      target: { value: "candidate" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Clear expiry" }));
    fireEvent.click(screen.getByRole("button", { name: "Save memory" }));

    await waitFor(() =>
      expect(updateMemory).toHaveBeenCalledWith(
        "memory-1",
        expect.objectContaining({
          content: "Updated memory",
          status: "candidate",
          expires_at: null,
        })
      )
    );

    fireEvent.click(screen.getByRole("button", { name: "Delete memory" }));
    await waitFor(() => expect(deleteMemory).toHaveBeenCalledWith("memory-1"));
  });
});
