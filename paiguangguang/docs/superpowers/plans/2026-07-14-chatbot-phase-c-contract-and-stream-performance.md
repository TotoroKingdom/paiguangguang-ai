# Chatbot Phase C Contract and Stream Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复缺陷 8–9，使前端 Conversation 状态与后端契约一致，并按时间/字符阈值限制流式 checkpoint，保证 terminal SSE 不被摘要刷新阻塞。

**Architecture:** 前端可查询状态只保留 active/archived，deleted 仅作为 DELETE response 的终态值；流式 producer 使用纯 checkpoint tracker 决定何时写部分正文，最终状态仍由单独事务强制落库。Phase B 的 durable job 负责 terminal SSE 之后的摘要和缓存刷新。

**Tech Stack:** TypeScript/React/Vitest、Python 3.12/SQLAlchemy/pytest、SSE。

## Global Constraints

- 普通 Conversation list 只允许 `active | archived`。
- deleted Conversation 不进入前端 page store，不提供 restore。
- 删除当前会话后必须清 URL、detail 和 selected ID。
- 首个非空 delta 立即 checkpoint；之后每 1.0 秒或新增 512 字符 checkpoint。
- completed/cancelled/failed 最终事务必须保存完整内容和 usage，不依赖周期 checkpoint。
- `message.completed -> usage.updated -> stream.end` 在 PostgreSQL commit 后立即排队，不调用摘要或长期记忆。

---

## File Map

- Modify: `frontend/features/chatbot/types/conversation.ts` — listable status 只保留 active/archived。
- Modify: `frontend/features/chatbot/stores/chatbot-store.tsx` — 两页 store、snapshot v2。
- Modify: `frontend/features/chatbot/hooks/use-conversations.ts` — 删除后移除并清 URL。
- Modify: `frontend/features/chatbot/hooks/use-messages.ts` — 移除 deleted 分支。
- Modify: `frontend/features/chatbot/components/conversation-sidebar.tsx` — 删除 Trash 和 deleted restore。
- Modify: `frontend/features/chatbot/components/chat-conversation-panel.tsx` — 无选择时使用合法 fallback。
- Modify: `frontend/features/chatbot/__tests__/use-conversations.test.tsx`、`conversation-sidebar.test.tsx`、`chatbot-workspace.test.tsx`。
- Modify: `backend/app/core/config.py`、`backend/.env.example` — checkpoint 阈值。
- Modify: `backend/app/chatbot/services/stream_service.py` — `_CheckpointTracker` 和调用顺序。
- Modify: `backend/tests/chatbot/test_chat_stream.py` — 写库次数和 terminal 顺序。

### Task 1: 移除前端 Trash/deleted 查询状态

**Files:**
- Modify: `frontend/features/chatbot/types/conversation.ts`
- Modify: `frontend/features/chatbot/stores/chatbot-store.tsx`
- Modify: `frontend/features/chatbot/hooks/use-conversations.ts`
- Modify: `frontend/features/chatbot/hooks/use-messages.ts`
- Modify: `frontend/features/chatbot/components/conversation-sidebar.tsx`
- Modify: `frontend/features/chatbot/components/chat-conversation-panel.tsx`
- Modify: `frontend/features/chatbot/__tests__/use-conversations.test.tsx`
- Modify: `frontend/features/chatbot/__tests__/conversation-sidebar.test.tsx`

**Interfaces:**
- Produces: `ConversationStatus = "active" | "archived"`。
- Produces: session snapshot `version: 2`，pages 只有 active/archived。
- Keeps: `DeleteResultData.status = "deleted"`，因为它是操作结果，不是 list filter。

- [ ] **Step 1: 将测试改为期望不存在 Trash 和 deleted page**

在 `conversation-sidebar.test.tsx` 的 action 测试增加：

```ts
expect(screen.queryByRole("button", { name: "Trash" })).not.toBeInTheDocument();
expect(screen.queryByText("deleted")).not.toBeInTheDocument();
```

在 `use-conversations.test.tsx` 的删除场景删除“deleted page 包含 conv-1”的旧断言，替换为：

```ts
expect(result.current.pages.active.items.some((item) => item.id === "conv-1")).toBe(false);
expect(result.current.pages.archived.items.some((item) => item.id === "conv-1")).toBe(false);
expect(result.current.selectedConversationId).toBe(null);
expect(replace).toHaveBeenCalledWith("/chat-bot");
```

将 hydration fixture 改成 `version: 2` 且只包含 active/archived。另加测试，把旧 `version: 1`（含 deleted page）写入 storage，断言不会 hydrate deleted item。

- [ ] **Step 2: 运行测试确认当前 Trash 和 deleted page 仍存在**

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/conversation-sidebar.test.tsx features/chatbot/__tests__/use-conversations.test.tsx
```

Expected: FAIL。

- [ ] **Step 3: 收窄类型和 store**

在 `types/conversation.ts`：

```ts
export type ConversationStatus = "active" | "archived";
```

保留：

```ts
export type DeleteResultData = {
  id: string;
  status: "deleted";
  cleanup_status: "pending" | "completed" | "retry";
};
```

在 `chatbot-store.tsx`：

```ts
type ChatbotStoreSnapshot = {
  version: 2;
  state: ChatbotStoreState;
};

export const CONVERSATION_STATUSES: ConversationStatus[] = ["active", "archived"];
```

`createInitialChatbotStoreState`、`cloneState`、`upsertConversation`、`remove_conversation` 的 pages 都只保留：

```ts
pages: {
  active: { ...PAGE_TEMPLATE, items: [] },
  archived: { ...PAGE_TEMPLATE, items: [] },
}
```

`normalizeSnapshot` 必须只接受 `candidate.version === 2`，旧 v1 snapshot 返回 null。持久化 snapshot 使用 `version: 2`。

- [ ] **Step 4: 删除组件和 hooks 中的 deleted 分支**

在 `conversation-sidebar.tsx`：

```ts
const STATUS_LABELS: Record<ConversationStatus, string> = {
  active: "Active",
  archived: "Archived",
};
```

- 删除 `isDeleted`。
- Restore 条件只允许 `conversation.status === "archived"`。
- Delete button 对 active 和 archived 都显示。

在 `use-conversations.ts`：

```ts
function createStatusFlags(value: boolean): StatusFlags {
  return { active: value, archived: value };
}

function createErrorFlags(value: string | null): ErrorFlags {
  return { active: value, archived: value };
}

function findConversationById(state: ChatbotStoreState, conversationId: string) {
  for (const status of ["active", "archived"] as const) {
    const found = state.pages[status].items.find((item) => item.id === conversationId);
    if (found) return found;
  }
  return null;
}
```

将 React import 加上 `useRef`，并在 hook 内增加：

```ts
const allowAutoSelectRef = useRef(true);
```

删除成功分支替换为：

```ts
await client.deleteConversation({ token, conversationId: conversation.id });
dispatch({ type: "remove_conversation", conversationId: conversation.id });
if (state.selectedConversationId === conversation.id) {
  allowAutoSelectRef.current = false;
  dispatch({ type: "set_selected_conversation_id", conversationId: null });
  dispatch({ type: "set_selected_status", status: "active" });
  setSelectedConversationDetail(null);
  clearUrl();
}
return conversation.id;
```

依赖数组加入 `clearUrl` 和 `state.selectedConversationId`。

在“没有 URL 且没有 selected conversation”自动打开第一条会话的 effect 分支前增加：

```ts
if (!allowAutoSelectRef.current) {
  return;
}
```

这样首次进入 `/chat-bot` 仍自动打开最近会话，但删除当前会话后不会因后续无关 render 又把 URL 改成另一条会话；用户显式选择或新建会话仍正常设置 selected ID 和 URL。

在 `use-messages.ts` 删除所有 `conversationStatus === "deleted"` 检查。在 `chat-conversation-panel.tsx` 将无 conversation fallback 改为：

```ts
const conversationStatus = conversation?.status ?? "active";
```

- [ ] **Step 5: 运行 Conversation 前端测试**

```powershell
Set-Location frontend
npm test -- features/chatbot/__tests__/conversation-sidebar.test.tsx features/chatbot/__tests__/use-conversations.test.tsx features/chatbot/__tests__/chatbot-workspace.test.tsx
```

Expected: PASS；没有请求 `status=deleted` 的测试或代码路径。

- [ ] **Step 6: 静态搜索 deleted 查询残留并提交**

```powershell
Set-Location ..
rg -n 'selectedStatus.*deleted|pages\.deleted|status === "deleted"|Trash' frontend/features/chatbot
```

Expected: 无输出；`DeleteResultData` 中的字面量不匹配这些查询模式。

```powershell
git add frontend/features/chatbot
git commit -m "fix(chatbot): align conversation status contract"
```

### Task 2: 实现流式 checkpoint 双阈值

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Modify: `backend/app/chatbot/services/stream_service.py`
- Modify: `backend/tests/chatbot/test_chat_stream.py`

**Interfaces:**
- Produces: `Settings.chatbot_checkpoint_interval_seconds: float = 1.0`。
- Produces: `Settings.chatbot_checkpoint_chars: int = 512`。
- Produces: `_CheckpointTracker.should_checkpoint(now, content_length)` 和 `mark(now, content_length)`。

- [ ] **Step 1: 写大量小 delta 只 checkpoint 一次的失败测试**

在 `test_chat_stream.py` 创建 100 个单字符 delta 后 completed，settings 使用极长时间阈值和 512 字符阈值。对 service spy：

```python
checkpoint_calls = 0
original = stream_service._checkpoint_partial

def counted_checkpoint(*args, **kwargs):
    nonlocal checkpoint_calls
    checkpoint_calls += 1
    return original(*args, **kwargs)

monkeypatch.setattr(stream_service, "_checkpoint_partial", counted_checkpoint)
events = list(stream_service.stream_completion(owner.id, conversation.id, "hello", request_id))

assert checkpoint_calls == 1
assert events[-1].event == "stream.end"
```

另加 600 字符测试，断言首 delta 加跨过 512 字符阈值时至少有第二次 checkpoint；最终 DB content 必须完整。

- [ ] **Step 2: 运行测试确认当前每个 delta 都写库**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_chat_stream.py -q
```

Expected: FAIL；100 个 delta 产生 100 次 checkpoint。

- [ ] **Step 3: 增加配置**

给 `Settings` 增加：

```python
chatbot_checkpoint_interval_seconds: float = 1.0
chatbot_checkpoint_chars: int = 512
```

在 `get_settings()` 增加：

```python
chatbot_checkpoint_interval_seconds=float(os.getenv("CHATBOT_CHECKPOINT_INTERVAL_SECONDS", "1.0")),
chatbot_checkpoint_chars=int(os.getenv("CHATBOT_CHECKPOINT_CHARS", "512")),
```

在 `backend/.env.example` 增加：

```dotenv
CHATBOT_CHECKPOINT_INTERVAL_SECONDS=1.0
CHATBOT_CHECKPOINT_CHARS=512
```

- [ ] **Step 4: 增加纯 checkpoint tracker**

在 `stream_service.py` 的 `_TerminalState` 后增加：

```python
@dataclass(slots=True)
class _CheckpointTracker:
    interval_seconds: float
    chars: int
    last_checkpoint_at: float
    last_content_length: int = 0
    has_checkpoint: bool = False

    def should_checkpoint(self, *, now: float, content_length: int) -> bool:
        if not self.has_checkpoint:
            return True
        return (
            now - self.last_checkpoint_at >= self.interval_seconds
            or content_length - self.last_content_length >= self.chars
        )

    def mark(self, *, now: float, content_length: int) -> None:
        self.has_checkpoint = True
        self.last_checkpoint_at = now
        self.last_content_length = content_length
```

在 `_produce_stream_events` 初始化：

```python
checkpoint = _CheckpointTracker(
    interval_seconds=max(0.1, float(self.settings.chatbot_checkpoint_interval_seconds)),
    chars=max(1, int(self.settings.chatbot_checkpoint_chars)),
    last_checkpoint_at=started_at,
)
```

把 delta 分支的无条件 `_checkpoint_partial` 改为：

```python
checkpoint_at = perf_counter()
if checkpoint.should_checkpoint(now=checkpoint_at, content_length=len(partial_content)):
    self._checkpoint_partial(
        accepted,
        user_id,
        partial_content=partial_content,
        usage=usage,
        started_at=started_at,
        first_delta_at=first_delta_at,
    )
    checkpoint.mark(now=checkpoint_at, content_length=len(partial_content))
```

usage event 可以强制调用一次 `_checkpoint_partial` 并 `mark`，因为 usage 可能在 terminal 之前独立到达；completed/cancelled/failed 继续由各自 finalize 方法保存最终 content/usage，不额外依赖 tracker。

- [ ] **Step 5: 添加 tracker 纯单元测试并运行**

在 `test_chat_stream.py` 直接测试 `_CheckpointTracker`：首个 true、0.5 秒/100 字符 false、1 秒 true、512 字符 true。运行：

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_chat_stream.py -q
```

Expected: PASS。

- [ ] **Step 6: 提交 Task 2**

```powershell
git add backend/app/core/config.py backend/.env.example backend/app/chatbot/services/stream_service.py backend/tests/chatbot/test_chat_stream.py
git commit -m "perf(chatbot): throttle stream checkpoints"
```

### Task 3: 锁定 terminal SSE 在后台工作之前返回

**Files:**
- Modify: `backend/tests/chatbot/test_chat_stream.py`
- Modify: `backend/app/chatbot/services/stream_service.py` only if test reveals a remaining synchronous call.

**Interfaces:**
- Consumes: Phase B 的 `CompletionJobService` durable enqueue。
- Produces: completed 分支调用顺序为 finalize/commit → terminal queue events；不调用 `_refresh_short_term_memory`。

- [ ] **Step 1: 写 slow summary 不参与 producer 的回归测试**

给测试中的 fake ChatService 设置：

```python
def forbidden_refresh(*args, **kwargs):
    raise AssertionError("summary refresh must not run before terminal SSE")

monkeypatch.setattr(stream_service, "_refresh_short_term_memory", forbidden_refresh)
events = list(stream_service.stream_completion(owner.id, conversation.id, "hello", request_id))
names = [event.event for event in events if isinstance(event, ChatStreamEvent)]
assert names[-3:] == ["message.completed", "usage.updated", "stream.end"]
```

同时查询 DB，断言 assistant 和 run 在 `stream.end` 后为 completed；查询 `ChatbotJob`，断言存在 `refresh_conversation_context` pending job。

- [ ] **Step 2: 运行测试**

```powershell
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_chat_stream.py backend/tests/chatbot/test_completion_jobs.py -q
```

Expected: PASS。如果失败，移除 completed 分支残留的 `_refresh_short_term_memory`，但不要移除 durable enqueue。

- [ ] **Step 3: 检查 completed 分支调用顺序**

```powershell
rg -n -C 12 '_finalize_completed|_refresh_short_term_memory|event="message.completed"|event="stream.end"' backend/app/chatbot/services/stream_service.py
```

Expected: `_finalize_completed` 先完成；completed 分支在 terminal event 前没有 `_refresh_short_term_memory`、summary、memory 或 Chroma 调用。

- [ ] **Step 4: 有代码修正时提交；无修正不创建空 commit**

```powershell
git add backend/app/chatbot/services/stream_service.py backend/tests/chatbot/test_chat_stream.py
git commit -m "test(chatbot): protect terminal stream latency"
```

### Task 4: Phase C 回归门禁

**Files:**
- Verify only.

**Interfaces:**
- Produces: 前后端契约和性能修复共同通过。

- [ ] **Step 1: 运行前端 Chatbot tests**

```powershell
Set-Location frontend
npm test -- features/chatbot
```

Expected: PASS。

- [ ] **Step 2: 运行后端 stream/conversation tests**

```powershell
Set-Location ..
$env:PYTHONPATH='backend'
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_chat_stream.py backend/tests/chatbot/test_stream_api.py backend/tests/chatbot/test_conversation_api.py -q
```

Expected: PASS。

- [ ] **Step 3: 运行前端 lint/build**

```powershell
Set-Location frontend
npm run lint
npm run build
```

Expected: 两条命令退出码 0。

- [ ] **Step 4: 检查 diff**

```powershell
Set-Location ..
git diff --check
git status --short
```

Expected: 无空白错误，只包含本计划声明文件。
