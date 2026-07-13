"use client";

import { useCallback, useLayoutEffect, useMemo, useRef, useState } from "react";

import type { MessageData } from "../types/message";
import type { ChatStreamPhase } from "../utils/merge-stream-event";
import { MessageItem } from "./message-item";

type MessageListProps = {
  messages: MessageData[];
  loadingHistory: boolean;
  historyError: string | null;
  hasMore: boolean;
  onLoadMore: () => void | Promise<void>;
  streamPhase: ChatStreamPhase;
  streamingMessageId: string | null;
  onStopGeneration?: (messageId?: string | null) => void | Promise<void>;
  onRetryMessage?: (messageId: string) => void | Promise<void>;
  onRegenerateMessage?: (messageId: string) => void | Promise<void>;
  stoppingMessageId?: string | null;
  actionsDisabled?: boolean;
};

const TOP_THRESHOLD_PX = 64;
const BOTTOM_THRESHOLD_PX = 120;

function isNearBottom(container: HTMLDivElement) {
  return container.scrollHeight - container.scrollTop - container.clientHeight <= BOTTOM_THRESHOLD_PX;
}

export function MessageList({
  messages,
  loadingHistory,
  historyError,
  hasMore,
  onLoadMore,
  streamPhase,
  streamingMessageId,
  onStopGeneration,
  onRetryMessage,
  onRegenerateMessage,
  stoppingMessageId = null,
  actionsDisabled = false,
}: MessageListProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const previousScrollHeightRef = useRef(0);
  const preserveAnchorRef = useRef(false);
  const stickToBottomRef = useRef(true);
  const loadingMoreRef = useRef(false);
  const [showJumpButton, setShowJumpButton] = useState(false);
  const [loadMorePending, setLoadMorePending] = useState(false);

  const canJumpToBottom = useMemo(() => messages.length > 0, [messages.length]);

  const scrollToBottom = useCallback(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    container.scrollTop = container.scrollHeight;
    stickToBottomRef.current = true;
    setShowJumpButton(false);
  }, []);

  const requestLoadMore = useCallback(async () => {
    if (!hasMore || loadingHistory || loadingMoreRef.current) {
      return;
    }
    const container = containerRef.current;
    if (!container) {
      await onLoadMore();
      return;
    }
    loadingMoreRef.current = true;
    previousScrollHeightRef.current = container.scrollHeight;
    preserveAnchorRef.current = true;
    setLoadMorePending(true);
    try {
      await onLoadMore();
    } finally {
      loadingMoreRef.current = false;
      setLoadMorePending(false);
    }
  }, [hasMore, loadingHistory, onLoadMore]);

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    if (preserveAnchorRef.current) {
      const delta = container.scrollHeight - previousScrollHeightRef.current;
      container.scrollTop = container.scrollTop + delta;
      preserveAnchorRef.current = false;
      return;
    }

    if (stickToBottomRef.current || streamPhase === "streaming") {
      container.scrollTop = container.scrollHeight;
      setShowJumpButton(false);
    }
  }, [messages, streamPhase]);

  const handleScroll = useCallback(async () => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const nearBottom = isNearBottom(container);
    stickToBottomRef.current = nearBottom;
    setShowJumpButton(!nearBottom && canJumpToBottom);

    if (container.scrollTop <= TOP_THRESHOLD_PX) {
      void requestLoadMore();
    }
  }, [canJumpToBottom, requestLoadMore]);

  return (
    <div className="relative flex h-full min-h-0 flex-col rounded-2xl border border-ink/10 bg-white/80 shadow-sm">
      <div className="border-b border-ink/10 px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm font-semibold text-ink">Messages</p>
          <div className="text-xs text-ink/55">
            {loadingHistory ? "Loading history…" : `${messages.length} messages`}
          </div>
        </div>
        {historyError ? <p className="mt-2 text-sm leading-6 text-clay">{historyError}</p> : null}
      </div>

      <div
        ref={containerRef}
        onScroll={() => void handleScroll()}
        className="min-h-0 flex-1 overflow-y-auto scroll-smooth px-4 py-4"
      >
        {loadMorePending ? (
          <div className="mb-3 text-center text-xs font-semibold uppercase tracking-wide text-ink/45">
            Loading earlier messages…
          </div>
        ) : null}

        {messages.length === 0 && !loadingHistory ? (
          <div className="rounded-2xl border border-dashed border-ink/15 bg-paper/50 p-8 text-sm leading-7 text-ink/65">
            No messages yet. Start the conversation from the composer below.
          </div>
        ) : null}

        <div className="space-y-4">
          {messages.map((message) => (
            <MessageItem
              key={message.id}
              message={message}
              isStreaming={streamingMessageId === message.id && streamPhase === "streaming"}
              stopping={stoppingMessageId === message.id}
              onStop={onStopGeneration ? () => onStopGeneration(message.id) : undefined}
              onRetry={onRetryMessage ? () => onRetryMessage(message.id) : undefined}
              onRegenerate={onRegenerateMessage ? () => onRegenerateMessage(message.id) : undefined}
              actionsDisabled={actionsDisabled}
            />
          ))}
        </div>
      </div>

      {showJumpButton ? (
        <div className="pointer-events-none absolute inset-x-0 bottom-6 flex justify-center">
          <button
            type="button"
            onClick={scrollToBottom}
            className="pointer-events-auto rounded-full border border-tide/30 bg-tide px-4 py-2 text-sm font-semibold text-paper shadow-lg transition hover:bg-tide/90"
          >
            Back to bottom
          </button>
        </div>
      ) : null}
    </div>
  );
}
