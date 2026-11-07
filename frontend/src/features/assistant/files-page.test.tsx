import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";
import { AssistantProvider, useAssistant } from "./provider";
import { FilesPage } from "./files-page";
function Draft() {
  const { state } = useAssistant();
  return <output data-testid="draft">{state.draft.fileIds.join(",")}</output>;
}
beforeEach(() => {
  const data = new Map<string, string>();
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    value: {
      getItem: (key: string) => data.get(key) ?? null,
      setItem: (key: string, value: string) => data.set(key, value),
      clear: () => data.clear(),
    },
  });
});
it("uploads metadata, selects multiple attachments, and confirms deletion", () => {
  render(
    <AssistantProvider>
      <FilesPage />
      <Draft />
    </AssistantProvider>,
  );
  fireEvent.change(screen.getByLabelText("上传本地文件"), {
    target: {
      files: [
        new File(["secret"], "新增.txt", { type: "text/plain" }),
        new File(["x"], "第二.txt"),
      ],
    },
  });
  expect(screen.getByText("新增.txt")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "选择聊天附件" }));
  const dialog = screen.getByRole("dialog");
  fireEvent.click(within(dialog).getByLabelText(/新增.txt/));
  fireEvent.click(within(dialog).getByLabelText(/第二.txt/));
  fireEvent.click(within(dialog).getByRole("button", { name: "用于聊天" }));
  expect(screen.getByTestId("draft").textContent?.split(",")).toHaveLength(2);
  fireEvent.click(screen.getByRole("button", { name: "删除文件：新增.txt" }));
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "确认删除" }));
  expect(screen.queryByText("新增.txt")).not.toBeInTheDocument();
  expect(screen.getByTestId("draft").textContent?.split(",")).toHaveLength(1);
});
