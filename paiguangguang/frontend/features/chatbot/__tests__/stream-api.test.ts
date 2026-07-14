import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  getBackendBaseUrl: vi.fn(() => "http://backend.test"),
  getJson: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, ...apiMocks };
});

import {
  listMessages,
  openChatStream,
  openRegenerateStream,
  openRetryStream,
} from "../api/stream";

describe("chatbot message API path contract", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getJson.mockResolvedValue({
      items: [],
      next_cursor: null,
      has_more: false,
    });
    fetchMock.mockResolvedValue(
      new Response(null, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("covers message history and all three streaming generation routes", async () => {
    await listMessages({
      token: "token",
      conversationId: "conv-1",
      limit: 50,
      before: "cursor-1",
    });
    await openChatStream({
      token: "token",
      conversationId: "conv-1",
      content: "Hello",
      clientRequestId: "request-send",
    });
    await openRetryStream({
      token: "token",
      conversationId: "conv-1",
      messageId: "message-1",
      clientRequestId: "request-retry",
    });
    await openRegenerateStream({
      token: "token",
      conversationId: "conv-1",
      messageId: "message-1",
      clientRequestId: "request-regenerate",
    });

    expect(apiMocks.getJson).toHaveBeenCalledWith(
      "/api/v1/chatbot/conversations/conv-1/messages?limit=50&before=cursor-1",
      { token: "token" }
    );
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "http://backend.test/api/v1/chatbot/conversations/conv-1/messages",
      "http://backend.test/api/v1/chatbot/conversations/conv-1/messages/message-1/retry",
      "http://backend.test/api/v1/chatbot/conversations/conv-1/messages/message-1/regenerate",
    ]);

    const sendInit = fetchMock.mock.calls[0][1] as RequestInit;
    expect(sendInit.method).toBe("POST");
    expect(JSON.parse(String(sendInit.body))).toEqual({
      content: "Hello",
      client_request_id: "request-send",
    });
    expect((sendInit.headers as Headers).get("Idempotency-Key")).toBe("request-send");
    expect((sendInit.headers as Headers).get("Authorization")).toBe("Bearer token");

    const retryInit = fetchMock.mock.calls[1][1] as RequestInit;
    expect(JSON.parse(String(retryInit.body))).toEqual({
      client_request_id: "request-retry",
    });
    expect((retryInit.headers as Headers).get("Idempotency-Key")).toBe("request-retry");

    const regenerateInit = fetchMock.mock.calls[2][1] as RequestInit;
    expect(JSON.parse(String(regenerateInit.body))).toEqual({
      client_request_id: "request-regenerate",
    });
    expect((regenerateInit.headers as Headers).get("Idempotency-Key")).toBe(
      "request-regenerate"
    );
  });
});
