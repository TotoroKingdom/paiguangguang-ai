import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  getJson: vi.fn(),
  patchJson: vi.fn(),
  deleteJson: vi.fn(),
}));

vi.mock("@/lib/api", () => apiMocks);

import { memoryApiClient } from "../api/memories";

describe("memory API path contract", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getJson.mockResolvedValue({});
    apiMocks.patchJson.mockResolvedValue({});
    apiMocks.deleteJson.mockResolvedValue({});
  });

  it("covers list filters, detail, update, and delete", async () => {
    await memoryApiClient.listMemories({
      token: "token",
      status: "active",
      memoryType: "project_context",
      conversationId: "conv-1",
      cursor: "cursor-1",
      limit: 20,
    });
    await memoryApiClient.getMemory({ token: "token", memoryId: "memory-1" });
    await memoryApiClient.updateMemory(
      { token: "token", memoryId: "memory-1" },
      { content: "Updated", status: "active", expires_at: null }
    );
    await memoryApiClient.deleteMemory({ token: "token", memoryId: "memory-1" });

    expect(apiMocks.getJson).toHaveBeenNthCalledWith(
      1,
      "/api/v1/chatbot/memories?status=active&memory_type=project_context&conversation_id=conv-1&limit=20&cursor=cursor-1",
      { token: "token" }
    );
    expect(apiMocks.getJson).toHaveBeenNthCalledWith(
      2,
      "/api/v1/chatbot/memories/memory-1",
      { token: "token" }
    );
    expect(apiMocks.patchJson).toHaveBeenCalledWith(
      "/api/v1/chatbot/memories/memory-1",
      { content: "Updated", status: "active", expires_at: null },
      { token: "token" }
    );
    expect(apiMocks.deleteJson).toHaveBeenCalledWith(
      "/api/v1/chatbot/memories/memory-1",
      { token: "token" }
    );
  });
});
