import { describe, expect, it } from "vitest";

import { splitStreamingMarkdown } from "../utils/split-streaming-markdown";

describe("splitStreamingMarkdown", () => {
  it("settles blocks only at blank lines", () => {
    expect(splitStreamingMarkdown("First paragraph.\n\nSecond para")).toEqual({
      stableBlocks: ["First paragraph.\n\n"],
      activeTail: "Second para",
    });
  });

  it("keeps an incomplete fenced code block in the active tail", () => {
    const value = "Intro.\n\n```ts\nconst answer = 42;\n\n";

    expect(splitStreamingMarkdown(value)).toEqual({
      stableBlocks: ["Intro.\n\n"],
      activeTail: "```ts\nconst answer = 42;\n\n",
    });
  });

  it("settles a closed fenced block at its following blank line", () => {
    const value = "```ts\nconst answer = 42;\n```\n\nTail";

    expect(splitStreamingMarkdown(value)).toEqual({
      stableBlocks: ["```ts\nconst answer = 42;\n```\n\n"],
      activeTail: "Tail",
    });
  });

  it("preserves every source character across stable blocks and the active tail", () => {
    const value = "One\r\n\r\nTwo\n\n\nThree";
    const parts = splitStreamingMarkdown(value);

    expect(`${parts.stableBlocks.join("")}${parts.activeTail}`).toBe(value);
  });
});
