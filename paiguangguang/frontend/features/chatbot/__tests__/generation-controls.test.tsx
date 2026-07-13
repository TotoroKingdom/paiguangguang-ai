import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChatComposer } from "../components/chat-composer";
import { MessageItem } from "../components/message-item";
import type { MessageData } from "../types/message";

function makeMessage(overrides: Partial<MessageData>): MessageData {
  return {
    id: "msg-1",
    conversation_id: "conv-1",
    role: "assistant",
    content: "Assistant answer",
    content_json: null,
    sequence_number: 2,
    status: "completed",
    model: "deepseek-chat",
    parent_message_id: "msg-user-1",
    client_request_id: null,
    prompt_tokens: 10,
    completion_tokens: 5,
    total_tokens: 15,
    error_code: null,
    created_at: "2026-07-13T10:00:00.000Z",
    updated_at: "2026-07-13T10:00:00.000Z",
    ...overrides,
  };
}

describe("generation controls", () => {
  it("renders retry and regenerate controls on terminal assistant messages", () => {
    const onRetry = vi.fn();
    const onRegenerate = vi.fn();

    render(
      <div>
        <MessageItem message={makeMessage({ status: "failed" })} onRetry={onRetry} />
        <MessageItem message={makeMessage({ status: "completed" })} onRegenerate={onRegenerate} />
      </div>
    );

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    fireEvent.click(screen.getByRole("button", { name: "Regenerate" }));

    expect(onRetry).toHaveBeenCalledTimes(1);
    expect(onRegenerate).toHaveBeenCalledTimes(1);
  });

  it("renders stop control on a streaming assistant message", () => {
    const onStop = vi.fn();

    render(<MessageItem message={makeMessage({ status: "streaming" })} onStop={onStop} />);

    fireEvent.click(screen.getByRole("button", { name: "Stop generation" }));
    expect(onStop).toHaveBeenCalledTimes(1);
  });

  it("shows stop control in the composer while sending", () => {
    const onStop = vi.fn();

    render(
      <ChatComposer
        value=""
        sending={true}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        onStop={onStop}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Stop generation" }));
    expect(onStop).toHaveBeenCalledTimes(1);
  });

  it("disables composer stop control while stopping", () => {
    render(
      <ChatComposer
        value=""
        sending={true}
        stopping={true}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        onStop={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: "Stopping..." })).toBeDisabled();
  });
});
