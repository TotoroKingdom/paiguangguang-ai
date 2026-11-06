import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { ApiMessage } from "./api";
import type { ChatMessage, Conversation } from "./types";

const api = vi.hoisted(() => ({
  apiCreateConversation: vi.fn(),
  createConversation: vi.fn(),
  createTurn: vi.fn(),
  deleteConversation: vi.fn(),
  getConversation: vi.fn(),
  listConversations: vi.fn(),
  patchMessage: vi.fn(),
  renameConversation: vi.fn(),
  apiCreateTurn: vi.fn(),
  apiDeleteConversation: vi.fn(),
  apiGetConversation: vi.fn(),
  apiListConversations: vi.fn(),
  apiPatchMessage: vi.fn(),
  apiRenameConversation: vi.fn(),
  apiMessageToChatMessage: vi.fn(),
  toConversation: vi.fn(),
  AssistantApiError: class AssistantApiError extends Error {},
}));
vi.mock("./api", () => api);

const messageRequests = new Map<string, ApiMessage["request"]>();

import { AssistantProvider, useAssistant } from "./provider";

const makeConversation = (id = "remote-1"): Conversation => ({
  id,
  title: "新对话",
  createdAt: "2026-01-01T09:00:00.000Z",
  updatedAt: "2026-01-01T09:00:00.000Z",
  messages: [],
  loaded: false,
  version: 1,
});
const toChat = (message: ApiMessage): ChatMessage => ({
  id: message.id,
  role: message.role,
  content: message.content,
  status: message.status,
  steps: message.steps,
  capability: message.capability,
  attachments: message.attachments,
  request: message.request ?? undefined,
});
const makeApiMessage = (
  id: string,
  role: "user" | "assistant",
  request: ApiMessage["request"] = null,
): ApiMessage => ({
  id,
  role,
  content: role === "user" ? request?.text ?? "问题" : "",
  status: role === "user" ? "complete" : "generating",
  steps: [],
  capability: role === "user" ? request?.capability ?? null : null,
  attachments: [],
  request,
  clientTurnId: role === "user" ? "turn-1" : null,
  createdAt: "2026-01-01T09:00:00.000Z",
  updatedAt: "2026-01-01T09:00:00.000Z",
});

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
  api.apiListConversations.mockResolvedValue([]);
  api.apiCreateConversation.mockImplementation(async () => makeConversation());
  api.createConversation.mockImplementation(async () => makeConversation());
  api.createTurn.mockImplementation(async (...args: Parameters<typeof api.apiCreateTurn>) => api.apiCreateTurn(...args));
  api.listConversations.mockResolvedValue([]);
  api.patchMessage.mockImplementation(async (...args: Parameters<typeof api.apiPatchMessage>) => api.apiPatchMessage(...args));
  api.apiMessageToChatMessage.mockImplementation(toChat);
  api.toConversation.mockImplementation((summary: Conversation) => ({ ...summary, messages: [] }));
  api.apiPatchMessage.mockImplementation(async (_conversationId: string, messageId: string, patch) => ({
    ...makeApiMessage(messageId, "assistant"),
    request: messageRequests.get(messageId) ?? null,
    ...patch,
  }));
  messageRequests.clear();
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

async function send(result: { current: ReturnType<typeof useAssistant> }, input: Parameters<ReturnType<typeof useAssistant>["sendMessage"]>[0]) {
  let id: string | null = null;
  await act(async () => {
    id = await result.current.sendMessage(input);
  });
  expect(id).toBeTruthy();
  return id as unknown as string;
}

function configureTurn() {
  api.apiCreateTurn.mockImplementation(async (conversationId: string, input) => {
    const request = { ...input, conversationId };
    messageRequests.set("assistant-1", request);
    return {
      conversation: { ...makeConversation(conversationId), title: input.text.slice(0, 24), version: 2 },
      userMessage: makeApiMessage("user-1", "user", request),
      assistantMessage: { ...makeApiMessage("assistant-1", "assistant", request), request },
    };
  });
}

it("stops the timer and preserves stopped output", async () => {
  vi.useFakeTimers();
  configureTurn();
  const { result } = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  const id = await send(result, { text: "你好", fileIds: [] });
  await act(async () => {
    vi.advanceTimersByTime(400);
    result.current.stopGeneration(id);
    await Promise.resolve();
  });
  const before = result.current.state.conversations.find((c) => c.id === id)!.messages[1];
  await act(async () => {
    vi.advanceTimersByTime(3000);
    await Promise.resolve();
  });
  expect(result.current.state.conversations.find((c) => c.id === id)!.messages[1]).toEqual(before);
  expect(before.status).toBe("stopped");
});

it("retries failed generation without duplicating user message", async () => {
  vi.useFakeTimers();
  configureTurn();
  const { result } = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  const id = await send(result, { text: "需求", fileIds: [], simulateFailure: true });
  await act(async () => {
    vi.advanceTimersByTime(800);
    await Promise.resolve();
  });
  expect(result.current.state.conversations.find((c) => c.id === id)!.messages[1].status).toBe("error");
  await act(async () => {
    result.current.retryMessage(id);
    await Promise.resolve();
  });
  await act(async () => {
    vi.advanceTimersByTime(1200);
    await Promise.resolve();
  });
  const messages = result.current.state.conversations.find((c) => c.id === id)!.messages;
  expect(messages).toHaveLength(2);
  expect(messages[1].status).toBe("complete");
});

it("persists drafts locally while sessions remain server-owned", async () => {
  const first = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  await act(async () => {
    first.result.current.dispatch({ type: "SET_DRAFT", patch: { text: "恢复" } });
    await Promise.resolve();
  });
  first.unmount();
  const second = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  expect(second.result.current.state.draft.text).toBe("恢复");
  expect(second.result.current.state.conversations).toEqual([]);
});

it("retries stopped output and finishes all skill steps", async () => {
  vi.useFakeTimers();
  configureTurn();
  const { result } = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  const id = await send(result, {
    text: "需求",
    fileIds: [],
    capability: { id: "skill-2", kind: "skill", name: "PRD编写" },
  });
  act(() => result.current.stopGeneration(id));
  await act(async () => {
    result.current.retryMessage(id);
    await Promise.resolve();
  });
  await act(async () => {
    vi.advanceTimersByTime(1200);
    await Promise.resolve();
  });
  const messages = result.current.state.conversations.find((c) => c.id === id)!.messages;
  expect(messages).toHaveLength(2);
  expect(messages[1].steps).toHaveLength(6);
  expect(messages[1].status).toBe("complete");
});

it("keeps working in memory when storage is unavailable", () => {
  Object.defineProperty(window, "localStorage", { configurable: true, get: () => { throw new Error("unavailable"); } });
  const { result } = renderHook(() => useAssistant(), { wrapper: AssistantProvider });
  expect(result.current.storageNotice).toContain("内存");
  act(() => result.current.dispatch({ type: "SET_DRAFT", patch: { text: "内存草稿" } }));
  expect(result.current.state.draft.text).toBe("内存草稿");
});
