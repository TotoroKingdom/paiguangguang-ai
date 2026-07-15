"use client";

import { memo } from "react";

import { splitStreamingMarkdown } from "../utils/split-streaming-markdown";
import { MarkdownContent } from "./markdown-content";

type StreamingMarkdownContentProps = {
  value: string;
  streaming: boolean;
};

const StableMarkdownBlock = memo(function StableMarkdownBlock({
  value,
  index,
}: {
  value: string;
  index: number;
}) {
  return (
    <div data-testid={`streaming-markdown-block-${index}`}>
      <MarkdownContent value={value} />
    </div>
  );
});

export function StreamingMarkdownContent({ value, streaming }: StreamingMarkdownContentProps) {
  if (!streaming) {
    return <MarkdownContent value={value} />;
  }

  const { stableBlocks, activeTail } = splitStreamingMarkdown(value);

  return (
    <div className="min-w-0">
      {stableBlocks.map((block, index) => (
        <StableMarkdownBlock key={`${index}:${block}`} value={block} index={index} />
      ))}
      {activeTail ? <MarkdownContent value={activeTail} /> : null}
      <span
        aria-hidden="true"
        className="chat-stream-cursor"
        data-testid="streaming-cursor"
      />
    </div>
  );
}
