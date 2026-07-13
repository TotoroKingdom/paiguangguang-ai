"use client";

import type { ReactNode } from "react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { MessageData } from "../types/message";

type MessageItemProps = {
  message: MessageData;
  isStreaming?: boolean;
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

export function MessageItem({ message, isStreaming = false }: MessageItemProps) {
  const isUser = message.role === "user";

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
      </div>
    </article>
  );
}
