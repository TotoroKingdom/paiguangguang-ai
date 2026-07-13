"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/api";

import { openChatStream, readChatStreamEvents } from "../api/stream";
import type { ParsedChatStreamEvent, StreamMessageCreatedData } from "../types/stream";

type UseChatStreamOptions = {
  token: string | null;
  conversationId: string | null;
  onEvent?: (event: ParsedChatStreamEvent) => void;
  onCreated?: (event: { event: "message.created"; data: StreamMessageCreatedData; sequence: number }) => void;
  onTerminal?: (event: ParsedChatStreamEvent) => void;
  onFailure?: (message: string) => void;
};

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

  useEffect(() => {
    return () => {
      abortController.current?.abort();
    };
  }, []);

  const sendMessage = useCallback(
    async (content: string, clientRequestId: string) => {
      if (!token || !conversationId) {
        return false;
      }

      abortController.current?.abort();
      const controller = new AbortController();
      abortController.current = controller;
      activeRequestId.current = clientRequestId;
      setSending(true);
      setError(null);

      try {
        const response = await openChatStream({
          token,
          conversationId,
          content,
          clientRequestId,
          signal: controller.signal,
        });
        for await (const event of readChatStreamEvents(response)) {
          if (controller.signal.aborted) {
            break;
          }
          onEvent?.(event);
          if (event.event === "message.created") {
            const createdEvent = event as { event: "message.created"; data: StreamMessageCreatedData; sequence: number };
            onCreated?.({
              event: "message.created",
              data: createdEvent.data,
              sequence: createdEvent.sequence,
            });
          }
          if (event.event === "stream.end" || event.event === "message.failed" || event.event === "message.cancelled") {
            onTerminal?.(event);
          }
        }
        return true;
      } catch (exception) {
        const message = exception instanceof ApiError ? exception.message : exception instanceof Error ? exception.message : "Unable to send message.";
        setError(message);
        onFailure?.(message);
        return false;
      } finally {
        if (activeRequestId.current === clientRequestId) {
          activeRequestId.current = null;
        }
        setSending(false);
      }
    },
    [conversationId, onCreated, onEvent, onTerminal, token]
  );

  return {
    sending,
    error,
    activeRequestId: activeRequestId.current,
    sendMessage,
    cancel: () => abortController.current?.abort(),
    clearError: () => setError(null),
  };
}
