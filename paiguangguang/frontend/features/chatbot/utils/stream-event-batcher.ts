import type { ParsedChatStreamEvent } from "../types/stream";

type DeltaEvent = Extract<ParsedChatStreamEvent, { event: "message.delta" }>;

type ChatStreamEventBatcherOptions = {
  emit: (event: ParsedChatStreamEvent) => void;
  delayMs?: number;
};

export type ChatStreamEventBatcher = {
  push: (event: ParsedChatStreamEvent) => void;
  flush: () => void;
  clear: () => void;
};

function isDeltaEvent(event: ParsedChatStreamEvent): event is DeltaEvent {
  if (event.event !== "message.delta" || typeof event.data !== "object" || event.data === null) {
    return false;
  }
  const data = event.data as Record<string, unknown>;
  return (
    typeof data.request_id === "string" &&
    typeof data.assistant_message_id === "string" &&
    typeof data.delta === "string"
  );
}

export function createChatStreamEventBatcher({
  emit,
  delayMs = 40,
}: ChatStreamEventBatcherOptions): ChatStreamEventBatcher {
  let pendingDelta: DeltaEvent | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;

  const cancelTimer = () => {
    if (timer !== null) {
      clearTimeout(timer);
    }
    timer = null;
  };

  const flush = () => {
    cancelTimer();
    if (pendingDelta === null) {
      return;
    }
    const event = pendingDelta;
    pendingDelta = null;
    emit(event);
  };

  const clear = () => {
    cancelTimer();
    pendingDelta = null;
  };

  const schedule = () => {
    if (timer === null) {
      timer = setTimeout(flush, delayMs);
    }
  };

  const push = (event: ParsedChatStreamEvent) => {
    if (!isDeltaEvent(event)) {
      flush();
      emit(event);
      return;
    }

    if (
      pendingDelta !== null &&
      pendingDelta.data.request_id === event.data.request_id &&
      pendingDelta.data.assistant_message_id === event.data.assistant_message_id
    ) {
      pendingDelta = {
        ...event,
        data: {
          ...event.data,
          delta: `${pendingDelta.data.delta}${event.data.delta}`,
        },
      };
    } else {
      flush();
      pendingDelta = event;
    }
    schedule();
  };

  return { push, flush, clear };
}
