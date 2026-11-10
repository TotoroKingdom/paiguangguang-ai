import { afterEach, describe, expect, it, vi } from "vitest";
import { createConversation, getConversation, listConversations, streamRun } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("assistant API client", () => {
  it("sends same-origin credentials and maps conversation summaries", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "conversation-1",
          title: "新对话",
          createdAt: "2026-01-01T00:00:00Z",
          updatedAt: "2026-01-01T00:00:00Z",
          version: 1,
        }),
        { status: 201, headers: { "content-type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const conversation = await createConversation();

    expect(conversation.messages).toEqual([]);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/conversations",
      expect.objectContaining({ credentials: "same-origin", method: "POST" }),
    );
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ title: "新对话" });
  });

  it("follows metadata cursors without loading message bodies", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [{ id: "1", title: "一", createdAt: "2026-01-01T00:00:00Z", updatedAt: "2026-01-01T00:00:00Z", version: 1 }],
            nextCursor: "next",
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            items: [{ id: "2", title: "二", createdAt: "2026-01-01T00:00:00Z", updatedAt: "2026-01-01T00:00:00Z", version: 1 }],
            nextCursor: null,
          }),
          { status: 200 },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    const conversations = await listConversations();

    expect(conversations.map((item) => item.id)).toEqual(["1", "2"]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1][0]).toContain("cursor=next");
  });

  it("preserves a server error status for retry decisions", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "冲突" }), { status: 409 }),
      ),
    );

    await expect(getConversation("missing")).rejects.toMatchObject({
      status: 409,
      retryable: false,
      message: "这条聊天已被其他页面更新，请刷新后重试。",
    });
  });

  it("does not send a client-selected provider mode for runtime execution", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response('data: {"type":"done","status":"completed"}\n\n', { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await streamRun(
      {
        conversationId: "conversation-1",
        clientTurnId: "turn-1",
        text: "使用服务端模型",
        capability: null,
        fileIds: [],
      },
      vi.fn(),
    );

    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string) as Record<string, unknown>;
    expect(body).not.toHaveProperty("mode");
  });
});
