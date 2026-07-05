# Codex Execution Tasks

This file is the task execution source of truth for Codex.

Before starting any task, read:

- `docs/PROJECT_SPEC.md`
- `docs/architecture.md`
- `docs/roadmap.md`
- `docs/codex_tasks.md`

## Mandatory Rules

- Execute exactly one task at a time.
- Do not implement future tasks.
- Do not redesign architecture unless explicitly instructed.
- Use `/api/v1` for every backend JSON API route.
- Keep route handlers thin and put business logic in services.
- Do not refactor unrelated code.
- Keep changes minimal and scoped.
- If a required decision is unclear, stop and ask.
- Add or update tests when the task changes backend behavior.
- Keep frontend API calls in `frontend/lib`, not scattered through page components.
- Keep backend response shapes aligned with frontend types.
- Treat the current RAG demo as the baseline. V2 tasks upgrade or replace baseline pieces; they do not rebuild the demo from scratch.

## Current Baseline

The project already has a runnable full-stack baseline:

- V1 Portfolio Chat with DeepSeek
- Knowledge Agent page with text upload or paste, ingestion, query, answer, and sources
- Backend RAG ingestion with deterministic chunking
- Chroma indexing and similarity search
- RAG query service with context assembly and DeepSeek answer generation
- Architecture visualization
- Mock Browser and Office Agent workflows
- Task status and SSE event endpoints

Do not re-execute old initialization tasks unless the user explicitly asks for a rebuild. Future work starts from the V2.1 task list below.

## Global Verification

Use the relevant commands for the touched area.

Frontend:

```powershell
cd frontend
npm run lint
npm run build
```

Backend:

```powershell
cd backend
python -m pytest
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

External model references:

- Alibaba Cloud Model Studio embedding API: `https://help.aliyun.com/zh/model-studio/text-embedding-synchronous-api`
- Alibaba Cloud Model Studio text rerank API: `https://help.aliyun.com/zh/model-studio/text-rerank-api`

---

# V2.1: Knowledge Base Foundation

Goal: upgrade the current RAG demo into a durable, permission-aware, manageable knowledge base.

V2.1 must not implement hybrid retrieval, rerank, eval, Redis cache, LangSmith, DOCX parsing, multi-workspace switching, or workspace invitations.

## Task 17: Postgres and Migration Foundation

Goal: introduce durable database infrastructure using Neon Postgres as the production target.

Allowed changes:

- `backend/requirements.txt`
- `backend/app/core/`
- `backend/app/db/` or equivalent database module
- `backend/alembic/`
- `backend/tests/`
- `backend/.env.example`

Requirements:

- Add SQLAlchemy 2.x, Alembic, and a Postgres driver.
- Add `DATABASE_URL` to backend settings and `.env.example`.
- Add a database session dependency usable by services and routes.
- Add Alembic configuration that reads `DATABASE_URL`.
- Keep tests independent from a live Neon database by allowing an override test database URL.

Constraints:

- No auth routes.
- No RAG behavior changes.
- No frontend changes.

Acceptance criteria:

- Database settings load from environment variables.
- Alembic can discover metadata and run migrations in tests.
- Unit tests cover settings and session construction with a test database URL.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 18: JWT Authentication

Goal: add self-hosted login and current-user APIs.

Allowed changes:

- `backend/app/api/`
- `backend/app/core/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/app/db/`
- `backend/alembic/`
- `backend/tests/`
- `backend/.env.example`

Endpoints:

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

Requirements:

- Add user persistence with email, display name, hashed password, active flag, created time, and updated time.
- Use JWT Bearer tokens for API authentication.
- Add settings for JWT secret, algorithm, and expiration.
- Use a modern password hashing library.
- Seed or test-create an initial admin user through test fixtures or a setup function.
- Return standard response envelopes for JSON responses.

Constraints:

- No RBAC enforcement beyond "authenticated user required".
- No frontend login UI yet.
- No admin CRUD yet.

Acceptance criteria:

- Valid credentials return an access token.
- Invalid credentials fail with a standard error response.
- `/api/v1/auth/me` returns the authenticated user.
- Protected dependency rejects missing or invalid tokens.
- Tests cover login success, login failure, and current-user lookup.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 19: RBAC and Default Workspace

Goal: add role, permission, and workspace authorization primitives.

Allowed changes:

- `backend/app/core/`
- `backend/app/db/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/alembic/`
- `backend/tests/`

Requirements:

- Add tables or models for roles, permissions, user-role assignments, workspaces, and workspace memberships.
- Create one default workspace used by V2.1.
- Define baseline roles: `user`, `document_admin`, and `system_admin`.
- Define permissions for document upload, document view, document delete, document reindex, knowledge query, user management, role management, and workspace management.
- Add service-level helpers for permission checks.

Constraints:

- No multi-workspace switching UI.
- No workspace invitations.
- No RAG query changes yet.

Acceptance criteria:

- A user can have one or more roles.
- Permission checks return deterministic allow or deny results.
- Default workspace exists after seed/setup.
- Tests cover role assignment and permission matrix behavior.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 20: Document Lifecycle Models

Goal: persist document, chunk, and ingestion job state.

Allowed changes:

- `backend/app/db/`
- `backend/app/schemas/`
- `backend/app/storage/`
- `backend/app/services/`
- `backend/alembic/`
- `backend/tests/`

Requirements:

- Add durable document records with `document_id`, title, content hash, owner user, workspace, permission scope, status, delete marker, error message, created time, and updated time.
- Add lifecycle status fields for parse, chunk, embedding, and index progress.
- Add durable chunk records with `chunk_id`, document ID, chunk index, text, character offsets, page number, and metadata.
- Add ingestion job records with job status, failure reason, started time, completed time, and retry/reindex metadata.
- Replace or wrap the in-memory RAG document repository behind a durable repository interface.

Constraints:

- No parser changes.
- No Chroma metadata changes.
- No frontend changes.

Acceptance criteria:

- Document lifecycle state can be created, updated, failed, deleted, and read back.
- Chunk metadata is stored durably.
- Ingestion jobs record status transitions.
- Tests cover document state transitions and deletion markers.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 21: TXT, Markdown, and PDF Parser Layer

Goal: add deterministic document parsing before chunking.

Allowed changes:

- `backend/app/services/`
- `backend/app/schemas/`
- `backend/tests/`
- `backend/requirements.txt`

Requirements:

- Add a parser interface that returns normalized text plus source metadata.
- Support `.txt`, `.md`, `.markdown`, and `.pdf`.
- Preserve PDF page numbers so chunks can carry page metadata.
- Reject unsupported file types with a standard error response.
- Add file size and empty-content validation.

Constraints:

- No DOCX parsing.
- No frontend upload UI changes unless strictly required by backend request shape.
- No embedding or Chroma behavior changes.

Acceptance criteria:

- TXT and Markdown parse deterministically.
- PDF parsing returns text with page metadata.
- Unsupported files and empty documents produce clear errors.
- Tests cover TXT, Markdown, PDF, unsupported type, and empty content.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 22: Background Ingestion Job Flow

Goal: move parsing, chunking, embedding, and indexing into a tracked background ingestion flow.

Allowed changes:

- `backend/app/api/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/app/storage/`
- `backend/tests/`

Endpoints:

- Extend `POST /api/v1/rag/documents`
- Extend `POST /api/v1/rag/ingest`
- Add `GET /api/v1/rag/documents/{document_id}`
- Add `GET /api/v1/rag/ingestion-jobs/{job_id}`

Requirements:

- Registering or uploading a document creates a durable document record.
- Ingesting a document creates an ingestion job and returns job/document status.
- The job flow updates parse, chunk, embedding, and index states.
- A failed step records `error_message` and leaves the document inspectable.
- Reindex requests mark stale chunks and create a new job.

Constraints:

- No Redis queue requirement.
- In-process background execution is acceptable for V2.1.
- No hybrid retrieval or rerank.

Acceptance criteria:

- Document status is observable before, during, and after ingestion.
- Failures preserve failure reason and do not leave a document falsely marked indexed.
- Reindex creates a new job without changing the document ID.
- Tests cover success, failure, and reindex state transitions.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 23: Alibaba Embedding Provider

Goal: replace the default placeholder embedding path with a switchable real provider.

Allowed changes:

- `backend/app/ai/`
- `backend/app/core/`
- `backend/tests/`
- `backend/.env.example`

Requirements:

- Add an embedding provider interface with provider selection through settings.
- Add Alibaba Cloud Model Studio provider using `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL`, and `EMBEDDING_MODEL`.
- Default `EMBEDDING_MODEL` to `text-embedding-v1`.
- Keep deterministic fake embeddings available for tests.
- Expose a clear configuration error when a real provider is selected without credentials.

Constraints:

- DeepSeek remains the answer generation model.
- No rerank provider yet.
- No frontend changes.

Acceptance criteria:

- The embedding provider can be selected by configuration.
- Alibaba requests are tested with mocked network calls.
- Missing key behavior is tested.
- Existing Chroma tests can still use deterministic embeddings.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 24: Chroma Metadata and Permission Filters

Goal: store citation and authorization metadata in Chroma and filter retrieval by user access.

Allowed changes:

- `backend/app/storage/`
- `backend/app/services/`
- `backend/app/schemas/`
- `backend/tests/`

Requirements:

- Write `document_id`, `chunk_id`, `owner_user_id`, `workspace_id`, permission scope, page number, title, chunk index, content hash, and lifecycle version into Chroma metadata.
- Add search filters based on the authenticated user's workspace and permissions.
- Preserve current similarity search behavior for permitted documents.
- Add a safe fallback when Chroma contains legacy chunks without full metadata.

Constraints:

- No query rewrite.
- No hybrid retrieval.
- No rerank.
- No frontend changes.

Acceptance criteria:

- A normal user cannot retrieve chunks outside their access scope.
- A system admin can retrieve permitted admin-scope chunks.
- Metadata survives indexing and search.
- Tests cover metadata writes, permission-filtered search, and legacy metadata behavior.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 25: Authenticated RAG Query and Citation Schema

Goal: require authentication for Knowledge Agent queries and return richer citation sources.

Allowed changes:

- `backend/app/api/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/tests/`
- `frontend/types/`
- `frontend/lib/`

Endpoint:

- Extend `POST /api/v1/rag/query`

Requirements:

- Require Bearer JWT for RAG query.
- Check `knowledge.query` permission before retrieval.
- Apply permission-filtered Chroma search.
- Extend source response fields to include `document_id`, `chunk_id`, `title`, `page_number`, `chunk_index`, `score`, `rerank_score`, and `metadata`.
- Preserve answer generation through DeepSeek.

Constraints:

- `rerank_score` should be nullable in V2.1.
- No query rewrite.
- No hybrid retrieval.
- No debug trace.

Acceptance criteria:

- Unauthenticated queries are rejected.
- Users without query permission are rejected.
- Users only receive sources they can access.
- Frontend types match backend source schema.
- Tests cover auth, permission denial, permitted retrieval, and citation payload shape.

Verification commands:

```powershell
cd backend
python -m pytest
```

```powershell
cd frontend
npm run lint
npm run build
```

## Task 26: Admin API for Knowledge Base Management

Goal: expose admin CRUD and lifecycle actions through backend APIs.

Allowed changes:

- `backend/app/api/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/tests/`

Endpoints:

- `/api/v1/admin/users`
- `/api/v1/admin/roles`
- `/api/v1/admin/permissions`
- `/api/v1/admin/workspaces`
- `/api/v1/admin/documents`
- `/api/v1/admin/ingestion-jobs`

Requirements:

- Add list, detail, create, update, and disable/delete operations where applicable.
- Add document delete and reindex actions.
- Require admin permissions for every admin endpoint.
- Return standard response envelopes.
- Keep route handlers thin and delegate to services.

Constraints:

- No admin frontend yet.
- No multi-workspace switching.
- No Redis cache invalidation yet.

Acceptance criteria:

- System admins can manage users, roles, permissions, workspaces, documents, and jobs.
- Non-admin users cannot access admin endpoints.
- Delete and reindex actions update durable document/job state.
- Tests cover success and permission denial for each endpoint group.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 27: Frontend Auth Shell

Goal: add frontend login state and authenticated API helpers.

Allowed changes:

- `frontend/app/`
- `frontend/components/`
- `frontend/features/`
- `frontend/lib/`
- `frontend/types/`

Requirements:

- Add a login page or login panel.
- Store and attach Bearer JWT for authenticated API calls.
- Add `GET /api/v1/auth/me` helper.
- Protect Knowledge Agent and admin routes from anonymous access.
- Show clear unauthorized and expired-session states.

Constraints:

- No admin CRUD UI yet.
- No visual redesign of unrelated pages.
- No external auth provider.

Acceptance criteria:

- User can log in from the frontend.
- Authenticated API calls include Bearer JWT.
- Anonymous users cannot use Knowledge Agent.
- Expired or invalid sessions can recover by logging in again.

Verification commands:

```powershell
cd frontend
npm run lint
npm run build
```

## Task 28: Admin Document Management UI

Goal: build the admin UI for document lifecycle operations.

Allowed changes:

- `frontend/app/admin/`
- `frontend/features/admin/`
- `frontend/lib/`
- `frontend/types/`

Requirements:

- Add document list with status, owner, workspace, permission scope, updated time, and failure reason.
- Add document detail view with chunks, ingestion jobs, source metadata, and lifecycle states.
- Add delete and reindex actions.
- Show loading, empty, forbidden, and error states.
- Use admin API helpers in `frontend/lib`.

Constraints:

- No user/role management UI in this task.
- No RAG debug page.
- No unrelated layout redesign.

Acceptance criteria:

- Admin can inspect document state and ingestion failures.
- Admin can delete and reindex documents.
- Non-admin users cannot access the page.
- UI remains usable on mobile.

Verification commands:

```powershell
cd frontend
npm run lint
npm run build
```

## Task 29: Admin User, Role, Permission, and Workspace UI

Goal: complete the admin management surface for RBAC and workspace records.

Allowed changes:

- `frontend/app/admin/`
- `frontend/features/admin/`
- `frontend/lib/`
- `frontend/types/`

Requirements:

- Add user list and user detail/edit surfaces.
- Add role and permission management surfaces.
- Add default workspace management surface.
- Allow assigning roles to users.
- Respect backend permission errors in the UI.

Constraints:

- No multi-workspace switcher for normal users.
- No invitation flow.
- No unrelated frontend redesign.

Acceptance criteria:

- System admins can manage users, roles, permissions, and the default workspace.
- Role assignment changes affect backend permission checks.
- Non-admin users cannot access admin management pages.
- Frontend types match admin API response shapes.

Verification commands:

```powershell
cd frontend
npm run lint
npm run build
```

## Task 30: Knowledge Agent Auth and Citation Rendering

Goal: update the Knowledge Agent UI for V2.1 authenticated usage and richer citations.

Allowed changes:

- `frontend/app/agents/knowledge/`
- `frontend/features/knowledge-agent/`
- `frontend/lib/`
- `frontend/types/`

Requirements:

- Require logged-in state before document ingestion or query.
- Render source title, page number, chunk index, score, nullable rerank score, and metadata.
- Show document ingestion status after upload or reindex.
- Show authorization errors distinctly from model or retrieval failures.

Constraints:

- No hybrid retrieval UI.
- No debug trace page.
- No admin CRUD behavior.

Acceptance criteria:

- Authenticated users can ingest permitted documents and ask questions.
- Unauthorized users see a clear access error.
- Citation cards show the richer V2.1 source metadata.
- Existing simple RAG workflow remains usable.

Verification commands:

```powershell
cd frontend
npm run lint
npm run build
```

---

# V2.2: Retrieval Quality

Goal: improve answer quality through query rewrite, hybrid retrieval, fusion, rerank, and context assembly.

V2.2 must not implement new admin-system scope, Redis cache, local eval, LangSmith, or streaming answers.

## Task 31: Query Rewrite Service

Goal: produce retrieval-ready query variants from the user's question.

Allowed changes:

- `backend/app/ai/`
- `backend/app/services/`
- `backend/app/schemas/`
- `backend/tests/`

Requirements:

- Add a query rewrite service that can return the original question plus zero or more rewritten retrieval queries.
- Use DeepSeek through the existing client when model-based rewrite is enabled.
- Add a deterministic fallback that returns the original query when rewrite is disabled or unavailable.
- Track rewrite metadata for later debug traces.

Constraints:

- No keyword retrieval yet.
- No rerank.
- No frontend changes.

Acceptance criteria:

- Rewrite output is deterministic in disabled/fallback mode.
- Model-based rewrite is tested with mocked DeepSeek calls.
- Empty or invalid rewrite output falls back to the original question.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 32: Keyword Retriever

Goal: add exact-term retrieval for identifiers and precise text.

Allowed changes:

- `backend/app/services/`
- `backend/app/storage/`
- `backend/app/db/`
- `backend/tests/`

Requirements:

- Add a keyword retriever over durable chunk text.
- Use Postgres full-text search with `simple` configuration where practical.
- Include exact substring or token fallback for route paths, class names, config keys, and version strings.
- Apply the same user/workspace permission filters as vector retrieval.
- Return a normalized hit shape compatible with vector hits.

Constraints:

- No RRF fusion yet.
- No rerank.
- No frontend changes.

Acceptance criteria:

- Keyword retriever finds exact identifiers that vector search may miss.
- Permission filters apply to keyword results.
- Tests cover normal keywords, identifiers, and unauthorized chunks.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 33: Hybrid Retrieval and RRF Fusion

Goal: combine vector and keyword retrieval into one ranked candidate list.

Allowed changes:

- `backend/app/services/`
- `backend/app/schemas/`
- `backend/tests/`

Requirements:

- Run vector retrieval and keyword retrieval for all rewrite queries.
- Merge candidates by `document_id` and `chunk_id`.
- Use Reciprocal Rank Fusion for deterministic ranking.
- Preserve per-route scores and source metadata for debug output.
- Keep `top_k` behavior predictable after fusion.

Constraints:

- No rerank provider yet.
- No context assembler overhaul yet.
- No frontend changes.

Acceptance criteria:

- Duplicate candidates are merged deterministically.
- RRF ranking is stable for repeated inputs.
- Vector-only and keyword-only hits can both appear in final candidates.
- Tests cover fusion ordering and duplicate handling.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 34: Qwen3 Rerank Provider

Goal: add a switchable rerank layer using Alibaba Cloud Model Studio.

Allowed changes:

- `backend/app/ai/`
- `backend/app/core/`
- `backend/app/services/`
- `backend/tests/`
- `backend/.env.example`

Requirements:

- Add a rerank provider interface.
- Add Alibaba provider using `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL`, and `RERANK_MODEL`.
- Default `RERANK_MODEL` to `qwen3-rerank`.
- Keep deterministic fake rerank provider for tests.
- Rerank hybrid candidates before context assembly when enabled.

Constraints:

- No answer generation model change.
- No LangSmith.
- No frontend changes.

Acceptance criteria:

- Rerank can be enabled or disabled by settings.
- Missing credentials produce clear configuration errors only when real rerank is selected.
- Mocked Alibaba rerank tests cover request/response handling.
- Rerank scores are preserved for citations and debug traces.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 35: Context Assembler

Goal: replace simple top-k concatenation with a structured context assembly layer.

Allowed changes:

- `backend/app/services/`
- `backend/app/schemas/`
- `backend/tests/`

Requirements:

- De-duplicate chunks by `document_id` and `chunk_id`.
- Optionally include adjacent chunks from the same document when within token budget.
- Preserve document title, page number, chunk index, score, rerank score, and metadata.
- Enforce a configurable context token or character budget.
- Produce prompt-ready context plus structured selected-source records.

Constraints:

- No frontend debug page.
- No Redis cache.
- No streaming response.

Acceptance criteria:

- Duplicate chunks are removed.
- Adjacent expansion does not exceed the context budget.
- Citation metadata remains aligned with selected context.
- Tests cover de-duplication, adjacent expansion, budget trimming, and empty context.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 36: Query API Debug Trace

Goal: expose optional retrieval trace data from the RAG query API.

Allowed changes:

- `backend/app/api/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/tests/`
- `frontend/types/`

Endpoint:

- Extend `POST /api/v1/rag/query`

Requirements:

- Add optional request field such as `include_debug`.
- When enabled and authorized, include rewrite output, vector hits, keyword hits, fusion scores, rerank scores, selected context, citations, latency, and model usage when available.
- Keep default responses concise when `include_debug` is false.
- Ensure debug output does not include unauthorized chunks.

Constraints:

- No standalone debug UI yet.
- No Redis cache.
- No LangSmith.

Acceptance criteria:

- Normal query responses remain compatible.
- Debug responses include every major retrieval decision.
- Unauthorized chunks never appear in debug output.
- Tests cover debug enabled, debug disabled, and permission-filtered traces.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 37: Frontend Citation and Source Quality

Goal: improve the Knowledge Agent source display for hybrid and reranked retrieval.

Allowed changes:

- `frontend/features/knowledge-agent/`
- `frontend/lib/`
- `frontend/types/`

Requirements:

- Render vector score, keyword/fusion data when available, rerank score, page number, chunk index, and document title.
- Keep source cards compact and scan-friendly.
- Show clear empty retrieval, insufficient context, and unauthorized states.
- Preserve mobile usability.

Constraints:

- No standalone RAG debug page.
- No admin page changes.
- No backend behavior changes.

Acceptance criteria:

- V2.2 source fields render without layout breakage.
- Missing optional fields render gracefully.
- Build and lint pass.

Verification commands:

```powershell
cd frontend
npm run lint
npm run build
```

---

# V2.3: Evaluation, Cache, Debug, and Stability

Goal: make the knowledge base measurable, cache-aware, debuggable, and safer under failure.

V2.3 must not make LangSmith a requirement and must not introduce local LLM hosting.

## Task 38: Local RAG Eval Dataset

Goal: add a repository-local evaluation dataset for repeatable RAG checks.

Allowed changes:

- `backend/evals/`
- `backend/tests/`
- `docs/`

Requirements:

- Add a small fixture corpus for evaluation.
- Add eval questions with expected documents, expected chunks or pages, expected answer notes, and citation expectations.
- Document how to extend the dataset.
- Keep the dataset small enough for local runs.

Constraints:

- No external tracing service.
- No Redis cache.
- No frontend changes.

Acceptance criteria:

- Dataset can be loaded by tests or scripts.
- Each eval case includes retrieval and answer expectations.
- Documentation explains the dataset format.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 39: Local Eval Runner and Metrics

Goal: add a local runner that measures retrieval, answer, and citation quality.

Allowed changes:

- `backend/evals/`
- `backend/app/services/`
- `backend/tests/`

Requirements:

- Add a command or test helper that runs the eval dataset.
- Report retrieval hit rate, answer pass/fail, citation correctness, and hallucination flags.
- Support deterministic mocked model output for unit tests.
- Make the runner usable without LangSmith.

Constraints:

- No frontend debug page.
- No cache behavior changes.

Acceptance criteria:

- Eval runner produces repeatable metrics locally.
- Failing cases are reported with enough detail to debug.
- Tests cover metric calculation.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 40: Redis Cache Adapter

Goal: add a cache abstraction with Redis support and in-memory fallback.

Allowed changes:

- `backend/app/core/`
- `backend/app/storage/`
- `backend/tests/`
- `backend/requirements.txt`
- `backend/.env.example`

Requirements:

- Add cache interface with `get`, `set`, `delete`, and prefix invalidation helpers.
- Use Redis when `REDIS_URL` is configured and dependency is installed.
- Use in-memory fallback for local development and tests.
- Define cache key components: user identity, permission scope, workspace, knowledge base version, retrieval strategy version, model version, and request hash.

Constraints:

- Do not cache RAG answers yet.
- Do not require Redis for tests.
- No frontend changes.

Acceptance criteria:

- Cache adapter works with in-memory fallback.
- Redis client construction is tested with mocks.
- Cache keys differ across users, workspaces, permission scopes, and strategy versions.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 41: RAG Cache Integration

Goal: cache expensive RAG pipeline steps without leaking data across permissions.

Allowed changes:

- `backend/app/services/`
- `backend/app/ai/`
- `backend/app/storage/`
- `backend/tests/`

Requirements:

- Add embedding cache.
- Add query rewrite cache.
- Add retrieval result cache.
- Add final answer cache.
- Include user, permission scope, workspace, knowledge base version, retrieval strategy version, model version, and request hash in keys.
- Add cache bypass or refresh option for debugging.

Constraints:

- No frontend debug page yet.
- No cache for unauthorized requests.
- No cross-user answer reuse unless permission scope and knowledge base version match exactly.

Acceptance criteria:

- Repeated equivalent requests can hit cache.
- Permission or knowledge base version changes produce different keys.
- Cached results preserve source metadata.
- Tests cover hit, miss, bypass, and permission isolation.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 42: RAG Debug Page

Goal: build a frontend page for inspecting retrieval decisions.

Allowed changes:

- `frontend/app/`
- `frontend/features/`
- `frontend/lib/`
- `frontend/types/`

Requirements:

- Add an authenticated debug page for authorized admin or document-admin users.
- Submit a question with `include_debug` enabled.
- Render query rewrite output, vector hits, keyword hits, RRF/fusion scores, rerank scores, selected context, prompt input summary, answer, citations, latency, token usage when available, and cache status.
- Show loading, empty, forbidden, and error states.

Constraints:

- No backend behavior changes except API helper typing if needed.
- No public anonymous debug access.
- No LangSmith integration.

Acceptance criteria:

- Authorized users can inspect a complete RAG trace.
- Unauthorized users cannot access the page.
- Debug content remains readable on desktop and usable on mobile.

Verification commands:

```powershell
cd frontend
npm run lint
npm run build
```

## Task 43: Delete, Reindex, and Cache Synchronization

Goal: keep Postgres, Chroma, and Redis cache consistent when documents change.

Allowed changes:

- `backend/app/services/`
- `backend/app/storage/`
- `backend/tests/`

Requirements:

- Deleting a document marks it deleted in Postgres, removes or tombstones Chroma chunks, and invalidates affected cache keys.
- Reindexing a document creates a new lifecycle version, refreshes chunks, refreshes Chroma entries, and invalidates affected cache keys.
- Query paths ignore deleted or stale document versions.
- Failures leave the previous indexed version available unless explicitly deleted.

Constraints:

- No new frontend screens.
- No production queue requirement.
- No LangSmith.

Acceptance criteria:

- Deleted documents cannot be retrieved or cited.
- Reindexed documents return new chunk metadata.
- Cache entries are invalidated on delete and reindex.
- Tests cover delete, reindex success, reindex failure, and stale version filtering.

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 44: Stability, Limits, and Structured Logging

Goal: add operational safeguards for the RAG pipeline.

Allowed changes:

- `backend/app/core/`
- `backend/app/api/`
- `backend/app/services/`
- `backend/tests/`
- `docs/`

Requirements:

- Add configurable file size limits.
- Add timeout handling around external embedding, rerank, and LLM calls.
- Add rate limiting or request throttling for expensive RAG endpoints.
- Add structured logs for ingestion and query pipeline stages.
- Return clear user-facing errors for validation, permissions, external model failure, timeout, and retrieval failure.
- Document the main failure modes and recovery behavior.

Constraints:

- No production observability vendor integration.
- No local LLM hosting.
- No frontend redesign.

Acceptance criteria:

- Oversized files are rejected before parsing.
- External model timeouts produce standard error responses and durable job errors.
- Expensive endpoints are throttled according to configuration.
- Logs include enough context to debug document ID, job ID, user ID, workspace ID, and pipeline stage.
- Tests cover limits, timeout handling, and error response shape.

Verification commands:

```powershell
cd backend
python -m pytest
```

---

# Future V3: Agent Workflows

The previous Browser Agent, Office Agent, and task event work remains outside the RAG V2 upgrade line. Do not extend those modules while executing V2.1, V2.2, or V2.3 unless the user explicitly asks for agent workflow work.
