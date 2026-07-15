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

function eventBlock(event: string, sequence: number, data: object) {
  return [`id: ${sequence}`, `event: ${event}`, `data: ${JSON.stringify(data)}`, "", ""].join("\n");
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

  it("batches deltas and dispatches terminal callbacks in order", async () => {
    const conversationId = "conv-a";
    const requestId = "req-a";
    const assistantMessageId = "assistant-req-a";
    const base = {
      schema_version: "1",
      request_id: requestId,
      conversation_id: conversationId,
      assistant_message_id: assistantMessageId,
      created_at: "2026-07-15T00:00:00.000Z",
    } as const;
    const body = [
      eventBlock("message.created", 1, {
        ...base,
        sequence: 1,
        replayed: false,
        user_message: {
          id: "user-req-a",
          sequence_number: 1,
          status: "completed",
          content: "hello",
          model: null,
          updated_at: base.created_at,
        },
        assistant_message: {
          id: assistantMessageId,
          sequence_number: 2,
          status: "pending",
          content: "",
          model: "deepseek-chat",
          updated_at: base.created_at,
        },
      }),
      eventBlock("message.delta", 2, { ...base, sequence: 2, delta: "Hel", content_length: 3 }),
      eventBlock("message.delta", 3, { ...base, sequence: 3, delta: "lo", content_length: 5 }),
      eventBlock("message.completed", 4, {
        ...base,
        sequence: 4,
        message: {
          id: assistantMessageId,
          status: "completed",
          content: "Hello",
          sequence_number: 2,
          model: "deepseek-chat",
          updated_at: base.created_at,
        },
        finish_reason: "stop",
      }),
      eventBlock("stream.end", 5, { ...base, sequence: 5, final_status: "completed" }),
    ].join("");
    streamMocks.openChatStream.mockResolvedValue(
      new Response(body, { headers: { "Content-Type": "text/event-stream" } })
    );
    const order: string[] = [];
    const onEvent = vi.fn((event: { event: string }) => order.push(`event:${event.event}`));
    const onTerminal = vi.fn((event: { event: string }) => order.push(`terminal:${event.event}`));
    const { result } = renderHook(() =>
      useChatStream({ token: "token", conversationId, onEvent, onTerminal })
    );

    await act(async () => {
      await result.current.sendMessage("hello", requestId);
    });

    const deltaEvents = onEvent.mock.calls
      .map(([event]) => event)
      .filter((event) => event.event === "message.delta");
    expect(deltaEvents).toHaveLength(1);
    expect((deltaEvents[0].data as { delta: string }).delta).toBe("Hello");
    expect(order.slice(-2)).toEqual(["event:stream.end", "terminal:stream.end"]);
  });
});
