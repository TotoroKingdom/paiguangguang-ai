import { deleteJson, getJson, patchJson } from "@/lib/api";

import { CHATBOT_API_BASE } from "./client";
import type { DeleteResultData } from "../types/conversation";
import type {
  MemoryData,
  MemoryPageData,
  MemoryListStatus,
  MemoryType,
  MemoryUpdateRequest,
} from "../types/memory";

export const memoryApiClient = {
  listMemories(options: {
    token: string | null;
    status: MemoryListStatus;
    memoryType?: MemoryType | null;
    conversationId?: string | null;
    cursor: string | null;
    limit: number;
  }) {
    const query = new URLSearchParams({ status: options.status });
    if (options.memoryType) {
      query.set("memory_type", options.memoryType);
    }
    if (options.conversationId) {
      query.set("conversation_id", options.conversationId);
    }
    query.set("limit", String(options.limit));
    if (options.cursor) {
      query.set("cursor", options.cursor);
    }
    return getJson<MemoryPageData>(`${CHATBOT_API_BASE}/memories?${query}`, {
      token: options.token,
    });
  },
  getMemory(options: { token: string | null; memoryId: string }) {
    return getJson<MemoryData>(`${CHATBOT_API_BASE}/memories/${options.memoryId}`, {
      token: options.token,
    });
  },
  updateMemory(
    options: { token: string | null; memoryId: string },
    request: MemoryUpdateRequest
  ) {
    return patchJson<MemoryData, MemoryUpdateRequest>(
      `${CHATBOT_API_BASE}/memories/${options.memoryId}`,
      request,
      { token: options.token }
    );
  },
  deleteMemory(options: { token: string | null; memoryId: string }) {
    return deleteJson<DeleteResultData>(
      `${CHATBOT_API_BASE}/memories/${options.memoryId}`,
      { token: options.token }
    );
  },
};

export type MemoryApiClient = typeof memoryApiClient;
