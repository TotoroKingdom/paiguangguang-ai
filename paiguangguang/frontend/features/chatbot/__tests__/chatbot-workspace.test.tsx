import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatbotShell } from "../components/chatbot-shell";

let storageKey: string | null = null;
let authUser: { id: string; email: string } | null;

vi.mock("@/components/auth-provider", () => ({
  useAuth: () => ({
    token: "token-123",
    user: authUser,
  }),
}));

vi.mock("../stores/chatbot-store", async () => {
  const actual = await vi.importActual<typeof import("../stores/chatbot-store")>("../stores/chatbot-store");
  return {
    ...actual,
    ChatbotStoreProvider: ({
      children,
      storageKey: nextStorageKey,
      fallback: _fallback,
    }: {
      children: React.ReactNode;
      storageKey?: string | null;
      fallback?: React.ReactNode;
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

vi.mock("../components/chatbot-sidebar", () => ({
  ChatbotSidebar: ({ open }: { open: boolean }) => <section data-testid="chatbot-sidebar">{String(open)}</section>,
}));

vi.mock("../components/chatbot-header", () => ({
  ChatbotHeader: ({ view }: { view: string }) => <header data-testid="chatbot-header">{view}</header>,
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

vi.mock("../components/memory-panel", () => ({
  MemoryPanel: ({ token }: { token: string | null }) => <section data-testid="memory-panel">{token}</section>,
}));

beforeEach(() => {
  storageKey = null;
  authUser = { id: "user-123", email: "owner@example.com" };
});

describe("ChatbotShell workspace", () => {
  it("wires the authenticated workspace with user-scoped persistence", () => {
    render(<ChatbotShell />);

    expect(storageKey).toBe("paiguangguang.chatbot:user-123");
    expect(screen.getByTestId("chatbot-shell")).toHaveClass("chatbot-theme", "h-full", "min-h-0", "overflow-hidden");
    expect(screen.getByTestId("chatbot-header").textContent).toBe("chat");
    expect(screen.getByTestId("chatbot-sidebar").textContent).toBe("false");
    expect(screen.getByTestId("panel").textContent).toContain("token-123");
    expect(screen.getByTestId("panel").textContent).toContain("streaming");
  });

  it("disables persistence when the user is logged out", () => {
    authUser = null;
    render(<ChatbotShell />);

    expect(storageKey).toBeNull();
  });
});
