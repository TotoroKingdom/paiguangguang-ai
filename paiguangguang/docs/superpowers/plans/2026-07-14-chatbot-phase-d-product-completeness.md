# Chatbot Phase D Product Completeness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成缺陷 10 的自动标题、Memory UI、功能开关、logout 清理、滚动体验和用户/运维文档。

**Architecture:** 自动标题继续走 Phase B durable job；Memory UI 作为独立 frontend feature slice 接入现有 API；功能开关在后端 router 和前端导航/页面双重控制；用户变化通过 Chatbot store 的 storage-key 生命周期清理所有会话缓存和 reader。

**Tech Stack:** FastAPI/SQLAlchemy/pytest、Next.js 14/React/TypeScript/Vitest/Testing Library、sessionStorage。

## Global Constraints

- 自动标题只能 CAS 更新 `title_source='default'`，绝不覆盖 manual。
- Memory UI 只访问当前 JWT 用户资源，不支持 deleted memory 列表或跨用户操作。
- `CHATBOT_ENABLED=false` 时后端返回稳定 503；`NEXT_PUBLIC_CHATBOT_ENABLED=false` 时前端不展示入口且页面 404。
- 匿名状态不持久化 Chatbot store；logout 删除上一用户 storage key。
- 用户离底超过 120px 时新 delta 不得修改 scrollTop。
- 不增加新的前端状态库。

---

## File Map

- Modify: `backend/tests/chatbot/test_completion_jobs.py` — 自动标题 CAS/race 验收。
- Create: `frontend/features/chatbot/types/memory.ts` — Memory DTO。
- Create: `frontend/features/chatbot/api/memories.ts` — Memory API client。
- Create: `frontend/features/chatbot/hooks/use-memories.ts` — filter/cursor/update/delete state。
- Create: `frontend/features/chatbot/components/memory-panel.tsx` — Memory 管理 UI。
- Modify: `frontend/features/chatbot/components/chatbot-shell.tsx` — Chat/Memories 视图。
- Create: `frontend/features/chatbot/__tests__/memory-panel.test.tsx`、`use-memories.test.tsx`。
- Modify: `backend/app/core/config.py`、`backend/app/chatbot/api/dependencies.py`、`backend/app/chatbot/api/router.py`、`backend/.env.example` — 后端开关。
- Create: `frontend/lib/features.ts`。
- Modify: `frontend/components/site-nav.tsx`、`frontend/app/chat-bot/page.tsx`、`frontend/app/chat-bot/page.test.tsx` — 前端开关。
- Create: `frontend/components/site-nav.test.tsx` — 关闭时隐藏导航入口。
- Modify: `frontend/features/chatbot/stores/chatbot-store.tsx`、`frontend/features/chatbot/components/chatbot-shell.tsx` — logout/storage 清理。
- Create: `frontend/features/chatbot/__tests__/chatbot-store.test.tsx`。
- Modify: `frontend/features/chatbot/components/message-list.tsx`、`frontend/features/chatbot/__tests__/message-list.test.tsx` — near-bottom 滚动。
- Modify: `README.md` — 开关、worker、清理、降级和验收命令。

### Task 1: 验收自动标题 durable job 和 manual-wins 竞态

**Files:**
- Modify: `backend/tests/chatbot/test_completion_jobs.py`
- Modify: `backend/app/chatbot/services/completion_jobs.py` only if Phase B implementation does not satisfy the test.

**Interfaces:**
- Consumes: `ConversationTitleService.derive_title`、`apply_auto_title`。
- Produces: 首轮用户消息压缩空白并截断 60 字符；manual title CAS 不受影响。

- [ ] **Step 1: 添加 default 标题更新测试**

先把 Phase B 创建的 `_seed_completed_turn` helper 增加参数 `user_content: str = "hello"`，创建 user message 时使用该参数；其他返回值和 fixture 行为保持不变。然后在 `test_completion_jobs.py` 增加：

```python
def test_auto_title_uses_first_user_message(tmp_path) -> None:
    factory, owner_id, conversation_id, user_message_id, assistant_message_id = _seed_completed_turn(
        tmp_path,
        user_content="  Design   a durable chatbot worker with retries  ",
    )
    service = ConversationTitleService(factory)
    changed = service.apply_auto_title(
        {
            "user_id": owner_id,
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
        }
    )
    assert changed is True
    with factory() as session:
        row = session.get(ChatbotConversation, conversation_id)
    assert row is not None
    assert row.title == "Design a durable chatbot worker with retries"
    assert row.title_source == "auto"
```

- [ ] **Step 2: 添加 manual-wins 竞态测试**

```python
def test_auto_title_never_overwrites_manual_title(tmp_path) -> None:
    factory, owner_id, conversation_id, user_message_id, assistant_message_id = _seed_completed_turn(tmp_path)
    with factory() as session:
        row = session.get(ChatbotConversation, conversation_id)
        row.title = "My manual title"
        row.title_source = "manual"
        session.commit()

    changed = ConversationTitleService(factory).apply_auto_title(
        {
            "user_id": owner_id,
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
        }
    )
    assert changed is False
    with factory() as session:
        row = session.get(ChatbotConversation, conversation_id)
    assert row.title == "My manual title"
    assert row.title_source == "manual"
```

- [ ] **Step 3: 运行测试；只在失败时修正 CAS**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_completion_jobs.py -q
```

Expected: PASS。若失败，确保更新 SQL 同时过滤 conversation ID、user ID、`title_source == "default"` 和 `deleted_at IS NULL`。

- [ ] **Step 4: 有修正时提交**

```powershell
git add backend/app/chatbot/services/completion_jobs.py backend/tests/chatbot/test_completion_jobs.py
git commit -m "test(chatbot): enforce manual title precedence"
```

无实现修正时仍可提交新增验收测试；不要创建空 commit。

### Task 2: 实现 Memory API client 和 state hook

**Files:**
- Create: `frontend/features/chatbot/types/memory.ts`
- Create: `frontend/features/chatbot/api/memories.ts`
- Create: `frontend/features/chatbot/hooks/use-memories.ts`
- Create: `frontend/features/chatbot/__tests__/use-memories.test.tsx`

**Interfaces:**
- Produces: `MemoryStatus = "candidate" | "active" | "superseded"`。
- Produces: `listMemories`、`updateMemory`、`deleteMemory`。
- Produces: `useMemories({ token })`，暴露 status/items/loading/error/hasMore/loadMore/update/delete。
- Consumes: Phase A `CHATBOT_API_BASE`。

- [ ] **Step 1: 写 hook 的筛选、更新和删除失败测试**

创建 `use-memories.test.tsx`，注入 client：

```tsx
const client = {
  listMemories: vi.fn().mockResolvedValue({
    items: [makeMemory("memory-1")],
    next_cursor: null,
    has_more: false,
  }),
  updateMemory: vi.fn().mockResolvedValue(makeMemory("memory-1", { content: "updated" })),
  deleteMemory: vi.fn().mockResolvedValue({
    id: "memory-1",
    status: "deleted",
    cleanup_status: "pending",
  }),
};

const { result } = renderHook(() => useMemories({ token: "token", client }));
await waitFor(() => expect(result.current.items).toHaveLength(1));
expect(client.listMemories).toHaveBeenCalledWith({
  token: "token",
  status: "active",
  cursor: null,
  limit: 20,
});

await act(async () => {
  await result.current.updateMemory("memory-1", { content: "updated" });
});
expect(result.current.items[0].content).toBe("updated");

await act(async () => {
  await result.current.deleteMemory("memory-1");
});
expect(result.current.items).toEqual([]);
```

- [ ] **Step 2: 运行测试确认模块不存在**

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/use-memories.test.tsx
```

Expected: collection ERROR。

- [ ] **Step 3: 创建 Memory types 和 client**

`types/memory.ts`：

```ts
export type MemoryStatus = "candidate" | "active" | "superseded";
export type MemoryType =
  | "preference"
  | "goal"
  | "project_context"
  | "explicit"
  | "fact"
  | "work_context";

export type MemoryData = {
  id: string;
  conversation_id: string | null;
  memory_type: MemoryType;
  content: string;
  importance: number;
  confidence: number;
  source_message_ids: string[];
  status: MemoryStatus;
  last_accessed_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
};

export type MemoryPageData = {
  items: MemoryData[];
  next_cursor: string | null;
  has_more: boolean;
};

export type MemoryUpdateRequest = {
  content?: string;
  status?: Extract<MemoryStatus, "candidate" | "active">;
  expires_at?: string | null;
};
```

`api/memories.ts` 使用统一 base：

```ts
import { deleteJson, getJson, patchJson } from "@/lib/api";
import { CHATBOT_API_BASE } from "./client";
import type { DeleteResultData } from "../types/conversation";
import type { MemoryData, MemoryPageData, MemoryStatus, MemoryUpdateRequest } from "../types/memory";

export const memoryApiClient = {
  listMemories(options: { token: string | null; status: MemoryStatus; cursor: string | null; limit: number }) {
    const query = new URLSearchParams({ status: options.status, limit: String(options.limit) });
    if (options.cursor) query.set("cursor", options.cursor);
    return getJson<MemoryPageData>(`${CHATBOT_API_BASE}/memories?${query}`, { token: options.token });
  },
  updateMemory(options: { token: string | null; memoryId: string }, request: MemoryUpdateRequest) {
    return patchJson<MemoryData, MemoryUpdateRequest>(
      `${CHATBOT_API_BASE}/memories/${options.memoryId}`,
      request,
      { token: options.token }
    );
  },
  deleteMemory(options: { token: string | null; memoryId: string }) {
    return deleteJson<DeleteResultData>(`${CHATBOT_API_BASE}/memories/${options.memoryId}`, {
      token: options.token,
    });
  },
};

export type MemoryApiClient = typeof memoryApiClient;
```

- [ ] **Step 4: 实现 useMemories**

`use-memories.ts` 使用局部 state，不写入 Chatbot Conversation store。核心行为：

```ts
"use client";

import { useCallback, useEffect, useState } from "react";
import { memoryApiClient, type MemoryApiClient } from "../api/memories";
import type { MemoryData, MemoryStatus, MemoryUpdateRequest } from "../types/memory";

type Options = {
  token: string | null;
  client?: MemoryApiClient;
  pageSize?: number;
};

export function useMemories({ token, client = memoryApiClient, pageSize = 20 }: Options) {
  const [status, setStatusState] = useState<MemoryStatus>("active");
  const [items, setItems] = useState<MemoryData[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (cursor: string | null = null, append = false) => {
    if (!token) return null;
    setLoading(true);
    setError(null);
    try {
      const page = await client.listMemories({ token, status, cursor, limit: pageSize });
      setItems((current) => append ? [...current, ...page.items] : page.items);
      setNextCursor(page.next_cursor);
      setHasMore(page.has_more);
      return page;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load memories.");
      return null;
    } finally {
      setLoading(false);
    }
  }, [client, pageSize, status, token]);

  useEffect(() => { void load(null, false); }, [load]);

  const setStatus = useCallback((next: MemoryStatus) => {
    setStatusState(next);
    setItems([]);
    setNextCursor(null);
    setHasMore(false);
  }, []);

  const updateMemory = useCallback(async (memoryId: string, request: MemoryUpdateRequest) => {
    if (!token) return null;
    setError(null);
    try {
      const updated = await client.updateMemory({ token, memoryId }, request);
      setItems((current) =>
        updated.status === status
          ? current.map((item) => item.id === memoryId ? updated : item)
          : current.filter((item) => item.id !== memoryId)
      );
      return updated;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to update memory.");
      return null;
    }
  }, [client, status, token]);

  const deleteMemory = useCallback(async (memoryId: string) => {
    if (!token) return false;
    setError(null);
    try {
      await client.deleteMemory({ token, memoryId });
      setItems((current) => current.filter((item) => item.id !== memoryId));
      return true;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to delete memory.");
      return false;
    }
  }, [client, token]);

  const loadMore = useCallback(() => {
    if (!hasMore || !nextCursor) return Promise.resolve(null);
    return load(nextCursor, true);
  }, [hasMore, load, nextCursor]);

  return {
    status,
    setStatus,
    items,
    loading,
    error,
    hasMore,
    loadMore,
    updateMemory,
    deleteMemory,
    refresh: () => load(null, false),
  };
}
```

- [ ] **Step 5: 运行 hook 测试并提交**

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/use-memories.test.tsx
```

Expected: PASS。

```powershell
Set-Location ..
git add frontend/features/chatbot/types/memory.ts frontend/features/chatbot/api/memories.ts frontend/features/chatbot/hooks/use-memories.ts frontend/features/chatbot/__tests__/use-memories.test.tsx
git commit -m "feat(chatbot): add memory management client"
```

### Task 3: 添加 Memory 管理 UI

**Files:**
- Create: `frontend/features/chatbot/components/memory-panel.tsx`
- Modify: `frontend/features/chatbot/components/chatbot-shell.tsx`
- Create: `frontend/features/chatbot/__tests__/memory-panel.test.tsx`

**Interfaces:**
- Consumes: `useMemories({ token })`。
- Produces: Chat/Memories 两种 workspace view；Memory 支持筛选、编辑、activate/candidate、删除和 load more。

- [ ] **Step 1: 写 MemoryPanel 交互失败测试**

Mock `useMemories`，render panel 后断言三个 filter button、memory 内容、Edit/Delete，并验证：

```tsx
fireEvent.click(screen.getByRole("button", { name: "Candidate" }));
expect(setStatus).toHaveBeenCalledWith("candidate");

fireEvent.click(screen.getByRole("button", { name: "Edit" }));
fireEvent.change(screen.getByRole("textbox", { name: "Memory content" }), {
  target: { value: "Updated memory" },
});
fireEvent.click(screen.getByRole("button", { name: "Save" }));
expect(updateMemory).toHaveBeenCalledWith("memory-1", { content: "Updated memory" });

fireEvent.click(screen.getByRole("button", { name: "Delete" }));
expect(deleteMemory).toHaveBeenCalledWith("memory-1");
```

- [ ] **Step 2: 运行测试确认组件不存在**

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/memory-panel.test.tsx
```

Expected: collection ERROR。

- [ ] **Step 3: 实现 MemoryPanel**

组件要求：

- 顶部 button：Active、Candidate、Superseded，映射到 `setStatus`。
- 每条 memory 展示 `memory_type`、confidence、content、updated_at。
- Edit 后使用本地 `editingId`/`editingContent` 显示带 `aria-label="Memory content"` 的 textarea。
- Save 调 `updateMemory(id, { content: editingContent.trim() })`，成功后退出编辑。
- candidate 显示 Activate，调用 `{ status: "active" }`；active 显示 Move to candidate。
- Delete 先 `window.confirm`，再调用 hook delete。
- loading/error/empty/load-more 都有明确状态。

不要把 Memory 正文写入 sessionStorage。

组件的状态和事件处理使用以下实现；className 可沿用现有 `paper/ink/tide/clay` 设计 token，但不得改变行为和 aria label：

```tsx
"use client";

import { useState } from "react";
import { useMemories } from "../hooks/use-memories";
import type { MemoryData, MemoryStatus } from "../types/memory";

const FILTERS: Array<{ status: MemoryStatus; label: string }> = [
  { status: "active", label: "Active" },
  { status: "candidate", label: "Candidate" },
  { status: "superseded", label: "Superseded" },
];

export function MemoryPanel({ token }: { token: string | null }) {
  const memories = useMemories({ token });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState("");

  function beginEdit(memory: MemoryData) {
    setEditingId(memory.id);
    setEditingContent(memory.content);
  }

  async function save(memoryId: string) {
    const content = editingContent.trim();
    if (!content) return;
    const updated = await memories.updateMemory(memoryId, { content });
    if (updated) {
      setEditingId(null);
      setEditingContent("");
    }
  }

  async function remove(memory: MemoryData) {
    if (!window.confirm(`Delete memory "${memory.content.slice(0, 40)}"?`)) return;
    await memories.deleteMemory(memory.id);
  }

  return (
    <section aria-label="Memories" className="rounded-2xl border border-ink/10 bg-white/80 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-2xl font-semibold text-ink">Memories</h2>
        <button type="button" onClick={() => void memories.refresh()}>Refresh</button>
      </div>
      <div className="mt-4 flex gap-2">
        {FILTERS.map((filter) => (
          <button
            key={filter.status}
            type="button"
            aria-pressed={memories.status === filter.status}
            onClick={() => memories.setStatus(filter.status)}
          >
            {filter.label}
          </button>
        ))}
      </div>
      {memories.error ? <p role="alert">{memories.error}</p> : null}
      {!memories.loading && memories.items.length === 0 ? <p>No memories.</p> : null}
      <div className="mt-4 space-y-3">
        {memories.items.map((memory) => (
          <article key={memory.id} className="rounded-xl border border-ink/10 p-4">
            <p>{memory.memory_type} · confidence {memory.confidence.toFixed(2)}</p>
            {editingId === memory.id ? (
              <>
                <textarea
                  aria-label="Memory content"
                  value={editingContent}
                  onChange={(event) => setEditingContent(event.target.value)}
                />
                <button type="button" onClick={() => void save(memory.id)}>Save</button>
                <button type="button" onClick={() => setEditingId(null)}>Cancel</button>
              </>
            ) : (
              <p>{memory.content}</p>
            )}
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" onClick={() => beginEdit(memory)}>Edit</button>
              {memory.status === "candidate" ? (
                <button
                  type="button"
                  onClick={() => void memories.updateMemory(memory.id, { status: "active" })}
                >
                  Activate
                </button>
              ) : null}
              {memory.status === "active" ? (
                <button
                  type="button"
                  onClick={() => void memories.updateMemory(memory.id, { status: "candidate" })}
                >
                  Move to candidate
                </button>
              ) : null}
              <button type="button" onClick={() => void remove(memory)}>Delete</button>
            </div>
          </article>
        ))}
      </div>
      {memories.hasMore ? (
        <button type="button" onClick={() => void memories.loadMore()}>Load more</button>
      ) : null}
      {memories.loading ? <p>Loading memories…</p> : null}
    </section>
  );
}
```

- [ ] **Step 4: 在 ChatbotShell 增加视图切换**

`ChatbotShellContent` 增加：

```tsx
const [view, setView] = useState<"chat" | "memories">("chat");
```

在现有 grid 前添加两个 button。`view === "memories"` 时只 render：

```tsx
<MemoryPanel token={token} />
```

`view === "chat"` 时 render 原 ConversationSidebar + ChatConversationPanel grid。切换 view 不改变 URL conversation 参数。

- [ ] **Step 5: 运行 UI tests 并提交**

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/memory-panel.test.tsx features/chatbot/__tests__/chatbot-workspace.test.tsx
```

Expected: PASS。

```powershell
Set-Location ..
git add frontend/features/chatbot/components/memory-panel.tsx frontend/features/chatbot/components/chatbot-shell.tsx frontend/features/chatbot/__tests__/memory-panel.test.tsx frontend/features/chatbot/__tests__/chatbot-workspace.test.tsx
git commit -m "feat(chatbot): add memory management workspace"
```

### Task 4: 增加前后端 Chatbot feature flag

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/chatbot/api/dependencies.py`
- Modify: `backend/app/chatbot/api/router.py`
- Modify: `backend/.env.example`
- Modify: `backend/tests/chatbot/test_conversation_api.py`
- Create: `frontend/lib/features.ts`
- Modify: `frontend/components/site-nav.tsx`
- Modify: `frontend/app/chat-bot/page.tsx`
- Modify: `frontend/app/chat-bot/page.test.tsx`
- Create: `frontend/components/site-nav.test.tsx`

**Interfaces:**
- Produces: `Settings.chatbot_enabled: bool = True`。
- Produces: `require_chatbot_enabled(settings=Depends(get_settings))`。
- Produces: `isChatbotEnabled(value?: string) -> boolean`。

- [ ] **Step 1: 写后端关闭时 503 的失败测试**

在 API test app 中 override `get_settings`：

```python
app.dependency_overrides[get_settings] = lambda: Settings(chatbot_enabled=False)
response = client.get("/api/v1/chatbot/conversations", headers=owner_headers)
assert response.status_code == 503
assert response.json()["error"]["code"] == "CHATBOT_DISABLED"
```

- [ ] **Step 2: 写前端 flag helper/page/nav 失败测试**

`page.test.tsx` mock `next/navigation.notFound`，分别传 `"false"` 和 `"true"` 测 `isChatbotEnabled`；关闭时 `notFound` 被调用。

创建 `frontend/components/site-nav.test.tsx`，mock `useAuth` 和 `usePathname`，在 `vi.stubEnv("NEXT_PUBLIC_CHATBOT_ENABLED", "false")` 后动态 import `SiteNav`，断言：

```tsx
render(<SiteNav />);
expect(screen.queryByRole("link", { name: "Chatbot" })).not.toBeInTheDocument();
expect(screen.getByRole("link", { name: "Knowledge" })).toBeInTheDocument();
```

每个测试后执行 `vi.unstubAllEnvs()` 和 `vi.resetModules()`，避免模块环境缓存污染其他测试。

- [ ] **Step 3: 运行测试确认开关不存在**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_conversation_api.py -q
Set-Location frontend
npm test -- app/chat-bot/page.test.tsx components/site-nav.test.tsx
```

Expected: FAIL。

- [ ] **Step 4: 实现后端 flag dependency**

Settings/get_settings：

```python
chatbot_enabled: bool = True
chatbot_enabled=_parse_bool(os.getenv("CHATBOT_ENABLED"), default=True),
```

`api/dependencies.py`：

```python
from fastapi import Depends
from app.chatbot.errors import ChatbotApiError
from app.core.config import Settings, get_settings

def require_chatbot_enabled(settings: Settings = Depends(get_settings)) -> None:
    if not settings.chatbot_enabled:
        raise ChatbotApiError(
            status_code=503,
            code="CHATBOT_DISABLED",
            message="Chatbot is temporarily unavailable",
        )
```

`api/router.py`：

```python
router = APIRouter(
    prefix="/api/v1/chatbot",
    tags=["chatbot"],
    dependencies=[Depends(require_chatbot_enabled)],
)
```

`.env.example` 增加 `CHATBOT_ENABLED=true`。

- [ ] **Step 5: 实现前端 flag**

`frontend/lib/features.ts`：

```ts
export function isChatbotEnabled(value = process.env.NEXT_PUBLIC_CHATBOT_ENABLED) {
  return value?.trim().toLowerCase() !== "false";
}
```

`site-nav.tsx` 在组件内 filter：

```ts
const visibleNavItems = navItems.filter(
  (item) => item.href !== "/chat-bot" || isChatbotEnabled()
);
```

页面：

```tsx
import { notFound } from "next/navigation";
import { isChatbotEnabled } from "@/lib/features";

export default function ChatBotPage() {
  if (!isChatbotEnabled()) notFound();
  return (
    <div className="mx-auto w-full max-w-7xl">
      <ChatbotShell />
    </div>
  );
}
```

- [ ] **Step 6: 运行 flag tests 并提交**

```powershell
Set-Location ..
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_conversation_api.py -q
Set-Location frontend
npm test -- app/chat-bot/page.test.tsx components/site-nav.test.tsx
```

Expected: PASS。

```powershell
Set-Location ..
git add backend/app/core/config.py backend/app/chatbot/api/dependencies.py backend/app/chatbot/api/router.py backend/.env.example backend/tests/chatbot/test_conversation_api.py frontend/lib/features.ts frontend/components/site-nav.tsx frontend/components/site-nav.test.tsx frontend/app/chat-bot/page.tsx frontend/app/chat-bot/page.test.tsx
git commit -m "feat(chatbot): add frontend and backend feature flags"
```

### Task 5: Logout 时清除 reader、store 和用户 storage

**Files:**
- Modify: `frontend/features/chatbot/stores/chatbot-store.tsx`
- Modify: `frontend/features/chatbot/components/chatbot-shell.tsx`
- Create: `frontend/features/chatbot/__tests__/chatbot-store.test.tsx`
- Modify: `frontend/features/chatbot/__tests__/use-chat-stream.test.tsx`

**Interfaces:**
- Consumes: Phase A `useChatStream` 对 token 变化的 abort effect。
- Produces: storage key 从 user key 变为 null/另一用户时删除旧 key并 clear pages。
- Produces: anonymous 状态 `storageKey=null`，绝不写 anonymous snapshot。

- [ ] **Step 1: 写 storage key 变化清理失败测试**

创建一个 harness 暴露 store state，先以 `paiguangguang.chatbot:user-1` render 并 dispatch page，然后 rerender `storageKey={null}`：

```tsx
expect(sessionStorage.getItem("paiguangguang.chatbot:user-1")).not.toBeNull();
rerender(<Harness storageKey={null} />);
await waitFor(() => {
  expect(sessionStorage.getItem("paiguangguang.chatbot:user-1")).toBeNull();
  expect(screen.getByTestId("conversation-count")).toHaveTextContent("0");
});
expect(sessionStorage.getItem("paiguangguang.chatbot:anonymous")).toBeNull();
```

在 `use-chat-stream.test.tsx` 增加 token 从 `"token"` 变 null 后旧事件不分发、`onFailure` 不调用。

- [ ] **Step 2: 运行测试确认旧 user snapshot 保留**

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/chatbot-store.test.tsx features/chatbot/__tests__/use-chat-stream.test.tsx
```

Expected: FAIL。

- [ ] **Step 3: 实现 storage-key 生命周期清理**

在 `ChatbotStoreProvider` 增加：

```ts
const previousStorageKeyRef = useRef<string | null>(normalizedStorageKey);
const hydratedStorageKeyRef = useRef<string | null>(null);
```

同时把 React import 加上 `useRef`。

用以下完整 effect 替换现有 hydrate effect：

```ts
useEffect(() => {
  if (typeof window === "undefined") {
    setIsHydrated(true);
    return;
  }

  const previousKey = previousStorageKeyRef.current;
  hydratedStorageKeyRef.current = null;
  if (previousKey && previousKey !== normalizedStorageKey) {
    window.sessionStorage.removeItem(previousKey);
  }
  dispatch({ type: "clear_pages" });
  previousStorageKeyRef.current = normalizedStorageKey;

  if (!normalizedStorageKey) {
    setIsHydrated(true);
    return;
  }

  setIsHydrated(false);
  try {
    const raw = window.sessionStorage.getItem(normalizedStorageKey);
    if (raw) {
      const snapshot = JSON.parse(raw) as ChatbotStoreSnapshot;
      const normalized = normalizeSnapshot(snapshot);
      if (normalized) {
        dispatch({ type: "hydrate", state: normalized });
      } else {
        window.sessionStorage.removeItem(normalizedStorageKey);
      }
    }
  } catch {
    window.sessionStorage.removeItem(normalizedStorageKey);
  } finally {
    hydratedStorageKeyRef.current = normalizedStorageKey;
    setIsHydrated(true);
  }
}, [normalizedStorageKey]);
```

持久化 effect 使用额外 guard，防止 storage key 切换的同一 render 把上一用户 state 写入新 key：

```ts
if (
  !normalizedStorageKey ||
  typeof window === "undefined" ||
  !isHydrated ||
  hydratedStorageKeyRef.current !== normalizedStorageKey
) {
  return;
}
```

在 `ChatbotShell`：

```ts
const storageKey = user ? `paiguangguang.chatbot:${user.id}` : null;
```

不得再使用 `paiguangguang.chatbot:anonymous`。

- [ ] **Step 4: 运行 logout/storage tests 并提交**

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/chatbot-store.test.tsx features/chatbot/__tests__/use-chat-stream.test.tsx
```

Expected: PASS。

```powershell
Set-Location ..
git add frontend/features/chatbot/stores/chatbot-store.tsx frontend/features/chatbot/components/chatbot-shell.tsx frontend/features/chatbot/__tests__/chatbot-store.test.tsx frontend/features/chatbot/__tests__/use-chat-stream.test.tsx
git commit -m "fix(chatbot): clear user state on logout"
```

### Task 6: 修复 streaming 强制滚到底部

**Files:**
- Modify: `frontend/features/chatbot/components/message-list.tsx`
- Modify: `frontend/features/chatbot/__tests__/message-list.test.tsx`

**Interfaces:**
- Produces: 只有 `stickToBottomRef.current === true` 才自动滚动。
- Keeps: history prepend anchor 和 Back to bottom button。

- [ ] **Step 1: 写用户向上滚动后 delta 不拉回的失败测试**

在 `message-list.test.tsx` render 后取得 scroll container（建议给容器增加 `data-testid="message-scroll-container"`），定义布局属性：

```tsx
const sharedProps = {
  loadingHistory: false,
  historyError: null,
  hasMore: false,
  onLoadMore: vi.fn(),
  streamingMessageId: "msg-1",
};
const { rerender } = render(
  <MessageList
    messages={[makeMessage({ content: "first", status: "streaming" })]}
    {...sharedProps}
    streamPhase="streaming"
  />
);
const container = screen.getByTestId("message-scroll-container");
Object.defineProperties(container, {
  scrollHeight: { configurable: true, value: 1000 },
  clientHeight: { configurable: true, value: 300 },
  scrollTop: { configurable: true, writable: true, value: 200 },
});
fireEvent.scroll(container);
expect(screen.getByRole("button", { name: "Back to bottom" })).toBeInTheDocument();

rerender(
  <MessageList
    messages={[makeMessage({ content: "next delta", status: "streaming" })]}
    {...sharedProps}
    streamPhase="streaming"
    streamingMessageId="msg-1"
  />
);
expect(container.scrollTop).toBe(200);
```

- [ ] **Step 2: 运行测试确认 streaming 分支强制滚到 1000**

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/message-list.test.tsx
```

Expected: FAIL；`scrollTop` 被设为 `scrollHeight`。

- [ ] **Step 3: 删除强制 streaming 条件**

在 scroll container 加：

```tsx
data-testid="message-scroll-container"
```

将 layout effect：

```ts
if (stickToBottomRef.current || streamPhase === "streaming") {
```

改为：

```ts
if (stickToBottomRef.current) {
```

保留 effect 对 `[messages, streamPhase]` 的依赖；phase 改变时如果用户仍在底部，仍应跟随。

- [ ] **Step 4: 运行 MessageList tests 并提交**

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/message-list.test.tsx
```

Expected: PASS，包括历史 anchor、jump button 和 Markdown 现有测试。

```powershell
Set-Location ..
git add frontend/features/chatbot/components/message-list.tsx frontend/features/chatbot/__tests__/message-list.test.tsx
git commit -m "fix(chatbot): respect manual scroll position"
```

### Task 7: 更新文档并执行最终验收

**Files:**
- Modify: `README.md`

**Interfaces:**
- Produces: 可复制的环境变量、migration、worker、测试和回滚说明。

- [ ] **Step 1: 更新 README Chatbot 部分**

必须写明：

```text
API base: /api/v1/chatbot
CHATBOT_ENABLED=true|false
NEXT_PUBLIC_CHATBOT_ENABLED=true|false
CHATBOT_WORKER_INTERVAL_SECONDS=30
CHATBOT_JOB_BATCH_SIZE=20
CHATBOT_JOB_MAX_ATTEMPTS=8
CHATBOT_JOB_STALE_SECONDS=300
CHATBOT_CHECKPOINT_INTERVAL_SECONDS=1.0
CHATBOT_CHECKPOINT_CHARS=512
```

并说明：

- migration head 为 `0007_create_chatbot_jobs`。
- deleted Conversation 没有 Trash/restore。
- SSE detach 不等于 stop。
- Redis/Chroma 故障时 PostgreSQL 消息和删除状态仍成功，cleanup job 自动重试。
- Memory UI 位于 `/chat-bot` 的 Memories view。

- [ ] **Step 2: 运行完整后端 Chatbot 测试**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot -q
```

Expected: 全部 PASS，0 failed。

- [ ] **Step 3: 运行完整前端测试、lint 和 build**

```powershell
Set-Location frontend
npm test
npm run lint
npm run build
```

Expected: 三条命令退出码 0。

- [ ] **Step 4: 验证 OpenAPI 契约**

```powershell
Set-Location ..
$env:PYTHONPATH='backend'
@'
from app.main import app
paths = app.openapi()["paths"]
assert "/api/v1/chatbot/conversations" in paths
assert "/api/v1/conversations" not in paths
print("chatbot OpenAPI contract: PASS")
'@ | .\.venv\Scripts\python.exe -
```

Expected: 输出 `chatbot OpenAPI contract: PASS`。

- [ ] **Step 5: 检查最终 diff 并提交 README**

```powershell
git diff --check
git status --short
git add README.md
git commit -m "docs(chatbot): document remediation operations"
```

Expected: 无空白错误，工作区只剩用户原有的无关改动；不要 stage 无关文件或环境秘密。
