"use client";

import type { MessageData } from "../types/message";
import { StreamingMarkdownContent } from "./streaming-markdown-content";

type MessageItemProps = {
  message: MessageData;
  isStreaming?: boolean;
  stopping?: boolean;
  onStop?: () => void | Promise<void>;
  onRetry?: () => void | Promise<void>;
  onRegenerate?: () => void | Promise<void>;
  actionsDisabled?: boolean;
};

export function MessageItem({
  message,
  isStreaming = false,
  stopping = false,
  onStop,
  onRetry,
  onRegenerate,
  actionsDisabled = false,
}: MessageItemProps) {
  const isUser = message.role === "user";
  const showStop = !isUser && (message.status === "pending" || message.status === "streaming") && onStop;
  const showRetry = !isUser && (message.status === "failed" || message.status === "cancelled") && onRetry;
  const showRegenerate = !isUser && message.status === "completed" && onRegenerate;
  const assistantContent =
    message.content || ((message.status === "pending" || message.status === "streaming") ? "Thinking..." : "");

  return (
    <article
      data-message-id={message.id}
      data-testid={`message-${message.id}`}
      className={["flex min-w-0", isUser ? "justify-end" : "justify-start"].join(" ")}
    >
      <div
        className={[
          "min-w-0",
          isUser
            ? "max-w-[min(42rem,88%)] rounded-[18px] border border-[var(--chat-border)] bg-[rgba(18,24,35,0.04)] px-4 py-3 text-ink"
            : "max-w-[min(48rem,100%)] py-1 text-ink",
        ].join(" ")}
      >
        <span className="sr-only">{isUser ? "You" : "Assistant"}</span>
        <span className="sr-only">{message.status}</span>

        <div className={["min-w-0", isUser ? "text-sm leading-7 whitespace-pre-wrap" : "pr-1"].join(" ")}>
          {isUser ? (
            <p className="whitespace-pre-wrap text-[15px] leading-7">{message.content}</p>
          ) : (
            <StreamingMarkdownContent
              value={assistantContent}
              streaming={message.status === "pending" || message.status === "streaming" || isStreaming}
            />
          )}
        </div>

        {message.status === "failed" ? (
          <p className="mt-2 text-xs leading-6 text-clay">
            {message.error_code ? `${message.error_code}` : "Message failed"}
          </p>
        ) : null}

        {showStop || showRetry || showRegenerate ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {showStop ? (
              <button
                type="button"
                onClick={() => void onStop?.()}
                disabled={actionsDisabled || stopping}
                className="rounded-full border border-clay/25 bg-white px-3 py-1.5 text-xs font-semibold text-clay transition hover:border-clay/40 hover:bg-clay/5 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {stopping ? "Stopping..." : "Stop generation"}
              </button>
            ) : null}
            {showRetry ? (
              <button
                type="button"
                onClick={() => void onRetry?.()}
                disabled={actionsDisabled}
                className="rounded-full border border-tide/25 bg-white px-3 py-1.5 text-xs font-semibold text-tide transition hover:border-tide/40 hover:bg-tide/5 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Retry
              </button>
            ) : null}
            {showRegenerate ? (
              <button
                type="button"
                onClick={() => void onRegenerate?.()}
                disabled={actionsDisabled}
                className="rounded-full border border-tide/25 bg-white px-3 py-1.5 text-xs font-semibold text-tide transition hover:border-tide/40 hover:bg-tide/5 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Regenerate
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </article>
  );
}
