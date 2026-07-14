import { deleteJson, getJson, patchJson, postJson } from "@/lib/api";

import type {
  ConversationCreateRequest,
  ConversationData,
  ConversationDetailData,
  ConversationPageData,
  ConversationStatus,
  ConversationUpdateRequest,
  DeleteResultData,
} from "../types/conversation";
import type { StopGenerationData, StopGenerationRequest } from "../types/message";

export const CHATBOT_API_BASE = "/api/v1/chatbot";

const DEFAULT_PAGE_SIZE = 20;

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

export async function listConversations(options: {
  token: string | null;
  status?: ConversationStatus;
  cursor?: string | null;
  limit?: number;
}): Promise<ConversationPageData> {
  const { token, status = "active", cursor = null, limit = DEFAULT_PAGE_SIZE } = options;
  return getJson<ConversationPageData>(
    `${CHATBOT_API_BASE}/conversations${buildQuery({ status, cursor, limit })}`,
    { token }
  );
}

export async function getConversation(options: {
  token: string | null;
  conversationId: string;
}): Promise<ConversationDetailData> {
  const { token, conversationId } = options;
  return getJson<ConversationDetailData>(`${CHATBOT_API_BASE}/conversations/${conversationId}`, {
    token,
  });
}

export async function createConversation(
  options: {
    token: string | null;
  },
  request: ConversationCreateRequest = {}
): Promise<ConversationData> {
  return postJson<ConversationData, ConversationCreateRequest>(
    `${CHATBOT_API_BASE}/conversations`,
    request,
    { token: options.token }
  );
}

export async function updateConversation(
  options: {
    token: string | null;
    conversationId: string;
  },
  request: ConversationUpdateRequest
): Promise<ConversationData> {
  return patchJson<ConversationData, ConversationUpdateRequest>(
    `${CHATBOT_API_BASE}/conversations/${options.conversationId}`,
    request,
    { token: options.token }
  );
}

export async function archiveConversation(options: {
  token: string | null;
  conversationId: string;
}): Promise<ConversationData> {
  return postJson<ConversationData, Record<string, never>>(
    `${CHATBOT_API_BASE}/conversations/${options.conversationId}/archive`,
    {},
    { token: options.token }
  );
}

export async function restoreConversation(options: {
  token: string | null;
  conversationId: string;
}): Promise<ConversationData> {
  return postJson<ConversationData, Record<string, never>>(
    `${CHATBOT_API_BASE}/conversations/${options.conversationId}/restore`,
    {},
    { token: options.token }
  );
}

export async function deleteConversation(options: {
  token: string | null;
  conversationId: string;
}): Promise<DeleteResultData> {
  return deleteJson<DeleteResultData>(`${CHATBOT_API_BASE}/conversations/${options.conversationId}`, {
    token: options.token,
  });
}

export async function stopGeneration(options: {
  token: string | null;
  conversationId: string;
  request: StopGenerationRequest;
}): Promise<StopGenerationData> {
  return postJson<StopGenerationData, StopGenerationRequest>(
    `${CHATBOT_API_BASE}/conversations/${options.conversationId}/stop`,
    options.request,
    { token: options.token }
  );
}

export const chatbotApiClient = {
  listConversations,
  getConversation,
  createConversation,
  updateConversation,
  archiveConversation,
  restoreConversation,
  deleteConversation,
  stopGeneration,
};

export type ChatbotApiClient = typeof chatbotApiClient;
