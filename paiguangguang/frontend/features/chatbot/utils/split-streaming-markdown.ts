export type StreamingMarkdownParts = {
  stableBlocks: string[];
  activeTail: string;
};

type Fence = {
  marker: "`" | "~";
  length: number;
};

export function splitStreamingMarkdown(value: string): StreamingMarkdownParts {
  const stableBlocks: string[] = [];
  let blockStart = 0;
  let cursor = 0;
  let fence: Fence | null = null;

  while (cursor < value.length) {
    const newline = value.indexOf("\n", cursor);
    const lineEnd = newline === -1 ? value.length : newline + 1;
    const line = value.slice(cursor, lineEnd);
    const body = line.replace(/\r?\n$/, "");
    const fenceLine = body.replace(/^[ \t]{0,3}/, "").match(/^(`{3,}|~{3,})(.*)$/);

    if (fenceLine) {
      const token = fenceLine[1];
      const marker = token[0] as Fence["marker"];
      if (fence === null) {
        fence = { marker, length: token.length };
      } else if (
        marker === fence.marker &&
        token.length >= fence.length &&
        fenceLine[2].trim() === ""
      ) {
        fence = null;
      }
    }

    if (fence === null && body.trim() === "" && lineEnd > blockStart) {
      const block = value.slice(blockStart, lineEnd);
      if (block.trim().length > 0) {
        stableBlocks.push(block);
        blockStart = lineEnd;
      }
    }
    cursor = lineEnd;
  }

  return {
    stableBlocks,
    activeTail: value.slice(blockStart),
  };
}
