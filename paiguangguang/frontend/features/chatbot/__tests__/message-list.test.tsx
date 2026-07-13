import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MessageList } from "../components/message-list";
import type { MessageData } from "../types/message";

function makeMessage(overrides: Partial<MessageData>): MessageData {
  return {
    id: "msg-1",
    conversation_id: "conv-1",
    role: "assistant",
    content: "Hello **world**\n\n[OpenAI](https://openai.com)\n\n`inline`",
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

describe("MessageList", () => {
  it("renders markdown content with safe links and code styling", () => {
    render(
      <MessageList
        messages={[makeMessage({})]}
        loadingHistory={false}
        historyError={null}
        hasMore={false}
        onLoadMore={vi.fn()}
        streamPhase="idle"
        streamingMessageId={null}
      />
    );

    expect(screen.getByText("Hello")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "OpenAI" })).toHaveAttribute("href", "https://openai.com/");
    expect(screen.getByText("inline")).toBeInTheDocument();
  });
});

