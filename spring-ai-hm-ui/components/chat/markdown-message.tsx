import { CodeBlock } from "@/components/chat/code-block";
import type { ReactNode } from "react";

type MarkdownMessageProps = {
  content: string;
};

type MarkdownSegment =
  | {
      code: string;
      language?: string;
      type: "code";
    }
  | {
      content: string;
      type: "text";
    };

export function MarkdownMessage({ content }: MarkdownMessageProps) {
  const segments = splitMarkdown(content);

  return (
    <div className="space-y-3">
      {segments.map((segment, index) => {
        if (segment.type === "code") {
          return (
            <CodeBlock
              key={`${index}-code`}
              code={segment.code}
              language={segment.language}
            />
          );
        }

        return <TextMarkdown key={`${index}-text`} content={segment.content} />;
      })}
    </div>
  );
}

function splitMarkdown(content: string): MarkdownSegment[] {
  const lines = content.split("\n");
  const segments: MarkdownSegment[] = [];
  let textBuffer: string[] = [];
  let codeBuffer: string[] = [];
  let codeLanguage = "";
  let inCodeBlock = false;

  function flushText() {
    if (textBuffer.length > 0) {
      segments.push({ content: textBuffer.join("\n"), type: "text" });
      textBuffer = [];
    }
  }

  for (const line of lines) {
    const codeFence = line.match(/^```([\w-]*)\s*$/);

    if (codeFence) {
      if (inCodeBlock) {
        segments.push({
          code: codeBuffer.join("\n"),
          language: codeLanguage,
          type: "code",
        });
        codeBuffer = [];
        codeLanguage = "";
        inCodeBlock = false;
      } else {
        flushText();
        codeLanguage = codeFence[1] ?? "";
        inCodeBlock = true;
      }

      continue;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
    } else {
      textBuffer.push(line);
    }
  }

  if (inCodeBlock) {
    segments.push({
      code: codeBuffer.join("\n"),
      language: codeLanguage,
      type: "code",
    });
  }

  flushText();

  return segments;
}

function TextMarkdown({ content }: MarkdownMessageProps) {
  const blocks = content.split(/\n{2,}/).filter((block) => block.trim());

  return (
    <>
      {blocks.map((block, index) => (
        <BlockMarkdown key={`${index}-${block.slice(0, 12)}`} block={block} />
      ))}
    </>
  );
}

function BlockMarkdown({ block }: { block: string }) {
  const lines = block.split("\n");
  const elements: ReactNode[] = [];
  let currentList: string[] = [];
  let currentOrderedList: string[] = [];
  let currentQuote: string[] = [];
  let currentPara: string[] = [];

  function flushList() {
    if (currentList.length > 0) {
      elements.push(
        <ul className="list-disc space-y-1 pl-5" key={`ul-${elements.length}`}>
          {currentList.map((line, i) => (
            <li key={`li-${i}`}>
              {renderInlineMarkdown(line.replace(/^\s*[-*]\s+/, ""))}
            </li>
          ))}
        </ul>,
      );
      currentList = [];
    }
  }

  function flushOrderedList() {
    if (currentOrderedList.length > 0) {
      elements.push(
        <ol
          className="list-decimal space-y-1 pl-5"
          key={`ol-${elements.length}`}
        >
          {currentOrderedList.map((line, i) => (
            <li key={`oli-${i}`}>
              {renderInlineMarkdown(line.replace(/^\s*\d+\.\s+/, ""))}
            </li>
          ))}
        </ol>,
      );
      currentOrderedList = [];
    }
  }

  function flushQuote() {
    if (currentQuote.length > 0) {
      elements.push(
        <blockquote
          className="border-l-2 border-zinc-300 pl-3 text-zinc-700"
          key={`bq-${elements.length}`}
        >
          {currentQuote.map((line, i) => (
            <span key={`bql-${i}`}>
              {i > 0 ? <br /> : null}
              {renderInlineMarkdown(line.replace(/^\s*>\s?/, ""))}
            </span>
          ))}
        </blockquote>,
      );
      currentQuote = [];
    }
  }

  function flushPara() {
    if (currentPara.length > 0) {
      elements.push(
        <p
          className="whitespace-pre-wrap break-words"
          key={`p-${elements.length}`}
        >
          {currentPara.map((line, i) => (
            <span key={`pl-${i}`}>
              {i > 0 ? <br /> : null}
              {renderInlineMarkdown(line)}
            </span>
          ))}
        </p>,
      );
      currentPara = [];
    }
  }

  for (const line of lines) {
    const trimmed = line.trim();
    const headingMatch = trimmed.match(/^(#{1,3})\s+(.+)$/);

    if (headingMatch) {
      flushList();
      flushOrderedList();
      flushQuote();
      flushPara();
      const level = headingMatch[1].length;
      const className =
        level === 1
          ? "text-xl font-semibold"
          : level === 2
            ? "text-lg font-semibold"
            : "text-base font-semibold";
      elements.push(
        <div className={className} key={`h-${elements.length}`}>
          {renderInlineMarkdown(headingMatch[2])}
        </div>,
      );
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      flushOrderedList();
      flushQuote();
      flushPara();
      currentList.push(line);
      continue;
    }

    if (/^\s*\d+\.\s+/.test(line)) {
      flushList();
      flushQuote();
      flushPara();
      currentOrderedList.push(line);
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      flushList();
      flushOrderedList();
      flushPara();
      currentQuote.push(line);
      continue;
    }

    flushList();
    flushOrderedList();
    flushQuote();
    currentPara.push(line);
  }

  flushList();
  flushOrderedList();
  flushQuote();
  flushPara();

  return <>{elements}</>;
}

function renderInlineMarkdown(text: string) {
  const tokenPattern =
    /(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\)|\*[^*]+\*)/g;
  const nodes: ReactNode[] = [];
  let cursor = 0;
  let match: RegExpExecArray | null;

  while ((match = tokenPattern.exec(text))) {
    if (match.index > cursor) {
      nodes.push(text.slice(cursor, match.index));
    }

    const token = match[0];

    if (token.startsWith("`")) {
      nodes.push(
        <code
          key={`${match.index}-${token}`}
          className="rounded bg-zinc-200 px-1 py-0.5 text-[0.9em] text-zinc-900"
        >
          {token.slice(1, -1)}
        </code>,
      );
    } else if (token.startsWith("**")) {
      nodes.push(
        <strong key={`${match.index}-${token}`} className="font-semibold">
          {token.slice(2, -2)}
        </strong>,
      );
    } else if (token.startsWith("*")) {
      nodes.push(
        <em key={`${match.index}-${token}`}>{token.slice(1, -1)}</em>,
      );
    } else {
      const linkMatch = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      const href = linkMatch?.[2] ?? "#";

      nodes.push(
        <a
          key={`${match.index}-${token}`}
          className="text-blue-600 underline underline-offset-2"
          href={href}
          rel="noreferrer"
          target="_blank"
        >
          {linkMatch?.[1] ?? token}
        </a>,
      );
    }

    cursor = match.index + token.length;
  }

  if (cursor < text.length) {
    nodes.push(text.slice(cursor));
  }

  return nodes;
}
