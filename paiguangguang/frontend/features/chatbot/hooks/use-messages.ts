"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError } from "@/lib/api";

import { listMessages } from "../api/stream";
import { useChatStream } from "./use-chat-stream";
import { stopGeneration as stopGenerationRequest } from "../api/client";
import type { MessageData } from "../types/message";
import type { ConversationStatus } from "../types/conversation";
import {
  createInitialChatStreamState,
  mergeChatStreamEvent,
  mergeMessageHistory,
  type ChatStreamState,
} from "../utils/merge-stream-event";

type UseMessagesOptions = {
  token: string | null;
  conversationId: string | null;
  conversationStatus: ConversationStatus;
  pageSize?: number;
};

function normalizeError(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unable to load messages.";
}

export function useMessages({
  token,
  conversationId,
  conversationStatus,
  pageSize = 50,
}: UseMessagesOptions) {
  const [streamState, setStreamState] = useState<ChatStreamState>(() =>
    createInitialChatStreamState([], conversationId)
  );
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [stoppingMessageId, setStoppingMessageId] = useState<string | null>(null);
  const [controlError, setControlError] = useState<string | null>(null);

  const activeConversationRef = useRef<string | null>(null);

  const resetConversationState = useCallback(() => {
    setStreamState(createInitialChatStreamState([], conversationId));
    setLoadingHistory(false);
    setHistoryError(null);
    setHasMore(false);
    setNextCursor(null);
    setDraft("");
    setStoppingMessageId(null);
    setControlError(null);
  }, [conversationId]);

  const loadHistory = useCallback(
    async (before: string | null = null, append = false) => {
      if (!token || !conversationId || conversationStatus === "deleted") {
        return null;
      }

      setLoadingHistory(true);
      setHistoryError(null);
      try {
        const page = await listMessages({ token, conversationId, limit: pageSize, before });
        setHasMore(page.has_more);
        setNextCursor(page.next_cursor);
        setStreamState((current) => ({
          ...current,
          messages: append ? mergeMessageHistory(current.messages, page.items) : mergeMessageHistory([], page.items),
        }));
        return page;
      } catch (error) {
        setHistoryError(normalizeError(error));
        return null;
      } finally {
        setLoadingHistory(false);
      }
    },
    [conversationId, conversationStatus, pageSize, token]
  );

  useEffect(() => {
    if (!conversationId || !token || conversationStatus === "deleted") {
      activeConversationRef.current = conversationId;
      resetConversationState();
      return;
    }

    if (activeConversationRef.current !== conversationId) {
      activeConversationRef.current = conversationId;
      resetConversationState();
      void loadHistory(null, false);
      return;
    }

    if (!streamState.messages.length && !loadingHistory && !historyError) {
      void loadHistory(null, false);
    }
  }, [conversationId, conversationStatus, historyError, loadHistory, loadingHistory, resetConversationState, streamState.messages.length, token]);

  const onStreamEvent = useCallback((event: Parameters<typeof mergeChatStreamEvent>[1]) => {
    setStreamState((current) => mergeChatStreamEvent(current, event));
  }, []);

  const onStreamCreated = useCallback(() => {
    return;
  }, []);

  const onStreamFailure = useCallback((message: string) => {
    setStreamState((current) => ({
      ...current,
      phase: "failed",
      error: {
        code: "CHATBOT_STREAM_ERROR",
        message,
        retryable: true,
      },
    }));
  }, []);

  const { sending, error: streamError, sendMessage, retryMessage, regenerateMessage } = useChatStream({
    token,
    conversationId,
    onEvent: onStreamEvent,
    onCreated: onStreamCreated,
    onFailure: onStreamFailure,
  });

  const submitMessage = useCallback(
    async (content: string) => {
      const message = content.trim();
      if (!message || !conversationId || conversationStatus !== "active" || !token) {
        return false;
      }

      setControlError(null);
      const clientRequestId = crypto.randomUUID();
      const draftSnapshot = message;
      setDraft("");
      const ok = await sendMessage(message, clientRequestId);
      if (!ok) {
        setDraft(draftSnapshot);
        return false;
      }
      return true;
    },
    [conversationId, conversationStatus, sendMessage, token]
  );

  const retryGeneration = useCallback(
    async (messageId: string) => {
      if (!token || !conversationId || conversationStatus !== "active") {
        return false;
      }
      setControlError(null);
      const clientRequestId = crypto.randomUUID();
      return retryMessage(messageId, clientRequestId);
    },
    [conversationId, conversationStatus, retryMessage, token]
  );

  const regenerateGeneration = useCallback(
    async (messageId: string) => {
      if (!token || !conversationId || conversationStatus !== "active") {
        return false;
      }
      setControlError(null);
      const clientRequestId = crypto.randomUUID();
      return regenerateMessage(messageId, clientRequestId);
    },
    [conversationId, conversationStatus, regenerateMessage, token]
  );

  const stopCurrentGeneration = useCallback(
    async (assistantMessageId?: string | null) => {
      if (!token || !conversationId) {
        return false;
      }
      setControlError(null);
      try {
        const response = await stopGenerationRequest({
          token,
          conversationId,
          request: {
            assistant_message_id: assistantMessageId ?? null,
          },
        });
        setStoppingMessageId(response.status === "cancellation_requested" ? response.assistant_message_id : null);
        return true;
      } catch (error) {
        setControlError(normalizeError(error));
        return false;
      }
    },
    [conversationId, token]
  );

  const loadMore = useCallback(async () => {
    if (!hasMore || !nextCursor) {
      return null;
    }
    return loadHistory(nextCursor, true);
  }, [hasMore, loadHistory, nextCursor]);

  const messages = useMemo<MessageData[]>(() => streamState.messages, [streamState.messages]);

  useEffect(() => {
    if (streamState.phase !== "streaming") {
      setStoppingMessageId(null);
    }
  }, [streamState.phase]);

  return {
    messages,
    loadingHistory,
    historyError,
    hasMore,
    nextCursor,
    streamingMessageId: streamState.activeAssistantMessageId,
    sendMessage: submitMessage,
    retryMessage: retryGeneration,
    regenerateMessage: regenerateGeneration,
    stopGeneration: stopCurrentGeneration,
    loadMore,
    sending,
    streamError: streamError ?? streamState.error?.message ?? null,
    controlError,
    streamPhase: streamState.phase,
    streamRetryable: streamState.error?.retryable ?? false,
    draft,
    setDraft,
    clearDraft: () => setDraft(""),
    stoppingMessageId,
    clearControlError: () => setControlError(null),
  };
}
