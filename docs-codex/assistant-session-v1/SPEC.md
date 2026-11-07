# Assistant Session Persistence V1

## Scope

This change makes assistant conversations and messages server-owned data stored in SQLite. The existing assistant UI and mock response generator remain in place; this release does not connect a real LLM, MCP runtime, RAG pipeline, file contents, or accounts.

## Contracts

- Anonymous browser isolation is provided by an HttpOnly, SameSite cookie issued by FastAPI. It is not authentication and must not be described as cross-device or sensitive-data security.
- Conversation CRUD always filters by the signed owner cookie. Missing and foreign resources return the same `404` response.
- Conversation ordering is `updated_at DESC, id DESC`. List responses contain metadata only and use an opaque cursor.
- `POST /api/v1/conversations/{id}/turns` atomically creates one user message and one assistant placeholder. `client_turn_id` makes retries idempotent.
- Assistant generation is simulated in the browser. Only the initial turn and final states (`complete`, `stopped`, `error`) are persisted; character-by-character output is never sent to the database.
- A read of a conversation converts orphaned `generating` assistant messages to `stopped` so refresh and retry cannot leave a permanent generating state.
- SQLite lives at `/data/assistant.db` in production and is mounted through a named Docker volume. The API is internal to the Compose network.
- The old `paiguangguang.assistant.v1` localStorage key is retained. Only non-seed user-created conversations are eligible for one-time, idempotent import; seed conversations are never silently imported.

## Acceptance

- [ ] Empty conversation creation and first turn write real SQLite rows.
- [ ] Refresh, direct URL, API restart, and container recreation preserve sessions.
- [ ] Rename, delete, search, cursor pagination, stop, error, and retry behave correctly.
- [ ] Two anonymous browser cookies cannot read or mutate each other's conversations.
- [ ] Invalid input, 404, optimistic conflict, duplicate turn, and transaction rollback are covered by tests.
- [ ] Frontend keeps drafts, capabilities, files, favorites, and connector demo state in localStorage.
- [ ] Deployment does not publish the backend or database port and does not remove the named volume.

