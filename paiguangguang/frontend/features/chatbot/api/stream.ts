import { ApiError, getBackendBaseUrl, getJson } from "@/lib/api";

import type { ChatRequest, MessagePageData } from "../types/message";
import type {
  ParsedChatStreamEvent,
  StreamEventName,
} from "../types/stream";

function buildQuery(params: Record<string, string | number | boolean | null | undefined>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") {
      continue;
    }
    query.set(key, String(value));
  }
  const suffix = query.toString();
  return suffix ? `?${suffix}` : "";
}

function parseEnvelopeError(payload: unknown, fallbackStatus: number) {
  if (
    payload &&
    typeof payload === "object" &&
    "error" in payload &&
    payload.error &&
    typeof payload.error === "object"
  ) {
    const error = payload.error as { code?: string; message?: string };
    return new ApiError(error.message || "Request failed", fallbackStatus, error.code || "REQUEST_FAILED");
  }
  return new ApiError("Request failed", fallbackStatus, "REQUEST_FAILED");
}

export async function listMessages(options: {
  token: string | null;
  conversationId: string;
  limit?: number;
  before?: string | null;
}): Promise<MessagePageData> {
  const { token, conversationId, limit = 50, before = null } = options;
  return getJson<MessagePageData>(
    `/api/v1/chatbot/conversations/${conversationId}/messages${buildQuery({ limit, before })}`,
    { token }
  );
}

export async function openChatStream(options: {
  token: string | null;
  conversationId: string;
  content: string;
  clientRequestId: string;
  signal?: AbortSignal | null;
}): Promise<Response> {
  const { token, conversationId, content, clientRequestId, signal } = options;
  const headers = new Headers({
    "Content-Type": "application/json",
    Accept: "text/event-stream",
    "Idempotency-Key": clientRequestId,
  });
  const normalizedToken = token?.trim();
  if (normalizedToken) {
    headers.set("Authorization", `Bearer ${normalizedToken}`);
  }

  const response = await fetch(`${getBackendBaseUrl()}/api/v1/chatbot/conversations/${conversationId}/messages`, {
    method: "POST",
    body: JSON.stringify({
      content,
      client_request_id: clientRequestId,
    } satisfies ChatRequest),
    headers,
    signal: signal ?? undefined,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw parseEnvelopeError(payload, response.status);
  }

  return response;
}

function parseEventBlock(block: string): ParsedChatStreamEvent | null {
  const lines = block.split("\n");
  const dataLines: string[] = [];
  let eventName = "";
  let sequence = 0;

  for (const line of lines) {
    if (!line || line.startsWith(":")) {
      continue;
    }
    const separator = line.indexOf(":");
    if (separator < 0) {
      continue;
    }
    const field = line.slice(0, separator).trim();
    const value = line.slice(separator + 1).replace(/^\s/, "");
    if (field === "event") {
      eventName = value;
    } else if (field === "data") {
      dataLines.push(value);
    } else if (field === "id") {
      const parsedSequence = Number(value);
      if (Number.isFinite(parsedSequence)) {
        sequence = parsedSequence;
      }
    }
  }

  if (!eventName || dataLines.length === 0) {
    return null;
  }

  const rawData = dataLines.join("\n");
  let data: unknown = rawData;
  try {
    data = JSON.parse(rawData) as unknown;
  } catch {
    data = rawData;
  }

  return {
    event: eventName,
    data,
    sequence,
  };
}

export async function* readChatStreamEvents(response: Response): AsyncGenerator<ParsedChatStreamEvent> {
  if (!response.body) {
    throw new Error("Streaming response body is empty");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    buffer = buffer.replace(/\r\n/g, "\n");

    while (true) {
      const boundary = buffer.indexOf("\n\n");
      if (boundary < 0) {
        break;
      }
      const block = buffer.slice(0, boundary).trim();
      buffer = buffer.slice(boundary + 2);
      if (!block) {
        continue;
      }
      const event = parseEventBlock(block);
      if (event) {
        yield event;
      }
    }
  }

  buffer += decoder.decode();
  buffer = buffer.replace(/\r\n/g, "\n").trim();
  if (buffer) {
    const event = parseEventBlock(buffer);
    if (event) {
      yield event;
    }
  }
}

export async function* streamChatEvents(options: {
  token: string | null;
  conversationId: string;
  content: string;
  clientRequestId: string;
  signal?: AbortSignal | null;
}): AsyncGenerator<ParsedChatStreamEvent> {
  const response = await openChatStream(options);
  yield* readChatStreamEvents(response);
}

export type { ParsedChatStreamEvent, StreamEventName };

