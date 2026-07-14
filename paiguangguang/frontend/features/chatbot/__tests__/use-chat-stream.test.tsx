import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const streamMocks = vi.hoisted(() => ({
  openChatStream: vi.fn(),
  openRetryStream: vi.fn(),
  openRegenerateStream: vi.fn(),
}));

vi.mock("../api/stream", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/stream")>();
  return { ...original, ...streamMocks };
});

import { useChatStream } from "../hooks/use-chat-stream";

function sseBlock(conversationId: string, requestId: string, sequence: number, delta: string) {
  return [
    `id: ${sequence}`,
    "event: message.delta",
    `data: ${JSON.stringify({
      schema_version: "1",
      request_id: requestId,
      conversation_id: conversationId,
      assistant_message_id: `assistant-${requestId}`,
      sequence,
      created_at: "2026-07-14T00:00:00.000Z",
      delta,
      content_length: delta.length,
    })}`,
    "",
    "",
  ].join("\n");
}

describe("useChatStream", () => {
  beforeEach(() => vi.clearAllMocks());

  it("detaches the old reader when conversation changes", async () => {
    let oldController: ReadableStreamDefaultController<Uint8Array>;
    const encoder = new TextEncoder();
    const response = new Response(
      new ReadableStream<Uint8Array>({
        start(controller) {
          oldController = controller;
        },
      }),
      { headers: { "Content-Type": "text/event-stream" } }
    );
    streamMocks.openChatStream.mockResolvedValue(response);
    const onEvent = vi.fn();
    const onFailure = vi.fn();

    const { result, rerender } = renderHook(
      ({ conversationId }) =>
        useChatStream({ token: "token", conversationId, onEvent, onFailure }),
      { initialProps: { conversationId: "conv-a" } }
    );

    let pending: Promise<boolean>;
    act(() => {
      pending = result.current.sendMessage("hello", "req-a");
    });
    await waitFor(() => expect(streamMocks.openChatStream).toHaveBeenCalledTimes(1));

    rerender({ conversationId: "conv-b" });
    act(() => {
      oldController!.enqueue(encoder.encode(sseBlock("conv-a", "req-a", 2, "late")));
      oldController!.close();
    });
    await act(async () => {
      await pending!;
    });

    expect(onEvent).not.toHaveBeenCalled();
    expect(onFailure).not.toHaveBeenCalled();
  });

  it("detaches the active reader when authentication is cleared", async () => {
    let controller: ReadableStreamDefaultController<Uint8Array>;
    const response = new Response(new ReadableStream<Uint8Array>({
      start(nextController) {
        controller = nextController;
      },
    }), { headers: { "Content-Type": "text/event-stream" } });
    streamMocks.openChatStream.mockResolvedValue(response);
    const onEvent = vi.fn();

    const { result, rerender } = renderHook(
      ({ token }) => useChatStream({ token, conversationId: "conv-a", onEvent }),
      { initialProps: { token: "token" as string | null } }
    );

    let pending: Promise<boolean>;
    act(() => {
      pending = result.current.sendMessage("hello", "req-a");
    });
    await waitFor(() => expect(streamMocks.openChatStream).toHaveBeenCalledTimes(1));

    rerender({ token: null });
    act(() => controller!.close());
    await act(async () => {
      await pending!;
    });

    expect(onEvent).not.toHaveBeenCalled();
    expect(result.current.sending).toBe(false);
  });
});
