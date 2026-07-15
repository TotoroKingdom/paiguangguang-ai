# Chatbot Frontend Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变路由、FastAPI 契约或现有业务语义的前提下，把 `/chat-bot` 重构为全高、双栏、固定阅读宽度的可靠聊天工作区，并补齐全部 `/api/v1/chatbot` 前端调用入口。

**Architecture:** 采用渐进式边界重构：保留 `ChatbotStoreProvider`、`useChatStream`、SSE parser 和 `mergeChatStreamEvent`，先通过 request version 修复 Conversation/detail/history 竞态，再拆分纯展示组件。`ChatbotShellContent`、`ChatConversationPanel` 和 `MemoryPanel` 分别是 Conversation、Message 和 Memory 的唯一数据控制器；子组件只接收 props，不自行请求。

**Tech Stack:** Next.js 14 App Router、React 18、TypeScript 5、Tailwind CSS 3、Framer Motion 12、react-markdown 9、remark-gfm 4、Vitest 2、Testing Library。

## Global Constraints

- 工作目录为仓库中的 `paiguangguang/` 项目目录；执行前使用 `superpowers:using-git-worktrees` 创建隔离 worktree。
- 不修改 `backend/**`、数据库迁移、FastAPI 路由、请求体、响应体或 SSE event schema。
- 不改变 `/chat-bot` 路由、`NEXT_PUBLIC_CHATBOT_ENABLED`、RouteGuard、AuthProvider 或登录流程。
- 不安装新依赖；只使用当前 `package.json` 已存在的依赖。
- 不复制 DeepSeek Logo、品牌名称、专属图标或文案。
- 不实现文件上传、模型切换、深度思考、联网、citations 或其他后端不存在的能力。
- Composer 只读显示当前 `conversation.model`。
- 保留用户级 `sessionStorage` key `paiguangguang.chatbot:{user_id}` 和 snapshot version 2。
- 保留 `Idempotency-Key`、Conversation/request/sequence 隔离、浏览器 reader detach 与显式 stop 的区别。
- 不把 Message、Conversation row 或 Memory row 的数据请求下沉到展示组件。
- 每个 Task 先运行失败测试，确认失败原因与目标缺口一致，再修改实现。
- 每个 Task 的 targeted tests 通过后运行 `git diff --check`，只提交该 Task 涉及文件。
- 设计依据：`docs/chatbot-frontend-refactor-design.md`。

---

## File Structure

### 保留为业务边界

- `frontend/features/chatbot/api/client.ts`：Conversation CRUD 与 Stop。
- `frontend/features/chatbot/api/stream.ts`：Message history、SSE 请求和 SSE parser。
- `frontend/features/chatbot/hooks/use-chat-stream.ts`：reader 生命周期；本计划不改变 detach 语义。
- `frontend/features/chatbot/utils/merge-stream-event.ts`：纯 stream reducer；除非既有回归测试失败，否则不修改。
- `frontend/features/chatbot/stores/chatbot-store.tsx`：Conversation cache 与用户级 hydration。

### 新增的聚焦组件

- `frontend/features/chatbot/components/chatbot-sidebar.tsx`：Desktop sidebar 与 Mobile drawer 外壳。
- `frontend/features/chatbot/components/chatbot-header.tsx`：Main header 与移动端 menu trigger。
- `frontend/features/chatbot/components/conversation-list.tsx`：Conversation list states。
- `frontend/features/chatbot/components/conversation-item.tsx`：单条 Conversation 与行内操作。
- `frontend/features/chatbot/components/markdown-content.tsx`：Markdown element map 与 SafeAnchor。
- `frontend/features/chatbot/components/code-block.tsx`：块级代码和复制反馈。
- `frontend/features/chatbot/components/memory-filters.tsx`：Memory status/type/scope。
- `frontend/features/chatbot/components/memory-list.tsx`：Memory list states。
- `frontend/features/chatbot/components/memory-detail-editor.tsx`：Memory detail form。

### 新增的测试文件

- `frontend/features/chatbot/__tests__/memory-api.test.ts`
- `frontend/features/chatbot/__tests__/stream-api.test.ts`
- `frontend/features/chatbot/__tests__/use-messages.test.tsx`
- `frontend/components/app-shell.test.tsx`
- `frontend/features/chatbot/__tests__/conversation-item.test.tsx`
- `frontend/features/chatbot/__tests__/markdown-content.test.tsx`
- `frontend/features/chatbot/__tests__/memory-detail-editor.test.tsx`

---

### Task 1: Complete and Lock the 16-Route Chatbot API Contract

**Files:**
- Modify: `frontend/features/chatbot/types/memory.ts`
- Modify: `frontend/features/chatbot/api/memories.ts`
- Modify: `frontend/features/chatbot/__tests__/api-client.test.ts`
- Create: `frontend/features/chatbot/__tests__/memory-api.test.ts`
- Create: `frontend/features/chatbot/__tests__/stream-api.test.ts`
- Modify: `frontend/features/chatbot/__tests__/use-memories.test.tsx`

**Interfaces:**
- Consumes: `CHATBOT_API_BASE`、`getJson`、`patchJson`、`deleteJson`。
- Produces:
  - `MemoryListStatus = "candidate" | "active" | "superseded"`
  - `MemoryRecordStatus = MemoryListStatus | "deleted" | "failed"`
  - `memoryApiClient.listMemories({ token, status, memoryType, conversationId, cursor, limit })`
  - `memoryApiClient.getMemory({ token, memoryId })`
  - Existing `updateMemory` and `deleteMemory` unchanged.
- Verifies all 16 FastAPI operations by HTTP method/path:
  - 8 Conversation operations in `api-client.test.ts`.
  - 4 Message/generation operations in `stream-api.test.ts`.
  - 4 Memory operations in `memory-api.test.ts`.

- [ ] **Step 1: Add the failing Memory path contract test**

Create `frontend/features/chatbot/__tests__/memory-api.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  getJson: vi.fn(),
  patchJson: vi.fn(),
  deleteJson: vi.fn(),
}));

vi.mock("@/lib/api", () => apiMocks);

import { memoryApiClient } from "../api/memories";

describe("memory API path contract", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getJson.mockResolvedValue({});
    apiMocks.patchJson.mockResolvedValue({});
    apiMocks.deleteJson.mockResolvedValue({});
  });

  it("covers list filters, detail, update, and delete", async () => {
    await memoryApiClient.listMemories({
      token: "token",
      status: "active",
      memoryType: "project_context",
      conversationId: "conv-1",
      cursor: "cursor-1",
      limit: 20,
    });
    await memoryApiClient.getMemory({ token: "token", memoryId: "memory-1" });
    await memoryApiClient.updateMemory(
      { token: "token", memoryId: "memory-1" },
      { content: "Updated", status: "active", expires_at: null }
    );
    await memoryApiClient.deleteMemory({ token: "token", memoryId: "memory-1" });

    expect(apiMocks.getJson).toHaveBeenNthCalledWith(
      1,
      "/api/v1/chatbot/memories?status=active&memory_type=project_context&conversation_id=conv-1&limit=20&cursor=cursor-1",
      { token: "token" }
    );
    expect(apiMocks.getJson).toHaveBeenNthCalledWith(
      2,
      "/api/v1/chatbot/memories/memory-1",
      { token: "token" }
    );
    expect(apiMocks.patchJson).toHaveBeenCalledWith(
      "/api/v1/chatbot/memories/memory-1",
      { content: "Updated", status: "active", expires_at: null },
      { token: "token" }
    );
    expect(apiMocks.deleteJson).toHaveBeenCalledWith(
      "/api/v1/chatbot/memories/memory-1",
      { token: "token" }
    );
  });
});
```

Extend `api-client.test.ts` to import `stopGeneration`, call:

```ts
await stopGeneration({
  token: "token",
  conversationId: "conv-1",
  request: { assistant_message_id: "message-1" },
});
```

Then assert the fourth POST call:

```ts
expect(apiMocks.postJson).toHaveBeenNthCalledWith(
  4,
  "/api/v1/chatbot/conversations/conv-1/stop",
  { assistant_message_id: "message-1" },
  { token: "token" }
);
```

Create `frontend/features/chatbot/__tests__/stream-api.test.ts`:

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({
  getBackendBaseUrl: vi.fn(() => "http://backend.test"),
  getJson: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, ...apiMocks };
});

import {
  listMessages,
  openChatStream,
  openRegenerateStream,
  openRetryStream,
} from "../api/stream";

describe("chatbot message API path contract", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getJson.mockResolvedValue({
      items: [],
      next_cursor: null,
      has_more: false,
    });
    fetchMock.mockResolvedValue(
      new Response(null, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("covers message history and all three streaming generation routes", async () => {
    await listMessages({
      token: "token",
      conversationId: "conv-1",
      limit: 50,
      before: "cursor-1",
    });
    await openChatStream({
      token: "token",
      conversationId: "conv-1",
      content: "Hello",
      clientRequestId: "request-send",
    });
    await openRetryStream({
      token: "token",
      conversationId: "conv-1",
      messageId: "message-1",
      clientRequestId: "request-retry",
    });
    await openRegenerateStream({
      token: "token",
      conversationId: "conv-1",
      messageId: "message-1",
      clientRequestId: "request-regenerate",
    });

    expect(apiMocks.getJson).toHaveBeenCalledWith(
      "/api/v1/chatbot/conversations/conv-1/messages?limit=50&before=cursor-1",
      { token: "token" }
    );
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "http://backend.test/api/v1/chatbot/conversations/conv-1/messages",
      "http://backend.test/api/v1/chatbot/conversations/conv-1/messages/message-1/retry",
      "http://backend.test/api/v1/chatbot/conversations/conv-1/messages/message-1/regenerate",
    ]);

    const sendInit = fetchMock.mock.calls[0][1] as RequestInit;
    expect(sendInit.method).toBe("POST");
    expect(JSON.parse(String(sendInit.body))).toEqual({
      content: "Hello",
      client_request_id: "request-send",
    });
    expect((sendInit.headers as Headers).get("Idempotency-Key")).toBe(
      "request-send"
    );
    expect((sendInit.headers as Headers).get("Authorization")).toBe(
      "Bearer token"
    );

    const retryInit = fetchMock.mock.calls[1][1] as RequestInit;
    expect(JSON.parse(String(retryInit.body))).toEqual({
      client_request_id: "request-retry",
    });
    expect((retryInit.headers as Headers).get("Idempotency-Key")).toBe(
      "request-retry"
    );

    const regenerateInit = fetchMock.mock.calls[2][1] as RequestInit;
    expect(JSON.parse(String(regenerateInit.body))).toEqual({
      client_request_id: "request-regenerate",
    });
    expect((regenerateInit.headers as Headers).get("Idempotency-Key")).toBe(
      "request-regenerate"
    );
  });
});
```

- [ ] **Step 2: Run the test and confirm the missing method/options failure**

Run from `frontend/`:

```powershell
npm test -- features/chatbot/__tests__/memory-api.test.ts
```

Expected: FAIL because `getMemory` does not exist and `listMemories` does not accept `memoryType` or `conversationId`. The existing Conversation/Message API functions are not changed by this failure.

- [ ] **Step 3: Align Memory read and list status types**

Replace the status declarations in `frontend/features/chatbot/types/memory.ts` with:

```ts
export type MemoryListStatus = "candidate" | "active" | "superseded";

export type MemoryRecordStatus = MemoryListStatus | "deleted" | "failed";

export type MemoryStatus = MemoryListStatus;
```

Change `MemoryData.status` to:

```ts
status: MemoryRecordStatus;
```

Keep `MemoryUpdateRequest.status` restricted to candidate/active:

```ts
status?: Extract<MemoryListStatus, "candidate" | "active">;
```

- [ ] **Step 4: Implement the complete Memory client**

Replace `frontend/features/chatbot/api/memories.ts` with:

```ts
import { deleteJson, getJson, patchJson } from "@/lib/api";

import { CHATBOT_API_BASE } from "./client";
import type { DeleteResultData } from "../types/conversation";
import type {
  MemoryData,
  MemoryListStatus,
  MemoryPageData,
  MemoryType,
  MemoryUpdateRequest,
} from "../types/memory";

export const memoryApiClient = {
  listMemories(options: {
    token: string | null;
    status: MemoryListStatus;
    memoryType?: MemoryType | null;
    conversationId?: string | null;
    cursor: string | null;
    limit: number;
  }) {
    const query = new URLSearchParams({ status: options.status });
    if (options.memoryType) {
      query.set("memory_type", options.memoryType);
    }
    if (options.conversationId) {
      query.set("conversation_id", options.conversationId);
    }
    query.set("limit", String(options.limit));
    if (options.cursor) {
      query.set("cursor", options.cursor);
    }
    return getJson<MemoryPageData>(
      `${CHATBOT_API_BASE}/memories?${query}`,
      { token: options.token }
    );
  },
  getMemory(options: { token: string | null; memoryId: string }) {
    return getJson<MemoryData>(
      `${CHATBOT_API_BASE}/memories/${options.memoryId}`,
      { token: options.token }
    );
  },
  updateMemory(
    options: { token: string | null; memoryId: string },
    request: MemoryUpdateRequest
  ) {
    return patchJson<MemoryData, MemoryUpdateRequest>(
      `${CHATBOT_API_BASE}/memories/${options.memoryId}`,
      request,
      { token: options.token }
    );
  },
  deleteMemory(options: { token: string | null; memoryId: string }) {
    return deleteJson<DeleteResultData>(
      `${CHATBOT_API_BASE}/memories/${options.memoryId}`,
      { token: options.token }
    );
  },
};

export type MemoryApiClient = typeof memoryApiClient;
```

- [ ] **Step 5: Extend the existing Memory hook mock to satisfy the client**

In the client object inside `use-memories.test.tsx` add:

```ts
getMemory: vi.fn().mockResolvedValue(makeMemory("memory-1")),
```

- [ ] **Step 6: Run targeted tests and TypeScript**

Run from `frontend/`:

```powershell
npm test -- features/chatbot/__tests__/api-client.test.ts features/chatbot/__tests__/stream-api.test.ts features/chatbot/__tests__/memory-api.test.ts features/chatbot/__tests__/use-memories.test.tsx
npx tsc --noEmit --incremental false
```

Expected: all four test files PASS, covering all 16 chatbot HTTP method/path contracts, and TypeScript exits 0.

- [ ] **Step 7: Commit the Memory client contract**

```powershell
git add frontend/features/chatbot/types/memory.ts frontend/features/chatbot/api/memories.ts frontend/features/chatbot/__tests__/api-client.test.ts frontend/features/chatbot/__tests__/stream-api.test.ts frontend/features/chatbot/__tests__/memory-api.test.ts frontend/features/chatbot/__tests__/use-memories.test.tsx
git diff --cached --check
git commit -m "feat(chatbot): complete api contract"
```

---

### Task 2: Isolate Conversation Detail Requests

**Files:**
- Modify: `frontend/features/chatbot/hooks/use-conversations.ts`
- Modify: `frontend/features/chatbot/__tests__/use-conversations.test.tsx`

**Interfaces:**
- Consumes: existing `useConversations` API and `client.getConversation`.
- Produces: the same public hook API; only the newest detail request may update `selectedConversationDetail`, store, loading/error, or URL.

- [ ] **Step 1: Add a deferred-promise race regression test**

Add this helper near the top of `use-conversations.test.tsx`:

```ts
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, resolve, reject };
}
```

Add this test:

```tsx
it("ignores a stale conversation detail response after a newer selection", async () => {
  const first = deferred<ConversationDetailData>();
  const second = deferred<ConversationDetailData>();
  const client = makeClient({
    listConversations: vi.fn().mockResolvedValue({
      items: [],
      next_cursor: null,
      has_more: false,
    }),
    getConversation: vi
      .fn()
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise),
  });
  const { result } = renderConversationsHook(client);

  await waitFor(() => expect(client.listConversations).toHaveBeenCalledTimes(1));

  let firstSelection!: Promise<ConversationDetailData | null>;
  let secondSelection!: Promise<ConversationDetailData | null>;
  act(() => {
    firstSelection = result.current.openConversation("conv-a");
    secondSelection = result.current.openConversation("conv-b");
  });

  await act(async () => {
    second.resolve(makeDetail("conv-b", { title: "Newest" }));
    await secondSelection;
  });
  await act(async () => {
    first.resolve(makeDetail("conv-a", { title: "Stale" }));
    await firstSelection;
  });

  expect(result.current.selectedConversationId).toBe("conv-b");
  expect(result.current.selectedConversation?.title).toBe("Newest");
  expect(push).toHaveBeenLastCalledWith("/chat-bot?conversation=conv-b");
});
```

- [ ] **Step 2: Run the test and confirm stale A overwrites B**

Run from `frontend/`:

```powershell
npm test -- features/chatbot/__tests__/use-conversations.test.tsx
```

Expected: FAIL with selected Conversation or last pushed URL equal to `conv-a`.

- [ ] **Step 3: Add request-version ownership to the hook**

Inside `useConversations`, add:

```ts
const detailRequestVersionRef = useRef(0);

const invalidateDetailRequests = useCallback(() => {
  detailRequestVersionRef.current += 1;
  setDetailLoading(false);
}, []);

useEffect(() => {
  detailRequestVersionRef.current += 1;
  setDetailLoading(false);
  setDetailError(null);
}, [token]);

useEffect(() => {
  return () => {
    detailRequestVersionRef.current += 1;
  };
}, []);
```

At the start of `openConversation`, after the token guard, capture a version:

```ts
const requestVersion = detailRequestVersionRef.current + 1;
detailRequestVersionRef.current = requestVersion;
const ownsRequest = () => detailRequestVersionRef.current === requestVersion;
```

Replace the current `try/catch/finally` body of `openConversation` with:

```ts
setDetailLoading(true);
setDetailError(null);
try {
  const detail = await client.getConversation({ token, conversationId });
  if (!ownsRequest()) {
    return null;
  }
  const summary = conversationDetailToSummary(detail);
  dispatch({ type: "upsert_conversation", conversation: summary });
  dispatch({ type: "set_selected_status", status: summary.status });
  dispatch({ type: "set_selected_conversation_id", conversationId: summary.id });
  setSelectedConversationDetail(detail);
  if (options.syncUrl !== false) {
    pushUrl(summary.id);
  }
  return detail;
} catch (error) {
  if (!ownsRequest()) {
    return null;
  }
  if (error instanceof ApiError && error.status === 404) {
    dispatch({ type: "set_selected_conversation_id", conversationId: null });
    dispatch({ type: "set_selected_status", status: "active" });
    setSelectedConversationDetail(null);
    clearUrl();
    return null;
  }
  setDetailError(normalizeErrorMessage(error));
  return null;
} finally {
  if (ownsRequest()) {
    setDetailLoading(false);
  }
}
```

Add `client` to `openConversation` dependencies. At the start of `createConversation`、`renameConversation`、`archiveConversation`、`restoreConversation` and `deleteConversation` call:

```ts
invalidateDetailRequests();
```

Add `invalidateDetailRequests` to those callback dependency arrays.

Replace the inline `clearSelection` returned by the hook with a callback:

```ts
const clearSelection = useCallback(() => {
  invalidateDetailRequests();
  allowAutoSelectRef.current = false;
  dispatch({ type: "set_selected_conversation_id", conversationId: null });
  setSelectedConversationDetail(null);
  setDetailError(null);
  clearUrl();
}, [clearUrl, dispatch, invalidateDetailRequests]);
```

Return `clearSelection` by reference. This prevents a stale detail request from restoring a Conversation after the user intentionally clears the selection and prevents its loading flag from remaining stuck.

- [ ] **Step 4: Run the Conversation hook test suite**

```powershell
npm test -- features/chatbot/__tests__/use-conversations.test.tsx
npx tsc --noEmit --incremental false
```

Expected: all existing and new Conversation hook tests PASS; TypeScript exits 0.

- [ ] **Step 5: Commit request isolation**

```powershell
git add frontend/features/chatbot/hooks/use-conversations.ts frontend/features/chatbot/__tests__/use-conversations.test.tsx
git diff --cached --check
git commit -m "fix(chatbot): isolate conversation detail requests"
```

---

### Task 3: Isolate Message History Requests

**Files:**
- Modify: `frontend/features/chatbot/hooks/use-messages.ts`
- Create: `frontend/features/chatbot/__tests__/use-messages.test.tsx`

**Interfaces:**
- Consumes: `listMessages`, `useChatStream`, selected `conversationId`.
- Produces: unchanged `useMessages` return shape; only a history request owned by the current Conversation may update messages, cursor, loading, or error.

- [ ] **Step 1: Add the failing cross-conversation history test**

Create `frontend/features/chatbot/__tests__/use-messages.test.tsx`:

```tsx
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { MessageData, MessagePageData } from "../types/message";

const mocks = vi.hoisted(() => ({
  listMessages: vi.fn(),
  stopGeneration: vi.fn(),
}));

vi.mock("../api/stream", () => ({
  listMessages: mocks.listMessages,
}));

vi.mock("../api/client", () => ({
  stopGeneration: mocks.stopGeneration,
}));

vi.mock("../hooks/use-chat-stream", () => ({
  useChatStream: () => ({
    sending: false,
    error: null,
    sendMessage: vi.fn(),
    retryMessage: vi.fn(),
    regenerateMessage: vi.fn(),
  }),
}));

import { useMessages } from "../hooks/use-messages";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

function message(conversationId: string): MessageData {
  return {
    id: `message-${conversationId}`,
    conversation_id: conversationId,
    role: "assistant",
    content: `history-${conversationId}`,
    content_json: null,
    sequence_number: 1,
    status: "completed",
    model: "deepseek-chat",
    parent_message_id: null,
    client_request_id: null,
    prompt_tokens: 0,
    completion_tokens: 0,
    total_tokens: 0,
    error_code: null,
    created_at: "2026-07-14T00:00:00.000Z",
    updated_at: "2026-07-14T00:00:00.000Z",
  };
}

describe("useMessages history isolation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("ignores history that resolves after the selected conversation changes", async () => {
    const first = deferred<MessagePageData>();
    const second = deferred<MessagePageData>();
    mocks.listMessages
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise);

    const { result, rerender } = renderHook(
      ({ conversationId }) =>
        useMessages({
          token: "token",
          conversationId,
          conversationStatus: "active",
        }),
      { initialProps: { conversationId: "conv-a" as string | null } }
    );

    await waitFor(() => expect(mocks.listMessages).toHaveBeenCalledTimes(1));
    rerender({ conversationId: "conv-b" });
    await waitFor(() => expect(mocks.listMessages).toHaveBeenCalledTimes(2));

    await act(async () => {
      second.resolve({
        items: [message("conv-b")],
        next_cursor: null,
        has_more: false,
      });
      await Promise.resolve();
    });
    await act(async () => {
      first.resolve({
        items: [message("conv-a")],
        next_cursor: null,
        has_more: false,
      });
      await Promise.resolve();
    });

    expect(result.current.messages.map((item) => item.conversation_id)).toEqual([
      "conv-b",
    ]);
  });
});
```

- [ ] **Step 2: Run the test and confirm old history wins**

```powershell
npm test -- features/chatbot/__tests__/use-messages.test.tsx
```

Expected: FAIL because the late `conv-a` page replaces the `conv-b` messages.

- [ ] **Step 3: Add request ownership to history loading**

In `use-messages.ts` add:

```ts
const historyRequestVersionRef = useRef(0);
```

At the beginning of `resetConversationState` invalidate existing history:

```ts
historyRequestVersionRef.current += 1;
```

Replace the body of `loadHistory` after its token/conversation guard with:

```ts
const targetConversationId = conversationId;
const requestVersion = historyRequestVersionRef.current + 1;
historyRequestVersionRef.current = requestVersion;
const ownsRequest = () =>
  historyRequestVersionRef.current === requestVersion &&
  activeConversationRef.current === targetConversationId;

setLoadingHistory(true);
setHistoryError(null);
try {
  const page = await listMessages({
    token,
    conversationId: targetConversationId,
    limit: pageSize,
    before,
  });
  if (!ownsRequest()) {
    return null;
  }
  setHasMore(page.has_more);
  setNextCursor(page.next_cursor);
  setStreamState((current) => ({
    ...current,
    messages: append
      ? mergeMessageHistory(current.messages, page.items)
      : mergeMessageHistory([], page.items),
  }));
  return page;
} catch (error) {
  if (!ownsRequest()) {
    return null;
  }
  setHistoryError(normalizeError(error));
  return null;
} finally {
  if (ownsRequest()) {
    setLoadingHistory(false);
  }
}
```

Keep `activeConversationRef.current = conversationId` before `resetConversationState()` in the Conversation-change effect.

- [ ] **Step 4: Run history, stream, and type tests**

```powershell
npm test -- features/chatbot/__tests__/use-messages.test.tsx features/chatbot/__tests__/chat-stream.test.ts features/chatbot/__tests__/use-chat-stream.test.tsx
npx tsc --noEmit --incremental false
```

Expected: all selected tests PASS and TypeScript exits 0.

- [ ] **Step 5: Commit history isolation**

```powershell
git add frontend/features/chatbot/hooks/use-messages.ts frontend/features/chatbot/__tests__/use-messages.test.tsx
git diff --cached --check
git commit -m "fix(chatbot): isolate message history requests"
```

---

### Task 4: Create the Route-Aware Full-Height Host

**Files:**
- Modify: `frontend/components/app-shell.tsx`
- Create: `frontend/components/app-shell.test.tsx`
- Modify: `frontend/app/chat-bot/page.tsx`
- Modify: `frontend/app/chat-bot/page.test.tsx`
- Modify: `frontend/features/chatbot/stores/chatbot-store.tsx`
- Modify: `frontend/features/chatbot/__tests__/chatbot-store.test.tsx`

**Interfaces:**
- Consumes: `usePathname`、`SiteNav`、`ChatbotStoreProvider`.
- Produces:
  - `AppShell` emits a dedicated `main` for `/chat-bot`.
  - `ChatbotStoreProvider({ children, storageKey, fallback })`.
  - `ChatBotPage` renders `ChatbotShell` without a width wrapper.

- [ ] **Step 1: Add the failing AppShell route test**

Create `frontend/components/app-shell.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

let pathname = "/chat-bot";

vi.mock("next/navigation", () => ({
  usePathname: () => pathname,
}));

vi.mock("@/components/site-nav", () => ({
  SiteNav: () => <nav data-testid="site-nav">Global navigation</nav>,
}));

import { AppShell } from "./app-shell";

describe("AppShell route layout", () => {
  beforeEach(() => {
    pathname = "/chat-bot";
  });

  it("gives Chatbot a full-height main without the global navigation", () => {
    render(
      <AppShell>
        <div>Chatbot</div>
      </AppShell>
    );

    expect(screen.queryByTestId("site-nav")).not.toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveClass("h-dvh", "overflow-hidden");
  });

  it("keeps the existing shell for other application routes", () => {
    pathname = "/agents/knowledge";
    render(
      <AppShell>
        <div>Knowledge</div>
      </AppShell>
    );

    expect(screen.getByTestId("site-nav")).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveClass("px-4", "sm:px-6", "lg:px-8");
  });
});
```

- [ ] **Step 2: Add the failing store hydration fallback test**

Append to `chatbot-store.test.tsx` and import `renderToString` from `react-dom/server`:

```tsx
it("renders a stable fallback before a stored snapshot hydrates", () => {
  const html = renderToString(
    <ChatbotStoreProvider
      storageKey="paiguangguang.chatbot:user-123"
      fallback={<div>Hydrating Chatbot</div>}
    >
      <div>workspace</div>
    </ChatbotStoreProvider>
  );

  expect(html).toContain("Hydrating Chatbot");
  expect(html).not.toContain("workspace");
});
```

- [ ] **Step 3: Run the host tests and confirm both APIs are missing**

Run from `frontend/`:

```powershell
npm test -- components/app-shell.test.tsx features/chatbot/__tests__/chatbot-store.test.tsx app/chat-bot/page.test.tsx
```

Expected: FAIL because AppShell still renders SiteNav/padding and `fallback` is not a Provider prop.

- [ ] **Step 4: Implement the Chatbot AppShell branch**

Replace `AppShell`'s return logic with:

```tsx
const isHome = pathname === "/";
const isChatbot = pathname === "/chat-bot";

if (isChatbot) {
  return (
    <main className="h-dvh w-full overflow-hidden">
      {children}
    </main>
  );
}

return (
  <>
    {!isHome ? <SiteNav /> : null}
    <main
      className={
        isHome
          ? "w-full p-0"
          : "w-full px-4 py-6 sm:px-6 md:py-8 lg:px-8"
      }
    >
      {children}
    </main>
  </>
);
```

Do not edit `SiteNav`.

- [ ] **Step 5: Remove the Chatbot page width wrapper**

Keep the feature flag branch in `page.tsx` and replace its return with:

```tsx
return <ChatbotShell />;
```

Update `page.test.tsx` so it still asserts `chatbot-shell` renders and `notFound` is called when disabled; do not add a new route.

- [ ] **Step 6: Add a fallback prop to the store Provider**

Extend both provider prop types:

```tsx
export function ChatbotStoreProvider({
  children,
  storageKey,
  fallback = null,
}: {
  children: ReactNode;
  storageKey?: string | null;
  fallback?: ReactNode;
}) {
  const normalizedStorageKey = storageKey?.trim() || null;
  const previousStorageKey = useRef(normalizedStorageKey);

  useEffect(() => {
    const previous = previousStorageKey.current;
    if (previous && !normalizedStorageKey && typeof window !== "undefined") {
      window.sessionStorage.removeItem(previous);
    }
    previousStorageKey.current = normalizedStorageKey;
  }, [normalizedStorageKey]);

  return (
    <ScopedChatbotStoreProvider
      key={normalizedStorageKey ?? "logged-out"}
      storageKey={normalizedStorageKey}
      fallback={fallback}
    >
      {children}
    </ScopedChatbotStoreProvider>
  );
}
```

Add `fallback: ReactNode` to `ScopedChatbotStoreProvider` and replace `return null` with:

```tsx
if (!isHydrated) {
  return <>{fallback}</>;
}
```

- [ ] **Step 7: Run route, store, and type checks**

```powershell
npm test -- components/app-shell.test.tsx features/chatbot/__tests__/chatbot-store.test.tsx app/chat-bot/page.test.tsx
npx tsc --noEmit --incremental false
```

Expected: all selected tests PASS and TypeScript exits 0.

- [ ] **Step 8: Commit the route host**

```powershell
git add frontend/components/app-shell.tsx frontend/components/app-shell.test.tsx frontend/app/chat-bot/page.tsx frontend/app/chat-bot/page.test.tsx frontend/features/chatbot/stores/chatbot-store.tsx frontend/features/chatbot/__tests__/chatbot-store.test.tsx
git diff --cached --check
git commit -m "feat(chatbot): add full-height route host"
```

---

### Task 5: Build the Responsive Chatbot Shell and Sidebar

**Files:**
- Create: `frontend/features/chatbot/components/chatbot-sidebar.tsx`
- Create: `frontend/features/chatbot/components/chatbot-header.tsx`
- Modify: `frontend/features/chatbot/components/chatbot-shell.tsx`
- Modify: `frontend/features/chatbot/components/chat-conversation-panel.tsx`
- Modify: `frontend/features/chatbot/__tests__/chatbot-workspace.test.tsx`

**Interfaces:**
- Consumes: `useAuth`, `useConversations`, existing `ConversationSidebar`, `ChatConversationPanel`, `MemoryPanel`.
- Produces:
  - `WorkspaceView = "chat" | "memories"`
  - `ChatbotSidebar({ open, collapsed, activeView, onClose, onToggleCollapsed, onChangeView, onLogout, children })`
  - `ChatbotHeader({ title, status, onOpenSidebar })`
  - `ChatbotShellContent` remains the single `useConversations` caller.

- [ ] **Step 1: Extend the workspace test with shell-state assertions**

Add assertions to the existing authenticated-workspace test:

```tsx
expect(screen.getByTestId("responsive-sidebar")).toHaveTextContent("chat");
expect(screen.getByTestId("sidebar")).toBeInTheDocument();
expect(screen.getByTestId("panel")).toBeInTheDocument();
expect(screen.getByRole("main")).toHaveClass("min-h-0", "min-w-0");
```

Add these hoisted counters and component mocks before the tests:

```tsx
const shellMocks = vi.hoisted(() => ({
  useConversations: vi.fn(),
}));

vi.mock("../components/chatbot-sidebar", () => ({
  ChatbotSidebar: ({
    activeView,
    onChangeView,
    children,
  }: {
    activeView: "chat" | "memories";
    onChangeView: (view: "chat" | "memories") => void;
    children: React.ReactNode;
  }) => (
    <aside data-testid="responsive-sidebar">
      <span>{activeView}</span>
      <button type="button" onClick={() => onChangeView("memories")}>
        Open memories
      </button>
      {children}
    </aside>
  ),
}));

vi.mock("../components/memory-panel", () => ({
  MemoryPanel: () => <section data-testid="memory-panel">Memory panel</section>,
}));
```

Make the existing `useConversations` module mock call `shellMocks.useConversations()` and return the existing controller fixture. In `beforeEach` clear the mock and set its return value. Add:

```tsx
it("switches workspace views with one conversation hook call per render", () => {
  render(<ChatbotShell />);

  expect(screen.getByTestId("panel")).toBeInTheDocument();
  expect(shellMocks.useConversations).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "Open memories" }));

  expect(screen.getByTestId("memory-panel")).toBeInTheDocument();
  expect(screen.queryByTestId("panel")).not.toBeInTheDocument();
  expect(shellMocks.useConversations).toHaveBeenCalledTimes(2);
});
```

Add `fireEvent` to the Testing Library import.

Add `logout: vi.fn()` to the `useAuth` mock return so the shell receives a callable logout handler.

- [ ] **Step 2: Run the workspace test and confirm the new shell is absent**

```powershell
npm test -- features/chatbot/__tests__/chatbot-workspace.test.tsx
```

Expected: FAIL because `ChatbotSidebar` and the full-height `main` are not present.

- [ ] **Step 3: Create the responsive Sidebar shell**

Create `chatbot-sidebar.tsx` with this public interface and structure:

```tsx
"use client";

import type {ReactNode} from "react";
import Link from "next/link";
import {AnimatePresence, motion, useReducedMotion} from "framer-motion";

export type WorkspaceView = "chat" | "memories";

type ChatbotSidebarProps = {
    open: boolean;
    collapsed: boolean;
    activeView: WorkspaceView;
    onClose: () => void;
    onToggleCollapsed: () => void;
    onChangeView: (view: WorkspaceView) => void;
    onLogout: () => void;
    children: ReactNode;
};

function SidebarContents({
                             collapsed,
                             activeView,
                             onToggleCollapsed,
                             onChangeView,
                             onLogout,
                             children,
                         }: Omit<ChatbotSidebarProps, "open" | "onClose">) {
    return (
        <div className="flex h-full min-h-0 flex-col bg-[var(--chat-sidebar)] text-[var(--chat-text)]">
            <div className="flex h-14 items-center justify-between border-b border-[var(--chat-border)] px-3">
                <Link href="/" aria-label="Back to home"
                      className="rounded-lg px-2 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--chat-accent)]">
                    {collapsed ? "←" : "AI Chat"}
                </Link>
                <button type="button" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
                        onClick={onToggleCollapsed}>
                    {collapsed ? "›" : "‹"}
                </button>
            </div>
            {!collapsed ? <div className="min-h-0 flex-1">{children}</div> : <div className="flex-1"/>}
            <nav className="space-y-1 border-t border-[var(--chat-border)] p-2" aria-label="Chatbot workspace">
                {(["chat", "memories"] as WorkspaceView[]).map((view) => (
                    <button
                        key={view}
                        type="button"
                        aria-pressed={activeView === view}
                        onClick={() => onChangeView(view)}
                        className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-[var(--chat-subtle)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--chat-accent)]"
                    >
                        {collapsed ? view.slice(0, 1).toUpperCase() : view === "chat" ? "Conversations" : "Memories"}
                    </button>
                ))}
                <button type="button" onClick={onLogout}
                        className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-[var(--chat-subtle)]">
                    {collapsed ? "×" : "Sign out"}
                </button>
            </nav>
        </div>
    );
}

export function ChatbotSidebar(props: ChatbotSidebarProps) {
    const reduceMotion = useReducedMotion();
    const duration = reduceMotion ? 0 : 0.18;

    return (
        <>
            <motion.aside
                className="hidden h-full shrink-0 overflow-hidden border-r border-[var(--chat-border)] lg:block"
                animate={{width: props.collapsed ? 64 : 280}}
                transition={{duration}}
            >
                <SidebarContents
                    collapsed={props.collapsed}
                    activeView={props.activeView}
                    onToggleCollapsed={props.onToggleCollapsed}
                    onChangeView={props.onChangeView}
                    onLogout={props.onLogout}
                >
                    {props.children}
                </SidebarContents>
            </motion.aside>
            <AnimatePresence>
                {props.open ? (
                    <>
                        <motion.button
                            type="button"
                            aria-label="Close sidebar"
                            className="fixed inset-0 z-40 bg-black/35 lg:hidden"
                            initial={{opacity: 0}}
                            animate={{opacity: 1}}
                            exit={{opacity: 0}}
                            transition={{duration}}
                            onClick={props.onClose}
                        />
                        <motion.aside
                            className="fixed inset-y-0 left-0 z-50 w-[min(86vw,320px)] border-r border-[var(--chat-border)] shadow-2xl md:w-72 lg:hidden"
                            initial={{x: "-100%"}}
                            animate={{x: 0}}
                            exit={{x: "-100%"}}
                            transition={{duration}}
                        >
                            <SidebarContents
                                collapsed={false}
                                activeView={props.activeView}
                                onToggleCollapsed={props.onToggleCollapsed}
                                onChangeView={(view) => {
                                    props.onChangeView(view);
                                    props.onClose();
                                }}
                                onLogout={props.onLogout}
                            >
                                {props.children}
                            </SidebarContents>
                        </motion.aside>
                    </>
                ) : null}
            </AnimatePresence>
        </>
    );
}
```

The explicit props above deliberately keep `open` and `onClose` out of `SidebarContents`.

- [ ] **Step 4: Create the Main header**

Create `chatbot-header.tsx`:

```tsx
"use client";

import type { ConversationStatus } from "../types/conversation";

type ChatbotHeaderProps = {
  title: string;
  status: ConversationStatus | null;
  onOpenSidebar: () => void;
};

export function ChatbotHeader({ title, status, onOpenSidebar }: ChatbotHeaderProps) {
  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-[var(--chat-border)] px-4 md:px-6 lg:px-8">
      <button
        type="button"
        aria-label="Open conversations"
        onClick={onOpenSidebar}
        className="rounded-lg px-2 py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--chat-accent)] lg:hidden"
      >
        ☰
      </button>
      <h1 className="min-w-0 truncate text-base font-semibold text-[var(--chat-text)]">
        {title}
      </h1>
      {status === "archived" ? (
        <span className="ml-auto rounded-full bg-[var(--chat-subtle)] px-2.5 py-1 text-xs text-[var(--chat-muted)]">
          Archived
        </span>
      ) : null}
    </header>
  );
}
```

- [ ] **Step 5: Recompose ChatbotShell without adding a second data hook**

In `chatbot-shell.tsx`:

- Keep one `useConversations` call inside `ChatbotShellContent`.
- Add `view`、`sidebarOpen`、`sidebarCollapsed` local state.
- Read `logout` from `useAuth` in the same content component that renders Sidebar.
- Close the mobile drawer after selecting a Conversation.
- Render `<MemoryPanel token={token} />` only when view is memories. Task 11 adds the current-Conversation scope prop after the Memory controller supports it.
- Render a `main` with `min-h-0 min-w-0 flex-1`.
- Pass `detailLoading`、`detailError`、a retry callback, and `onOpenSidebar` into `ChatConversationPanel`:

```tsx
<ChatConversationPanel
  token={token}
  conversation={conversations.selectedConversation}
  activeGeneration={
    conversations.selectedConversationDetail?.active_generation ?? null
  }
  detailLoading={conversations.detailLoading}
  detailError={conversations.detailError}
  onRetryDetail={() => void conversations.refreshCurrentStatus()}
  onOpenSidebar={() => setSidebarOpen(true)}
/>
```
- Supply `ChatbotWorkspaceSkeleton` as the store `fallback`.

Define the hydration fallback in `chatbot-shell.tsx`:

```tsx
function ChatbotWorkspaceSkeleton() {
  return (
    <div
      aria-label="Loading chatbot workspace"
      className="chatbot-theme flex h-full bg-[var(--chat-page)]"
    >
      <div className="hidden w-[280px] border-r border-[var(--chat-border)] bg-[var(--chat-sidebar)] lg:block" />
      <div className="min-w-0 flex-1 p-6">
        <div className="mx-auto h-8 w-full max-w-3xl animate-pulse rounded-lg bg-[var(--chat-subtle)]" />
      </div>
    </div>
  );
}
```

Pass it as `fallback={<ChatbotWorkspaceSkeleton />}` on `ChatbotStoreProvider`.

Use this outer skeleton:

```tsx
<div className="chatbot-theme flex h-full min-h-0 overflow-hidden bg-[var(--chat-page)]">
  <ChatbotSidebar>{conversationSidebar}</ChatbotSidebar>
  <main className="flex min-h-0 min-w-0 flex-1 flex-col">
    {view === "memories" ? memoryWorkspace : chatWorkspace}
  </main>
</div>
```

Add an Escape key effect that only sets `sidebarOpen` to false; it must not change Conversation or view.

- [ ] **Step 6: Replace the old header card with ChatbotHeader**

Extend `ChatConversationPanelProps` with:

```ts
detailLoading?: boolean;
detailError?: string | null;
onRetryDetail?: () => void | Promise<void>;
onOpenSidebar: () => void;
```

Render `ChatbotHeader` before no-selection/loading/error/selected states. Keep `useMessages` invoked once per rendered panel and do not move it into `MessageList`.

- [ ] **Step 7: Run workspace and type tests**

```powershell
npm test -- features/chatbot/__tests__/chatbot-workspace.test.tsx features/chatbot/__tests__/conversation-sidebar.test.tsx
npx tsc --noEmit --incremental false
```

Expected: selected tests PASS, the mocked `useConversations` is called once per shell render, and TypeScript exits 0.

- [ ] **Step 8: Commit the responsive shell**

```powershell
git add frontend/features/chatbot/components/chatbot-sidebar.tsx frontend/features/chatbot/components/chatbot-header.tsx frontend/features/chatbot/components/chatbot-shell.tsx frontend/features/chatbot/components/chat-conversation-panel.tsx frontend/features/chatbot/__tests__/chatbot-workspace.test.tsx
git diff --cached --check
git commit -m "feat(chatbot): build responsive chat shell"
```

---

### Task 6: Split Conversation List and Row Actions

**Files:**
- Modify: `frontend/features/chatbot/hooks/use-conversations.ts`
- Modify: `frontend/features/chatbot/components/conversation-sidebar.tsx`
- Create: `frontend/features/chatbot/components/conversation-list.tsx`
- Create: `frontend/features/chatbot/components/conversation-item.tsx`
- Modify: `frontend/features/chatbot/__tests__/use-conversations.test.tsx`
- Modify: `frontend/features/chatbot/__tests__/conversation-sidebar.test.tsx`
- Create: `frontend/features/chatbot/__tests__/conversation-item.test.tsx`

**Interfaces:**
- Consumes: Conversation CRUD callbacks from `useConversations`.
- Produces:
  - `renameConversation(conversation, nextTitle)` with no `window.prompt`.
  - `deleteConversation(conversation)` with no `window.confirm`.
  - `ConversationItem` callbacks return `Promise<boolean>`.
  - `ConversationList` is pure and performs no data fetching.

- [ ] **Step 1: Change hook tests to reject browser dialogs**

Remove the `window.confirm` spy from the existing delete test and keep the direct call:

```tsx
await act(async () => {
  await result.current.deleteConversation(makeConversation("conv-1"));
});
```

Add assertions:

```tsx
expect(window.confirm).not.toHaveBeenCalled();
expect(window.prompt).not.toHaveBeenCalled();
```

Stub both methods with `vi.spyOn` before the assertion so calls can be observed, and restore both spies after the test.

- [ ] **Step 2: Add the ConversationItem interaction test**

Create `conversation-item.test.tsx` with a representative active Conversation and tests for:

```tsx
it("renames inline without selecting the row", async () => {
  const onSelect = vi.fn();
  const onRename = vi.fn().mockResolvedValue(true);
  render(
    <ConversationItem
      conversation={makeConversation("conv-1")}
      selected={true}
      onSelect={onSelect}
      onRename={onRename}
      onArchive={vi.fn().mockResolvedValue(true)}
      onRestore={vi.fn().mockResolvedValue(true)}
      onDelete={vi.fn().mockResolvedValue(true)}
    />
  );

  fireEvent.click(screen.getByRole("button", { name: "More actions" }));
  fireEvent.click(screen.getByRole("button", { name: "Rename" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Conversation title" }), {
    target: { value: "Renamed" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save name" }));

  await waitFor(() =>
    expect(onRename).toHaveBeenCalledWith("Renamed")
  );
  expect(onSelect).not.toHaveBeenCalled();
});
```

Add a second test that opens Delete, clicks Cancel, then opens Delete and confirms; assert `onDelete` is called once and the confirm button is disabled while the returned Promise is pending.

- [ ] **Step 3: Run the hook and item tests**

```powershell
npm test -- features/chatbot/__tests__/use-conversations.test.tsx features/chatbot/__tests__/conversation-item.test.tsx
```

Expected: FAIL because the hook still uses browser dialogs and `ConversationItem` does not exist.

- [ ] **Step 4: Remove browser dialogs from the hook**

Change the rename signature to require a title:

```ts
const renameConversation = useCallback(
  async (conversation: ConversationData, nextTitle: string) => {
    if (!token) {
      return null;
    }
    const title = nextTitle.trim();
    if (!title) {
      return null;
    }
    invalidateDetailRequests();
    setDetailError(null);
    try {
      const updated = await client.updateConversation(
        { token, conversationId: conversation.id },
        { title }
      );
      dispatch({ type: "upsert_conversation", conversation: updated });
      if (
        state.selectedConversationId === conversation.id &&
        selectedConversationDetail
      ) {
        setSelectedConversationDetail({
          ...selectedConversationDetail,
          ...updated,
        });
      }
      return updated;
    } catch (error) {
      setDetailError(normalizeErrorMessage(error));
      return null;
    }
  },
  [
    client,
    dispatch,
    invalidateDetailRequests,
    selectedConversationDetail,
    state.selectedConversationId,
    token,
  ]
);
```

Delete the `window.prompt` branch. Delete the `window.confirm` branch from `deleteConversation` so the hook performs deletion immediately when called. Keep success-after-response removal; do not optimistically delete. Update the hook regression test to spy on `window.prompt` and `window.confirm`, call the new explicit-title rename and direct delete methods, and assert neither browser API was called.

- [ ] **Step 5: Implement ConversationItem as a local interaction state machine**

Create `conversation-item.tsx` with:

```ts
export type ConversationItemProps = {
  conversation: ConversationData;
  selected: boolean;
  onSelect: () => void;
  onRename: (title: string) => Promise<boolean>;
  onArchive: () => Promise<boolean>;
  onRestore: () => Promise<boolean>;
  onDelete: () => Promise<boolean>;
};
```

Use local state:

```ts
const [mode, setMode] = useState<"idle" | "menu" | "rename" | "delete">("idle");
const [title, setTitle] = useState(conversation.title);
const [pending, setPending] = useState<"rename" | "archive" | "restore" | "delete" | null>(null);
const [error, setError] = useState<string | null>(null);
```

Use one helper for mutations:

```ts
async function runAction(
  kind: Exclude<typeof pending, null>,
  action: () => Promise<boolean>
) {
  if (pending) {
    return;
  }
  setPending(kind);
  setError(null);
  try {
    const ok = await action();
    if (ok) {
      setMode("idle");
    } else {
      setError("Action failed. Try again.");
    }
  } finally {
    setPending(null);
  }
}
```

Render:

- A dedicated select button with the title and formatted update time.
- A sibling `More actions` button; never nest a button inside the select button.
- Menu actions Rename、Archive or Restore、Delete.
- Rename form with `aria-label="Conversation title"`, Save name, Cancel.
- Delete confirmation text, Delete conversation, Cancel.
- `role="alert"` for the local error.
- Real `disabled` attributes whenever `pending !== null`.
- Classes using `--chat-*` variables, 44–48px row height, truncate, focus-visible ring.

- [ ] **Step 6: Implement the pure ConversationList**

Create `conversation-list.tsx` with props:

```ts
type ConversationListProps = {
  items: ConversationData[];
  selectedConversationId: string | null;
  loading: boolean;
  error: string | null;
  hasMore: boolean;
  onSelect: (conversationId: string) => void;
  onLoadMore: () => Promise<void> | void;
  onRetry: () => Promise<void> | void;
  onRename: (conversation: ConversationData, title: string) => Promise<boolean>;
  onArchive: (conversation: ConversationData) => Promise<boolean>;
  onRestore: (conversation: ConversationData) => Promise<boolean>;
  onDelete: (conversation: ConversationData) => Promise<boolean>;
};
```

Map rows to `ConversationItem` and adapt IDs/Conversation arguments in callbacks. Render exactly one of initial skeleton, error+Retry, empty state, or rows. Preserve rows while `loading` is true after an initial successful load.

- [ ] **Step 7: Reduce ConversationSidebar to toolbar + list**

Keep its existing public props so `ChatbotShell` does not change. Add local `creating` state around `onCreateConversation`. Render:

- New chat button.
- Active/Archived tabs.
- Refresh.
- `ConversationList`.
- Load more through `ConversationList`.

Adapt hook result callbacks to boolean:

```tsx
onRename={async (conversation, title) =>
  Boolean(await onRenameConversation(conversation, title))
}
onArchive={async (conversation) =>
  Boolean(await onArchiveConversation(conversation))
}
onRestore={async (conversation) =>
  Boolean(await onRestoreConversation(conversation))
}
onDelete={async (conversation) =>
  Boolean(await onDeleteConversation(conversation))
}
```

- [ ] **Step 8: Run Conversation tests and TypeScript**

```powershell
npm test -- features/chatbot/__tests__/use-conversations.test.tsx features/chatbot/__tests__/conversation-sidebar.test.tsx features/chatbot/__tests__/conversation-item.test.tsx
npx tsc --noEmit --incremental false
```

Expected: all selected tests PASS and TypeScript exits 0.

- [ ] **Step 9: Commit the Conversation UI split**

```powershell
git add frontend/features/chatbot/hooks/use-conversations.ts frontend/features/chatbot/components/conversation-sidebar.tsx frontend/features/chatbot/components/conversation-list.tsx frontend/features/chatbot/components/conversation-item.tsx frontend/features/chatbot/__tests__/use-conversations.test.tsx frontend/features/chatbot/__tests__/conversation-sidebar.test.tsx frontend/features/chatbot/__tests__/conversation-item.test.tsx
git diff --cached --check
git commit -m "feat(chatbot): split conversation sidebar interactions"
```

---

### Task 7: Extract Markdown and Code Rendering

**Files:**
- Create: `frontend/features/chatbot/components/code-block.tsx`
- Create: `frontend/features/chatbot/components/markdown-content.tsx`
- Modify: `frontend/features/chatbot/components/message-item.tsx`
- Create: `frontend/features/chatbot/__tests__/markdown-content.test.tsx`
- Modify: `frontend/features/chatbot/__tests__/message-list.test.tsx`

**Interfaces:**
- Consumes: `react-markdown`、`remark-gfm`、Clipboard API on click.
- Produces:
  - `CodeBlock({ code, language })`
  - `MarkdownContent({ content })`
  - `SafeAnchor` remains protocol-restricted to http/https/mailto.

- [ ] **Step 1: Add semantic and security tests**

Create `markdown-content.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MarkdownContent } from "../components/markdown-content";

describe("MarkdownContent", () => {
  beforeEach(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it("renders GFM, quotes, tables, inline code, and block code", () => {
    render(
      <MarkdownContent
        content={[
          "## Heading",
          "",
          "> Quote",
          "",
          "| A | B |",
          "| - | - |",
          "| 1 | 2 |",
          "",
          "`inline`",
          "",
          "~~~ts",
          "const value = 1;",
          "~~~",
        ].join("\n")}
      />
    );

    expect(screen.getByRole("heading", { name: "Heading" })).toBeInTheDocument();
    expect(screen.getByText("Quote").closest("blockquote")).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("inline").closest("code")).toBeInTheDocument();
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy code" })).toBeInTheDocument();
  });

  it("copies code and blocks unsafe links", async () => {
    render(
      <MarkdownContent
        content={"~~~js\nalert('safe text');\n~~~\n\n[unsafe](javascript:alert(1))"}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Copy code" }));
    await waitFor(() =>
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith("alert('safe text');")
    );
    expect(screen.getByText("unsafe").closest("a")).toBeNull();
  });
});
```

- [ ] **Step 2: Run the test and confirm the components are missing**

```powershell
npm test -- features/chatbot/__tests__/markdown-content.test.tsx
```

Expected: FAIL because `markdown-content.tsx` does not exist.

- [ ] **Step 3: Implement CodeBlock**

Create `code-block.tsx`:

```tsx
"use client";

import { useEffect, useRef, useState } from "react";

const LANGUAGE_LABELS: Record<string, string> = {
  js: "JavaScript",
  javascript: "JavaScript",
  ts: "TypeScript",
  typescript: "TypeScript",
  tsx: "TSX",
  jsx: "JSX",
  py: "Python",
  python: "Python",
  json: "JSON",
  bash: "Shell",
  sh: "Shell",
  text: "Text",
};

export function CodeBlock({
  code,
  language = "text",
}: {
  code: string;
  language?: string;
}) {
  const [status, setStatus] = useState<"idle" | "copied" | "failed">("idle");
  const resetTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (resetTimer.current) {
        clearTimeout(resetTimer.current);
      }
    };
  }, []);

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(code);
      setStatus("copied");
    } catch {
      setStatus("failed");
    }
    if (resetTimer.current) {
      clearTimeout(resetTimer.current);
    }
    resetTimer.current = setTimeout(() => setStatus("idle"), 1600);
  }

  const label = LANGUAGE_LABELS[language.toLowerCase()] ?? language;

  return (
    <div className="my-4 overflow-hidden rounded-xl border border-[var(--chat-border)] bg-[var(--chat-code-bg)]">
      <div className="flex items-center justify-between border-b border-[var(--chat-border)] px-3 py-2 text-xs text-[var(--chat-muted)]">
        <span>{label}</span>
        <button
          type="button"
          aria-label="Copy code"
          onClick={() => void copyCode()}
          className="rounded-md px-2 py-1 hover:bg-[var(--chat-subtle)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--chat-accent)]"
        >
          {status === "copied" ? "Copied" : status === "failed" ? "Copy failed" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-4 text-sm leading-6">
        <code>{code}</code>
      </pre>
    </div>
  );
}
```

- [ ] **Step 4: Implement MarkdownContent**

Create `markdown-content.tsx`:

```tsx
import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { CodeBlock } from "./code-block";

function SafeAnchor({ href, children }: { href?: string; children?: ReactNode }) {
  if (!href) {
    return <span>{children}</span>;
  }
  try {
    const url = new URL(href, "http://localhost");
    if (!["http:", "https:", "mailto:"].includes(url.protocol)) {
      return <span>{children}</span>;
    }
    const targetHref = url.protocol === "mailto:" ? href : url.toString();
    return (
      <a
        href={targetHref}
        target="_blank"
        rel="noreferrer noopener"
        className="text-[var(--chat-accent)] underline decoration-current/40 underline-offset-4 hover:decoration-current"
      >
        {children}
      </a>
    );
  } catch {
    return <span>{children}</span>;
  }
}

export function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="chat-markdown text-[15px] leading-7 text-[var(--chat-text)]">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => <SafeAnchor href={href}>{children}</SafeAnchor>,
          h1: ({ children }) => <h1 className="mb-3 mt-6 text-[1.35rem] font-semibold">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-3 mt-6 text-[1.2rem] font-semibold">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-2 mt-5 text-[1.1rem] font-semibold">{children}</h3>,
          p: ({ children }) => <p className="my-3 whitespace-pre-wrap">{children}</p>,
          ul: ({ children }) => <ul className="my-3 list-disc space-y-1.5 pl-6">{children}</ul>,
          ol: ({ children }) => <ol className="my-3 list-decimal space-y-1.5 pl-6">{children}</ol>,
          blockquote: ({ children }) => (
            <blockquote className="my-4 border-l-[3px] border-[var(--chat-accent)] bg-[var(--chat-subtle)] px-4 py-2 text-[var(--chat-muted)]">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto">
              <table className="w-full border-collapse text-sm">{children}</table>
            </div>
          ),
          th: ({ children }) => <th className="border border-[var(--chat-border)] bg-[var(--chat-subtle)] px-3 py-2 text-left">{children}</th>,
          td: ({ children }) => <td className="border border-[var(--chat-border)] px-3 py-2 align-top">{children}</td>,
          code: ({ className, children, ...props }) => {
            const raw = String(children);
            const language = /language-([\w-]+)/.exec(className ?? "")?.[1] ?? "text";
            const isBlock = Boolean(className) || raw.includes("\n");
            if (isBlock) {
              return <CodeBlock code={raw.replace(/\n$/, "")} language={language} />;
            }
            return (
              <code
                className="rounded-md bg-[var(--chat-subtle)] px-1.5 py-0.5 font-mono text-[0.9em]"
                {...props}
              >
                {children}
              </code>
            );
          },
          pre: ({ children }) => <>{children}</>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
```

- [ ] **Step 5: Make MessageItem use the extracted renderer and target layout**

Remove `ReactMarkdown`、`remarkGfm` and `SafeAnchor` from `message-item.tsx`. Import `MarkdownContent`. Replace the current article/body wrappers with:

```tsx
<article
  data-message-id={message.id}
  className={isUser ? "flex justify-end" : "w-full"}
>
  <div
    className={
      isUser
        ? "max-w-[75%] rounded-[14px] border border-[var(--chat-border)] bg-[var(--chat-subtle)] px-3.5 py-2.5 text-[15px] leading-6 text-[var(--chat-text)] max-md:max-w-[86%]"
        : "w-full text-[var(--chat-text)]"
    }
  >
    {isUser ? (
      <p className="whitespace-pre-wrap">{message.content}</p>
    ) : (
      <MarkdownContent
        content={message.content || (message.status === "pending" ? "Thinking…" : "")}
      />
    )}
    {message.status === "failed" ? (
      <p className="mt-2 text-xs text-[var(--chat-danger)]">
        {message.error_code ?? "Message failed"}
      </p>
    ) : null}
    {actionControls}
  </div>
</article>
```

Define `actionControls` immediately before the return:

```tsx
const actionControls =
  showStop || showRetry || showRegenerate ? (
    <div className="mt-3 flex flex-wrap gap-2">
      {showStop ? (
        <button
          type="button"
          onClick={() => void onStop?.()}
          disabled={actionsDisabled || stopping}
          className="rounded-lg border border-[var(--chat-danger)]/30 px-2.5 py-1.5 text-xs font-medium text-[var(--chat-danger)] hover:bg-[var(--chat-danger)]/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--chat-accent)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {stopping ? "Stopping…" : "Stop generation"}
        </button>
      ) : null}
      {showRetry ? (
        <button
          type="button"
          onClick={() => void onRetry?.()}
          disabled={actionsDisabled}
          className="rounded-lg border border-[var(--chat-border)] px-2.5 py-1.5 text-xs font-medium hover:bg-[var(--chat-subtle)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--chat-accent)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Retry
        </button>
      ) : null}
      {showRegenerate ? (
        <button
          type="button"
          onClick={() => void onRegenerate?.()}
          disabled={actionsDisabled}
          className="rounded-lg border border-[var(--chat-border)] px-2.5 py-1.5 text-xs font-medium hover:bg-[var(--chat-subtle)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--chat-accent)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Regenerate
        </button>
      ) : null}
    </div>
  ) : null;
```

Use `isStreaming` in the assistant empty-content fallback:

```tsx
content={
  message.content ||
  (message.status === "pending" || isStreaming ? "Thinking…" : "")
}
```

Remove the role/status metadata row and all message card shadows.

- [ ] **Step 6: Run Markdown and Message tests**

```powershell
npm test -- features/chatbot/__tests__/markdown-content.test.tsx features/chatbot/__tests__/message-list.test.tsx features/chatbot/__tests__/generation-controls.test.tsx
npx tsc --noEmit --incremental false
```

Expected: all selected tests PASS and TypeScript exits 0.

- [ ] **Step 7: Commit message rendering**

```powershell
git add frontend/features/chatbot/components/code-block.tsx frontend/features/chatbot/components/markdown-content.tsx frontend/features/chatbot/components/message-item.tsx frontend/features/chatbot/__tests__/markdown-content.test.tsx frontend/features/chatbot/__tests__/message-list.test.tsx
git diff --cached --check
git commit -m "feat(chatbot): render assistant replies as documents"
```

---

### Task 8: Stabilize the Message Viewport and Scroll Controls

**Files:**
- Modify: `frontend/features/chatbot/hooks/use-messages.ts`
- Modify: `frontend/features/chatbot/components/message-list.tsx`
- Modify: `frontend/features/chatbot/components/chat-conversation-panel.tsx`
- Modify: `frontend/features/chatbot/__tests__/message-list.test.tsx`

**Interfaces:**
- Consumes: existing history state and scroll refs.
- Produces:
  - `useMessages.retryHistory(): Promise<MessagePageData | null>`
  - `MessageList.onRetryHistory`
  - Immediate stream follow; smooth scroll only for explicit Jump.

- [ ] **Step 1: Add scroll behavior and history retry tests**

Extend `message-list.test.tsx`:

```tsx
it("uses smooth scrolling only when the user requests the bottom", () => {
  const props = {
    loadingHistory: false,
    historyError: null,
    hasMore: false,
    onLoadMore: vi.fn(),
    onRetryHistory: vi.fn(),
    streamPhase: "streaming" as const,
    streamingMessageId: "msg-1",
  };
  const { container, rerender } = render(
    <MessageList {...props} messages={[makeMessage({ content: "First" })]} />
  );
  const scroller = container.querySelector(".overflow-y-auto") as HTMLDivElement;
  const scrollTo = vi.fn();
  Object.defineProperties(scroller, {
    scrollHeight: { configurable: true, value: 1000 },
    clientHeight: { configurable: true, value: 200 },
    scrollTo: { configurable: true, value: scrollTo },
  });
  scroller.scrollTop = 100;
  fireEvent.scroll(scroller);
  rerender(
    <MessageList
      {...props}
      messages={[makeMessage({ content: "First plus delta" })]}
    />
  );

  expect(scrollTo).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Back to bottom" }));
  expect(scrollTo).toHaveBeenCalledWith({ top: 1000, behavior: "smooth" });
});

it("offers a retry action when history loading fails", () => {
  const onRetryHistory = vi.fn();
  render(
    <MessageList
      messages={[]}
      loadingHistory={false}
      historyError="offline"
      hasMore={false}
      onLoadMore={vi.fn()}
      onRetryHistory={onRetryHistory}
      streamPhase="idle"
      streamingMessageId={null}
    />
  );

  fireEvent.click(screen.getByRole("button", { name: "Retry history" }));
  expect(onRetryHistory).toHaveBeenCalledTimes(1);
});
```

Add `onRetryHistory={vi.fn()}` to all existing MessageList test renders.

- [ ] **Step 2: Run MessageList tests and confirm the prop/behavior failure**

```powershell
npm test -- features/chatbot/__tests__/message-list.test.tsx
```

Expected: FAIL because `onRetryHistory` is not a prop and the current Jump does not call `scrollTo` with smooth behavior.

- [ ] **Step 3: Expose retryHistory from useMessages**

Add to the return object:

```ts
retryHistory: () => loadHistory(null, false),
```

Do not clear existing messages before retry. The request ownership guard from Task 3 remains in force.

- [ ] **Step 4: Separate immediate following from explicit smooth Jump**

In `MessageListProps` add:

```ts
onRetryHistory: () => void | Promise<void>;
```

Replace `scrollToBottom` with:

```ts
const scrollToBottom = useCallback((behavior: ScrollBehavior = "auto") => {
  const container = containerRef.current;
  if (!container) {
    return;
  }
  if (behavior === "smooth") {
    container.scrollTo({ top: container.scrollHeight, behavior });
  } else {
    container.scrollTop = container.scrollHeight;
  }
  stickToBottomRef.current = true;
  setShowJumpButton(false);
}, []);
```

Keep direct assignment in `useLayoutEffect`:

```ts
if (stickToBottomRef.current) {
  container.scrollTop = container.scrollHeight;
  setShowJumpButton(false);
}
```

Remove `scroll-smooth` from the scroll container. Change the Jump handler to:

```tsx
onClick={() => scrollToBottom("smooth")}
```

Replace the old message header, card wrapper, error text, and component return with this complete structure:

```tsx
return (
  <div className="relative flex min-h-0 flex-1 flex-col">
    <div
      ref={containerRef}
      onScroll={() => void handleScroll()}
      className="min-h-0 flex-1 overflow-y-auto px-4 py-6 md:px-6 lg:px-8"
    >
      <div className="mx-auto w-full max-w-3xl space-y-7">
        {historyError ? (
          <div
            role="alert"
            className="rounded-xl border border-[var(--chat-danger)]/30 bg-[var(--chat-danger)]/10 p-4 text-sm text-[var(--chat-text)]"
          >
            <p>{historyError}</p>
            <button
              type="button"
              onClick={() => void onRetryHistory()}
              className="mt-2 rounded-lg px-2 py-1 font-semibold text-[var(--chat-danger)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--chat-accent)]"
            >
              Retry history
            </button>
          </div>
        ) : null}

        {loadMorePending ? (
          <div
            role="status"
            className="text-center text-xs font-medium text-[var(--chat-muted)]"
          >
            Loading earlier messages…
          </div>
        ) : null}

        {messages.length === 0 && !loadingHistory ? (
          <div className="py-16 text-center text-sm leading-7 text-[var(--chat-muted)]">
            No messages yet. Start the conversation below.
          </div>
        ) : null}

        {messages.map((message) => (
          <MessageItem
            key={message.id}
            message={message}
            isStreaming={
              streamingMessageId === message.id &&
              streamPhase === "streaming"
            }
            stopping={stoppingMessageId === message.id}
            onStop={
              onStopGeneration
                ? () => onStopGeneration(message.id)
                : undefined
            }
            onRetry={
              onRetryMessage ? () => onRetryMessage(message.id) : undefined
            }
            onRegenerate={
              onRegenerateMessage
                ? () => onRegenerateMessage(message.id)
                : undefined
            }
            actionsDisabled={actionsDisabled}
          />
        ))}
      </div>
    </div>

    {showJumpButton ? (
      <div className="pointer-events-none absolute inset-x-0 bottom-5 flex justify-center">
        <button
          type="button"
          onClick={() => scrollToBottom("smooth")}
          className="pointer-events-auto rounded-full border border-[var(--chat-border)] bg-[var(--chat-surface)] px-4 py-2 text-sm font-medium text-[var(--chat-text)] shadow-md hover:bg-[var(--chat-subtle)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--chat-accent)]"
        >
          Back to bottom
        </button>
      </div>
    ) : null}
  </div>
);
```

- [ ] **Step 5: Wire retryHistory in ChatConversationPanel**

Pass:

```tsx
onRetryHistory={() => void messages.retryHistory()}
```

Do not add a second call to `useMessages`.

- [ ] **Step 6: Run scroll, stream, and type checks**

```powershell
npm test -- features/chatbot/__tests__/message-list.test.tsx features/chatbot/__tests__/chat-stream.test.ts features/chatbot/__tests__/use-chat-stream.test.tsx
npx tsc --noEmit --incremental false
```

Expected: scroll tests, stream tests, and TypeScript all PASS.

- [ ] **Step 7: Commit viewport behavior**

```powershell
git add frontend/features/chatbot/hooks/use-messages.ts frontend/features/chatbot/components/message-list.tsx frontend/features/chatbot/components/chat-conversation-panel.tsx frontend/features/chatbot/__tests__/message-list.test.tsx
git diff --cached --check
git commit -m "fix(chatbot): stabilize message viewport scrolling"
```

---

### Task 9: Rebuild the Composer Around Send-or-Stop

**Files:**
- Modify: `frontend/features/chatbot/components/chat-composer.tsx`
- Modify: `frontend/features/chatbot/components/chat-conversation-panel.tsx`
- Modify: `frontend/features/chatbot/__tests__/chat-composer.test.tsx`
- Modify: `frontend/features/chatbot/__tests__/generation-controls.test.tsx`

**Interfaces:**
- Consumes: current draft/stream/control API from `useMessages` and `conversation.model`.
- Produces:
  - required `ChatComposer.model: string`
  - IME-safe Enter behavior
  - 1–6 row textarea
  - exactly one primary Send or Stop action

- [ ] **Step 1: Add Composer contract tests**

Extend `chat-composer.test.tsx`:

```tsx
it("does not submit Enter while an IME composition is active", () => {
  const onSubmit = vi.fn();
  render(
    <ChatComposer
      value="你好"
      model="deepseek-chat"
      onChange={vi.fn()}
      onSubmit={onSubmit}
    />
  );
  const textbox = screen.getByRole("textbox");

  fireEvent.compositionStart(textbox);
  fireEvent.keyDown(textbox, { key: "Enter" });
  expect(onSubmit).not.toHaveBeenCalled();

  fireEvent.compositionEnd(textbox);
  fireEvent.keyDown(textbox, { key: "Enter" });
  expect(onSubmit).toHaveBeenCalledWith("你好");
});

it("shows the current model and replaces Send with Stop while generating", () => {
  render(
    <ChatComposer
      value=""
      model="deepseek-chat"
      sending={true}
      onChange={vi.fn()}
      onSubmit={vi.fn()}
      onStop={vi.fn()}
    />
  );

  expect(screen.getByText("deepseek-chat")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Send message" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Stop generation" })).toBeInTheDocument();
});
```

Update every existing `ChatComposer` test render to pass:

```tsx
model="deepseek-chat"
```

- [ ] **Step 2: Run Composer tests and confirm the missing prop/IME failure**

```powershell
npm test -- features/chatbot/__tests__/chat-composer.test.tsx features/chatbot/__tests__/generation-controls.test.tsx
```

Expected: FAIL because `model` is absent and Enter sends during composition.

- [ ] **Step 3: Add auto-height and composition state**

Update the React imports in `chat-composer.tsx`:

```tsx
import {
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
```

Add required `model: string` to `ChatComposerProps`. Inside the component add:

```tsx
const textareaRef = useRef<HTMLTextAreaElement | null>(null);
const [isComposing, setIsComposing] = useState(false);
const maxTextareaHeight = 168;

useLayoutEffect(() => {
  const textarea = textareaRef.current;
  if (!textarea) {
    return;
  }
  textarea.style.height = "0px";
  const nextHeight = Math.min(textarea.scrollHeight, maxTextareaHeight);
  textarea.style.height = `${nextHeight}px`;
  textarea.style.overflowY =
    textarea.scrollHeight > maxTextareaHeight ? "auto" : "hidden";
}, [value]);
```

Use this key/composition handling on the textarea:

```tsx
onKeyDown={(event) => {
  if (
    event.key === "Enter" &&
    !event.shiftKey &&
    !isComposing &&
    !event.nativeEvent.isComposing
  ) {
    event.preventDefault();
    if (canSubmit) {
      void onSubmit(value);
    }
  }
}}
onCompositionStart={() => setIsComposing(true)}
onCompositionEnd={() => setIsComposing(false)}
```

- [ ] **Step 4: Replace the Composer markup**

Replace the current form body with:

```tsx
<form
  onSubmit={handleSubmit}
  className="mx-auto w-full max-w-3xl rounded-[20px] border border-[var(--chat-border)] bg-[var(--chat-surface)] p-3 shadow-[0_12px_32px_rgba(0,0,0,0.08)]"
>
  <label className="sr-only" htmlFor="chat-message">
    Message
  </label>
  <textarea
    id="chat-message"
    ref={textareaRef}
    rows={1}
    value={value}
    disabled={disabled || sending}
    maxLength={maxLength}
    onChange={(event) => onChange(event.target.value)}
    onKeyDown={(event) => {
      if (
        event.key === "Enter" &&
        !event.shiftKey &&
        !isComposing &&
        !event.nativeEvent.isComposing
      ) {
        event.preventDefault();
        if (canSubmit) {
          void onSubmit(value);
        }
      }
    }}
    onCompositionStart={() => setIsComposing(true)}
    onCompositionEnd={() => setIsComposing(false)}
    placeholder="Message the assistant"
    className="max-h-[168px] min-h-11 w-full resize-none bg-transparent px-2 py-2 text-[15px] leading-6 text-[var(--chat-text)] outline-none placeholder:text-[var(--chat-muted)] disabled:cursor-not-allowed"
  />
  {error ? (
    <p role="alert" className="px-2 py-2 text-sm text-[var(--chat-danger)]">
      {error}
    </p>
  ) : null}
  <div className="flex items-center gap-3 px-1 pt-2 text-xs text-[var(--chat-muted)]">
    <span className="truncate" title={model}>
      {model}
    </span>
    <span
      className={
        value.length > maxLength * 0.9
          ? "ml-auto text-[var(--chat-danger)]"
          : "ml-auto"
      }
    >
      {value.length}/{maxLength}
    </span>
    {sending && onStop ? (
      <button
        type="button"
        onClick={() => void onStop()}
        disabled={stopping}
        aria-label="Stop generation"
        className="rounded-full bg-[var(--chat-text)] px-3 py-2 font-semibold text-[var(--chat-page)] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {stopping ? "Stopping…" : "Stop"}
      </button>
    ) : (
      <button
        type="submit"
        disabled={!canSubmit}
        aria-label="Send message"
        className="rounded-full bg-[var(--chat-accent)] px-3 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        Send
      </button>
    )}
  </div>
</form>
```

Delete the Clear button and the old separate Stop button. Keep `handleSubmit` and `canSubmit`.

- [ ] **Step 5: Treat detached server generation as active in ChatConversationPanel**

Compute after `useMessages`:

```ts
const detachedGenerationActive =
  activeGeneration?.status === "pending" ||
  activeGeneration?.status === "streaming";
const generationActive =
  messages.sending ||
  messages.streamPhase === "streaming" ||
  detachedGenerationActive;
const activeAssistantMessageId =
  messages.streamingMessageId ??
  activeGeneration?.assistant_message_id ??
  null;
```

Replace the Composer call with:

```tsx
<ChatComposer
  value={messages.draft}
  model={conversation.model}
  disabled={!canSend}
  sending={generationActive}
  stopping={
    Boolean(activeAssistantMessageId) &&
    messages.stoppingMessageId === activeAssistantMessageId
  }
  error={
    conversation.status !== "active"
      ? "Archived conversations are read-only."
      : messages.controlError ?? messages.streamError
  }
  onChange={messages.setDraft}
  onSubmit={(content) => void messages.sendMessage(content)}
  onStop={
    generationActive
      ? () => void messages.stopGeneration(activeAssistantMessageId)
      : undefined
  }
/>
```

Remove duplicate stream/control error panels from the header area.

- [ ] **Step 6: Run Composer, generation, Message, and type tests**

```powershell
npm test -- features/chatbot/__tests__/chat-composer.test.tsx features/chatbot/__tests__/generation-controls.test.tsx features/chatbot/__tests__/message-list.test.tsx
npx tsc --noEmit --incremental false
```

Expected: all selected tests PASS and TypeScript exits 0.

- [ ] **Step 7: Commit Composer behavior**

```powershell
git add frontend/features/chatbot/components/chat-composer.tsx frontend/features/chatbot/components/chat-conversation-panel.tsx frontend/features/chatbot/__tests__/chat-composer.test.tsx frontend/features/chatbot/__tests__/generation-controls.test.tsx
git diff --cached --check
git commit -m "feat(chatbot): center composer generation controls"
```

---

### Task 10: Expand useMemories into the Single Memory Controller

**Files:**
- Modify: `frontend/features/chatbot/types/memory.ts`
- Modify: `frontend/features/chatbot/hooks/use-memories.ts`
- Modify: `frontend/features/chatbot/__tests__/use-memories.test.tsx`

**Interfaces:**
- Consumes: complete `MemoryApiClient` from Task 1.
- Produces:
  - `MemoryScope = "all" | "current"`
  - list filters: `status`、`memoryType`、`scope`
  - detail state: `selectedMemoryId`、`detail`、`detailLoading`、`detailError`
  - `selectMemory`、`clearSelection`
  - per-resource `pendingAction` and `mutationError`
  - versioned list and detail requests.

- [ ] **Step 1: Add filter and detail race tests**

Extend `use-memories.test.tsx` with:

```tsx
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

it("passes type and current-conversation filters to the API", async () => {
  const client = {
    listMemories: vi.fn().mockResolvedValue({
      items: [],
      next_cursor: null,
      has_more: false,
    }),
    getMemory: vi.fn(),
    updateMemory: vi.fn(),
    deleteMemory: vi.fn(),
  };
  const { result } = renderHook(() =>
    useMemories({
      token: "token",
      client,
      currentConversationId: "conv-1",
    })
  );

  await waitFor(() => expect(client.listMemories).toHaveBeenCalledTimes(1));
  act(() => result.current.setMemoryType("project_context"));
  await waitFor(() =>
    expect(client.listMemories).toHaveBeenLastCalledWith(
      expect.objectContaining({ memoryType: "project_context" })
    )
  );
  act(() => result.current.setScope("current"));
  await waitFor(() =>
    expect(client.listMemories).toHaveBeenLastCalledWith(
      expect.objectContaining({ conversationId: "conv-1" })
    )
  );
});

it("ignores a stale memory detail response", async () => {
  const first = deferred<MemoryData>();
  const second = deferred<MemoryData>();
  const client = {
    listMemories: vi.fn().mockResolvedValue({
      items: [makeMemory("memory-a"), makeMemory("memory-b")],
      next_cursor: null,
      has_more: false,
    }),
    getMemory: vi
      .fn()
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise),
    updateMemory: vi.fn(),
    deleteMemory: vi.fn(),
  };
  const { result } = renderHook(() => useMemories({ token: "token", client }));
  await waitFor(() => expect(result.current.items).toHaveLength(2));

  let firstLoad!: Promise<MemoryData | null>;
  let secondLoad!: Promise<MemoryData | null>;
  act(() => {
    firstLoad = result.current.selectMemory("memory-a");
    secondLoad = result.current.selectMemory("memory-b");
  });
  await act(async () => {
    second.resolve(makeMemory("memory-b", { content: "Newest" }));
    await secondLoad;
  });
  await act(async () => {
    first.resolve(makeMemory("memory-a", { content: "Stale" }));
    await firstLoad;
  });

  expect(result.current.selectedMemoryId).toBe("memory-b");
  expect(result.current.detail?.content).toBe("Newest");
});
```

Update the existing client mock in the load/update/delete test to include:

```ts
getMemory: vi.fn().mockResolvedValue(makeMemory("memory-1")),
```

Update that test's first list-call assertion to the expanded client contract:

```ts
expect(client.listMemories).toHaveBeenCalledWith({
  token: "token",
  status: "active",
  memoryType: null,
  conversationId: null,
  cursor: null,
  limit: 20,
});
```

- [ ] **Step 2: Run the Memory hook tests and confirm missing filter/detail state**

```powershell
npm test -- features/chatbot/__tests__/use-memories.test.tsx
```

Expected: FAIL because `currentConversationId`、`setMemoryType`、`setScope`、`selectMemory` and detail state do not exist.

- [ ] **Step 3: Add the MemoryScope type**

In `types/memory.ts` add:

```ts
export type MemoryScope = "all" | "current";
```

- [ ] **Step 4: Add filter, detail, and request ownership state**

In `use-memories.ts` add `useRef` to the React imports and import `MemoryListStatus`、`MemoryScope`、`MemoryType`. Extend options:

```ts
type Options = {
  token: string | null;
  client?: MemoryApiClient;
  pageSize?: number;
  currentConversationId?: string | null;
};
```

Inside the hook add:

```ts
const [status, setStatus] = useState<MemoryListStatus>("active");
const [memoryType, setMemoryType] = useState<MemoryType | null>(null);
const [scope, setScopeState] = useState<MemoryScope>("all");
const [selectedMemoryId, setSelectedMemoryId] = useState<string | null>(null);
const [detail, setDetail] = useState<MemoryData | null>(null);
const [detailLoading, setDetailLoading] = useState(false);
const [detailError, setDetailError] = useState<string | null>(null);
const [pendingAction, setPendingAction] = useState<{
  memoryId: string;
  kind: "save" | "delete";
} | null>(null);
const [mutationError, setMutationError] = useState<string | null>(null);
const listRequestVersionRef = useRef(0);
const detailRequestVersionRef = useRef(0);

const conversationFilter =
  scope === "current" ? currentConversationId ?? null : null;
const scopeUnavailable =
  scope === "current" && !currentConversationId;
```

Delete the old `setStatusState` wrapper.

- [ ] **Step 5: Replace list loading with versioned filtering**

Replace `load` with:

```ts
const load = useCallback(
  async (cursor: string | null = null, append = false) => {
    if (!token) {
      return null;
    }
    const requestVersion = listRequestVersionRef.current + 1;
    listRequestVersionRef.current = requestVersion;
    const ownsRequest = () => listRequestVersionRef.current === requestVersion;

    setLoading(true);
    setError(null);
    try {
      const page = await client.listMemories({
        token,
        status,
        memoryType,
        conversationId: conversationFilter,
        cursor,
        limit: pageSize,
      });
      if (!ownsRequest()) {
        return null;
      }
      setItems((current) => (append ? [...current, ...page.items] : page.items));
      setNextCursor(page.next_cursor);
      setHasMore(page.has_more);
      return page;
    } catch (cause) {
      if (!ownsRequest()) {
        return null;
      }
      setError(cause instanceof Error ? cause.message : "Unable to load memories.");
      return null;
    } finally {
      if (ownsRequest()) {
        setLoading(false);
      }
    }
  },
  [client, conversationFilter, memoryType, pageSize, status, token]
);
```

Use an effect that clears page/detail state and loads the new filter:

```ts
useEffect(() => {
  if (scopeUnavailable) {
    setScopeState("all");
    return;
  }
  listRequestVersionRef.current += 1;
  detailRequestVersionRef.current += 1;
  setItems([]);
  setNextCursor(null);
  setHasMore(false);
  setLoading(false);
  setSelectedMemoryId(null);
  setDetail(null);
  setDetailLoading(false);
  setDetailError(null);
  setMutationError(null);
  void load(null, false);
}, [load, scopeUnavailable]);
```

The `scopeUnavailable` guard avoids issuing one request for a now-missing current Conversation and a second request after falling back to “all”.

- [ ] **Step 6: Add versioned detail loading**

Add:

```ts
const selectMemory = useCallback(
  async (memoryId: string) => {
    if (!token) {
      return null;
    }
    const requestVersion = detailRequestVersionRef.current + 1;
    detailRequestVersionRef.current = requestVersion;
    const ownsRequest = () =>
      detailRequestVersionRef.current === requestVersion;

    setSelectedMemoryId(memoryId);
    setDetailLoading(true);
    setDetailError(null);
    try {
      const memory = await client.getMemory({ token, memoryId });
      if (!ownsRequest()) {
        return null;
      }
      setDetail(memory);
      return memory;
    } catch (cause) {
      if (!ownsRequest()) {
        return null;
      }
      setDetailError(
        cause instanceof Error ? cause.message : "Unable to load memory."
      );
      return null;
    } finally {
      if (ownsRequest()) {
        setDetailLoading(false);
      }
    }
  },
  [client, token]
);

const clearSelection = useCallback(() => {
  detailRequestVersionRef.current += 1;
  setSelectedMemoryId(null);
  setDetail(null);
  setDetailError(null);
  setDetailLoading(false);
}, []);
```

- [ ] **Step 7: Synchronize update/delete with filters and detail**

Define:

```ts
const matchesFilters = useCallback(
  (memory: MemoryData) =>
    memory.status === status &&
    (!memoryType || memory.memory_type === memoryType) &&
    (!conversationFilter || memory.conversation_id === conversationFilter),
  [conversationFilter, memoryType, status]
);
```

Replace `updateMemory` with:

```ts
const updateMemory = useCallback(
  async (memoryId: string, request: MemoryUpdateRequest) => {
    if (!token) {
      return null;
    }
    setPendingAction({ memoryId, kind: "save" });
    setMutationError(null);
    try {
      const updated = await client.updateMemory({ token, memoryId }, request);
      setItems((current) =>
        matchesFilters(updated)
          ? current.map((item) => (item.id === memoryId ? updated : item))
          : current.filter((item) => item.id !== memoryId)
      );
      if (selectedMemoryId === memoryId) {
        setDetail(updated);
      }
      return updated;
    } catch (cause) {
      setMutationError(
        cause instanceof Error ? cause.message : "Unable to update memory."
      );
      return null;
    } finally {
      setPendingAction((current) =>
        current?.memoryId === memoryId && current.kind === "save"
          ? null
          : current
      );
    }
  },
  [client, matchesFilters, selectedMemoryId, token]
);
```

Replace `deleteMemory` with:

```ts
const deleteMemory = useCallback(
  async (memoryId: string) => {
    if (!token) {
      return false;
    }
    setPendingAction({ memoryId, kind: "delete" });
    setMutationError(null);
    try {
      await client.deleteMemory({ token, memoryId });
      setItems((current) =>
        current.filter((item) => item.id !== memoryId)
      );
      if (selectedMemoryId === memoryId) {
        clearSelection();
      }
      return true;
    } catch (cause) {
      setMutationError(
        cause instanceof Error ? cause.message : "Unable to delete memory."
      );
      return false;
    } finally {
      setPendingAction((current) =>
        current?.memoryId === memoryId && current.kind === "delete"
          ? null
          : current
      );
    }
  },
  [clearSelection, client, selectedMemoryId, token]
);
```

The list/detail state changes happen only after API success; do not optimistically remove or overwrite data.

- [ ] **Step 8: Return the complete controller interface**

Return:

```ts
return {
  status,
  setStatus,
  memoryType,
  setMemoryType,
  scope,
  setScope: (next: MemoryScope) =>
    setScopeState(next === "current" && !currentConversationId ? "all" : next),
  items,
  loading,
  error,
  hasMore,
  loadMore,
  refresh: () => load(null, false),
  selectedMemoryId,
  detail,
  detailLoading,
  detailError,
  selectMemory,
  clearSelection,
  pendingAction,
  mutationError,
  updateMemory,
  deleteMemory,
};
```

- [ ] **Step 9: Run Memory hook, API, and type checks**

```powershell
npm test -- features/chatbot/__tests__/memory-api.test.ts features/chatbot/__tests__/use-memories.test.tsx
npx tsc --noEmit --incremental false
```

Expected: all selected tests PASS and TypeScript exits 0.

- [ ] **Step 10: Commit the Memory controller**

```powershell
git add frontend/features/chatbot/types/memory.ts frontend/features/chatbot/hooks/use-memories.ts frontend/features/chatbot/__tests__/use-memories.test.tsx
git diff --cached --check
git commit -m "feat(chatbot): add memory workspace controller"
```

---

### Task 11: Build the Memory Filters, List, and Detail Editor

**Files:**
- Create: `frontend/features/chatbot/components/memory-filters.tsx`
- Create: `frontend/features/chatbot/components/memory-list.tsx`
- Create: `frontend/features/chatbot/components/memory-detail-editor.tsx`
- Modify: `frontend/features/chatbot/components/memory-panel.tsx`
- Modify: `frontend/features/chatbot/components/chatbot-shell.tsx`
- Create: `frontend/features/chatbot/__tests__/memory-detail-editor.test.tsx`
- Modify: `frontend/features/chatbot/__tests__/memory-panel.test.tsx`
- Modify: `frontend/features/chatbot/__tests__/chatbot-workspace.test.tsx`

**Interfaces:**
- Consumes: controller returned by `useMemories` from Task 10.
- Produces:
  - `MemoryFilters` for status/type/scope.
  - `MemoryList` with pure list states.
  - `MemoryDetailEditor` for content/status/expires_at/delete.
  - `MemoryPanel({ token, currentConversationId, onOpenSidebar })` remains the only `useMemories` caller.

- [ ] **Step 1: Add the detail editor test**

Create `memory-detail-editor.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MemoryDetailEditor } from "../components/memory-detail-editor";
import type { MemoryData } from "../types/memory";

const memory: MemoryData = {
  id: "memory-1",
  conversation_id: "conv-1",
  memory_type: "project_context",
  content: "Project memory",
  importance: 0.8,
  confidence: 0.9,
  source_message_ids: [],
  status: "active",
  last_accessed_at: null,
  expires_at: null,
  created_at: "2026-07-14T00:00:00.000Z",
  updated_at: "2026-07-14T00:00:00.000Z",
};

describe("MemoryDetailEditor", () => {
  it("saves content, status, and expiry", async () => {
    const onSave = vi.fn().mockResolvedValue(true);
    render(
      <MemoryDetailEditor
        memory={memory}
        loading={false}
        error={null}
        saving={false}
        deleting={false}
        mutationError={null}
        onRetry={vi.fn()}
        onSave={onSave}
        onDelete={vi.fn().mockResolvedValue(true)}
      />
    );

    fireEvent.change(screen.getByRole("textbox", { name: "Memory content" }), {
      target: { value: "Updated memory" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: "Memory status" }), {
      target: { value: "candidate" },
    });
    fireEvent.change(screen.getByLabelText("Expires at"), {
      target: { value: "2026-08-01T12:30" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save memory" }));

    await waitFor(() =>
      expect(onSave).toHaveBeenCalledWith({
        content: "Updated memory",
        status: "candidate",
        expires_at: new Date("2026-08-01T12:30").toISOString(),
      })
    );
  });

  it("requires a second action before deleting", async () => {
    const onDelete = vi.fn().mockResolvedValue(true);
    render(
      <MemoryDetailEditor
        memory={memory}
        loading={false}
        error={null}
        saving={false}
        deleting={false}
        mutationError={null}
        onRetry={vi.fn()}
        onSave={vi.fn().mockResolvedValue(true)}
        onDelete={onDelete}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Delete memory" }));
    expect(onDelete).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Confirm delete" }));
    await waitFor(() => expect(onDelete).toHaveBeenCalledTimes(1));
  });
});
```

- [ ] **Step 2: Run Memory component tests and confirm the editor is missing**

```powershell
npm test -- features/chatbot/__tests__/memory-detail-editor.test.tsx features/chatbot/__tests__/memory-panel.test.tsx
```

Expected: FAIL because `MemoryDetailEditor` does not exist.

- [ ] **Step 3: Implement MemoryFilters**

Create `memory-filters.tsx`:

```tsx
import type {
  MemoryListStatus,
  MemoryScope,
  MemoryType,
} from "../types/memory";

const STATUS_OPTIONS: Array<{ value: MemoryListStatus; label: string }> = [
  { value: "active", label: "Active" },
  { value: "candidate", label: "Candidate" },
  { value: "superseded", label: "Superseded" },
];

const TYPE_OPTIONS: Array<{ value: MemoryType | ""; label: string }> = [
  { value: "", label: "All types" },
  { value: "preference", label: "Preference" },
  { value: "goal", label: "Goal" },
  { value: "project_context", label: "Project context" },
  { value: "explicit", label: "Explicit" },
  { value: "fact", label: "Fact" },
  { value: "work_context", label: "Work context" },
];

type MemoryFiltersProps = {
  status: MemoryListStatus;
  memoryType: MemoryType | null;
  scope: MemoryScope;
  hasCurrentConversation: boolean;
  onStatusChange: (status: MemoryListStatus) => void;
  onMemoryTypeChange: (memoryType: MemoryType | null) => void;
  onScopeChange: (scope: MemoryScope) => void;
};

export function MemoryFilters(props: MemoryFiltersProps) {
  return (
    <div className="grid gap-3 border-b border-[var(--chat-border)] p-4 sm:grid-cols-3">
      <label className="text-xs font-medium text-[var(--chat-muted)]">
        Status
        <select
          aria-label="Memory status filter"
          value={props.status}
          onChange={(event) =>
            props.onStatusChange(event.target.value as MemoryListStatus)
          }
          className="mt-1 w-full rounded-lg border border-[var(--chat-border)] bg-[var(--chat-surface)] px-3 py-2 text-sm text-[var(--chat-text)]"
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>
      <label className="text-xs font-medium text-[var(--chat-muted)]">
        Type
        <select
          aria-label="Memory type filter"
          value={props.memoryType ?? ""}
          onChange={(event) =>
            props.onMemoryTypeChange(
              event.target.value ? (event.target.value as MemoryType) : null
            )
          }
          className="mt-1 w-full rounded-lg border border-[var(--chat-border)] bg-[var(--chat-surface)] px-3 py-2 text-sm text-[var(--chat-text)]"
        >
          {TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>
      <label className="text-xs font-medium text-[var(--chat-muted)]">
        Scope
        <select
          aria-label="Memory scope filter"
          value={props.scope}
          onChange={(event) =>
            props.onScopeChange(event.target.value as MemoryScope)
          }
          className="mt-1 w-full rounded-lg border border-[var(--chat-border)] bg-[var(--chat-surface)] px-3 py-2 text-sm text-[var(--chat-text)]"
        >
          <option value="all">All conversations</option>
          <option value="current" disabled={!props.hasCurrentConversation}>
            Current conversation
          </option>
        </select>
      </label>
    </div>
  );
}
```

- [ ] **Step 4: Implement the pure MemoryList**

Create `memory-list.tsx`:

```tsx
import type { MemoryData } from "../types/memory";

type MemoryListProps = {
  items: MemoryData[];
  selectedMemoryId: string | null;
  loading: boolean;
  error: string | null;
  hasMore: boolean;
  onSelect: (memoryId: string) => void;
  onRetry: () => void | Promise<void>;
  onLoadMore: () => void | Promise<void>;
};

export function MemoryList(props: MemoryListProps) {
  if (props.loading && props.items.length === 0) {
    return <div aria-label="Loading memories" className="space-y-2 p-3">{[0, 1, 2].map((item) => <div key={item} className="h-16 animate-pulse rounded-lg bg-[var(--chat-subtle)]" />)}</div>;
  }
  if (props.error && props.items.length === 0) {
    return (
      <div role="alert" className="m-3 rounded-lg border border-[var(--chat-danger)]/30 p-4 text-sm">
        <p>{props.error}</p>
        <button type="button" onClick={() => void props.onRetry()}>Retry</button>
      </div>
    );
  }
  if (props.items.length === 0) {
    return <p className="p-6 text-sm text-[var(--chat-muted)]">No memories match these filters.</p>;
  }
  return (
    <div className="min-h-0 overflow-y-auto p-2">
      <div className="space-y-1">
        {props.items.map((memory) => (
          <button
            key={memory.id}
            type="button"
            aria-current={props.selectedMemoryId === memory.id ? "true" : undefined}
            onClick={() => props.onSelect(memory.id)}
            className="w-full rounded-lg px-3 py-3 text-left hover:bg-[var(--chat-subtle)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--chat-accent)]"
          >
            <span className="block text-xs uppercase text-[var(--chat-muted)]">{memory.memory_type}</span>
            <span className="mt-1 block line-clamp-2 text-sm text-[var(--chat-text)]">{memory.content}</span>
          </button>
        ))}
      </div>
      {props.hasMore ? (
        <button type="button" onClick={() => void props.onLoadMore()} disabled={props.loading} className="mt-3 w-full rounded-lg px-3 py-2 text-sm">
          {props.loading ? "Loading…" : "Load more"}
        </button>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 5: Implement MemoryDetailEditor**

Create `memory-detail-editor.tsx` with the prop contract used in Step 1. Add:

```tsx
"use client";

import { useEffect, useState, type FormEvent } from "react";

import type { MemoryData, MemoryUpdateRequest } from "../types/memory";

function toLocalDateTime(value: string | null) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

export function MemoryDetailEditor(props: {
  memory: MemoryData | null;
  loading: boolean;
  error: string | null;
  saving: boolean;
  deleting: boolean;
  mutationError: string | null;
  onRetry: () => void | Promise<void>;
  onSave: (request: MemoryUpdateRequest) => Promise<boolean>;
  onDelete: () => Promise<boolean>;
}) {
  const [content, setContent] = useState("");
  const [status, setStatus] = useState<"candidate" | "active">("active");
  const [expiresAt, setExpiresAt] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    if (!props.memory) {
      setContent("");
      setStatus("active");
      setExpiresAt("");
      setConfirmDelete(false);
      return;
    }
    setContent(props.memory.content);
    setStatus(props.memory.status === "candidate" ? "candidate" : "active");
    setExpiresAt(toLocalDateTime(props.memory.expires_at));
    setConfirmDelete(false);
  }, [props.memory]);

  if (props.loading) {
    return <div aria-label="Loading memory detail" className="m-6 h-52 animate-pulse rounded-xl bg-[var(--chat-subtle)]" />;
  }
  if (props.error) {
    return <div role="alert" className="m-6"><p>{props.error}</p><button type="button" onClick={() => void props.onRetry()}>Retry detail</button></div>;
  }
  if (!props.memory) {
    return <p className="p-6 text-sm text-[var(--chat-muted)]">Select a memory to view its details.</p>;
  }

  const editable =
    props.memory.status === "active" || props.memory.status === "candidate";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editable || !content.trim()) {
      return;
    }
    await props.onSave({
      content: content.trim(),
      status,
      expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
    });
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="flex h-full min-h-0 flex-col gap-4 overflow-y-auto p-5">
      <p className="text-xs uppercase text-[var(--chat-muted)]">{props.memory.memory_type}</p>
      <label className="text-sm font-medium">
        Content
        <textarea
          aria-label="Memory content"
          value={content}
          disabled={!editable || props.saving || props.deleting}
          onChange={(event) => setContent(event.target.value)}
          className="mt-1 min-h-40 w-full rounded-xl border border-[var(--chat-border)] bg-[var(--chat-surface)] p-3"
        />
      </label>
      <label className="text-sm font-medium">
        Status
        <select
          aria-label="Memory status"
          value={status}
          disabled={!editable || props.saving || props.deleting}
          onChange={(event) => setStatus(event.target.value as "candidate" | "active")}
          className="mt-1 w-full rounded-lg border border-[var(--chat-border)] bg-[var(--chat-surface)] px-3 py-2"
        >
          <option value="active">Active</option>
          <option value="candidate">Candidate</option>
        </select>
      </label>
      <label className="text-sm font-medium">
        Expires at
        <input
          aria-label="Expires at"
          type="datetime-local"
          value={expiresAt}
          disabled={!editable || props.saving || props.deleting}
          onChange={(event) => setExpiresAt(event.target.value)}
          className="mt-1 w-full rounded-lg border border-[var(--chat-border)] bg-[var(--chat-surface)] px-3 py-2"
        />
      </label>
      {props.mutationError ? <p role="alert" className="text-sm text-[var(--chat-danger)]">{props.mutationError}</p> : null}
      <div className="mt-auto flex flex-wrap gap-2">
        <button type="submit" disabled={!editable || props.saving || props.deleting || !content.trim()}>
          {props.saving ? "Saving…" : "Save memory"}
        </button>
        {!confirmDelete ? (
          <button type="button" disabled={props.saving || props.deleting} onClick={() => setConfirmDelete(true)}>Delete memory</button>
        ) : (
          <>
            <button type="button" disabled={props.deleting} onClick={() => void props.onDelete()}>
              {props.deleting ? "Deleting…" : "Confirm delete"}
            </button>
            <button type="button" disabled={props.deleting} onClick={() => setConfirmDelete(false)}>Cancel</button>
          </>
        )}
      </div>
    </form>
  );
}
```

- [ ] **Step 6: Recompose MemoryPanel**

Change props to:

```ts
export function MemoryPanel({
  token,
  currentConversationId,
  onOpenSidebar,
}: {
  token: string | null;
  currentConversationId: string | null;
  onOpenSidebar: () => void;
})
```

Call `useMemories({ token, currentConversationId })` once. Render:

```tsx
<section aria-label="Memories" className="flex min-h-0 flex-1 flex-col bg-[var(--chat-page)]">
  <header className="flex h-14 items-center gap-3 border-b border-[var(--chat-border)] px-4 md:px-6">
    <button
      type="button"
      aria-label="Open conversations"
      onClick={onOpenSidebar}
      className="rounded-lg px-2 py-2 lg:hidden"
    >
      ☰
    </button>
    <h1 className="text-lg font-semibold">Memories</h1>
    <button type="button" onClick={() => void memories.refresh()} disabled={memories.loading} className="ml-auto">Refresh</button>
  </header>
  <MemoryFilters
    status={memories.status}
    memoryType={memories.memoryType}
    scope={memories.scope}
    hasCurrentConversation={Boolean(currentConversationId)}
    onStatusChange={memories.setStatus}
    onMemoryTypeChange={memories.setMemoryType}
    onScopeChange={memories.setScope}
  />
  <div className="grid min-h-0 flex-1 md:grid-cols-[minmax(240px,320px)_minmax(0,1fr)]">
    <MemoryList
      items={memories.items}
      selectedMemoryId={memories.selectedMemoryId}
      loading={memories.loading}
      error={memories.error}
      hasMore={memories.hasMore}
      onSelect={(memoryId) => void memories.selectMemory(memoryId)}
      onRetry={() => void memories.refresh()}
      onLoadMore={() => void memories.loadMore()}
    />
    <div className="min-h-0 border-t border-[var(--chat-border)] md:border-l md:border-t-0">
      <MemoryDetailEditor
        memory={memories.detail}
        loading={memories.detailLoading}
        error={memories.detailError}
        saving={memories.pendingAction?.kind === "save"}
        deleting={memories.pendingAction?.kind === "delete"}
        mutationError={memories.mutationError}
        onRetry={async () => {
          if (memories.selectedMemoryId) {
            await memories.selectMemory(memories.selectedMemoryId);
          }
        }}
        onSave={async (request) => Boolean(memories.selectedMemoryId && await memories.updateMemory(memories.selectedMemoryId, request))}
        onDelete={async () => Boolean(memories.selectedMemoryId && await memories.deleteMemory(memories.selectedMemoryId))}
      />
    </div>
  </div>
</section>
```

Remove all `window.confirm` usage and the old inline edit UI.

- [ ] **Step 7: Pass the current Conversation from ChatbotShell**

Change the MemoryPanel call to:

```tsx
<MemoryPanel
  token={token}
  currentConversationId={conversations.selectedConversationId}
  onOpenSidebar={() => setSidebarOpen(true)}
/>
```

Update MemoryPanel mocks in `chatbot-workspace.test.tsx` and controller mocks in `memory-panel.test.tsx` to include the Task 10 return fields. In every real `MemoryPanel` test render pass `currentConversationId="conv-1"` and `onOpenSidebar={vi.fn()}`. Add a test that clicks the “Open conversations” button and observes that callback; this keeps Memories navigable on tablet/mobile after the drawer closes.

- [ ] **Step 8: Run Memory workspace, shell, and type checks**

```powershell
npm test -- features/chatbot/__tests__/memory-detail-editor.test.tsx features/chatbot/__tests__/memory-panel.test.tsx features/chatbot/__tests__/use-memories.test.tsx features/chatbot/__tests__/chatbot-workspace.test.tsx
npx tsc --noEmit --incremental false
```

Expected: all selected tests PASS and TypeScript exits 0.

- [ ] **Step 9: Commit the Memory UI**

```powershell
git add frontend/features/chatbot/components/memory-filters.tsx frontend/features/chatbot/components/memory-list.tsx frontend/features/chatbot/components/memory-detail-editor.tsx frontend/features/chatbot/components/memory-panel.tsx frontend/features/chatbot/components/chatbot-shell.tsx frontend/features/chatbot/__tests__/memory-detail-editor.test.tsx frontend/features/chatbot/__tests__/memory-panel.test.tsx frontend/features/chatbot/__tests__/chatbot-workspace.test.tsx
git diff --cached --check
git commit -m "feat(chatbot): build memory management workspace"
```

---

### Task 12: Finalize Theme, Accessibility, Motion, and Regression Gates

**Files:**
- Modify: `frontend/app/globals.css`
- Modify: `frontend/features/chatbot/components/chatbot-shell.tsx`
- Modify: `frontend/features/chatbot/components/chat-conversation-panel.tsx`
- Modify: `frontend/features/chatbot/__tests__/chatbot-workspace.test.tsx`
- Modify: `frontend/features/chatbot/__tests__/chat-composer.test.tsx`

**Interfaces:**
- Consumes: the component boundaries and semantic controls completed in Tasks 4–11.
- Produces:
  - chatbot-scoped light/dark design tokens.
  - safe-area-aware Composer dock.
  - consistent focus, disabled, and reduced-motion behavior.
  - a full-height workspace contract at 360 px, 768 px, and 1440 px widths.
- Does not introduce global chatbot state, new requests, new routes, new dependencies, upload controls, mode controls, or model switching.

- [ ] **Step 1: Add the final workspace and unsupported-control assertions**

In the outer skeleton returned by the `ChatbotShellContent` mock fixture test, target a stable shell test id. Extend `chatbot-workspace.test.tsx` with:

```tsx
it("renders the full-height themed workspace contract", () => {
  render(<ChatbotShell />);

  expect(screen.getByTestId("chatbot-shell")).toHaveClass(
    "chatbot-theme",
    "h-full",
    "min-h-0",
    "overflow-hidden"
  );
  expect(screen.getByRole("main")).toHaveClass(
    "min-h-0",
    "min-w-0",
    "flex-1"
  );
});
```

Extend `chat-composer.test.tsx`:

```tsx
it("does not expose unsupported upload or mode controls", () => {
  render(
    <ChatComposer
      value=""
      model="deepseek-chat"
      onChange={vi.fn()}
      onSubmit={vi.fn()}
    />
  );

  expect(screen.queryByRole("button", { name: /upload/i })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /deep think/i })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /search web/i })).not.toBeInTheDocument();
  expect(screen.getByText("deepseek-chat")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the targeted tests and confirm the missing shell marker**

Run from `frontend/`:

```powershell
npm test -- features/chatbot/__tests__/chatbot-workspace.test.tsx features/chatbot/__tests__/chat-composer.test.tsx
```

Expected: the workspace test FAILS because `data-testid="chatbot-shell"` has not been added; the unsupported-control assertion already passes.

- [ ] **Step 3: Add chatbot-scoped light/dark tokens and state styles**

Append to `frontend/app/globals.css`:

```css
.chatbot-theme {
  --chat-page: #ffffff;
  --chat-sidebar: #f5f6f7;
  --chat-surface: #ffffff;
  --chat-subtle: #f4f5f6;
  --chat-text: #24262a;
  --chat-muted: #6b7280;
  --chat-border: #e4e6e9;
  --chat-accent: #2d6f73;
  --chat-danger: #b65f3b;
  --chat-code-bg: #f7f8fa;
  color: var(--chat-text);
  color-scheme: light;
}

.chatbot-theme :where(button, a, input, textarea, select):focus-visible {
  outline: 2px solid var(--chat-accent);
  outline-offset: 2px;
}

.chatbot-theme :where(button, input, textarea, select):disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.chatbot-theme :where(button, a) {
  transition:
    color 150ms ease,
    background-color 150ms ease,
    border-color 150ms ease,
    opacity 150ms ease;
}

.chatbot-composer-dock {
  padding-bottom: max(12px, env(safe-area-inset-bottom));
}

@media (prefers-color-scheme: dark) {
  .chatbot-theme {
    --chat-page: #171819;
    --chat-sidebar: #111213;
    --chat-surface: #212326;
    --chat-subtle: #292b2f;
    --chat-text: #eceef1;
    --chat-muted: #a5aab3;
    --chat-border: #35383d;
    --chat-accent: #73b6bb;
    --chat-danger: #e58c68;
    --chat-code-bg: #111315;
    color-scheme: dark;
  }
}

@media (prefers-reduced-motion: reduce) {
  .chatbot-theme *,
  .chatbot-theme *::before,
  .chatbot-theme *::after {
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}
```

These selectors remain under `.chatbot-theme` so the portfolio/home styling and its existing global background are unchanged.

- [ ] **Step 4: Mark the shell and add the safe-area Composer dock**

Change the Task 5 outer shell opening tag to:

```tsx
<div
  data-testid="chatbot-shell"
  className="chatbot-theme flex h-full min-h-0 overflow-hidden bg-[var(--chat-page)]"
>
```

In `chat-conversation-panel.tsx`, wrap the Task 9 `ChatComposer` call without changing its props:

```tsx
<div className="chatbot-composer-dock shrink-0 border-t border-[var(--chat-border)] bg-[var(--chat-page)] px-3 pt-3 md:px-6 lg:px-8">
  <ChatComposer
    value={messages.draft}
    model={conversation.model}
    disabled={!canSend}
    sending={generationActive}
    stopping={
      Boolean(activeAssistantMessageId) &&
      messages.stoppingMessageId === activeAssistantMessageId
    }
    error={
      conversation.status !== "active"
        ? "Archived conversations are read-only."
        : messages.controlError ?? messages.streamError
    }
    onChange={messages.setDraft}
    onSubmit={(content) => void messages.sendMessage(content)}
    onStop={
      generationActive
        ? () => void messages.stopGeneration(activeAssistantMessageId)
        : undefined
    }
  />
</div>
```

Do not make the Composer `fixed` or `sticky`. It stays in the panel's flex column so the MessageList remains the only scrolling chat region and mobile safe-area padding does not overlap content.

- [ ] **Step 5: Audit semantic and motion behavior**

Verify in the touched components:

- Every icon-only button has an `aria-label`: mobile menu, drawer close, sidebar collapse, row menu, copy, Send, and Stop.
- Loading text that changes asynchronously uses `role="status"` or an accessible label without moving focus.
- Errors use `role="alert"` and retain an adjacent retry action when retry is possible.
- Framer Motion is used only for sidebar width/drawer opacity/translation, and `useReducedMotion` makes transition duration zero.
- No `AnimatePresence mode="popLayout"`, spring layout animation, or MessageList item layout animation is added.
- The dark theme changes tokens only; semantic hierarchy, borders, code contrast, and disabled states remain visible.

- [ ] **Step 6: Run the complete frontend verification**

Run from `frontend/`:

```powershell
npm test
npm run lint
npx tsc --noEmit --incremental false
npm run build
```

Expected:

- all Vitest files PASS.
- ESLint exits 0 with no new warnings.
- TypeScript exits 0.
- Next.js production build exits 0 and still emits the existing `/chat-bot` route.

- [ ] **Step 7: Re-run backend contract regression without changing backend**

Run from the repository root:

```powershell
uv run pytest backend/tests/chatbot/test_conversation_api.py backend/tests/chatbot/test_memory_api.py backend/tests/chatbot/test_stream_api.py backend/tests/chatbot/test_generation_controls.py -q
```

Expected: all selected FastAPI contract tests PASS. If a backend test fails, diagnose the mismatch; do not edit `backend/**` or change the contract in this frontend plan.

- [ ] **Step 8: Perform the responsive and interaction acceptance pass**

Run from `frontend/`:

```powershell
npm run dev
```

Open `/chat-bot` with a valid login and verify:

| Viewport | Acceptance criteria |
| --- | --- |
| 1440 × 900 | Sidebar is 280 px expanded/64 px collapsed; main content has no page-level horizontal scroll; assistant text and Composer are both capped at `max-w-3xl`; only MessageList scrolls. |
| 768 × 1024 | Sidebar is a drawer; overlay click and Escape close it; changing view or selecting a Conversation closes it; the centered reading column remains within the viewport. |
| 360 × 800 | No clipped actions or horizontal page scroll; user bubbles remain at most 86%; Composer stays visible above the soft keyboard; safe-area padding is present; textarea grows to 168 px then scrolls internally. |
| Light/dark | Page, sidebar, surface, code blocks, border, muted text, focus ring, danger, disabled, and hover states remain distinguishable. |

Then exercise this sequence without reloading:

1. Switch rapidly from Conversation A to B while A detail/history is still loading; only B remains selected.
2. Send a message, observe token streaming, scroll upward, and confirm the viewport does not pull back to the bottom.
3. Use “Back to bottom”; only this explicit action scrolls smoothly.
4. Stop an active generation; confirm Send replaces Stop after completion/cancellation.
5. Switch to Memories, filter by type/current Conversation, open two details rapidly, edit one, and delete only after inline confirmation.
6. Switch back to Chat; Conversation and cached messages remain intact and no duplicate list/detail request appears in the network panel.
7. Refresh `/chat-bot?conversation=<id>`; hydration completes without a React mismatch and the URL-selected Conversation wins.

Stop the dev server after the pass.

- [ ] **Step 9: Inspect the final diff and commit the theme/regression gate**

Run from the repository root:

```powershell
git diff --check
git status --short
git diff --stat
git diff -- frontend/app/globals.css frontend/features/chatbot
```

Confirm:

- `backend/**`、route names、AuthProvider/RouteGuard behavior and dependencies are unchanged.
- no upload, model-switch, deep-thinking, web-search, citation, or new API code exists.
- each data controller is still called once at its intended boundary.
- no unrelated user changes are staged.

Then commit only this task:

```powershell
git add frontend/app/globals.css frontend/features/chatbot/components/chatbot-shell.tsx frontend/features/chatbot/components/chat-conversation-panel.tsx frontend/features/chatbot/__tests__/chatbot-workspace.test.tsx frontend/features/chatbot/__tests__/chat-composer.test.tsx
git diff --cached --check
git commit -m "style(chatbot): finalize responsive chat theme"
```

---

## Completion Criteria

The implementation is complete only when all of the following are true:

- The 16-route contract tests in `api-client.test.ts`, `stream-api.test.ts`, and `memory-api.test.ts` pass.
- Conversation/detail/history/Memory race tests pass and stale requests cannot replace current state.
- Send, Retry, Regenerate, Stop, archive, restore, rename, delete, Memory filters/detail/update/delete all have reachable UI actions.
- File upload, model switching, deep thinking, web search, citation UI, copied branding, and copied product language are absent.
- `/chat-bot` is full-height and isolated from the normal SiteNav/page padding while all other routes keep the existing shell.
- Desktop, tablet, mobile, dark mode, reduced motion, soft-keyboard, loading/error/empty/disabled, and scroll acceptance checks pass.
- `npm test`、`npm run lint`、`npx tsc --noEmit --incremental false`、`npm run build` and the selected backend contract suite all exit 0.
- The final diff contains no changes under `backend/**` and no dependency/route changes.
