import { deleteJson, getJson, patchJson } from "@/lib/api";

import { CHATBOT_API_BASE } from "./client";
import type { DeleteResultData } from "../types/conversation";
import type {
  MemoryData,
  MemoryPageData,
  MemoryStatus,
  MemoryUpdateRequest,
} from "../types/memory";

export const memoryApiClient = {
  listMemories(options: {
    token: string | null;
    status: MemoryStatus;
    cursor: string | null;
    limit: number;
  }) {
    const query = new URLSearchParams({
      status: options.status,
      limit: String(options.limit),
    });
    if (options.cursor) {
      query.set("cursor", options.cursor);
    }
    return getJson<MemoryPageData>(`${CHATBOT_API_BASE}/memories?${query}`, {
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
