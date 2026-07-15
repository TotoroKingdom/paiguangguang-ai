import { afterEach, describe, expect, it, vi } from "vitest";

import type { ParsedChatStreamEvent } from "../types/stream";
import { createChatStreamEventBatcher } from "../utils/stream-event-batcher";

type DeltaEvent = Extract<ParsedChatStreamEvent, { event: "message.delta" }>;
type CompletedEvent = Extract<ParsedChatStreamEvent, { event: "message.completed" }>;

function makeDelta(sequence: number, delta: string, contentLength: number): DeltaEvent {
  return {
    event: "message.delta",
    sequence,
    data: {
      schema_version: "1",
      request_id: "req-1",
      conversation_id: "conv-1",
      assistant_message_id: "assistant-1",
      sequence,
      created_at: `2026-07-15T00:00:${String(sequence).padStart(2, "0")}.000Z`,
      delta,
      content_length: contentLength,
    },
  };
}

function makeCompleted(sequence: number, content: string): CompletedEvent {
  return {
    event: "message.completed",
    sequence,
    data: {
      schema_version: "1",
      request_id: "req-1",
      conversation_id: "conv-1",
      assistant_message_id: "assistant-1",
      sequence,
      created_at: "2026-07-15T00:01:00.000Z",
      message: {
        id: "assistant-1",
        status: "completed",
        content,
        sequence_number: 2,
        model: "deepseek-chat",
        updated_at: "2026-07-15T00:01:00.000Z",
      },
      finish_reason: "stop",
    },
  };
}

describe("createChatStreamEventBatcher", () => {
  afterEach(() => vi.useRealTimers());

  it("coalesces rapid deltas without losing content or order", () => {
    vi.useFakeTimers();
    const emit = vi.fn();
    const batcher = createChatStreamEventBatcher({ emit, delayMs: 40 });

    for (let index = 1; index <= 100; index += 1) {
      batcher.push(makeDelta(index, "x", index));
    }

    expect(emit).not.toHaveBeenCalled();
    vi.advanceTimersByTime(40);
    expect(emit).toHaveBeenCalledTimes(1);
    expect(emit.mock.calls[0][0].data.delta).toBe("x".repeat(100));
    expect(emit.mock.calls[0][0].sequence).toBe(100);
    expect(emit.mock.calls[0][0].data.content_length).toBe(100);
  });

  it("flushes buffered text before a terminal event", () => {
    vi.useFakeTimers();
    const events: ParsedChatStreamEvent[] = [];
    const batcher = createChatStreamEventBatcher({ emit: (event) => events.push(event) });

    batcher.push(makeDelta(2, "Hello", 5));
    batcher.push(makeCompleted(3, "Hello"));

    expect(events.map((event) => event.event)).toEqual(["message.delta", "message.completed"]);
  });

  it("clear discards a detached stream's pending delta", () => {
    vi.useFakeTimers();
    const emit = vi.fn();
    const batcher = createChatStreamEventBatcher({ emit });

    batcher.push(makeDelta(2, "stale", 5));
    batcher.clear();
    vi.runAllTimers();

    expect(emit).not.toHaveBeenCalled();
  });
});
