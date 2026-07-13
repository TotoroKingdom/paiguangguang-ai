import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChatComposer } from "../components/chat-composer";

describe("ChatComposer", () => {
  it("submits on enter and preserves multiline input on shift enter", () => {
    const onChange = vi.fn();
    const onSubmit = vi.fn();

    render(
      <ChatComposer
        value={"Hello"}
        onChange={onChange}
        onSubmit={onSubmit}
      />
    );

    fireEvent.keyDown(screen.getByRole("textbox"), { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledWith("Hello");

    fireEvent.keyDown(screen.getByRole("textbox"), { key: "Enter", shiftKey: true });
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("disables submit when over the limit", () => {
    render(
      <ChatComposer
        value={"x".repeat(4001)}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });
});

