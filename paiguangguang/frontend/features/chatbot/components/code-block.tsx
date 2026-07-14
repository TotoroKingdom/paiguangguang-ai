"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

type CodeBlockProps = {
  value: string;
  language?: string | null;
};

export function CodeBlock({ value, language = null }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const label = useMemo(() => {
    if (language) {
      return language;
    }
    return "code";
  }, [language]);

  const handleCopy = useCallback(async () => {
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
      }
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }, [value]);

  useEffect(() => {
    if (!copied) {
      return;
    }
    const timeout = window.setTimeout(() => setCopied(false), 1500);
    return () => window.clearTimeout(timeout);
  }, [copied]);

  return (
    <figure className="my-4 overflow-hidden rounded-2xl border border-ink/10 bg-ink/[0.03]">
      <figcaption className="flex items-center justify-between gap-3 border-b border-ink/10 px-4 py-2 text-xs text-ink/50">
        <span className="font-mono uppercase tracking-[0.18em] text-ink/45">{label}</span>
        <button
          type="button"
          onClick={() => void handleCopy()}
          className="rounded-full border border-ink/10 bg-white px-3 py-1.5 font-semibold text-ink transition hover:border-tide/40 hover:bg-paper"
        >
          {copied ? "Copied" : "Copy code"}
        </button>
      </figcaption>
      <pre className="overflow-x-auto px-4 py-4 text-sm leading-6 text-ink">
        <code className="font-mono whitespace-pre-wrap">{value}</code>
      </pre>
    </figure>
  );
}
