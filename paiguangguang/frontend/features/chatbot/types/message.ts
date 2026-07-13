export type MessageRole = "user" | "assistant" | "system" | "tool";

export type MessageStatus = "pending" | "streaming" | "completed" | "failed" | "cancelled";

export type MessageData = {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  content_json: Record<string, unknown> | null;
  sequence_number: number;
  status: MessageStatus;
  model: string | null;
  parent_message_id: string | null;
  client_request_id: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  error_code: string | null;
  created_at: string;
  updated_at: string;
};

export type MessagePageData = {
  items: MessageData[];
  next_cursor: string | null;
  has_more: boolean;
};

export type ChatRequest = {
  content: string;
  client_request_id: string;
};

export type GenerationRequest = {
  client_request_id: string;
};

export type StopGenerationRequest = {
  assistant_message_id?: string | null;
};

export type StopGenerationData = {
  conversation_id: string;
  assistant_message_id: string;
  status: "cancellation_requested" | "cancelled" | "already_terminal";
};
