# Chatbot Streaming Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver database-independent SSE streaming and ChatGPT/DeepSeek-style smooth live Markdown rendering.

**Architecture:** Backend provider deltas are accumulated only in memory and queued immediately; the database is written once at a completed, cancelled, or failed terminal state. The frontend coalesces delta events into approximately 40ms dispatches, then renders stable Markdown blocks through memoized components while reparsing only the active tail.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, pytest, Next.js 14, React 18, TypeScript, Vitest, Testing Library, react-markdown, remark-gfm.

## Global Constraints

- Work directly on `main` as explicitly authorized by the user.
- Do not persist partial assistant content during generation.
- Preserve terminal persistence for completed, cancelled, and failed outcomes.
- Accept loss of in-memory partial content after a backend process crash.
- Preserve stale-run recovery for abandoned runs.
- Render Markdown during streaming and coalesce UI updates at 40ms.
- Preserve URL protocol restrictions, code-block behavior, stop behavior, and scroll-away behavior.
- Do not add artificial token-by-token delays or redesign unrelated chatbot UI.

---

### Task 1: Remove Streaming Checkpoints From the Backend Hot Path

**Files:**
- Modify: `backend/tests/chatbot/test_chat_stream.py`
- Modify: `backend/app/chatbot/services/stream_service.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`

**Interfaces:**
- Consumes: `ChatStreamService.stream_completion(...) -> Iterator[ChatStreamEvent | str]` and existing terminal finalizers.
- Produces: `_produce_stream_events()` behavior where `message.delta` delivery performs zero SQL statements and terminal finalizers remain authoritative.

- [ ] **Step 1: Write a failing backend test proving delta delivery performs no SQL**

Add a gated provider generator to `test_chat_stream.py`. It lets the test reset SQL counters after `message.created`, then yields exactly one delta and pauses before completion:

```python
from threading import Event


def test_chat_stream_delta_delivery_performs_no_database_io(monkeypatch, tmp_path) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    release_delta = Event()
    release_completion = Event()
    request_id = "00000000-0000-0000-0000-000000000334"

    def provider_events():
        assert release_delta.wait(timeout=2)
        yield LLMStreamEvent(
            kind="delta",
            request_id=request_id,
            prompt_version="v1",
            model="deepseek-chat",
            content="Hello",
        )
        assert release_completion.wait(timeout=2)
        yield LLMStreamEvent(
            kind="completed",
            request_id=request_id,
            prompt_version="v1",
            model="deepseek-chat",
            content="Hello",
            finish_reason="stop",
        )

    fake_llm = FakeLLMClient(outcomes=[provider_events()])
    service = _build_service(session_factory, fake_llm)
    statements: list[str] = []
    engine = session_factory.kw["bind"]

    @event.listens_for(engine, "before_cursor_execute")
    def count_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    with session_factory() as session:
        owner = _create_user(session, email="no-checkpoint@example.com")
        session.commit()
    conversation = conversation_repo.create(
        owner.id, "Thread", "deepseek-chat", system_prompt_version="v1"
    )

    stream = iter(service.stream_completion(owner.id, conversation.id, "hello", request_id))
    assert next(stream).event == "message.created"
    statements.clear()
    release_delta.set()
    assert next(stream).event == "message.delta"
    assert statements == []

    release_completion.set()
    assert [event.event for event in stream][-1] == "stream.end"
```

- [ ] **Step 2: Run the focused backend test and verify RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_chat_stream.py::test_chat_stream_delta_delivery_performs_no_database_io -q
```

Expected: FAIL because the current delta path calls `_checkpoint_partial()` and executes SQL before queueing `message.delta`.

- [ ] **Step 3: Remove checkpoint behavior with the minimal production change**

In `stream_service.py`:

```python
# Remove _CheckpointTracker.
# Remove checkpoint initialization from _produce_stream_events().
# In the delta branch, retain only content accumulation, first-token logging,
# queue.put(message.delta), sequence increment, and continue.
# In the usage branch, retain only `usage = llm_event.usage` and continue.
# Remove _checkpoint_partial(). Terminal finalizers remain unchanged.
```

In `config.py`, remove `chatbot_checkpoint_interval_seconds`, `chatbot_checkpoint_chars`, and their environment parsing. Remove the matching entries from `backend/.env.example`.

- [ ] **Step 4: Run backend stream tests and verify GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot/test_chat_stream.py backend/tests/chatbot/test_stale_recovery.py -q
```

Expected: PASS. Delete the three obsolete tests named `test_chat_stream_throttles_many_small_delta_checkpoints`, `test_checkpoint_tracker_uses_time_and_character_thresholds`, and `test_chat_stream_checkpoints_after_character_threshold_and_finalizes_full_content`. The new zero-SQL delta test replaces their hot-path coverage; the existing completion, cancellation, failure, and stale-recovery tests retain terminal durability coverage.

- [ ] **Step 5: Commit the backend change**

```powershell
git add backend/tests/chatbot/test_chat_stream.py backend/app/chatbot/services/stream_service.py backend/app/core/config.py backend/.env.example
git commit -m "perf(chatbot): remove streaming database checkpoints"
```

---

### Task 2: Coalesce Frontend Delta Events Into 40ms Dispatches

**Files:**
- Create: `frontend/features/chatbot/utils/stream-event-batcher.ts`
- Create: `frontend/features/chatbot/__tests__/stream-event-batcher.test.ts`
- Modify: `frontend/features/chatbot/hooks/use-chat-stream.ts`
- Modify: `frontend/features/chatbot/__tests__/use-chat-stream.test.tsx`

**Interfaces:**
- Consumes: `ParsedChatStreamEvent` and an `(event) => void` ordered dispatch callback.
- Produces: `createChatStreamEventBatcher({ emit, delayMs? })` returning `{ push, flush, clear }`.

- [ ] **Step 1: Write failing batcher tests**

Create `stream-event-batcher.test.ts` with fake timers and helpers that build valid delta and terminal events:

```typescript
it("coalesces rapid deltas without losing content or order", () => {
  vi.useFakeTimers();
  const emit = vi.fn();
  const batcher = createChatStreamEventBatcher({ emit, delayMs: 40 });

  for (let index = 1; index <= 100; index += 1) {
    batcher.push(makeDelta(index, "x", index));
  }

  expect(emit).not.toHaveBeenCalled();
  vi.advanceTimersByTime(40);
  expect(emit).toHaveBeenCalledTimes(1);
  expect(emit.mock.calls[0][0].data.delta).toBe("x".repeat(100));
  expect(emit.mock.calls[0][0].sequence).toBe(100);
  expect(emit.mock.calls[0][0].data.content_length).toBe(100);
});

it("flushes buffered text before a terminal event", () => {
  vi.useFakeTimers();
  const events: ParsedChatStreamEvent[] = [];
  const batcher = createChatStreamEventBatcher({ emit: (event) => events.push(event) });
  batcher.push(makeDelta(2, "Hello", 5));
  batcher.push(makeCompleted(3, "Hello"));
  expect(events.map((event) => event.event)).toEqual(["message.delta", "message.completed"]);
});

it("clear discards a detached stream's pending delta", () => {
  vi.useFakeTimers();
  const emit = vi.fn();
  const batcher = createChatStreamEventBatcher({ emit });
  batcher.push(makeDelta(2, "stale", 5));
  batcher.clear();
  vi.runAllTimers();
  expect(emit).not.toHaveBeenCalled();
});
```

- [ ] **Step 2: Run batcher tests and verify RED**

Run:

```powershell
npm test -- --run features/chatbot/__tests__/stream-event-batcher.test.ts
```

from `frontend/`.

Expected: FAIL because `stream-event-batcher.ts` does not exist.

- [ ] **Step 3: Implement the event batcher**

Implement these exact public types and behaviors:

```typescript
type ChatStreamEventBatcherOptions = {
  emit: (event: ParsedChatStreamEvent) => void;
  delayMs?: number;
};

type ChatStreamEventBatcher = {
  push: (event: ParsedChatStreamEvent) => void;
  flush: () => void;
  clear: () => void;
};

export function createChatStreamEventBatcher({
  emit,
  delayMs = 40,
}: ChatStreamEventBatcherOptions): ChatStreamEventBatcher {
  let pendingDelta: Extract<ParsedChatStreamEvent, { event: "message.delta" }> | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;

  const cancelTimer = () => {
    if (timer !== null) clearTimeout(timer);
    timer = null;
  };
  const flush = () => {
    cancelTimer();
    if (!pendingDelta) return;
    const event = pendingDelta;
    pendingDelta = null;
    emit(event);
  };
  const clear = () => {
    cancelTimer();
    pendingDelta = null;
  };
  const schedule = () => {
    if (timer === null) timer = setTimeout(flush, delayMs);
  };
  const push = (event: ParsedChatStreamEvent) => {
    if (event.event !== "message.delta") {
      flush();
      emit(event);
      return;
    }
    if (pendingDelta &&
        pendingDelta.data.request_id === event.data.request_id &&
        pendingDelta.data.assistant_message_id === event.data.assistant_message_id) {
      pendingDelta = {
        ...event,
        data: { ...event.data, delta: pendingDelta.data.delta + event.data.delta },
      };
    } else {
      flush();
      pendingDelta = event;
    }
    schedule();
  };
  return { push, flush, clear };
}
```

- [ ] **Step 4: Integrate ordered batching into `useChatStream`**

Inside each `runGeneration`, use one ordered dispatcher for every callback:

```typescript
const dispatchEvent = (event: ParsedChatStreamEvent) => {
  onEvent?.(event);
  if (event.event === "message.created") {
    onCreated?.({ event: "message.created", data: event.data, sequence: event.sequence });
  }
  if (event.event === "stream.end" || event.event === "message.failed" || event.event === "message.cancelled") {
    onTerminal?.(event);
  }
};
const batcher = createChatStreamEventBatcher({ emit: dispatchEvent });
let detached = false;

for await (const event of readChatStreamEvents(response)) {
  if (controller.signal.aborted ||
      activeConversationId.current !== startedConversationId ||
      eventConversationId(event) !== startedConversationId) {
    detached = true;
    break;
  }
  batcher.push(event);
}
if (detached) batcher.clear();
else batcher.flush();
```

In the exception path, call `batcher.clear()` for abort/detach and `batcher.flush()` before reporting a real network failure. Extend the hook test to prove terminal callback ordering and stale-buffer disposal.

- [ ] **Step 5: Run frontend stream tests and verify GREEN**

Run from `frontend/`:

```powershell
npm test -- --run features/chatbot/__tests__/stream-event-batcher.test.ts features/chatbot/__tests__/use-chat-stream.test.tsx features/chatbot/__tests__/chat-stream.test.ts
```

Expected: PASS.

- [ ] **Step 6: Commit the batching change**

```powershell
git add frontend/features/chatbot/utils/stream-event-batcher.ts frontend/features/chatbot/__tests__/stream-event-batcher.test.ts frontend/features/chatbot/hooks/use-chat-stream.ts frontend/features/chatbot/__tests__/use-chat-stream.test.tsx
git commit -m "perf(chatbot): batch frontend stream updates"
```

---

### Task 3: Render Stable Markdown Blocks and an Active Streaming Tail

**Files:**
- Create: `frontend/features/chatbot/utils/split-streaming-markdown.ts`
- Create: `frontend/features/chatbot/components/streaming-markdown-content.tsx`
- Create: `frontend/features/chatbot/__tests__/split-streaming-markdown.test.ts`
- Create: `frontend/features/chatbot/__tests__/streaming-markdown-content.test.tsx`
- Modify: `frontend/features/chatbot/components/message-item.tsx`
- Modify: `frontend/features/chatbot/__tests__/message-item.test.tsx`
- Modify: `frontend/app/globals.css`

**Interfaces:**
- Consumes: accumulated assistant `value: string` and `streaming: boolean`.
- Produces: `splitStreamingMarkdown(value) -> { stableBlocks: string[]; activeTail: string }` and `<StreamingMarkdownContent value streaming />`.

- [ ] **Step 1: Write failing Markdown splitter tests**

```typescript
it("settles blocks only at blank lines", () => {
  expect(splitStreamingMarkdown("First paragraph.\n\nSecond para")).toEqual({
    stableBlocks: ["First paragraph.\n\n"],
    activeTail: "Second para",
  });
});

it("keeps an incomplete fenced code block in the active tail", () => {
  const value = "Intro.\n\n```ts\nconst answer = 42;\n\n";
  expect(splitStreamingMarkdown(value)).toEqual({
    stableBlocks: ["Intro.\n\n"],
    activeTail: "```ts\nconst answer = 42;\n\n",
  });
});

it("settles a closed fenced block at its following blank line", () => {
  const value = "```ts\nconst answer = 42;\n```\n\nTail";
  expect(splitStreamingMarkdown(value)).toEqual({
    stableBlocks: ["```ts\nconst answer = 42;\n```\n\n"],
    activeTail: "Tail",
  });
});
```

- [ ] **Step 2: Run splitter tests and verify RED**

Run from `frontend/`:

```powershell
npm test -- --run features/chatbot/__tests__/split-streaming-markdown.test.ts
```

Expected: FAIL because the splitter module does not exist.

- [ ] **Step 3: Implement the pure Markdown splitter**

Implement the splitter as a lossless line scanner:

```typescript
export type StreamingMarkdownParts = {
  stableBlocks: string[];
  activeTail: string;
};

export function splitStreamingMarkdown(value: string): StreamingMarkdownParts {
  const stableBlocks: string[] = [];
  let blockStart = 0;
  let cursor = 0;
  let fence: { marker: "`" | "~"; length: number } | null = null;

  while (cursor < value.length) {
    const newline = value.indexOf("\n", cursor);
    const lineEnd = newline === -1 ? value.length : newline + 1;
    const line = value.slice(cursor, lineEnd);
    const body = line.replace(/\r?\n$/, "");
    const fenceLine = body.replace(/^[ \t]{0,3}/, "").match(/^(`{3,}|~{3,})(.*)$/);

    if (fenceLine) {
      const token = fenceLine[1];
      const marker = token[0] as "`" | "~";
      if (fence === null) {
        fence = { marker, length: token.length };
      } else if (marker === fence.marker && token.length >= fence.length && fenceLine[2].trim() === "") {
        fence = null;
      }
    }

    if (fence === null && body.trim() === "" && lineEnd > blockStart) {
      stableBlocks.push(value.slice(blockStart, lineEnd));
      blockStart = lineEnd;
    }
    cursor = lineEnd;
  }

  return { stableBlocks, activeTail: value.slice(blockStart) };
}
```

- [ ] **Step 4: Write failing renderer and cursor tests**

```typescript
it("keeps settled blocks mounted while the active tail grows", () => {
  const { rerender } = render(
    <StreamingMarkdownContent value={"Settled.\n\nTail"} streaming />
  );
  const settled = screen.getByTestId("streaming-markdown-block-0");
  rerender(<StreamingMarkdownContent value={"Settled.\n\nTail grows"} streaming />);
  expect(screen.getByTestId("streaming-markdown-block-0")).toBe(settled);
  expect(screen.getByTestId("streaming-cursor")).toBeInTheDocument();
});

it("removes the cursor for a terminal message", () => {
  render(<StreamingMarkdownContent value="Done" streaming={false} />);
  expect(screen.queryByTestId("streaming-cursor")).not.toBeInTheDocument();
});
```

- [ ] **Step 5: Implement memoized stable blocks and cursor presentation**

Create a memoized stable-block component around the existing `MarkdownContent`:

```tsx
const StableMarkdownBlock = memo(function StableMarkdownBlock({ value, index }: { value: string; index: number }) {
  return (
    <div data-testid={`streaming-markdown-block-${index}`}>
      <MarkdownContent value={value} />
    </div>
  );
});

export function StreamingMarkdownContent({ value, streaming }: { value: string; streaming: boolean }) {
  if (!streaming) return <MarkdownContent value={value} />;
  const { stableBlocks, activeTail } = splitStreamingMarkdown(value);
  return (
    <div className="min-w-0">
      {stableBlocks.map((block, index) => (
        <StableMarkdownBlock key={`${index}:${block}`} value={block} index={index} />
      ))}
      {activeTail ? <MarkdownContent value={activeTail} /> : null}
      <span data-testid="streaming-cursor" aria-hidden="true" className="chat-stream-cursor" />
    </div>
  );
}
```

Update `MessageItem` to use this component for assistant messages and pass `streaming={message.status === "pending" || isStreaming}`.

Add cursor CSS:

```css
@keyframes chat-stream-cursor-blink {
  0%, 45% { opacity: 1; }
  55%, 100% { opacity: 0.2; }
}

.chat-stream-cursor {
  display: inline-block;
  width: 0.5rem;
  height: 1.05rem;
  margin-left: 0.18rem;
  border-radius: 999px;
  background: currentColor;
  vertical-align: -0.12rem;
  animation: chat-stream-cursor-blink 0.9s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  .chat-stream-cursor { animation: none; }
}
```

- [ ] **Step 6: Run Markdown and message tests and verify GREEN**

Run from `frontend/`:

```powershell
npm test -- --run features/chatbot/__tests__/split-streaming-markdown.test.ts features/chatbot/__tests__/streaming-markdown-content.test.tsx features/chatbot/__tests__/message-item.test.tsx features/chatbot/__tests__/markdown-content.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit the Markdown rendering change**

```powershell
git add frontend/features/chatbot/utils/split-streaming-markdown.ts frontend/features/chatbot/components/streaming-markdown-content.tsx frontend/features/chatbot/components/message-item.tsx frontend/features/chatbot/__tests__/split-streaming-markdown.test.ts frontend/features/chatbot/__tests__/streaming-markdown-content.test.tsx frontend/features/chatbot/__tests__/message-item.test.tsx frontend/app/globals.css
git commit -m "perf(chatbot): render streaming markdown incrementally"
```

---

### Task 4: Regression, Build, and Live Verification

**Files:**
- Verify: `backend/tests/chatbot/`
- Verify: `frontend/features/chatbot/`
- Verify: `frontend/app/globals.css`
- Modify: only a specific Task 1-3 file named by a failing regression, and only after reproducing that failure with its focused command.

**Interfaces:**
- Consumes: completed backend and frontend behavior from Tasks 1-3.
- Produces: verified chatbot stream with documented timing evidence.

- [ ] **Step 1: Run the complete backend chatbot suite**

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/chatbot -q
```

Expected: all tests PASS.

- [ ] **Step 2: Run the complete frontend suite**

From `frontend/`:

```powershell
npm test -- --run
```

Expected: all tests PASS without unhandled warnings.

- [ ] **Step 3: Run the frontend production build**

From `frontend/`:

```powershell
npm run build
```

Expected: Next.js production build succeeds with no TypeScript errors.

- [ ] **Step 4: Run live local verification**

Send a Markdown-producing prompt through the local chatbot and record:

- time to `message.created`;
- time to first `message.delta`;
- total streamed characters and duration;
- visible Markdown formation, cursor behavior, and final content;
- persisted terminal content after reloading the conversation.

Expected: no per-delta database delay, continuous batched output, final content preserved after reload.

- [ ] **Step 5: Run final diff checks and commit any verification-only corrections**

```powershell
git diff --check
git status --short
```

If Task 4 required corrections, stage only those files and commit with a focused message. If no correction was needed, do not create an empty commit.
