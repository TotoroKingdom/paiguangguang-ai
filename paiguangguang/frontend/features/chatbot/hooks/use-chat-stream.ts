"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/api";

import { openChatStream, openRegenerateStream, openRetryStream, readChatStreamEvents } from "../api/stream";
import type { ParsedChatStreamEvent, StreamMessageCreatedData } from "../types/stream";
import { createChatStreamEventBatcher } from "../utils/stream-event-batcher";

type UseChatStreamOptions = {
  token: string | null;
  conversationId: string | null;
  onEvent?: (event: ParsedChatStreamEvent) => void;
  onCreated?: (event: { event: "message.created"; data: StreamMessageCreatedData; sequence: number }) => void;
  onTerminal?: (event: ParsedChatStreamEvent) => void;
  onFailure?: (message: string) => void;
};

type StreamGenerationAction =
  | { kind: "send"; content: string }
  | { kind: "retry"; messageId: string }
  | { kind: "regenerate"; messageId: string };

function isAbortError(error: unknown) {
  return error instanceof DOMException
    ? error.name === "AbortError"
    : error instanceof Error && error.name === "AbortError";
}

function eventConversationId(event: ParsedChatStreamEvent) {
  if (
    event.data &&
    typeof event.data === "object" &&
    "conversation_id" in event.data &&
    typeof (event.data as { conversation_id?: unknown }).conversation_id === "string"
  ) {
    return (event.data as { conversation_id: string }).conversation_id;
  }
  return null;
}

export function useChatStream({
  token,
  conversationId,
  onEvent,
  onCreated,
  onTerminal,
  onFailure,
}: UseChatStreamOptions) {
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeRequestId = useRef<string | null>(null);
  const abortController = useRef<AbortController | null>(null);
  const activeConversationId = useRef<string | null>(conversationId);
  activeConversationId.current = conversationId;

  useEffect(() => {
    abortController.current?.abort();
    abortController.current = null;
    activeRequestId.current = null;
    setSending(false);
    return () => {
      abortController.current?.abort();
    };
  }, [conversationId, token]);

  const runGeneration = useCallback(
    async (action: StreamGenerationAction, clientRequestId: string) => {
      if (!token || !conversationId) {
        return false;
      }

      const startedConversationId = conversationId;
      abortController.current?.abort();
      const controller = new AbortController();
      abortController.current = controller;
      activeRequestId.current = clientRequestId;
      setSending(true);
      setError(null);
      let batcher: ReturnType<typeof createChatStreamEventBatcher> | null = null;

      try {
        const response =
          action.kind === "send"
            ? await openChatStream({
                token,
                conversationId,
                content: action.content,
                clientRequestId,
                signal: controller.signal,
              })
            : action.kind === "retry"
              ? await openRetryStream({
                  token,
                  conversationId,
                  messageId: action.messageId,
                  clientRequestId,
                  signal: controller.signal,
                })
              : await openRegenerateStream({
                  token,
                  conversationId,
                  messageId: action.messageId,
                  clientRequestId,
                  signal: controller.signal,
                });
        const dispatchEvent = (event: ParsedChatStreamEvent) => {
          if (controller.signal.aborted || activeConversationId.current !== startedConversationId) {
            return;
          }
          onEvent?.(event);
          if (event.event === "message.created") {
            const createdEvent = event as {
              event: "message.created";
              data: StreamMessageCreatedData;
              sequence: number;
            };
            onCreated?.({
              event: "message.created",
              data: createdEvent.data,
              sequence: createdEvent.sequence,
            });
          }
          if (event.event === "stream.end" || event.event === "message.failed" || event.event === "message.cancelled") {
            onTerminal?.(event);
          }
        };
        batcher = createChatStreamEventBatcher({ emit: dispatchEvent });
        let detached = false;

        for await (const event of readChatStreamEvents(response)) {
          if (
            controller.signal.aborted ||
            activeConversationId.current !== startedConversationId ||
            eventConversationId(event) !== startedConversationId
          ) {
            detached = true;
            break;
          }
          batcher.push(event);
        }
        if (detached) {
          batcher.clear();
        } else {
          batcher.flush();
        }
        return true;
      } catch (exception) {
        if (controller.signal.aborted || isAbortError(exception)) {
          batcher?.clear();
          return false;
        }
        batcher?.flush();
        const message =
          exception instanceof ApiError
            ? exception.message
            : exception instanceof Error
              ? exception.message
              : "Unable to send message.";
        setError(message);
        onFailure?.(message);
        return false;
      } finally {
        batcher?.clear();
        if (abortController.current === controller) {
          abortController.current = null;
          if (activeRequestId.current === clientRequestId) {
            activeRequestId.current = null;
          }
          setSending(false);
        }
      }
    },
    [conversationId, onCreated, onEvent, onFailure, onTerminal, token]
  );

  const sendMessage = useCallback(
    (content: string, clientRequestId: string) => runGeneration({ kind: "send", content }, clientRequestId),
    [runGeneration]
  );

  const retryMessage = useCallback(
    (messageId: string, clientRequestId: string) => runGeneration({ kind: "retry", messageId }, clientRequestId),
    [runGeneration]
  );

  const regenerateMessage = useCallback(
    (messageId: string, clientRequestId: string) =>
      runGeneration({ kind: "regenerate", messageId }, clientRequestId),
    [runGeneration]
  );

  return {
    sending,
    error,
    activeRequestId: activeRequestId.current,
    sendMessage,
    retryMessage,
    regenerateMessage,
    cancel: () => abortController.current?.abort(),
    clearError: () => setError(null),
  };
}
