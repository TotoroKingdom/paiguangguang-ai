import { render, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChatbotStoreProvider } from "../stores/chatbot-store";

describe("ChatbotStoreProvider persistence lifecycle", () => {
  it("removes the authenticated snapshot when persistence is disabled", async () => {
    const storageKey = "paiguangguang.chatbot:user-123";
    window.sessionStorage.setItem(storageKey, JSON.stringify({
      version: 2,
      state: {
        selectedStatus: "active",
        selectedConversationId: null,
        pages: {
          active: { items: [], nextCursor: null, hasMore: false, loaded: false },
          archived: { items: [], nextCursor: null, hasMore: false, loaded: false },
        },
      },
    }));

    const { rerender } = render(
      <ChatbotStoreProvider storageKey={storageKey}>
        <div>workspace</div>
      </ChatbotStoreProvider>
    );

    rerender(
      <ChatbotStoreProvider storageKey={null}>
        <div>workspace</div>
      </ChatbotStoreProvider>
    );

    await waitFor(() => expect(window.sessionStorage.getItem(storageKey)).toBeNull());
  });
});
