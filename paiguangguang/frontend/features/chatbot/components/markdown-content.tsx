"use client";

import type { ReactNode } from "react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { CodeBlock } from "./code-block";

type MarkdownContentProps = {
  value: string;
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

    return (
      <a
        href={url.protocol === "mailto:" ? href : url.toString()}
        target="_blank"
        rel="noopener noreferrer"
        className="underline decoration-tide/40 underline-offset-2 transition hover:decoration-tide/80"
      >
        {children}
      </a>
    );
  } catch {
    return <span>{children}</span>;
  }
}

export function MarkdownContent({ value }: MarkdownContentProps) {
  return (
    <div className="min-w-0 break-words text-[15px] leading-7 text-ink">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => <SafeAnchor href={href}>{children}</SafeAnchor>,
          blockquote: ({ children }) => (
            <blockquote className="my-4 rounded-r-xl border-l-2 border-tide/30 pl-4 pr-2 text-ink/70">
              {children}
            </blockquote>
          ),
          code: ({ className, children, ...props }: any) => {
            const inline = Boolean(props?.inline);
            const rawCodeValue = String(children);
            const codeValue = rawCodeValue.replace(/\n$/, "");
            const isBlock = Boolean(className) || /\n/.test(rawCodeValue);

            if (inline || !isBlock) {
              return (
                <code className="rounded bg-[var(--chat-subtle)] px-1.5 py-0.5 font-mono text-[0.92em] text-ink">
                  {children}
                </code>
              );
            }

            const languageMatch = className?.match(/language-([a-zA-Z0-9_-]+)/);
            return <CodeBlock value={codeValue} language={languageMatch?.[1] ?? null} />;
          },
          em: ({ children }) => <em className="italic text-ink/90">{children}</em>,
          h1: ({ children }) => <h1 className="my-4 text-2xl font-semibold tracking-tight text-ink">{children}</h1>,
          h2: ({ children }) => <h2 className="my-4 text-xl font-semibold tracking-tight text-ink">{children}</h2>,
          h3: ({ children }) => <h3 className="my-3 text-lg font-semibold text-ink">{children}</h3>,
          hr: () => <hr className="my-6 border-[var(--chat-border)]" />,
          img: ({ alt, src }) => (
            <img
              alt={alt ?? ""}
              src={src ?? ""}
              className="my-4 max-w-full rounded-[18px] border border-[var(--chat-border)]"
            />
          ),
          li: ({ children }) => <li className="my-1">{children}</li>,
          ol: ({ children }) => <ol className="my-3 list-decimal space-y-1 pl-6">{children}</ol>,
          p: ({ children }) => <p className="my-2.5 whitespace-pre-wrap">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto rounded-[18px] border border-[var(--chat-border)]">
              <table className="min-w-full border-collapse text-left text-sm">{children}</table>
            </div>
          ),
          tbody: ({ children }) => <tbody className="divide-y divide-[var(--chat-border)]">{children}</tbody>,
          td: ({ children }) => <td className="border-r border-[var(--chat-border)] px-3 py-2 align-top last:border-r-0">{children}</td>,
          th: ({ children }) => (
            <th className="border-r border-[var(--chat-border)] bg-[var(--chat-subtle)] px-3 py-2 font-semibold text-ink last:border-r-0">
              {children}
            </th>
          ),
          tr: ({ children }) => <tr>{children}</tr>,
          ul: ({ children }) => <ul className="my-3 list-disc space-y-1 pl-6">{children}</ul>,
        }}
      >
        {value}
      </ReactMarkdown>
    </div>
  );
}
