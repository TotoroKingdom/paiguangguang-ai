import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MarkdownContent } from "../components/markdown-content";

describe("MarkdownContent", () => {
  it("renders headings, tables, safe links, and code blocks", () => {
    render(
      <MarkdownContent
        value={[
          "# Title",
          "",
          "> Quote",
          "",
          "| Name | Value |",
          "| --- | --- |",
          "| Alpha | 1 |",
          "",
          "[OpenAI](https://openai.com)",
          "",
          "[Unsafe](javascript:alert(1))",
          "",
          "```ts",
          "const count = 1;",
          "```",
        ].join("\n")}
      />
    );

    expect(screen.getByRole("heading", { name: "Title", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("Quote")).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "OpenAI" })).toHaveAttribute("href", "https://openai.com/");
    expect(screen.queryByRole("link", { name: "Unsafe" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy code" })).toBeInTheDocument();
    expect(screen.getByText("const count = 1;")).toBeInTheDocument();
  });
});
