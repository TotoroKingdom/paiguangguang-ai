import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";
import { AssistantProvider, useAssistant } from "./provider";
import { CatalogPage } from "./catalog-page";

function Draft() {
  const { state } = useAssistant();
  return <output data-testid="draft">{state.draft.capability?.name}</output>;
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
it("filters capabilities, manages favorites, and selects one for chat", () => {
  render(
    <AssistantProvider>
      <CatalogPage kind="tool" />
      <Draft />
    </AssistantProvider>,
  );
  fireEvent.change(screen.getByLabelText("搜索工具"), { target: { value: "网页" } });
  expect(screen.getByText("共 1 个工具")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /^网页搜索 / }));
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "用于聊天" }));
  expect(screen.getByTestId("draft")).toHaveTextContent("网页搜索");
  fireEvent.click(screen.getByRole("button", { name: "管理常用" }));
  const checkbox = within(screen.getByRole("dialog")).getByLabelText("网页搜索");
  expect(checkbox).toBeChecked();
  fireEvent.click(checkbox);
  expect(checkbox).not.toBeChecked();
});
it("reports invalid skill imports", () => {
  render(
    <AssistantProvider>
      <CatalogPage kind="skill" />
    </AssistantProvider>,
  );
  fireEvent.change(screen.getByLabelText("导入技能文件"), {
    target: { files: [new File(["abc"], "bad.txt")] },
  });
  expect(screen.getByRole("alert")).toHaveTextContent(".md");
});

it("configures a connector, exposes simulated failure, and retries", async () => {
  render(
    <AssistantProvider>
      <CatalogPage kind="mcp" />
    </AssistantProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: /^数据库MCP/ }));
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "连接设置" }));
  const config = screen.getByRole("dialog");
  fireEvent.change(within(config).getByLabelText("连接地址"), {
    target: { value: "https://example.com/mcp" },
  });
  fireEvent.click(within(config).getByRole("button", { name: "保存配置" }));
  fireEvent.click(screen.getByRole("button", { name: /^数据库MCP/ }));
  fireEvent.click(within(screen.getByRole("dialog")).getByLabelText("模拟连接失败"));
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "测试连接" }));
  expect(
    await within(screen.getByRole("dialog")).findByText("模拟连接失败，请重试。"),
  ).toBeInTheDocument();
  fireEvent.click(within(screen.getByRole("dialog")).getByLabelText("模拟连接失败"));
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "重试连接" }));
  expect(await within(screen.getByRole("dialog")).findByText("状态：已连接")).toBeInTheDocument();
});

it("imports a nonempty skill and confirms deleting it", async () => {
  render(
    <AssistantProvider>
      <CatalogPage kind="skill" />
    </AssistantProvider>,
  );
  const file = new File(["# 我的技能\n正文内容"], "skill.md", { type: "text/markdown" });
  Object.defineProperty(file, "text", { value: async () => "# 我的技能\n正文内容" });
  fireEvent.change(screen.getByLabelText("导入技能文件"), { target: { files: [file] } });
  fireEvent.click(await screen.findByRole("button", { name: /^我的技能 / }));
  expect(
    within(screen.getByRole("dialog")).getByText(/正文内容/, { selector: "pre" }),
  ).toBeInTheDocument();
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "删除技能" }));
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "取消" }));
  expect(screen.getByRole("button", { name: /^我的技能 / })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /^我的技能 / }));
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "删除技能" }));
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "确认删除" }));
  expect(screen.queryByRole("button", { name: /^我的技能 / })).not.toBeInTheDocument();
});
it("rejects empty skill content and invalid connector addresses", async () => {
  const { unmount } = render(
    <AssistantProvider>
      <CatalogPage kind="skill" />
    </AssistantProvider>,
  );
  const file = new File([" "], "empty.md");
  Object.defineProperty(file, "text", { value: async () => "  " });
  fireEvent.change(screen.getByLabelText("导入技能文件"), { target: { files: [file] } });
  expect(await screen.findByRole("alert")).toHaveTextContent("正文不能为空");
  unmount();
  render(
    <AssistantProvider>
      <CatalogPage kind="mcp" />
    </AssistantProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "连接设置" }));
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: /数据库MCP/ }));
  fireEvent.change(within(screen.getByRole("dialog")).getByLabelText("连接地址"), {
    target: { value: "file:///local" },
  });
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "保存配置" }));
  expect(within(screen.getByRole("dialog")).getByRole("alert")).toHaveTextContent("HTTP 或 HTTPS");
});
function ResetButton() {
  const { resetDemo } = useAssistant();
  return <button onClick={resetDemo}>重置测试</button>;
}
it("ignores a pending connection result after reset", async () => {
  render(
    <AssistantProvider>
      <CatalogPage kind="mcp" />
      <ResetButton />
    </AssistantProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: /^数据库MCP/ }));
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "测试连接" }));
  fireEvent.click(screen.getByRole("button", { name: "重置测试" }));
  await new Promise((resolve) => setTimeout(resolve, 400));
  expect(within(screen.getByRole("dialog")).getByText("状态：待配置")).toBeInTheDocument();
});
