import type { MessageData } from "../types/message";
import type {
  ParsedChatStreamEvent,
  StreamErrorData,
  StreamMessageCreatedData,
} from "../types/stream";

export type ChatStreamPhase = "idle" | "streaming" | "completed" | "failed" | "cancelled";

export type ChatStreamState = {
  messages: MessageData[];
  conversationId: string | null;
  activeRequestId: string | null;
  activeAssistantMessageId: string | null;
  lastSequence: number;
  phase: ChatStreamPhase;
  error: StreamErrorData | null;
};

function toTimestamp(value: string | null | undefined) {
  return value ?? new Date().toISOString();
}

function compareMessages(left: MessageData, right: MessageData) {
  if (left.sequence_number !== right.sequence_number) {
    return left.sequence_number - right.sequence_number;
  }
  return left.id.localeCompare(right.id);
}

function sortMessages(messages: MessageData[]) {
  return [...messages].sort(compareMessages);
}

function upsertMessage(messages: MessageData[], message: MessageData) {
  const existingIndex = messages.findIndex((item) => item.id === message.id);
  if (existingIndex >= 0) {
    const nextMessages = [...messages];
    nextMessages[existingIndex] = {
      ...nextMessages[existingIndex],
      ...message,
    };
    return sortMessages(nextMessages);
  }
  return sortMessages([...messages, message]);
}

function updateAssistantMessage(
  messages: MessageData[],
  assistantMessageId: string,
  updater: (message: MessageData) => MessageData
) {
  const index = messages.findIndex((message) => message.id === assistantMessageId);
  if (index < 0) {
    return messages;
  }
  const nextMessages = [...messages];
  nextMessages[index] = updater(nextMessages[index]);
  return sortMessages(nextMessages);
}

function createMessageFromSnapshot(
  snapshot: StreamMessageCreatedData,
  requestId: string,
  role: "user" | "assistant"
): MessageData {
  const message = role === "user" ? snapshot.user_message : snapshot.assistant_message;
  return {
    id: message.id,
    conversation_id: snapshot.conversation_id,
    role,
    content: message.content,
    content_json: null,
    sequence_number: message.sequence_number,
    status: message.status,
    model: message.model,
    parent_message_id: role === "assistant" ? snapshot.user_message.id : null,
    client_request_id: requestId,
    prompt_tokens: 0,
    completion_tokens: 0,
    total_tokens: 0,
    error_code: null,
    created_at: toTimestamp(message.updated_at ?? snapshot.created_at),
    updated_at: toTimestamp(message.updated_at ?? snapshot.created_at),
  };
}

function hasRequestId(data: unknown): data is { request_id: string } {
  return !!data && typeof data === "object" && "request_id" in data && typeof (data as { request_id?: unknown }).request_id === "string";
}

function hasConversationId(data: unknown): data is { conversation_id: string } {
  return Boolean(
    data &&
      typeof data === "object" &&
      "conversation_id" in data &&
      typeof (data as { conversation_id?: unknown }).conversation_id === "string"
  );
}

export function createInitialChatStreamState(
  messages: MessageData[] = [],
  conversationId: string | null = null
): ChatStreamState {
  return {
    messages: sortMessages(messages),
    conversationId,
    activeRequestId: null,
    activeAssistantMessageId: null,
    lastSequence: 0,
    phase: "idle",
    error: null,
  };
}

export function mergeChatStreamEvent(
  state: ChatStreamState,
  event: ParsedChatStreamEvent
): ChatStreamState {
  const requestId = hasRequestId(event.data) ? event.data.request_id : null;
  const eventConversationId = hasConversationId(event.data) ? event.data.conversation_id : null;

  if (
    state.conversationId !== null &&
    eventConversationId !== null &&
    eventConversationId !== state.conversationId
  ) {
    return state;
  }

  if (event.event === "message.created") {
    const data = event.data as StreamMessageCreatedData;
    if (state.activeRequestId === data.request_id && event.sequence <= state.lastSequence) {
      return state;
    }
    const userMessage = createMessageFromSnapshot(data, data.request_id, "user");
    const assistantMessage = createMessageFromSnapshot(data, data.request_id, "assistant");
    return {
      ...state,
      messages: upsertMessage(upsertMessage(state.messages, userMessage), assistantMessage),
      conversationId: data.conversation_id,
      activeRequestId: data.request_id,
      activeAssistantMessageId: data.assistant_message_id,
      lastSequence: event.sequence,
      phase: assistantMessage.status === "completed" ? "completed" : "streaming",
      error: null,
    };
  }

  if (requestId === null || requestId !== state.activeRequestId) {
    return state;
  }
  if (event.sequence > 0 && event.sequence <= state.lastSequence) {
    return state;
  }

  if (event.event === "message.delta") {
    const data = event.data as Extract<ParsedChatStreamEvent, { event: "message.delta" }>["data"];
    const nextMessages = updateAssistantMessage(state.messages, data.assistant_message_id, (message) => ({
      ...message,
      content: message.content.length >= data.content_length ? message.content : `${message.content}${data.delta}`,
      status: "streaming",
      updated_at: data.created_at,
    }));
    return {
      ...state,
      messages: nextMessages,
      activeRequestId: data.request_id,
      activeAssistantMessageId: data.assistant_message_id,
      lastSequence: Math.max(state.lastSequence, event.sequence),
      phase: "streaming",
      error: null,
    };
  }

  if (event.event === "message.completed") {
    const data = event.data as Extract<ParsedChatStreamEvent, { event: "message.completed" }>["data"];
    const nextMessages = updateAssistantMessage(state.messages, data.assistant_message_id, (message) => ({
      ...message,
      content: data.message.content,
      sequence_number: data.message.sequence_number,
      status: "completed",
      model: data.message.model,
      updated_at: data.message.updated_at,
    }));
    return {
      ...state,
      messages: nextMessages,
      activeRequestId: data.request_id,
      activeAssistantMessageId: data.assistant_message_id,
      lastSequence: Math.max(state.lastSequence, event.sequence),
      phase: "completed",
      error: null,
    };
  }

  if (event.event === "message.failed") {
    const data = event.data as Extract<ParsedChatStreamEvent, { event: "message.failed" }>["data"];
    const nextMessages = updateAssistantMessage(state.messages, data.assistant_message_id, (message) => ({
      ...message,
      content: data.content,
      status: "failed",
      error_code: data.error.code,
      updated_at: data.created_at,
    }));
    return {
      ...state,
      messages: nextMessages,
      activeRequestId: data.request_id,
      activeAssistantMessageId: data.assistant_message_id,
      lastSequence: Math.max(state.lastSequence, event.sequence),
      phase: "failed",
      error: data.error,
    };
  }

  if (event.event === "message.cancelled") {
    const data = event.data as Extract<ParsedChatStreamEvent, { event: "message.cancelled" }>["data"];
    const nextMessages = updateAssistantMessage(state.messages, data.assistant_message_id, (message) => ({
      ...message,
      content: data.content,
      status: "cancelled",
      updated_at: data.created_at,
    }));
    return {
      ...state,
      messages: nextMessages,
      activeRequestId: data.request_id,
      activeAssistantMessageId: data.assistant_message_id,
      lastSequence: Math.max(state.lastSequence, event.sequence),
      phase: "cancelled",
      error: null,
    };
  }

  if (event.event === "usage.updated") {
    const data = event.data as Extract<ParsedChatStreamEvent, { event: "usage.updated" }>["data"];
    const nextMessages = updateAssistantMessage(state.messages, data.assistant_message_id, (message) => ({
      ...message,
      prompt_tokens: data.prompt_tokens ?? message.prompt_tokens,
      completion_tokens: data.completion_tokens ?? message.completion_tokens,
      total_tokens: data.total_tokens ?? message.total_tokens,
      updated_at: data.created_at,
    }));
    return {
      ...state,
      messages: nextMessages,
      activeRequestId: data.request_id,
      activeAssistantMessageId: data.assistant_message_id,
      lastSequence: Math.max(state.lastSequence, event.sequence),
      phase: state.phase,
      error: state.error,
    };
  }

  if (event.event === "stream.end") {
    const data = event.data as Extract<ParsedChatStreamEvent, { event: "stream.end" }>["data"];
    return {
      ...state,
      messages: state.messages,
      activeRequestId: null,
      activeAssistantMessageId: data.assistant_message_id,
      lastSequence: Math.max(state.lastSequence, event.sequence),
      phase: data.final_status,
      error: state.error,
    };
  }

  return state;
}

export function mergeMessageHistory(messages: MessageData[], incoming: MessageData[]) {
  const merged = new Map<string, MessageData>();
  for (const message of messages) {
    merged.set(message.id, message);
  }
  for (const message of incoming) {
    merged.set(message.id, message);
  }
  return sortMessages(Array.from(merged.values()));
}
