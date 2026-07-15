import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MessageItem } from "../components/message-item";
import type { MessageData } from "../types/message";

function makeMessage(overrides: Partial<MessageData>): MessageData {
  return {
    id: "msg-1",
    conversation_id: "conv-1",
    role: "assistant",
    content: "Hello **world**\n\n[OpenAI](https://openai.com)",
    content_json: null,
    sequence_number: 2,
    status: "completed",
    model: "deepseek-chat",
    parent_message_id: null,
    client_request_id: "req-1",
    prompt_tokens: 10,
    completion_tokens: 5,
    total_tokens: 15,
    error_code: null,
    created_at: "2026-07-13T10:00:00.000Z",
    updated_at: "2026-07-13T10:00:00.000Z",
    ...overrides,
  };
}

describe("MessageItem", () => {
  it("renders assistant messages as prose without the heavy card treatment", () => {
    render(<MessageItem message={makeMessage({})} />);

    const article = screen.getByTestId("message-msg-1");
    expect(article).not.toHaveClass("justify-end");
    expect(article).not.toHaveClass("shadow-sm");
    expect(screen.getByRole("link", { name: "OpenAI" })).toHaveAttribute("href", "https://openai.com/");
  });

  it("renders user messages as a light right-aligned bubble", () => {
    render(
      <MessageItem
        message={makeMessage({
          role: "user",
          content: "I need a summary",
        })}
      />
    );

    const article = screen.getByTestId("message-msg-1");
    expect(article).toHaveClass("justify-end");
    expect(screen.getByText("You")).toBeInTheDocument();
    expect(screen.getByText("I need a summary")).toBeInTheDocument();
  });

  it("shows the streaming cursor only while an assistant response is active", () => {
    const { rerender } = render(
      <MessageItem message={makeMessage({ status: "streaming", content: "Working" })} />
    );

    expect(screen.getByTestId("streaming-cursor")).toBeInTheDocument();

    rerender(<MessageItem message={makeMessage({ status: "completed", content: "Done" })} />);
    expect(screen.queryByTestId("streaming-cursor")).not.toBeInTheDocument();
  });
});
