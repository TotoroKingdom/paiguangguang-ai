"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Check, Copy } from "lucide-react";

import { Button } from "@/components/ui/button";

type CodeBlockProps = {
  code: string;
  language?: string;
};

const LANGUAGE_KEYWORDS: Record<string, string[]> = {
  css: [
    "align-items",
    "background",
    "border",
    "color",
    "display",
    "flex",
    "grid",
    "justify-content",
    "margin",
    "padding",
  ],
  js: [
    "async",
    "await",
    "break",
    "const",
    "continue",
    "else",
    "export",
    "for",
    "from",
    "function",
    "if",
    "import",
    "let",
    "return",
    "throw",
    "try",
  ],
  json: ["false", "null", "true"],
  ts: [
    "async",
    "await",
    "const",
    "export",
    "from",
    "function",
    "import",
    "interface",
    "let",
    "return",
    "type",
  ],
  tsx: [
    "async",
    "await",
    "const",
    "export",
    "from",
    "function",
    "import",
    "interface",
    "return",
    "type",
  ],
};

const LANGUAGE_ALIASES: Record<string, string> = {
  javascript: "js",
  jsx: "tsx",
  typescript: "ts",
};

export function CodeBlock({ code, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const normalizedLanguage = normalizeLanguage(language);
  const highlightedLines = useMemo(
    () => highlightCode(code, normalizedLanguage),
    [code, normalizedLanguage],
  );

  async function copyCode() {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  return (
    <div className="my-4 overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-100">
      <div className="flex h-9 items-center justify-between border-b border-white/10 bg-zinc-900 px-3">
        <span className="text-xs text-zinc-400">
          {normalizedLanguage || "text"}
        </span>
        <Button
          className="h-7 px-2 text-xs text-zinc-300 hover:bg-white/10 hover:text-white"
          size="sm"
          type="button"
          variant="ghost"
          onClick={copyCode}
        >
          {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      <pre className="overflow-x-auto p-4 text-[13px] leading-6">
        <code>
          {highlightedLines.map((line, lineIndex) => (
            <span key={`${lineIndex}-${line.raw}`} className="block">
              {line.nodes.length > 0 ? line.nodes : "\u00A0"}
            </span>
          ))}
        </code>
      </pre>
    </div>
  );
}

function normalizeLanguage(language?: string) {
  if (!language) {
    return "";
  }

  const normalized = language.toLowerCase().replace(/^language-/, "");

  return LANGUAGE_ALIASES[normalized] ?? normalized;
}

function highlightCode(code: string, language: string) {
  const keywords = LANGUAGE_KEYWORDS[language] ?? LANGUAGE_KEYWORDS.js;
  const keywordPattern = new RegExp(`\\b(${keywords.join("|")})\\b`, "g");

  return code.replace(/\n$/, "").split("\n").map((line) => ({
    raw: line,
    nodes: tokenizeLine(line, keywordPattern),
  }));
}

function tokenizeLine(line: string, keywordPattern: RegExp) {
  const tokenPattern =
    /("(?:\\.|[^"])*"|'(?:\\.|[^'])*'|`(?:\\.|[^`])*`|\/\/.*|\/\*.*\*\/|\b\d+(?:\.\d+)?\b)/g;
  const nodes: ReactNode[] = [];
  let cursor = 0;
  let tokenMatch: RegExpExecArray | null;

  while ((tokenMatch = tokenPattern.exec(line))) {
    appendKeywordNodes(line.slice(cursor, tokenMatch.index), keywordPattern, nodes);

    const token = tokenMatch[0];
    const className = token.startsWith("//") || token.startsWith("/*")
      ? "text-zinc-500"
      : /^\d/.test(token)
        ? "text-amber-300"
        : "text-emerald-300";

    nodes.push(
      <span key={`${tokenMatch.index}-${token}`} className={className}>
        {token}
      </span>,
    );
    cursor = tokenMatch.index + token.length;
  }

  appendKeywordNodes(line.slice(cursor), keywordPattern, nodes);

  return nodes;
}

function appendKeywordNodes(
  text: string,
  keywordPattern: RegExp,
  nodes: ReactNode[],
) {
  let cursor = 0;
  let keywordMatch: RegExpExecArray | null;

  keywordPattern.lastIndex = 0;

  while ((keywordMatch = keywordPattern.exec(text))) {
    if (keywordMatch.index > cursor) {
      nodes.push(text.slice(cursor, keywordMatch.index));
    }

    nodes.push(
      <span
        key={`${nodes.length}-${keywordMatch[0]}`}
        className="font-medium text-sky-300"
      >
        {keywordMatch[0]}
      </span>,
    );
    cursor = keywordMatch.index + keywordMatch[0].length;
  }

  if (cursor < text.length) {
    nodes.push(text.slice(cursor));
  }
}
