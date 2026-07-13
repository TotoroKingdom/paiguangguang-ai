"use client";

import type { ReactNode } from "react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { MessageData } from "../types/message";

type MessageItemProps = {
  message: MessageData;
  isStreaming?: boolean;
  stopping?: boolean;
  onStop?: () => void | Promise<void>;
  onRetry?: () => void | Promise<void>;
  onRegenerate?: () => void | Promise<void>;
  actionsDisabled?: boolean;
};

function SafeAnchor({
  href,
  children,
}: {
  href?: string;
  children?: ReactNode;
}) {
  if (!href) {
    return <span>{children}</span>;
  }

  try {
    const url = new URL(href, "http://localhost");
    if (!["http:", "https:", "mailto:"].includes(url.protocol)) {
      return <span>{children}</span>;
    }
    const targetHref = url.protocol === "mailto:" ? href : url.toString();
    return (
      <a href={targetHref} target="_blank" rel="noreferrer noopener">
        {children}
      </a>
    );
  } catch {
    return <span>{children}</span>;
  }
}

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

  return (
    <article
      data-message-id={message.id}
      className={["flex", isUser ? "justify-end" : "justify-start"].join(" ")}
    >
      <div
        className={[
          "max-w-[min(42rem,85%)] rounded-2xl px-4 py-3 shadow-sm",
          isUser ? "bg-ink text-paper" : "border border-ink/10 bg-white text-ink",
        ].join(" ")}
      >
        <div className="flex items-center justify-between gap-3 text-[11px] uppercase tracking-wide">
          <span className={isUser ? "text-paper/70" : "text-ink/45"}>{isUser ? "You" : "Assistant"}</span>
          <span className={isUser ? "text-paper/60" : "text-ink/40"}>
            {message.status}
            {isStreaming ? " • streaming" : ""}
          </span>
        </div>

        <div className={["mt-2 text-sm leading-7", isUser ? "whitespace-pre-wrap" : ""].join(" ")}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ href, children }) => <SafeAnchor href={href}>{children}</SafeAnchor>,
                code: ({ children, ...props }) => (
                  <code className="rounded bg-paper px-1.5 py-0.5 font-mono text-[0.9em] text-ink" {...props}>
                    {children}
                  </code>
                ),
                pre: ({ children }) => <pre className="overflow-x-auto rounded-lg bg-paper">{children}</pre>,
                p: ({ children }) => <p className="whitespace-pre-wrap">{children}</p>,
              }}
            >
              {message.content || (message.status === "pending" ? "Thinking…" : "")}
            </ReactMarkdown>
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
