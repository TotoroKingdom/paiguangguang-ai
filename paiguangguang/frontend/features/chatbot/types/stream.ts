import type { MessageData, MessageStatus } from "./message";

export type StreamSchemaVersion = "1";

export type StreamEventName =
  | "message.created"
  | "message.delta"
  | "message.completed"
  | "message.failed"
  | "message.cancelled"
  | "usage.updated"
  | "stream.end";

export type StreamMessageSnapshot = Pick<
  MessageData,
  "id" | "sequence_number" | "status" | "content" | "model" | "updated_at"
> & {
  updated_at: string | null;
};

export type StreamMessageCreatedData = {
  schema_version: StreamSchemaVersion;
  request_id: string;
  conversation_id: string;
  assistant_message_id: string;
  sequence: number;
  created_at: string;
  replayed: boolean;
  user_message: StreamMessageSnapshot;
  assistant_message: StreamMessageSnapshot;
};

export type StreamMessageDeltaData = {
  schema_version: StreamSchemaVersion;
  request_id: string;
  conversation_id: string;
  assistant_message_id: string;
  sequence: number;
  created_at: string;
  delta: string;
  content_length: number;
};

export type StreamMessageCompletedData = {
  schema_version: StreamSchemaVersion;
  request_id: string;
  conversation_id: string;
  assistant_message_id: string;
  sequence: number;
  created_at: string;
  message: {
    id: string;
    status: "completed";
    content: string;
    sequence_number: number;
    model: string | null;
    updated_at: string;
  };
  finish_reason: string | null;
};

export type StreamErrorData = {
  code: string;
  message: string;
  retryable: boolean;
};

export type StreamMessageFailedData = {
  schema_version: StreamSchemaVersion;
  request_id: string;
  conversation_id: string;
  assistant_message_id: string;
  sequence: number;
  created_at: string;
  error: StreamErrorData;
  partial: boolean;
  content: string;
};

export type StreamMessageCancelledData = {
  schema_version: StreamSchemaVersion;
  request_id: string;
  conversation_id: string;
  assistant_message_id: string;
  sequence: number;
  created_at: string;
  reason: "user_requested";
  content: string;
};

export type StreamUsageUpdatedData = {
  schema_version: StreamSchemaVersion;
  request_id: string;
  conversation_id: string;
  assistant_message_id: string;
  sequence: number;
  created_at: string;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  source: "provider" | "unknown";
};

export type StreamEndData = {
  schema_version: StreamSchemaVersion;
  request_id: string;
  conversation_id: string;
  assistant_message_id: string;
  sequence: number;
  created_at: string;
  final_status: Extract<MessageStatus, "completed" | "failed" | "cancelled">;
};

export type ChatStreamEventPayload =
  | { event: "message.created"; data: StreamMessageCreatedData; sequence: number }
  | { event: "message.delta"; data: StreamMessageDeltaData; sequence: number }
  | { event: "message.completed"; data: StreamMessageCompletedData; sequence: number }
  | { event: "message.failed"; data: StreamMessageFailedData; sequence: number }
  | { event: "message.cancelled"; data: StreamMessageCancelledData; sequence: number }
  | { event: "usage.updated"; data: StreamUsageUpdatedData; sequence: number }
  | { event: "stream.end"; data: StreamEndData; sequence: number };

export type UnknownChatStreamEventPayload = {
  event: string;
  data: unknown;
  sequence: number;
};

export type ParsedChatStreamEvent = ChatStreamEventPayload | UnknownChatStreamEventPayload;

