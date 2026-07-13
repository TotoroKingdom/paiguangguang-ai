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
});
