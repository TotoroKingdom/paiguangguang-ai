import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { AssistantProvider, useAssistant } from "./provider";
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
afterEach(() => {
  vi.useRealTimers();
});
it("stops the timer and preserves stopped output", () => {
  vi.useFakeTimers();
  const { result } = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  let id = "";
  act(() => {
    id = result.current.sendMessage({ text: "你好", fileIds: [] });
  });
  act(() => {
    vi.advanceTimersByTime(400);
    result.current.stopGeneration(id);
  });
  const before = result.current.state.conversations.find((c) => c.id === id)!.messages[1];
  act(() => {
    vi.advanceTimersByTime(3000);
  });
  expect(result.current.state.conversations.find((c) => c.id === id)!.messages[1]).toEqual(before);
  expect(before.status).toBe("stopped");
});
it("retries failed generation without duplicating user message", () => {
  vi.useFakeTimers();
  const { result } = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  let id = "";
  act(() => {
    id = result.current.sendMessage({ text: "需求", fileIds: [], simulateFailure: true });
  });
  act(() => {
    vi.advanceTimersByTime(800);
  });
  expect(result.current.state.conversations.find((c) => c.id === id)!.messages[1].status).toBe(
    "error",
  );
  act(() => {
    result.current.retryMessage(id);
  });
  act(() => {
    vi.advanceTimersByTime(1200);
  });
  const messages = result.current.state.conversations.find((c) => c.id === id)!.messages;
  expect(messages).toHaveLength(2);
  expect(messages[1].status).toBe("complete");
});
it("restores before persisting", () => {
  const first = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  act(() => first.result.current.dispatch({ type: "SET_DRAFT", patch: { text: "恢复" } }));
  first.unmount();
  const second = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  expect(second.result.current.state.draft.text).toBe("恢复");
});

it("retries stopped output and finishes all skill steps", () => {
  vi.useFakeTimers();
  const { result } = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  let id = "";
  act(() => {
    id = result.current.sendMessage({
      text: "需求",
      fileIds: [],
      capability: { id: "skill-2", kind: "skill", name: "PRD编写" },
    });
  });
  act(() => result.current.stopGeneration(id));
  act(() => result.current.retryMessage(id));
  act(() => vi.advanceTimersByTime(1200));
  const messages = result.current.state.conversations.find((c) => c.id === id)!.messages;
  expect(messages).toHaveLength(2);
  expect(messages[1].steps).toHaveLength(6);
  expect(messages[1].status).toBe("complete");
});
it("keeps working in memory when storage is unavailable", () => {
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    get: () => {
      throw new Error("unavailable");
    },
  });
  const { result } = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  expect(result.current.storageNotice).toContain("内存");
  act(() => result.current.dispatch({ type: "SET_DRAFT", patch: { text: "内存草稿" } }));
  expect(result.current.state.draft.text).toBe("内存草稿");
});
it("reset cancels pending generation", () => {
  vi.useFakeTimers();
  const { result } = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  let id = "";
  act(() => {
    id = result.current.sendMessage({ text: "测试", fileIds: [] });
  });
  act(() => result.current.resetDemo());
  act(() => vi.advanceTimersByTime(5000));
  expect(result.current.state.conversations.some((c) => c.id === id)).toBe(false);
  expect(vi.getTimerCount()).toBe(0);
});

it("retries the specified older failed message without changing the newer error", () => {
  vi.useFakeTimers();
  const { result } = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  let id = "";
  act(() => {
    id = result.current.sendMessage({ text: "第一条", fileIds: [], simulateFailure: true });
  });
  act(() => vi.advanceTimersByTime(800));
  act(() => {
    result.current.sendMessage({
      conversationId: id,
      text: "第二条",
      fileIds: [],
      simulateFailure: true,
    });
  });
  act(() => vi.advanceTimersByTime(800));
  const before = result.current.state.conversations.find((c) => c.id === id)!.messages;
  const oldId = before[1].id;
  const newId = before[3].id;
  act(() => result.current.retryMessage(id, oldId));
  act(() => vi.advanceTimersByTime(1200));
  const messages = result.current.state.conversations.find((c) => c.id === id)!.messages;
  expect(messages.find((m) => m.id === oldId)?.status).toBe("complete");
  expect(messages.find((m) => m.id === newId)?.status).toBe("error");
  expect(messages).toHaveLength(4);
});
it("does not interrupt an active generation when retry is requested", () => {
  vi.useFakeTimers();
  const { result } = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  let id = "";
  act(() => {
    id = result.current.sendMessage({ text: "失败", fileIds: [], simulateFailure: true });
  });
  act(() => vi.advanceTimersByTime(800));
  const oldId = result.current.state.conversations.find((c) => c.id === id)!.messages[1].id;
  act(() => {
    result.current.sendMessage({ conversationId: id, text: "进行中", fileIds: [] });
  });
  act(() => result.current.retryMessage(id, oldId));
  act(() => vi.advanceTimersByTime(1200));
  const messages = result.current.state.conversations.find((c) => c.id === id)!.messages;
  expect(messages[1].status).toBe("error");
  expect(messages[3].status).toBe("complete");
});

it("retry reports disconnected MCP without starting simulation", () => {
  vi.useFakeTimers();
  const { result } = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  let id = "";
  act(() => {
    id = result.current.sendMessage({
      text: "知识查询",
      fileIds: [],
      capability: { id: "mcp-1", kind: "mcp", name: "知识中心MCP" },
      simulateFailure: true,
    });
  });
  act(() => vi.advanceTimersByTime(800));
  const connector = result.current.state.connectors.find((c) => c.id === "mcp-1")!;
  act(() =>
    result.current.dispatch({
      type: "UPSERT_CONNECTOR",
      connector: { ...connector, status: "disconnected" },
    }),
  );
  act(() => result.current.retryMessage(id));
  const message = result.current.state.conversations.find((c) => c.id === id)!.messages[1];
  expect(message.status).toBe("error");
  expect(message.content).toBe("连接器未完成模拟连接，请先配置");
  expect(vi.getTimerCount()).toBe(0);
});
it("retry preserves historical request while dropping deleted skill and attachment from execution", () => {
  vi.useFakeTimers();
  const { result } = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  const skill = {
    id: "personal-1",
    kind: "skill" as const,
    name: "个人技能",
    source: "personal" as const,
    description: "示例",
    category: "个人",
    icon: "skill",
    steps: ["个人步骤"],
  };
  let id = "";
  act(() => result.current.dispatch({ type: "IMPORT_SKILL", skill }));
  act(() => {
    id = result.current.sendMessage({
      text: "处理资料",
      fileIds: ["file-1"],
      capability: skill,
      simulateFailure: true,
    });
  });
  act(() => vi.advanceTimersByTime(800));
  act(() => {
    result.current.dispatch({ type: "DELETE_SKILL", id: skill.id });
    result.current.dispatch({ type: "DELETE_FILE", id: "file-1" });
  });
  act(() => result.current.retryMessage(id));
  act(() => vi.advanceTimersByTime(1200));
  const messages = result.current.state.conversations.find((c) => c.id === id)!.messages;
  expect(messages[0].attachments?.[0].name).toBe("项目需求.md");
  expect(messages[1].request?.capability?.id).toBe(skill.id);
  expect(messages[1].request?.fileIds).toEqual(["file-1"]);
  expect(messages[1].content).toContain("原能力已不可用");
  expect(messages[1].content).toContain("原附件已删除");
  expect(messages[1].steps?.[0].title).toBe("理解任务");
});
