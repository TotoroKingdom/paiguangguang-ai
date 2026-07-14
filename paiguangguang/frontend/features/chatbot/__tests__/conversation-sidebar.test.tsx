import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ConversationSidebar } from "../components/conversation-sidebar";
import type { ConversationData, ConversationStatus } from "../types/conversation";

function makeConversation(
  id: string,
  status: ConversationStatus = "active"
): ConversationData {
  return {
    id,
    title: "Project sync",
    title_source: "manual",
    status,
    model: "deepseek-chat",
    last_message_at: "2026-07-13T10:00:00.000Z",
    created_at: "2026-07-13T09:00:00.000Z",
    updated_at: "2026-07-13T10:00:00.000Z",
    archived_at: status === "archived" ? "2026-07-13T10:05:00.000Z" : null,
  };
}

const handlers = {
  onChangeStatus: vi.fn(),
  onSelectConversation: vi.fn(),
  onLoadMore: vi.fn(),
  onCreateConversation: vi.fn(),
  onRenameConversation: vi.fn(),
  onArchiveConversation: vi.fn(),
  onRestoreConversation: vi.fn(),
  onDeleteConversation: vi.fn(),
  onRefresh: vi.fn(),
};

describe("ConversationSidebar", () => {
  it("renders empty and loading states", () => {
    render(
      <ConversationSidebar
        selectedStatus="active"
        selectedConversationId={null}
        conversations={[]}
        loading={true}
        error={null}
        hasMore={false}
        {...handlers}
      />
    );

    expect(screen.getByText("Loading conversations")).toBeInTheDocument();
    expect(screen.getByText("New chat")).toBeInTheDocument();
  });

  it("renders an error state with retry", () => {
    render(
      <ConversationSidebar
        selectedStatus="active"
        selectedConversationId={null}
        conversations={[]}
        loading={false}
        error="backend unavailable"
        hasMore={false}
        {...handlers}
      />
    );

    expect(screen.getByText("Unable to load conversations")).toBeInTheDocument();
    expect(screen.getByText("backend unavailable")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(handlers.onRefresh).toHaveBeenCalledTimes(1);
  });

  it("fires action callbacks from the list and tabs", () => {
    render(
      <ConversationSidebar
        selectedStatus="active"
        selectedConversationId="conv-1"
        conversations={[makeConversation("conv-1"), makeConversation("conv-2", "archived")]}
        loading={false}
        error={null}
        hasMore={true}
        {...handlers}
      />
    );

    const firstConversation = screen.getAllByText("Project sync")[0]?.closest("article");
    if (!firstConversation) {
      throw new Error("Conversation article not found");
    }

    fireEvent.click(screen.getByRole("button", { name: "Archived" }));
    fireEvent.click(within(firstConversation).getAllByRole("button")[0]);
    fireEvent.click(within(firstConversation).getByRole("button", { name: "Rename" }));
    fireEvent.click(within(firstConversation).getByRole("button", { name: "Archive" }));
    fireEvent.click(within(firstConversation).getByRole("button", { name: "Delete" }));
    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    fireEvent.click(screen.getByRole("button", { name: "New chat" }));

    expect(handlers.onChangeStatus).toHaveBeenCalledWith("archived");
    expect(handlers.onSelectConversation).toHaveBeenCalledWith("conv-1");
    expect(handlers.onRenameConversation).toHaveBeenCalledTimes(1);
    expect(handlers.onArchiveConversation).toHaveBeenCalledTimes(1);
    expect(handlers.onDeleteConversation).toHaveBeenCalledTimes(1);
    expect(handlers.onLoadMore).toHaveBeenCalledTimes(1);
    expect(handlers.onCreateConversation).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: "Trash" })).not.toBeInTheDocument();
    expect(screen.queryByText("deleted")).not.toBeInTheDocument();
  });
});
