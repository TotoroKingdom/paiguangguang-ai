# Chatbot Streaming Performance Design

## Goal

Make chatbot replies feel like ChatGPT or DeepSeek: the first text appears promptly, subsequent text flows smoothly with live Markdown formatting, and database work never throttles SSE delivery.

## Confirmed Decisions

- Remove partial-response checkpoint persistence from the streaming hot path.
- Persist an assistant response only when generation reaches a terminal state: completed, cancelled, or failed.
- Accept that a backend process crash can lose the partial assistant text accumulated in memory.
- Keep the existing stale-run recovery behavior for pending or streaming records left behind by a process crash.
- Render Markdown while the response is streaming.
- Coalesce frontend deltas into UI updates approximately every 40 milliseconds.

## Current Problem

The backend currently receives a provider delta, performs a synchronous database checkpoint, and only then puts the delta into the SSE queue. A checkpoint loads several ORM objects whose `selectin` relationships expand one checkpoint into many remote database queries. Because the remote database operation can take longer than the configured checkpoint interval, nearly every provider delta triggers another checkpoint. The observed result is roughly one displayed token per second even though a direct DeepSeek stream is fast.

The frontend also merges every individual delta into React state and passes the entire accumulated response through `ReactMarkdown`. Long responses therefore repeatedly parse and render already stable content.

## Backend Architecture

### Streaming data flow

1. Accept the turn and persist the user message, empty assistant message, and pending LLM run as today.
2. Start consuming the DeepSeek stream.
3. For every non-empty provider delta:
   - append it to the in-memory `partial_content` buffer;
   - immediately put the corresponding `message.delta` event into the SSE queue;
   - perform no database reads or writes.
4. When the provider reaches a terminal outcome, persist the full terminal snapshot once.
5. Emit the terminal message event, usage event, and `stream.end` event.

### Terminal persistence

Terminal persistence remains authoritative and includes:

- the complete or partial assistant content;
- assistant and LLM run status;
- model and finish reason;
- prompt, completion, and total token counts when available;
- latency and first-token latency;
- completion, cancellation, or failure timestamps;
- conversation `updated_at`;
- the existing post-completion jobs for a successfully completed response.

The current checkpoint tracker, checkpoint configuration values, and `_checkpoint_partial()` call path are removed because they no longer represent supported behavior.

### Failure semantics

- Completed generation: persist the full response once as completed.
- User cancellation: persist the accumulated partial response once as cancelled.
- Provider failure: persist the accumulated partial response once as failed, including the mapped error information.
- Browser disconnect: the producer continues independently and persists the eventual terminal result.
- Backend process crash: partial text held only in memory is lost. Existing stale-run recovery later marks the abandoned run as failed.

## Frontend Architecture

### Delta batching

Introduce a focused stream-event batching unit between the SSE reader and the existing state merge callback.

- `message.delta` events for the same active request and assistant message are concatenated in arrival order.
- A scheduled flush runs approximately every 40 milliseconds.
- The combined event carries the last source sequence number, content length, and timestamp so the existing stale-event protection remains correct.
- A non-delta event first flushes any pending delta, then dispatches itself.
- `onCreated` and `onTerminal` callbacks run from the ordered dispatch path, after the corresponding event has reached the state merge callback.
- Conversation change, authentication loss, cancellation, and component cleanup discard pending work belonging to the detached stream.
- A terminal event cannot overtake buffered text.

This keeps network consumption continuous while limiting React updates to roughly 25 frames per second.

### Incremental Markdown rendering

Split a streaming assistant response into stable Markdown blocks and one active tail. A block becomes stable only at a blank-line boundary outside a fenced code block; an open fenced code block always remains in the active tail until its closing fence arrives.

- Stable blocks are boundaries completed outside fenced code blocks, such as completed paragraphs, headings, lists, tables, and fenced code sections.
- Stable blocks render through memoized Markdown components and retain stable keys, so subsequent deltas do not parse them again.
- Only the active tail is reparsed on each batched UI update.
- When the message becomes terminal, the authoritative full content is rendered without a streaming cursor.
- Incomplete Markdown syntax remains visible as ordinary text until enough input arrives to form the intended structure.

The renderer keeps the existing URL protocol restrictions and code-block behavior.

### Streaming presentation

- Show a small cursor at the end of the active assistant response while its status is pending or streaming.
- Remove the cursor immediately on completed, cancelled, or failed status.
- Disable cursor animation under `prefers-reduced-motion`.
- Preserve the existing sticky-to-bottom behavior.
- If the user scrolls away from the bottom, streaming updates must not pull the viewport back down.

## Interfaces and Responsibilities

### Backend

- `ChatStreamService._produce_stream_events`: owns provider consumption, in-memory content assembly, event ordering, cancellation checks, and terminal coordination.
- Terminal finalizers: own the single authoritative database write for completed, cancelled, or failed outcomes.
- Stale recovery: owns cleanup after process-level interruption; it does not reconstruct lost partial content.

### Frontend

- Stream event batcher: owns delta accumulation, the 40ms flush schedule, event ordering, and cleanup.
- Existing stream hook: owns request lifecycle and sends parsed events through the batcher.
- Streaming Markdown renderer: owns block segmentation, memoization, active-tail parsing, and cursor presentation.
- Existing reducer/state merge: remains authoritative for conversation and request identity, message snapshots, terminal state, and sequence guards.

## Testing Strategy

### Backend tests

- Prove that streaming deltas do not call `_checkpoint_partial()` or any replacement checkpoint path.
- Simulate a terminal database write blocked behind a synchronization barrier and prove all deltas are queued before the terminal write is released.
- Verify completed, cancelled, and failed streams each persist exactly one terminal snapshot with the expected content and status.
- Verify the terminal event sequence remains `message.completed|cancelled|failed`, `usage.updated`, then `stream.end`.
- Verify stale recovery still handles a run abandoned before terminal persistence.

### Frontend tests

- With fake timers, enqueue 100 rapid deltas and prove they produce only a small number of UI dispatches while preserving every character in order.
- Verify a terminal event flushes pending text before the terminal snapshot.
- Verify conversation change, authentication loss, and abort discard pending events from the detached stream.
- Verify stable Markdown blocks do not rerender when only the active tail changes.
- Verify fenced code blocks are not split while incomplete.
- Verify the cursor appears only during pending or streaming states and respects reduced-motion behavior.
- Preserve existing unsafe-link rejection tests.

### End-to-end verification

- Run the backend chatbot test suite.
- Run the frontend Vitest suite.
- Run the frontend production build for TypeScript and Next.js verification.
- Use the local chatbot with a real DeepSeek response and confirm prompt first text, continuous output, live Markdown formatting, correct stop behavior, and final history persistence.

## Acceptance Criteria

- No database operation occurs for an individual provider delta.
- SSE queue delivery is independent of terminal database latency.
- Rapid provider deltas appear as smooth updates at approximately 25 UI updates per second.
- The final rendered response exactly matches the authoritative terminal content.
- Previously completed Markdown blocks are not repeatedly reparsed as the active tail grows.
- Completed, cancelled, and failed responses remain durable after their terminal write succeeds.
- Process crashes may lose partial content, as explicitly accepted, but stale-run recovery still produces a consistent failed state.
- Backend tests, frontend tests, and the frontend production build pass.

## Out of Scope

- Recovering partial assistant text after a backend process crash.
- Changing the DeepSeek model, provider protocol, or prompting strategy.
- Adding token-by-token artificial typing delays.
- Redesigning the chatbot layout, colors, or general visual identity.
