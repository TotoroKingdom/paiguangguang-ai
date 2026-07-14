"use client";

import type { MessageData } from "../types/message";
import { MarkdownContent } from "./markdown-content";

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
            ? "max-w-[min(40rem,88%)] rounded-2xl border border-ink/10 bg-ink/[0.04] px-4 py-3 text-ink"
            : "max-w-[min(50rem,100%)] py-1 text-ink",
        ].join(" ")}
      >
        <div className="flex items-center justify-between gap-3 text-[11px] uppercase tracking-[0.18em]">
          <span className={isUser ? "text-ink/60" : "text-ink/45"}>{isUser ? "You" : "Assistant"}</span>
          <span className={isUser ? "text-ink/45" : "text-ink/40"}>
            {message.status}
            {isStreaming ? " · streaming" : ""}
          </span>
        </div>

        <div className={["mt-2 min-w-0", isUser ? "text-sm leading-7 whitespace-pre-wrap" : "pr-1"].join(" ")}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <MarkdownContent value={assistantContent} />
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
                className="rounded-full border border-clay/30 bg-white px-3 py-1.5 text-xs font-semibold text-clay transition hover:border-clay/50 hover:bg-clay/5 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {stopping ? "Stopping..." : "Stop generation"}
              </button>
            ) : null}
            {showRetry ? (
              <button
                type="button"
                onClick={() => void onRetry?.()}
                disabled={actionsDisabled}
                className="rounded-full border border-tide/30 bg-white px-3 py-1.5 text-xs font-semibold text-tide transition hover:border-tide/50 hover:bg-tide/5 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Retry
              </button>
            ) : null}
            {showRegenerate ? (
              <button
                type="button"
                onClick={() => void onRegenerate?.()}
                disabled={actionsDisabled}
                className="rounded-full border border-tide/30 bg-white px-3 py-1.5 text-xs font-semibold text-tide transition hover:border-tide/50 hover:bg-tide/5 disabled:cursor-not-allowed disabled:opacity-60"
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
