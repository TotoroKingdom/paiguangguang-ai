import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  getJson: vi.fn(),
  postJson: vi.fn(),
  patchJson: vi.fn(),
  deleteJson: vi.fn(),
}));

vi.mock("@/lib/api", () => apiMocks);

import {
  archiveConversation,
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
  restoreConversation,
  stopGeneration,
  updateConversation,
} from "../api/client";

describe("chatbot API path contract", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getJson.mockResolvedValue({ items: [], next_cursor: null, has_more: false });
    apiMocks.postJson.mockResolvedValue({});
    apiMocks.patchJson.mockResolvedValue({});
    apiMocks.deleteJson.mockResolvedValue({});
  });

  it("uses /api/v1/chatbot for every conversation operation", async () => {
    await listConversations({ token: "token", status: "active", limit: 20 });
    await getConversation({ token: "token", conversationId: "conv-1" });
    await createConversation({ token: "token" }, { title: "Thread" });
    await updateConversation(
      { token: "token", conversationId: "conv-1" },
      { title: "Renamed" }
    );
    await archiveConversation({ token: "token", conversationId: "conv-1" });
    await restoreConversation({ token: "token", conversationId: "conv-1" });
    await deleteConversation({ token: "token", conversationId: "conv-1" });
    await stopGeneration({
      token: "token",
      conversationId: "conv-1",
      request: { assistant_message_id: "message-1" },
    });

    expect(apiMocks.getJson).toHaveBeenNthCalledWith(
      1,
      "/api/v1/chatbot/conversations?status=active&limit=20",
      { token: "token" }
    );
    expect(apiMocks.getJson).toHaveBeenNthCalledWith(
      2,
      "/api/v1/chatbot/conversations/conv-1",
      { token: "token" }
    );
    expect(apiMocks.postJson.mock.calls[0][0]).toBe("/api/v1/chatbot/conversations");
    expect(apiMocks.patchJson.mock.calls[0][0]).toBe(
      "/api/v1/chatbot/conversations/conv-1"
    );
    expect(apiMocks.postJson.mock.calls[1][0]).toBe(
      "/api/v1/chatbot/conversations/conv-1/archive"
    );
    expect(apiMocks.postJson.mock.calls[2][0]).toBe(
      "/api/v1/chatbot/conversations/conv-1/restore"
    );
    expect(apiMocks.deleteJson.mock.calls[0][0]).toBe(
      "/api/v1/chatbot/conversations/conv-1"
    );
    expect(apiMocks.postJson).toHaveBeenNthCalledWith(
      4,
      "/api/v1/chatbot/conversations/conv-1/stop",
      { assistant_message_id: "message-1" },
      { token: "token" }
    );
  });
});
