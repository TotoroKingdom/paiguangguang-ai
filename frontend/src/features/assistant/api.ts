import type {
  CapabilityRef,
  Conversation,
  ChatMessage,
  ExecutionStep,
  SendMessageInput,
} from "./types";

export type ConversationSummary = {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  version: number;
};

export type ApiMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status: ChatMessage["status"];
  steps: ExecutionStep[];
  capability: CapabilityRef | null;
  attachments: { id: string; name: string }[];
  request: SendMessageInput | null;
  clientTurnId: string | null;
  createdAt: string;
  updatedAt: string;
};

export type ApiConversation = ConversationSummary & { messages: ApiMessage[] };

export type ApiCapability = CapabilityRef & {
  description: string;
  category: string;
  icon: string;
  source: "system" | "managed";
  steps: string[];
  tools: string[];
  content: string | null;
  executionMode: "demo" | "simulated";
  visibility: "platform" | "private";
  accessMode: "all_active" | "granted";
  authorized: boolean;
  ready: boolean;
  testStatus: string;
  blockedReason: string;
  primaryAction: string;
  version: number;
  versionId: string;
};

export class AssistantApiError extends Error {
  status: number;
  retryable: boolean;

  constructor(message: string, status = 0) {
    super(message);
    this.name = "AssistantApiError";
    this.status = status;
    this.retryable = status === 0 || status >= 500 || status === 408 || status === 429;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      credentials: "same-origin",
      ...init,
      headers: {
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new AssistantApiError("无法连接会话服务，请检查网络后重试。", 0);
  }
  if (!response.ok) {
    let detail = "会话服务暂时不可用，请重试。";
    try {
      const body = (await response.json()) as {
        detail?: string;
        error?: { message?: string };
      };
      if (body.error?.message) detail = body.error.message;
      else if (body.detail) detail = body.detail;
    } catch {
      /* The server may return an empty or non-JSON error response. */
    }
    if (response.status === 404) detail = "找不到这条聊天，或它属于另一个浏览器。";
    if (response.status === 409) detail = "这条聊天已被其他页面更新，请刷新后重试。";
    throw new AssistantApiError(detail, response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function toConversation(summary: ConversationSummary): Conversation {
  return {
    id: summary.id,
    title: summary.title,
    createdAt: summary.createdAt,
    updatedAt: summary.updatedAt,
    messages: [],
    loaded: false,
    version: summary.version,
  };
}

export function toLoadedConversation(conversation: ApiConversation): Conversation {
  return {
    ...toConversation(conversation),
    loaded: true,
    messages: conversation.messages.map((message) => ({
      id: message.id,
      role: message.role,
      content: message.content,
      status: message.status,
      steps: message.steps,
      capability: message.capability,
      attachments: message.attachments,
      request: message.request ?? undefined,
    })),
  };
}

export async function listConversations(query = ""): Promise<Conversation[]> {
  const summaries: ConversationSummary[] = [];
  let cursor: string | null = null;
  do {
    const params = new URLSearchParams({ limit: "100" });
    if (query.trim()) params.set("q", query.trim());
    if (cursor) params.set("cursor", cursor);
    const response = await request<{ items: ConversationSummary[]; nextCursor: string | null }>(
      `/api/v1/conversations?${params.toString()}`,
    );
    summaries.push(...response.items);
    cursor = response.nextCursor;
  } while (cursor);
  return summaries.map(toConversation);
}

export async function listCapabilities(): Promise<ApiCapability[]> {
  const response = await request<{ items: ApiCapability[] }>("/api/v1/capabilities");
  return response.items;
}

export async function getConversation(id: string): Promise<Conversation> {
  return toLoadedConversation(await request<ApiConversation>(`/api/v1/conversations/${id}`));
}

export async function createConversation(title = "新对话", migrationKey?: string): Promise<Conversation> {
  const response = await request<ConversationSummary>("/api/v1/conversations", {
    method: "POST",
    body: JSON.stringify({
      title,
      ...(migrationKey ? { migrationKey } : {}),
    }),
  });
  return toConversation(response);
}

export async function renameConversation(
  id: string,
  title: string,
  version: number,
): Promise<Conversation> {
  return toConversation(
    await request<ConversationSummary>(`/api/v1/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title, version }),
    }),
  );
}

export async function deleteConversation(id: string): Promise<void> {
  await request<void>(`/api/v1/conversations/${id}`, { method: "DELETE" });
}

export type CreatedTurn = {
  conversation: ConversationSummary;
  userMessage: ApiMessage;
  assistantMessage: ApiMessage;
};

export async function createTurn(
  conversationId: string,
  input: SendMessageInput,
  attachments: { id: string; name: string }[],
  clientTurnId: string,
): Promise<CreatedTurn> {
  return request<CreatedTurn>(`/api/v1/conversations/${conversationId}/turns`, {
    method: "POST",
    body: JSON.stringify({
      clientTurnId,
      text: input.text,
      capability: input.capability ?? null,
      attachments,
      request: { ...input, conversationId },
    }),
  });
}

export async function patchMessage(
  conversationId: string,
  messageId: string,
  patch: {
    content: string;
    status: ChatMessage["status"];
    steps: ExecutionStep[];
    request?: SendMessageInput | null;
  },
): Promise<ApiMessage> {
  return request<ApiMessage>(
    `/api/v1/conversations/${conversationId}/messages/${messageId}`,
    { method: "PATCH", body: JSON.stringify(patch) },
  );
}

export function apiMessageToChatMessage(message: ApiMessage): ChatMessage {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    status: message.status,
    steps: message.steps,
    capability: message.capability,
    attachments: message.attachments,
    request: message.request ?? undefined,
  };
}

export type RuntimeEvent =
  | {
      type: "start";
      conversation: ConversationSummary;
      userMessage: ApiMessage;
      assistantMessage: ApiMessage;
    }
  | { type: "run"; runId: string }
  | { type: "chunk"; content: string }
  | { type: "tool"; name: string; result: Record<string, unknown> }
  | { type: "mcp"; serverId: string; name: string; result: Record<string, unknown> }
  | {
      type: "agent";
      dependencies: { id: string; kind: string; versionId: string; version: number; name: string }[];
    }
  | { type: "done"; runId: string; status: string }
  | { type: "error"; runId?: string; code: string; message?: string };

function authCsrfToken(): string {
  if (typeof document === "undefined") return "";
  const prefix = "paiguangguang_csrf=";
  return (
    document.cookie
      .split(";")
      .map((item) => item.trim())
      .find((item) => item.startsWith(prefix))
      ?.slice(prefix.length) ?? ""
  );
}

export async function streamRun(
  input: {
    conversationId: string;
    clientTurnId: string;
    text: string;
    capability: CapabilityRef | null;
    fileIds: string[];
  },
  onEvent: (event: RuntimeEvent) => void,
): Promise<void> {
  const response = await fetch("/api/v1/assistant/runs/stream", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": authCsrfToken(),
    },
    body: JSON.stringify({
      conversationId: input.conversationId,
      clientTurnId: input.clientTurnId,
      text: input.text,
      capabilityId: input.capability?.id ?? null,
      capabilityKind: input.capability?.kind ?? null,
      toolArguments: {},
      mode: "fake",
    }),
  });
  if (!response.ok || !response.body) {
    let message = "真实执行请求失败，请重试。";
    try {
      const body = (await response.json()) as { error?: { message?: string } };
      if (body.error?.message) message = body.error.message;
    } catch {
      /* keep fallback */
    }
    throw new AssistantApiError(message, response.status);
  }
  await consumeSse(response, onEvent);
}

export async function retryRunStream(
  input: { conversationId: string; messageId: string },
  onEvent: (event: RuntimeEvent) => void,
): Promise<void> {
  const response = await fetch("/api/v1/assistant/runs/retry/stream", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": authCsrfToken(),
    },
    body: JSON.stringify(input),
  });
  if (!response.ok || !response.body) {
    let message = "重试请求失败，请稍后再试。";
    try {
      const body = (await response.json()) as { error?: { message?: string } };
      if (body.error?.message) message = body.error.message;
    } catch {
      /* keep fallback */
    }
    throw new AssistantApiError(message, response.status);
  }
  await consumeSse(response, onEvent);
}

async function consumeSse(
  response: Response,
  onEvent: (event: RuntimeEvent) => void,
): Promise<void> {
  if (!response.body) return;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let separator = buffer.indexOf("\n\n");
    while (separator >= 0) {
      const block = buffer.slice(0, separator);
      buffer = buffer.slice(separator + 2);
      const line = block.split("\n").find((item) => item.startsWith("data:"));
      if (line) {
        try {
          onEvent(JSON.parse(line.slice(5).trim()) as RuntimeEvent);
        } catch {
          /* ignore malformed SSE frames */
        }
      }
      separator = buffer.indexOf("\n\n");
    }
  }
}

export async function cancelRun(runId: string): Promise<void> {
  await fetch(`/api/v1/assistant/runs/${runId}/cancel`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": authCsrfToken() },
    body: "{}",
  });
}

