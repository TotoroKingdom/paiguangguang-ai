import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatbotShell } from "../components/chatbot-shell";

let storageKey: string | null = null;

vi.mock("@/components/auth-provider", () => ({
  useAuth: () => ({
    token: "token-123",
    user: {
      id: "user-123",
      email: "owner@example.com",
    },
  }),
}));

vi.mock("../stores/chatbot-store", async () => {
  const actual = await vi.importActual<typeof import("../stores/chatbot-store")>("../stores/chatbot-store");
  return {
    ...actual,
    ChatbotStoreProvider: ({
      children,
      storageKey: nextStorageKey,
    }: {
      children: React.ReactNode;
      storageKey?: string | null;
    }) => {
      storageKey = nextStorageKey ?? null;
      return <>{children}</>;
    },
  };
});

vi.mock("../hooks/use-conversations", () => ({
  useConversations: () => ({
    selectedStatus: "active",
    selectedConversationId: "conv-1",
    conversations: [
      {
        id: "conv-1",
        title: "Workspace conversation",
        title_source: "manual",
        status: "active",
        model: "deepseek-chat",
        last_message_at: "2026-07-13T10:00:00.000Z",
        created_at: "2026-07-13T09:00:00.000Z",
        updated_at: "2026-07-13T10:00:00.000Z",
        archived_at: null,
      },
    ],
    loading: false,
    error: null,
    hasMore: false,
    selectedConversation: {
      id: "conv-1",
      title: "Workspace conversation",
      title_source: "manual",
      status: "active",
      model: "deepseek-chat",
      last_message_at: "2026-07-13T10:00:00.000Z",
      created_at: "2026-07-13T09:00:00.000Z",
      updated_at: "2026-07-13T10:00:00.000Z",
      archived_at: null,
      active_generation: {
        assistant_message_id: "msg-2",
        status: "streaming",
        started_at: "2026-07-13T10:01:00.000Z",
      },
    },
    selectedConversationDetail: {
      active_generation: {
        assistant_message_id: "msg-2",
        status: "streaming",
        started_at: "2026-07-13T10:01:00.000Z",
      },
    },
    selectStatus: vi.fn(),
    selectConversation: vi.fn(),
    loadMore: vi.fn(),
    createConversation: vi.fn(),
    renameConversation: vi.fn(),
    archiveConversation: vi.fn(),
    restoreConversation: vi.fn(),
    deleteConversation: vi.fn(),
    refreshCurrentStatus: vi.fn(),
  }),
}));

vi.mock("../components/conversation-sidebar", () => ({
  ConversationSidebar: ({ selectedStatus, conversations }: { selectedStatus: string; conversations: Array<{ id: string; title: string }> }) => (
    <section data-testid="sidebar">
      <span>{selectedStatus}</span>
      <span>{conversations[0]?.title ?? "none"}</span>
    </section>
  ),
}));

vi.mock("../components/chat-conversation-panel", () => ({
  ChatConversationPanel: ({
    token,
    conversation,
    activeGeneration,
  }: {
    token: string | null;
    conversation: { id: string; title: string } | null;
    activeGeneration: { status: string } | null;
  }) => (
    <section data-testid="panel">
      <span>{token}</span>
      <span>{conversation?.title ?? "none"}</span>
      <span>{activeGeneration?.status ?? "none"}</span>
    </section>
  ),
}));

beforeEach(() => {
  storageKey = null;
});

describe("ChatbotShell workspace", () => {
  it("wires the authenticated workspace with user-scoped persistence", () => {
    render(<ChatbotShell />);

    expect(storageKey).toBe("paiguangguang.chatbot:user-123");
    expect(screen.getByTestId("sidebar").textContent).toContain("Workspace conversation");
    expect(screen.getByTestId("panel").textContent).toContain("token-123");
    expect(screen.getByTestId("panel").textContent).toContain("streaming");
  });
});
