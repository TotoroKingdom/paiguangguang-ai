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

  it("shows the current model in the composer footer and ignores enter while composing", () => {
    const onSubmit = vi.fn();

    render(
      <ChatComposer
        value={"Hello"}
        model="deepseek-chat"
        onChange={vi.fn()}
        onSubmit={onSubmit}
      />
    );

    expect(screen.getByText("Model: deepseek-chat")).toBeInTheDocument();

    const textbox = screen.getByRole("textbox");
    fireEvent.compositionStart(textbox);
    fireEvent.keyDown(textbox, { key: "Enter" });
    expect(onSubmit).not.toHaveBeenCalled();

    fireEvent.compositionEnd(textbox);
    fireEvent.keyDown(textbox, { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledWith("Hello");
  });
});
