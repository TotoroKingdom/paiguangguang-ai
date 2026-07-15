import { renderHook, waitFor, act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api";

import { ChatbotStoreProvider } from "../stores/chatbot-store";
import { useConversations } from "../hooks/use-conversations";
import type { ChatbotApiClient } from "../api/client";
import type { ConversationData, ConversationDetailData, DeleteResultData } from "../types/conversation";

const push = vi.fn();
const replace = vi.fn();
let pathname = "/chat-bot";
let searchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
  useRouter: () => ({
    push,
    replace,
    refresh: vi.fn(),
  }),
  useSearchParams: () => searchParams,
}));

function makeConversation(id: string, overrides: Partial<ConversationData> = {}): ConversationData {
  return {
    id,
    title: `Conversation ${id}`,
    title_source: "manual",
    status: "active",
    model: "deepseek-chat",
    last_message_at: "2026-07-13T10:00:00.000Z",
    created_at: "2026-07-13T09:00:00.000Z",
    updated_at: "2026-07-13T10:00:00.000Z",
    archived_at: null,
    ...overrides,
  };
}

function makeDetail(id: string, overrides: Partial<ConversationDetailData> = {}): ConversationDetailData {
  return {
    ...makeConversation(id),
    active_generation: null,
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, resolve, reject };
}

function makeClient(overrides: Partial<ChatbotApiClient> = {}): ChatbotApiClient {
  return {
    listConversations: vi.fn(),
    getConversation: vi.fn(),
    createConversation: vi.fn(),
    updateConversation: vi.fn(),
    archiveConversation: vi.fn(),
    restoreConversation: vi.fn(),
    deleteConversation: vi.fn(),
    ...overrides,
  } as ChatbotApiClient;
}

function renderConversationsHook(client: ChatbotApiClient, storageKey = "chatbot:test") {
  return renderHook(() => useConversations({ token: "token", client, pageSize: 2 }), {
    wrapper: ({ children }) => <ChatbotStoreProvider storageKey={storageKey}>{children}</ChatbotStoreProvider>,
  });
}

beforeEach(() => {
  push.mockReset();
  replace.mockReset();
  pathname = "/chat-bot";
  searchParams = new URLSearchParams();
  window.sessionStorage.clear();
});

describe("useConversations", () => {
  it("restores a conversation from the URL and loads the active page", async () => {
    searchParams = new URLSearchParams("conversation=conv-2");
    const client = makeClient({
      listConversations: vi.fn().mockResolvedValue({
        items: [makeConversation("conv-1"), makeConversation("conv-2")],
        next_cursor: null,
        has_more: false,
      }),
      getConversation: vi.fn().mockResolvedValue(makeDetail("conv-2", { title: "Selected conversation" })),
    });

    const { result } = renderConversationsHook(client);

    await waitFor(() => {
      expect(result.current.selectedConversationId).toBe("conv-2");
    });

    expect(result.current.selectedConversation?.title).toBe("Selected conversation");
    expect(result.current.conversations).toHaveLength(2);
    expect(client.listConversations).toHaveBeenCalledWith({
      token: "token",
      status: "active",
      cursor: null,
      limit: 2,
    });
    expect(replace).not.toHaveBeenCalled();
  });

  it("loads more conversations for the selected status", async () => {
    const client = makeClient({
      listConversations: vi
        .fn()
        .mockResolvedValueOnce({
          items: [makeConversation("conv-1"), makeConversation("conv-2")],
          next_cursor: "cursor-2",
          has_more: true,
        })
        .mockResolvedValueOnce({
          items: [makeConversation("conv-3")],
          next_cursor: null,
          has_more: false,
        }),
      getConversation: vi.fn().mockResolvedValue(makeDetail("conv-1")),
    });

    const { result } = renderConversationsHook(client);

    await waitFor(() => {
      expect(result.current.conversations).toHaveLength(2);
    });

    await act(async () => {
      await result.current.loadMore();
    });

    expect(result.current.conversations).toHaveLength(3);
    expect(result.current.hasMore).toBe(false);
  });

  it("stores create rename archive and delete changes in the sidebar state", async () => {
    const client = makeClient({
      listConversations: vi.fn().mockResolvedValue({
        items: [makeConversation("conv-1")],
        next_cursor: null,
        has_more: false,
      }),
      getConversation: vi.fn().mockImplementation(
        async ({ conversationId }: { token: string | null; conversationId: string }) =>
          makeDetail(conversationId)
      ),
      createConversation: vi.fn().mockResolvedValue(makeConversation("conv-2", { title: "Created conversation" })),
      updateConversation: vi.fn().mockResolvedValue(makeConversation("conv-1", { title: "Renamed conversation" })),
      archiveConversation: vi.fn().mockResolvedValue({
        id: "conv-1",
        title: "Conversation conv-1",
        title_source: "manual",
        status: "archived",
        model: "deepseek-chat",
        last_message_at: "2026-07-13T10:00:00.000Z",
        created_at: "2026-07-13T09:00:00.000Z",
        updated_at: "2026-07-13T10:00:00.000Z",
        archived_at: "2026-07-13T10:05:00.000Z",
      }),
      restoreConversation: vi.fn().mockResolvedValue({
        id: "conv-1",
        title: "Conversation conv-1",
        title_source: "manual",
        status: "active",
        model: "deepseek-chat",
        last_message_at: "2026-07-13T10:00:00.000Z",
        created_at: "2026-07-13T09:00:00.000Z",
        updated_at: "2026-07-13T10:00:00.000Z",
        archived_at: null,
      }),
      deleteConversation: vi.fn().mockResolvedValue({ id: "conv-1", status: "deleted", cleanup_status: "completed" }),
    });

    const { result } = renderConversationsHook(client);

    await waitFor(() => {
      expect(result.current.conversations).toHaveLength(1);
    });

    await act(async () => {
      await result.current.createConversation({ title: "Created conversation" });
    });
    expect(result.current.selectedConversationId).toBe("conv-2");
    expect(push).toHaveBeenCalledWith("/chat-bot?conversation=conv-2");

    await act(async () => {
      await result.current.renameConversation(makeConversation("conv-1"), "Renamed conversation");
    });
    expect(result.current.pages.active.items.find((conversation) => conversation.id === "conv-1")?.title).toBe(
      "Renamed conversation"
    );
    expect(client.updateConversation).toHaveBeenCalledWith(
      { token: "token", conversationId: "conv-1" },
      { title: "Renamed conversation" }
    );

    await act(async () => {
      await result.current.archiveConversation(makeConversation("conv-1"));
    });
    expect(client.archiveConversation).toHaveBeenCalledTimes(1);
    expect(result.current.pages.archived.items.some((conversation) => conversation.id === "conv-1")).toBe(true);

    await act(async () => {
      await result.current.restoreConversation(makeConversation("conv-1", { status: "archived" }));
    });
    expect(client.restoreConversation).toHaveBeenCalledTimes(1);
    expect(result.current.pages.active.items.some((conversation) => conversation.id === "conv-1")).toBe(true);

    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    await act(async () => {
      await result.current.deleteConversation(makeConversation("conv-1"));
    });
    expect(client.deleteConversation).toHaveBeenCalledTimes(1);
    expect(result.current.pages.active.items.some((conversation) => conversation.id === "conv-1")).toBe(false);
    expect(result.current.pages.archived.items.some((conversation) => conversation.id === "conv-1")).toBe(false);
    expect(result.current.selectedConversationId).toBe(null);
    expect(replace).toHaveBeenCalledWith("/chat-bot");
    confirmSpy.mockRestore();
  });

  it("removes a conversation from the sidebar immediately while delete is pending", async () => {
    const deleteRequest = deferred<DeleteResultData>();
    const client = makeClient({
      listConversations: vi.fn().mockResolvedValue({
        items: [makeConversation("conv-1"), makeConversation("conv-2")],
        next_cursor: null,
        has_more: false,
      }),
      deleteConversation: vi.fn().mockReturnValue(deleteRequest.promise),
    });

    const { result } = renderConversationsHook(client);

    await waitFor(() => {
      expect(result.current.conversations).toHaveLength(2);
    });

    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const deletePromise = result.current.deleteConversation(makeConversation("conv-1"));

    await waitFor(() => {
      expect(result.current.pages.active.items.map((conversation) => conversation.id)).toEqual(["conv-2"]);
    });
    expect(client.deleteConversation).toHaveBeenCalledWith({ token: "token", conversationId: "conv-1" });

    deleteRequest.resolve({
      id: "conv-1",
      status: "deleted",
      cleanup_status: "completed",
    });

    await deletePromise;

    expect(result.current.pages.active.items.map((conversation) => conversation.id)).toEqual(["conv-2"]);
    confirmSpy.mockRestore();
  });

  it("restores a conversation if delete fails after the optimistic update", async () => {
    const deleteRequest = deferred<DeleteResultData>();
    const client = makeClient({
      listConversations: vi.fn().mockResolvedValue({
        items: [makeConversation("conv-1"), makeConversation("conv-2")],
        next_cursor: null,
        has_more: false,
      }),
      deleteConversation: vi.fn().mockReturnValue(deleteRequest.promise),
    });

    const { result } = renderConversationsHook(client);

    await waitFor(() => {
      expect(result.current.conversations).toHaveLength(2);
    });

    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const deletePromise = result.current.deleteConversation(makeConversation("conv-1"));

    await waitFor(() => {
      expect(result.current.pages.active.items.map((conversation) => conversation.id)).toEqual(["conv-2"]);
    });

    deleteRequest.reject(new Error("delete failed"));

    await deletePromise;

    await waitFor(() => {
      expect(result.current.pages.active.items.map((conversation) => conversation.id)).toEqual([
        "conv-2",
        "conv-1",
      ]);
    });
    confirmSpy.mockRestore();
  });

  it("shows an error when the backend rejects the active page request", async () => {
    const client = makeClient({
      listConversations: vi.fn().mockRejectedValue(new Error("boom")),
    });

    const { result } = renderConversationsHook(client);

    await waitFor(() => {
      expect(client.listConversations).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(result.current.error).toBe("boom");
    });
  });

  it("clears the URL when the selected conversation no longer exists", async () => {
    searchParams = new URLSearchParams("conversation=missing");
    const client = makeClient({
      listConversations: vi.fn().mockResolvedValue({
        items: [makeConversation("conv-1")],
        next_cursor: null,
        has_more: false,
      }),
      getConversation: vi.fn().mockRejectedValue(new ApiError("Conversation not found", 404, "CHATBOT_CONVERSATION_NOT_FOUND")),
    });

    const { result } = renderConversationsHook(client);

    await waitFor(() => {
      expect(result.current.selectedConversationId).toBe(null);
    });

    expect(replace).toHaveBeenCalledWith("/chat-bot");
  });

  it("ignores a stale conversation detail response after a newer selection", async () => {
    const first = deferred<ConversationDetailData>();
    const second = deferred<ConversationDetailData>();
    const client = makeClient({
      listConversations: vi.fn().mockResolvedValue({
        items: [],
        next_cursor: null,
        has_more: false,
      }),
      getConversation: vi
        .fn()
        .mockImplementationOnce(() => first.promise)
        .mockImplementationOnce(() => second.promise),
    });
    const { result } = renderConversationsHook(client);

    await waitFor(() => expect(client.listConversations).toHaveBeenCalledTimes(1));

    let firstSelection!: Promise<ConversationDetailData | null>;
    let secondSelection!: Promise<ConversationDetailData | null>;
    act(() => {
      firstSelection = result.current.openConversation("conv-a");
      secondSelection = result.current.openConversation("conv-b");
    });

    await act(async () => {
      second.resolve(makeDetail("conv-b", { title: "Newest" }));
      await secondSelection;
    });
    await act(async () => {
      first.resolve(makeDetail("conv-a", { title: "Stale" }));
      await firstSelection;
    });

    expect(result.current.selectedConversationId).toBe("conv-b");
    expect(result.current.selectedConversation?.title).toBe("Newest");
    expect(push).toHaveBeenLastCalledWith("/chat-bot?conversation=conv-b");
  });

  it("hydrates from session storage without refetching when the page is already cached", async () => {
    const snapshot = {
      version: 2,
      state: {
        selectedStatus: "archived",
        selectedConversationId: "conv-9",
        pages: {
          active: {
            items: [],
            nextCursor: null,
            hasMore: false,
            loaded: false,
          },
          archived: {
            items: [makeConversation("conv-9", { status: "archived", title: "Archived memory" })],
            nextCursor: null,
            hasMore: false,
            loaded: true,
          },
        },
      },
    };
    window.sessionStorage.setItem("chatbot:test", JSON.stringify(snapshot));
    const client = makeClient();

    const { result } = renderConversationsHook(client);

    await waitFor(() => {
      expect(result.current.selectedConversationId).toBe("conv-9");
    });
    expect(result.current.selectedConversation?.title).toBe("Archived memory");
    expect(client.listConversations).not.toHaveBeenCalled();
  });

  it("rejects legacy snapshots that contain a deleted page", async () => {
    window.sessionStorage.setItem(
      "chatbot:test",
      JSON.stringify({
        version: 1,
        state: {
          selectedStatus: "deleted",
          selectedConversationId: "conv-deleted",
          pages: {
            active: { items: [], nextCursor: null, hasMore: false, loaded: true },
            archived: { items: [], nextCursor: null, hasMore: false, loaded: true },
            deleted: {
              items: [makeConversation("conv-deleted")],
              nextCursor: null,
              hasMore: false,
              loaded: true,
            },
          },
        },
      })
    );
    const client = makeClient({
      listConversations: vi.fn().mockResolvedValue({
        items: [],
        next_cursor: null,
        has_more: false,
      }),
    });

    const { result } = renderConversationsHook(client);

    await waitFor(() => expect(result.current.selectedStatus).toBe("active"));
    expect(result.current.selectedConversationId).toBe(null);
    expect(result.current.pages.active.items).toEqual([]);
    expect(result.current.pages.archived.items).toEqual([]);
  });
});
