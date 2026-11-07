import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import { AssistantDialog } from "./assistant-dialog";

function Example() {
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState(false);
  return (
    <>
      <button onClick={() => setOpen(true)}>打开设置</button>
      {open && (
        <AssistantDialog title={confirm ? "确认重置" : "设置"} onClose={() => setOpen(false)}>
          {confirm ? (
            <button onClick={() => setConfirm(false)}>取消</button>
          ) : (
            <button onClick={() => setConfirm(true)}>重置</button>
          )}
        </AssistantDialog>
      )}
    </>
  );
}
describe("AssistantDialog", () => {
  it("contains keyboard focus, closes with Escape and restores its trigger", () => {
    render(<Example />);
    const trigger = screen.getByRole("button", { name: "打开设置" });
    trigger.focus();
    fireEvent.click(trigger);
    const close = screen.getByRole("button", { name: "关闭弹窗" });
    const reset = screen.getByRole("button", { name: "重置" });
    reset.focus();
    fireEvent.keyDown(reset, { key: "Tab" });
    expect(close).toHaveFocus();
    fireEvent.keyDown(close, { key: "Tab", shiftKey: true });
    expect(reset).toHaveFocus();
    fireEvent.keyDown(reset, { key: "Escape" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
  it("recovers focus when a confirmation replaces the focused content", () => {
    render(<Example />);
    fireEvent.click(screen.getByRole("button", { name: "打开设置" }));
    const reset = screen.getByRole("button", { name: "重置" });
    reset.focus();
    fireEvent.click(reset);
    expect(screen.getByRole("dialog", { name: "确认重置" })).toContainElement(
      document.activeElement as HTMLElement,
    );
    screen.getByRole("button", { name: "打开设置" }).focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(screen.getByRole("button", { name: "关闭弹窗" })).toHaveFocus();
  });
});
