import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StreamingMarkdownContent } from "../components/streaming-markdown-content";

describe("StreamingMarkdownContent", () => {
  it("keeps settled blocks mounted while the active tail grows", () => {
    const { rerender } = render(
      <StreamingMarkdownContent value={"Settled.\n\nTail"} streaming />
    );
    const settled = screen.getByTestId("streaming-markdown-block-0");

    rerender(<StreamingMarkdownContent value={"Settled.\n\nTail grows"} streaming />);

    expect(screen.getByTestId("streaming-markdown-block-0")).toBe(settled);
    expect(screen.getByText("Tail grows")).toBeInTheDocument();
    expect(screen.getByTestId("streaming-cursor")).toBeInTheDocument();
  });

  it("removes the cursor for a terminal message", () => {
    render(<StreamingMarkdownContent value="Done" streaming={false} />);

    expect(screen.getByText("Done")).toBeInTheDocument();
    expect(screen.queryByTestId("streaming-cursor")).not.toBeInTheDocument();
  });
});
