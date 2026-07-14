# Chatbot Phase A Frontend Stream Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复缺陷 1–3，使前端请求命中正确 Chatbot API，并保证 SSE 事件不会跨请求或跨会话污染状态。

**Architecture:** API 路径由单一常量生成；`mergeChatStreamEvent` 是纯状态机，使用 `conversation_id + request_id + sequence` 三元边界；`useChatStream` 只管理浏览器 reader 生命周期，切换会话时 detach 而不调用服务器 stop。

**Tech Stack:** Next.js 14、React 18、TypeScript、Vitest、Testing Library、Fetch ReadableStream/SSE。

## Global Constraints

- Chatbot API 基础路径固定为 `/api/v1/chatbot`。
- 切换会话或 token 变化只 abort 当前 reader，不调用 `POST /stop`。
- `AbortError` 不展示为生成失败。
- 每个新 `request_id` 的 SSE sequence 可以从 1 重新开始。
- 所有实现先写失败测试，再写最小修复。

---

## File Map

- Modify: `frontend/features/chatbot/api/client.ts` — 导出唯一 API base 并构造 Conversation/Stop URL。
- Modify: `frontend/features/chatbot/api/stream.ts` — 复用同一 API base 构造 Message/SSE URL。
- Create: `frontend/features/chatbot/__tests__/api-client.test.ts` — 路径契约测试。
- Modify: `frontend/features/chatbot/utils/merge-stream-event.ts` — request/conversation/sequence 状态机。
- Modify: `frontend/features/chatbot/hooks/use-messages.ts` — 以当前 conversation 初始化 reducer。
- Modify: `frontend/features/chatbot/hooks/use-chat-stream.ts` — reader abort 和迟到事件隔离。
- Modify: `frontend/features/chatbot/__tests__/chat-stream.test.ts` — 连续请求和旧事件测试。
- Create: `frontend/features/chatbot/__tests__/use-chat-stream.test.tsx` — 会话切换 reader 生命周期测试。

### Task 1: 统一 Chatbot API 基础路径

**Files:**
- Create: `frontend/features/chatbot/__tests__/api-client.test.ts`
- Modify: `frontend/features/chatbot/api/client.ts`
- Modify: `frontend/features/chatbot/api/stream.ts`

**Interfaces:**
- Produces: `export const CHATBOT_API_BASE = "/api/v1/chatbot"`。
- Consumes: `getJson`、`postJson`、`patchJson`、`deleteJson` 和 `getBackendBaseUrl` 的现有签名。

- [ ] **Step 1: 写失败的 Conversation 路径契约测试**

创建 `frontend/features/chatbot/__tests__/api-client.test.ts`：

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  getJson: vi.fn(),
  postJson: vi.fn(),
  patchJson: vi.fn(),
  deleteJson: vi.fn(),
}));

vi.mock("@/lib/api", () => apiMocks);

import {
  archiveConversation,
  createConversation,
  deleteConversation,
  getConversation,
  listConversations,
  restoreConversation,
  updateConversation,
} from "../api/client";

describe("chatbot API path contract", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getJson.mockResolvedValue({ items: [], next_cursor: null, has_more: false });
    apiMocks.postJson.mockResolvedValue({});
    apiMocks.patchJson.mockResolvedValue({});
    apiMocks.deleteJson.mockResolvedValue({});
  });

  it("uses /api/v1/chatbot for every conversation operation", async () => {
    await listConversations({ token: "token", status: "active", limit: 20 });
    await getConversation({ token: "token", conversationId: "conv-1" });
    await createConversation({ token: "token" }, { title: "Thread" });
    await updateConversation(
      { token: "token", conversationId: "conv-1" },
      { title: "Renamed" }
    );
    await archiveConversation({ token: "token", conversationId: "conv-1" });
    await restoreConversation({ token: "token", conversationId: "conv-1" });
    await deleteConversation({ token: "token", conversationId: "conv-1" });

    expect(apiMocks.getJson).toHaveBeenNthCalledWith(
      1,
      "/api/v1/chatbot/conversations?status=active&limit=20",
      { token: "token" }
    );
    expect(apiMocks.getJson).toHaveBeenNthCalledWith(
      2,
      "/api/v1/chatbot/conversations/conv-1",
      { token: "token" }
    );
    expect(apiMocks.postJson.mock.calls[0][0]).toBe("/api/v1/chatbot/conversations");
    expect(apiMocks.patchJson.mock.calls[0][0]).toBe("/api/v1/chatbot/conversations/conv-1");
    expect(apiMocks.postJson.mock.calls[1][0]).toBe("/api/v1/chatbot/conversations/conv-1/archive");
    expect(apiMocks.postJson.mock.calls[2][0]).toBe("/api/v1/chatbot/conversations/conv-1/restore");
    expect(apiMocks.deleteJson.mock.calls[0][0]).toBe("/api/v1/chatbot/conversations/conv-1");
  });
});
```

- [ ] **Step 2: 运行测试，确认旧路径导致失败**

Run:

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/api-client.test.ts
```

Expected: FAIL；实际路径以 `/api/v1/conversations` 开头。

- [ ] **Step 3: 导出并应用唯一 API base**

在 `frontend/features/chatbot/api/client.ts` 的 `DEFAULT_PAGE_SIZE` 前加入：

```ts
export const CHATBOT_API_BASE = "/api/v1/chatbot";
```

把该文件七个 Conversation URL 改为：

```ts
`${CHATBOT_API_BASE}/conversations${buildQuery({ status, cursor, limit })}`
`${CHATBOT_API_BASE}/conversations/${conversationId}`
`${CHATBOT_API_BASE}/conversations`
`${CHATBOT_API_BASE}/conversations/${options.conversationId}`
`${CHATBOT_API_BASE}/conversations/${options.conversationId}/archive`
`${CHATBOT_API_BASE}/conversations/${options.conversationId}/restore`
`${CHATBOT_API_BASE}/conversations/${options.conversationId}`
```

同时把 stop URL 改为：

```ts
`${CHATBOT_API_BASE}/conversations/${options.conversationId}/stop`
```

在 `frontend/features/chatbot/api/stream.ts` 导入常量：

```ts
import { CHATBOT_API_BASE } from "./client";
```

将 Message GET 和 SSE fetch URL 分别改为：

```ts
`${CHATBOT_API_BASE}/conversations/${conversationId}/messages${buildQuery({ limit, before })}`
`${getBackendBaseUrl()}${CHATBOT_API_BASE}${path}`
```

- [ ] **Step 4: 运行路径测试和现有流测试**

Run:

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/api-client.test.ts features/chatbot/__tests__/chat-stream.test.ts
```

Expected: 两个测试文件全部 PASS。

- [ ] **Step 5: 提交 Task 1**

```powershell
git add frontend/features/chatbot/api/client.ts frontend/features/chatbot/api/stream.ts frontend/features/chatbot/__tests__/api-client.test.ts
git commit -m "fix(chatbot): align frontend API paths"
```

### Task 2: 将 SSE 序号隔离到当前 request 和 conversation

**Files:**
- Modify: `frontend/features/chatbot/utils/merge-stream-event.ts`
- Modify: `frontend/features/chatbot/hooks/use-messages.ts`
- Modify: `frontend/features/chatbot/__tests__/chat-stream.test.ts`

**Interfaces:**
- Produces: `createInitialChatStreamState(messages?: MessageData[], conversationId?: string | null)`。
- Produces: `ChatStreamState.conversationId: string | null`。
- Consumes: 每个已知 SSE payload 中的 `request_id`、`conversation_id` 和 HTTP 流内 `sequence`。

- [ ] **Step 1: 添加连续请求从 sequence 1 重启的失败测试**

在 `chat-stream.test.ts` 现有 describe 中增加辅助函数和测试：

```ts
function createdEvent(requestId: string, conversationId: string, suffix: string) {
  return {
    event: "message.created" as const,
    sequence: 1,
    data: {
      schema_version: "1" as const,
      request_id: requestId,
      conversation_id: conversationId,
      assistant_message_id: `assistant-${suffix}`,
      sequence: 1,
      created_at: "2026-07-14T00:00:00.000Z",
      replayed: false,
      user_message: {
        id: `user-${suffix}`,
        sequence_number: suffix === "1" ? 1 : 3,
        status: "completed" as const,
        content: `question-${suffix}`,
        model: null,
        updated_at: "2026-07-14T00:00:00.000Z",
      },
      assistant_message: {
        id: `assistant-${suffix}`,
        sequence_number: suffix === "1" ? 2 : 4,
        status: "pending" as const,
        content: "",
        model: "deepseek-chat",
        updated_at: "2026-07-14T00:00:00.000Z",
      },
    },
  };
}

it("resets sequence deduplication for a new request", () => {
  const initial = createInitialChatStreamState([], "conv-1");
  const firstCreated = mergeChatStreamEvent(initial, createdEvent("req-1", "conv-1", "1"));
  const firstEnd = mergeChatStreamEvent(firstCreated, {
    event: "stream.end",
    sequence: 5,
    data: {
      schema_version: "1",
      request_id: "req-1",
      conversation_id: "conv-1",
      assistant_message_id: "assistant-1",
      sequence: 5,
      created_at: "2026-07-14T00:00:01.000Z",
      final_status: "completed",
    },
  });

  const secondCreated = mergeChatStreamEvent(firstEnd, createdEvent("req-2", "conv-1", "2"));
  const secondDelta = mergeChatStreamEvent(secondCreated, {
    event: "message.delta",
    sequence: 2,
    data: {
      schema_version: "1",
      request_id: "req-2",
      conversation_id: "conv-1",
      assistant_message_id: "assistant-2",
      sequence: 2,
      created_at: "2026-07-14T00:00:02.000Z",
      delta: "second answer",
      content_length: 13,
    },
  });

  expect(secondCreated.lastSequence).toBe(1);
  expect(secondDelta.messages.find((item) => item.id === "assistant-2")?.content).toBe("second answer");
});
```

- [ ] **Step 2: 添加旧 conversation/request 迟到事件失败测试**

继续增加：

```ts
it("ignores events from another conversation or inactive request", () => {
  const current = mergeChatStreamEvent(
    createInitialChatStreamState([], "conv-b"),
    createdEvent("req-b", "conv-b", "2")
  );

  const staleConversation = mergeChatStreamEvent(current, {
    event: "message.delta",
    sequence: 9,
    data: {
      schema_version: "1",
      request_id: "req-a",
      conversation_id: "conv-a",
      assistant_message_id: "assistant-a",
      sequence: 9,
      created_at: "2026-07-14T00:00:03.000Z",
      delta: "stale",
      content_length: 5,
    },
  });
  const staleRequest = mergeChatStreamEvent(current, {
    event: "message.delta",
    sequence: 9,
    data: {
      schema_version: "1",
      request_id: "req-a",
      conversation_id: "conv-b",
      assistant_message_id: "assistant-a",
      sequence: 9,
      created_at: "2026-07-14T00:00:03.000Z",
      delta: "stale",
      content_length: 5,
    },
  });

  expect(staleConversation).toBe(current);
  expect(staleRequest).toBe(current);
});
```

- [ ] **Step 3: 运行测试，确认 sequence 和隔离断言失败**

Run:

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/chat-stream.test.ts
```

Expected: FAIL；第二个 `message.created` 的 `lastSequence` 仍为 5，且 state 尚无 `conversationId`。

- [ ] **Step 4: 实现 reducer 的三层事件边界**

给 `ChatStreamState` 增加：

```ts
conversationId: string | null;
```

将初始化函数改为：

```ts
export function createInitialChatStreamState(
  messages: MessageData[] = [],
  conversationId: string | null = null
): ChatStreamState {
  return {
    messages: sortMessages(messages),
    conversationId,
    activeRequestId: null,
    activeAssistantMessageId: null,
    lastSequence: 0,
    phase: "idle",
    error: null,
  };
}
```

在 `hasRequestId` 后增加：

```ts
function hasConversationId(data: unknown): data is { conversation_id: string } {
  return Boolean(
    data &&
      typeof data === "object" &&
      "conversation_id" in data &&
      typeof (data as { conversation_id?: unknown }).conversation_id === "string"
  );
}
```

用下面的 guard 替换 `mergeChatStreamEvent` 开头现有 sequence 判断：

```ts
const requestId = hasRequestId(event.data) ? event.data.request_id : null;
const eventConversationId = hasConversationId(event.data) ? event.data.conversation_id : null;

if (
  state.conversationId !== null &&
  eventConversationId !== null &&
  eventConversationId !== state.conversationId
) {
  return state;
}

if (event.event === "message.created") {
  const data = event.data as StreamMessageCreatedData;
  if (state.activeRequestId === data.request_id && event.sequence <= state.lastSequence) {
    return state;
  }
  const userMessage = createMessageFromSnapshot(data, data.request_id, "user");
  const assistantMessage = createMessageFromSnapshot(data, data.request_id, "assistant");
  return {
    ...state,
    messages: upsertMessage(upsertMessage(state.messages, userMessage), assistantMessage),
    conversationId: data.conversation_id,
    activeRequestId: data.request_id,
    activeAssistantMessageId: data.assistant_message_id,
    lastSequence: event.sequence,
    phase: assistantMessage.status === "completed" ? "completed" : "streaming",
    error: null,
  };
}

if (requestId === null || requestId !== state.activeRequestId) {
  return state;
}
if (event.sequence > 0 && event.sequence <= state.lastSequence) {
  return state;
}
```

删除函数后方旧的 `message.created` 分支，其他事件分支保持原有更新逻辑。

在 `use-messages.ts` 中把初始和 reset 创建改为携带会话 ID：

```ts
const [streamState, setStreamState] = useState<ChatStreamState>(() =>
  createInitialChatStreamState([], conversationId)
);

const resetConversationState = useCallback(() => {
  setStreamState(createInitialChatStreamState([], conversationId));
  setLoadingHistory(false);
  setHistoryError(null);
  setHasMore(false);
  setNextCursor(null);
  setDraft("");
  setStoppingMessageId(null);
  setControlError(null);
}, [conversationId]);
```

- [ ] **Step 5: 运行 reducer 测试**

Run:

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/chat-stream.test.ts
```

Expected: PASS，包括连续 request、重复事件和跨会话迟到事件。

- [ ] **Step 6: 提交 Task 2**

```powershell
git add frontend/features/chatbot/utils/merge-stream-event.ts frontend/features/chatbot/hooks/use-messages.ts frontend/features/chatbot/__tests__/chat-stream.test.ts
git commit -m "fix(chatbot): isolate SSE state per request"
```

### Task 3: 会话切换时 detach 旧 reader

**Files:**
- Create: `frontend/features/chatbot/__tests__/use-chat-stream.test.tsx`
- Modify: `frontend/features/chatbot/hooks/use-chat-stream.ts`

**Interfaces:**
- Consumes: `conversationId` 和 `token` 当前 render 值。
- Produces: `cancel()` 只 abort reader；不会触发 `onFailure` 或 stop API。
- Produces: 旧 controller 的 `finally` 不得把新请求的 `sending` 改为 false。

- [ ] **Step 1: 写会话切换后忽略旧流事件的失败测试**

创建 `use-chat-stream.test.tsx`：

```tsx
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const streamMocks = vi.hoisted(() => ({
  openChatStream: vi.fn(),
  openRetryStream: vi.fn(),
  openRegenerateStream: vi.fn(),
}));

vi.mock("../api/stream", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/stream")>();
  return { ...original, ...streamMocks };
});

import { useChatStream } from "../hooks/use-chat-stream";

function sseBlock(conversationId: string, requestId: string, sequence: number, delta: string) {
  return [
    `id: ${sequence}`,
    "event: message.delta",
    `data: ${JSON.stringify({
      schema_version: "1",
      request_id: requestId,
      conversation_id: conversationId,
      assistant_message_id: `assistant-${requestId}`,
      sequence,
      created_at: "2026-07-14T00:00:00.000Z",
      delta,
      content_length: delta.length,
    })}`,
    "",
    "",
  ].join("\n");
}

describe("useChatStream", () => {
  beforeEach(() => vi.clearAllMocks());

  it("detaches the old reader when conversation changes", async () => {
    let oldController: ReadableStreamDefaultController<Uint8Array>;
    const encoder = new TextEncoder();
    const response = new Response(
      new ReadableStream<Uint8Array>({ start(controller) { oldController = controller; } }),
      { headers: { "Content-Type": "text/event-stream" } }
    );
    streamMocks.openChatStream.mockResolvedValue(response);
    const onEvent = vi.fn();
    const onFailure = vi.fn();

    const { result, rerender } = renderHook(
      ({ conversationId }) =>
        useChatStream({ token: "token", conversationId, onEvent, onFailure }),
      { initialProps: { conversationId: "conv-a" } }
    );

    let pending: Promise<boolean>;
    act(() => {
      pending = result.current.sendMessage("hello", "req-a");
    });
    await waitFor(() => expect(streamMocks.openChatStream).toHaveBeenCalledTimes(1));

    rerender({ conversationId: "conv-b" });
    act(() => {
      oldController!.enqueue(encoder.encode(sseBlock("conv-a", "req-a", 2, "late")));
      oldController!.close();
    });
    await act(async () => { await pending!; });

    expect(onEvent).not.toHaveBeenCalled();
    expect(onFailure).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: 运行测试，确认旧事件仍调用 onEvent**

Run:

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/use-chat-stream.test.tsx
```

Expected: FAIL；旧 `conv-a` delta 仍传给 `onEvent`，或 abort 被当作 failure。

- [ ] **Step 3: 实现 reader 生命周期隔离**

在 `use-chat-stream.ts` 增加两个 helper：

```ts
function isAbortError(error: unknown) {
  return error instanceof DOMException
    ? error.name === "AbortError"
    : error instanceof Error && error.name === "AbortError";
}

function eventConversationId(event: ParsedChatStreamEvent) {
  if (
    event.data &&
    typeof event.data === "object" &&
    "conversation_id" in event.data &&
    typeof (event.data as { conversation_id?: unknown }).conversation_id === "string"
  ) {
    return (event.data as { conversation_id: string }).conversation_id;
  }
  return null;
}
```

在 hook 内增加 ref，并在每次 render 同步当前会话：

```ts
const activeConversationId = useRef<string | null>(conversationId);
activeConversationId.current = conversationId;
```

用下面的 effect 替换只在 unmount abort 的 effect：

```ts
useEffect(() => {
  abortController.current?.abort();
  abortController.current = null;
  activeRequestId.current = null;
  setSending(false);
  return () => {
    abortController.current?.abort();
  };
}, [conversationId, token]);
```

在 `runGeneration` 通过前置检查后捕获：

```ts
const startedConversationId = conversationId;
```

将事件循环开头改为：

```ts
for await (const event of readChatStreamEvents(response)) {
  if (
    controller.signal.aborted ||
    activeConversationId.current !== startedConversationId ||
    eventConversationId(event) !== startedConversationId
  ) {
    break;
  }
  onEvent?.(event);
  if (event.event === "message.created") {
    const createdEvent = event as {
      event: "message.created";
      data: StreamMessageCreatedData;
      sequence: number;
    };
    onCreated?.({
      event: "message.created",
      data: createdEvent.data,
      sequence: createdEvent.sequence,
    });
  }
  if (
    event.event === "stream.end" ||
    event.event === "message.failed" ||
    event.event === "message.cancelled"
  ) {
    onTerminal?.(event);
  }
}
```

将 catch 改为：

```ts
} catch (exception) {
  if (controller.signal.aborted || isAbortError(exception)) {
    return false;
  }
  const message =
    exception instanceof ApiError
      ? exception.message
      : exception instanceof Error
        ? exception.message
        : "Unable to send message.";
  setError(message);
  onFailure?.(message);
  return false;
```

将 finally 改为只清理当前 controller：

```ts
} finally {
  if (abortController.current === controller) {
    abortController.current = null;
    if (activeRequestId.current === clientRequestId) {
      activeRequestId.current = null;
    }
    setSending(false);
  }
}
```

- [ ] **Step 4: 运行 hook 和 reducer 测试**

Run:

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/use-chat-stream.test.tsx features/chatbot/__tests__/chat-stream.test.ts
```

Expected: PASS；会话切换不分发旧事件，不调用 `onFailure`。

- [ ] **Step 5: 提交 Task 3**

```powershell
git add frontend/features/chatbot/hooks/use-chat-stream.ts frontend/features/chatbot/__tests__/use-chat-stream.test.tsx
git commit -m "fix(chatbot): detach streams on conversation switch"
```

### Task 4: Phase A 回归门禁

**Files:**
- Verify only; no source changes expected.

**Interfaces:**
- Produces: 前端测试、lint 和生产构建均通过的阶段门禁。

- [ ] **Step 1: 运行 Chatbot 前端测试**

```powershell
Set-Location frontend
npm test -- features/chatbot
```

Expected: 所有 Chatbot Vitest tests PASS。

- [ ] **Step 2: 运行完整前端测试**

```powershell
Set-Location frontend
npm test
```

Expected: 全部 PASS，0 failed。

- [ ] **Step 3: 运行 lint**

```powershell
Set-Location frontend
npm run lint
```

Expected: 退出码 0，无 ESLint error。

- [ ] **Step 4: 运行生产构建**

```powershell
Set-Location frontend
npm run build
```

Expected: Next.js build 成功，`/chat-bot` 页面编译通过。

- [ ] **Step 5: 检查阶段 diff 并提交门禁修正（只有确有修正时）**

```powershell
Set-Location ..
git status --short
git diff --check
```

Expected: 没有空白错误；只包含本计划声明的前端文件。如门禁无需修正，不创建空 commit。
