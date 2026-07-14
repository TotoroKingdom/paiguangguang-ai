import { describe, expect, it } from "vitest";

import { readChatStreamEvents } from "../api/stream";
import { createInitialChatStreamState, mergeChatStreamEvent } from "../utils/merge-stream-event";
import type { ParsedChatStreamEvent } from "../types/stream";

function makeStream(chunks: string[]) {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      const encoder = new TextEncoder();
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

function createdEvent(requestId: string, conversationId: string, suffix: string) {
  return {
    event: "message.created" as const,
    sequence: 1,
    data: {
      schema_version: "1" as const,
      request_id: requestId,
      conversation_id: conversationId,
      assistant_message_id: `assistant-${suffix}`,
      sequence: 1,
      created_at: "2026-07-14T00:00:00.000Z",
      replayed: false,
      user_message: {
        id: `user-${suffix}`,
        sequence_number: suffix === "1" ? 1 : 3,
        status: "completed" as const,
        content: `question-${suffix}`,
        model: null,
        updated_at: "2026-07-14T00:00:00.000Z",
      },
      assistant_message: {
        id: `assistant-${suffix}`,
        sequence_number: suffix === "1" ? 2 : 4,
        status: "pending" as const,
        content: "",
        model: "deepseek-chat",
        updated_at: "2026-07-14T00:00:00.000Z",
      },
    },
  };
}

describe("chat stream utilities", () => {
  it("parses chunked SSE blocks across boundaries", async () => {
    const response = new Response(
      makeStream([
        "id: 1\nevent: message.created\ndata: {\"schema_version\":\"1\",\"request_id\":\"req-1\",\"conversation_id\":\"conv-1\",\"assistant_message_id\":\"msg-assistant\",\"sequence\":1,\"created_at\":\"2026-07-13T10:00:00.000Z\",\"replayed\":false,\"user_message\":{\"id\":\"msg-user\",\"sequence_number\":1,\"status\":\"completed\",\"content\":\"Hello\",\"model\":null,\"updated_at\":\"2026-07-13T10:00:00.000Z\"},\"assistant_message\":{\"id\":\"msg-assistant\",\"sequence_number\":2,\"status\":\"pending\",\"content\":\"\",\"model\":\"deepseek-chat\",\"updated_at\":\"2026-07-13T10:00:00.000Z\"}}\n\n",
        "id: 2\nevent: message.del",
        "ta\ndata: {\"schema_version\":\"1\",\"request_id\":\"req-1\",\"conversation_id\":\"conv-1\",\"assistant_message_id\":\"msg-assistant\",\"sequence\":2,\"created_at\":\"2026-07-13T10:00:01.000Z\",\"delta\":\" world\",\"content_length\":11}\n\n",
        "id: 3\nevent: stream.end\ndata: {\"schema_version\":\"1\",\"request_id\":\"req-1\",\"conversation_id\":\"conv-1\",\"assistant_message_id\":\"msg-assistant\",\"sequence\":3,\"created_at\":\"2026-07-13T10:00:02.000Z\",\"final_status\":\"completed\"}\n\n",
      ]),
      {
        headers: { "Content-Type": "text/event-stream" },
      }
    );

    const events: ParsedChatStreamEvent[] = [];
    for await (const event of readChatStreamEvents(response)) {
      events.push(event);
    }

    expect(events).toHaveLength(3);
    expect(events[0].event).toBe("message.created");
    expect(events[1].event).toBe("message.delta");
    expect(events[1].sequence).toBe(2);
    expect(events[2].event).toBe("stream.end");
  });

  it("merges stream deltas and final status without duplicating sequence events", () => {
    const created = {
      event: "message.created" as const,
      sequence: 1,
      data: {
        schema_version: "1" as const,
        request_id: "req-1",
        conversation_id: "conv-1",
        assistant_message_id: "msg-assistant",
        sequence: 1,
        created_at: "2026-07-13T10:00:00.000Z",
        replayed: false,
        user_message: {
          id: "msg-user",
          sequence_number: 1,
          status: "completed" as const,
          content: "Hello",
          model: null,
          updated_at: "2026-07-13T10:00:00.000Z",
        },
        assistant_message: {
          id: "msg-assistant",
          sequence_number: 2,
          status: "pending" as const,
          content: "",
          model: "deepseek-chat",
          updated_at: "2026-07-13T10:00:00.000Z",
        },
      },
    };
    const delta = {
      event: "message.delta" as const,
      sequence: 2,
      data: {
        schema_version: "1" as const,
        request_id: "req-1",
        conversation_id: "conv-1",
        assistant_message_id: "msg-assistant",
        sequence: 2,
        created_at: "2026-07-13T10:00:01.000Z",
        delta: " world",
        content_length: 11,
      },
    };
    const completed = {
      event: "message.completed" as const,
      sequence: 3,
      data: {
        schema_version: "1" as const,
        request_id: "req-1",
        conversation_id: "conv-1",
        assistant_message_id: "msg-assistant",
        sequence: 3,
        created_at: "2026-07-13T10:00:02.000Z",
        message: {
          id: "msg-assistant",
          status: "completed" as const,
          content: "Hello world",
          sequence_number: 2,
          model: "deepseek-chat",
          updated_at: "2026-07-13T10:00:02.000Z",
        },
        finish_reason: "stop",
      },
    };

    const stateAfterCreated = mergeChatStreamEvent(createInitialChatStreamState(), created);
    expect(stateAfterCreated.messages).toHaveLength(2);
    expect(stateAfterCreated.messages[1].content).toBe("");

    const stateAfterDelta = mergeChatStreamEvent(stateAfterCreated, delta);
    expect(stateAfterDelta.messages[1].content).toBe(" world");

    const stateAfterCompleted = mergeChatStreamEvent(stateAfterDelta, completed);
    expect(stateAfterCompleted.messages[1].content).toBe("Hello world");
    expect(stateAfterCompleted.phase).toBe("completed");

    const deduped = mergeChatStreamEvent(stateAfterCompleted, completed);
    expect(deduped.messages).toHaveLength(2);
  });

  it("resets sequence deduplication for a new request", () => {
    const initial = createInitialChatStreamState([], "conv-1");
    const firstCreated = mergeChatStreamEvent(initial, createdEvent("req-1", "conv-1", "1"));
    const firstEnd = mergeChatStreamEvent(firstCreated, {
      event: "stream.end",
      sequence: 5,
      data: {
        schema_version: "1",
        request_id: "req-1",
        conversation_id: "conv-1",
        assistant_message_id: "assistant-1",
        sequence: 5,
        created_at: "2026-07-14T00:00:01.000Z",
        final_status: "completed",
      },
    });

    const secondCreated = mergeChatStreamEvent(
      firstEnd,
      createdEvent("req-2", "conv-1", "2")
    );
    const secondDelta = mergeChatStreamEvent(secondCreated, {
      event: "message.delta",
      sequence: 2,
      data: {
        schema_version: "1",
        request_id: "req-2",
        conversation_id: "conv-1",
        assistant_message_id: "assistant-2",
        sequence: 2,
        created_at: "2026-07-14T00:00:02.000Z",
        delta: "second answer",
        content_length: 13,
      },
    });

    expect(secondCreated.lastSequence).toBe(1);
    expect(secondDelta.messages.find((item) => item.id === "assistant-2")?.content).toBe(
      "second answer"
    );
  });

  it("ignores events from another conversation or inactive request", () => {
    const current = mergeChatStreamEvent(
      createInitialChatStreamState([], "conv-b"),
      createdEvent("req-b", "conv-b", "2")
    );

    const staleConversation = mergeChatStreamEvent(current, {
      event: "message.delta",
      sequence: 9,
      data: {
        schema_version: "1",
        request_id: "req-a",
        conversation_id: "conv-a",
        assistant_message_id: "assistant-a",
        sequence: 9,
        created_at: "2026-07-14T00:00:03.000Z",
        delta: "stale",
        content_length: 5,
      },
    });
    const staleRequest = mergeChatStreamEvent(current, {
      event: "message.delta",
      sequence: 9,
      data: {
        schema_version: "1",
        request_id: "req-a",
        conversation_id: "conv-b",
        assistant_message_id: "assistant-a",
        sequence: 9,
        created_at: "2026-07-14T00:00:03.000Z",
        delta: "stale",
        content_length: 5,
      },
    });

    expect(staleConversation).toBe(current);
    expect(staleRequest).toBe(current);
  });
});
