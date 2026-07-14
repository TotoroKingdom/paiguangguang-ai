import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const setStatus = vi.fn();
const updateMemory = vi.fn().mockResolvedValue({ id: "memory-1" });
const deleteMemory = vi.fn().mockResolvedValue(true);

vi.mock("../hooks/use-memories", () => ({
  useMemories: () => ({
    status: "active",
    setStatus,
    items: [
      {
        id: "memory-1",
        conversation_id: null,
        memory_type: "project_context",
        content: "Project memory",
        importance: 0.8,
        confidence: 0.9,
        source_message_ids: [],
        status: "active",
        last_accessed_at: null,
        expires_at: null,
        created_at: "2026-07-14T00:00:00.000Z",
        updated_at: "2026-07-14T00:00:00.000Z",
      },
    ],
    loading: false,
    error: null,
    hasMore: false,
    loadMore: vi.fn(),
    updateMemory,
    deleteMemory,
    refresh: vi.fn(),
  }),
}));

import { MemoryPanel } from "../components/memory-panel";

describe("MemoryPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  it("filters, edits, and deletes memories", async () => {
    render(<MemoryPanel token="token" />);

    fireEvent.click(screen.getByRole("button", { name: "Candidate" }));
    expect(setStatus).toHaveBeenCalledWith("candidate");

    expect(screen.getByText("Project memory")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    fireEvent.change(screen.getByRole("textbox", { name: "Memory content" }), {
      target: { value: "Updated memory" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(updateMemory).toHaveBeenCalledWith("memory-1", {
        content: "Updated memory",
      })
    );

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(deleteMemory).toHaveBeenCalledWith("memory-1"));
  });
});
