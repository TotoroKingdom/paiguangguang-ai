# Roadmap

## V1: Foundation + Portfolio Chat

Goal: create a runnable full-stack portfolio base with one working AI chat module.

Deliverables:

- Next.js frontend skeleton with routes `/`, `/agents/knowledge`, `/agents/browser`, `/agents/office`, `/architecture`
- FastAPI backend skeleton with `/api/v1/health`
- Shared response envelope for backend JSON APIs
- Basic navigation and layout
- Portfolio Chat backend API using DeepSeek
- Portfolio Chat UI connected to backend

Not included:

- No RAG
- No Chroma
- No Redis
- No LangGraph
- No file upload

Acceptance:

- Frontend starts locally
- Backend starts locally
- `/api/v1/health` returns the standard response envelope
- Portfolio Chat works end to end when `DEEPSEEK_API_KEY` is configured
- Missing API key produces a clear configuration error

Verification commands:

```powershell
cd frontend
npm run lint
npm run build
```

```powershell
cd backend
python -m pytest
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Current RAG Baseline

The existing Knowledge Agent is the baseline for V2 work. It already demonstrates a runnable RAG flow:

- Text upload or paste from the Knowledge Agent page
- Deterministic text chunking
- Chroma indexing and similarity search
- Context assembly for DeepSeek
- Answer generation with source chunks
- Frontend answer and source rendering

Architecture Visualization, mock Browser Agent, mock Office Agent, and task event endpoints are also baseline portfolio modules. V2 tasks should upgrade the Knowledge Agent baseline instead of re-implementing it from scratch.

## V2: Enterprise Knowledge Base Upgrade

Goal: upgrade the current RAG demo into a manageable, permission-aware, inspectable enterprise knowledge base.

V2 is split into three sub-phases. Each sub-phase must be implemented through the task list in `docs/codex_tasks.md`, one task at a time.

### V2.1: Knowledge Base Foundation

Goal: make documents, users, permissions, ingestion state, citations, and admin operations durable and controllable.

Deliverables:

- Neon Postgres connection through `DATABASE_URL`
- SQLAlchemy 2.x models and Alembic migrations
- Self-hosted JWT authentication with password hashing
- RBAC with users, roles, permissions, and a single default workspace
- Document lifecycle records with parse, chunk, embedding, index, delete, error, and update state
- TXT, Markdown, and PDF parsing, including PDF page numbers for citation metadata
- Background ingestion jobs that update durable status records
- Alibaba Cloud Model Studio embedding provider behind a switchable embedding interface
- Chroma writes with `document_id`, `chunk_id`, `user_id`, `workspace_id`, permission scope, page number, title, and chunk index metadata
- Permission-filtered RAG retrieval based on the authenticated user
- Citation-ready source metadata in query responses
- Admin API and frontend for users, roles, permissions, workspaces, documents, ingestion status, delete, and reindex actions

Not included:

- No hybrid retrieval
- No rerank
- No local eval runner
- No Redis cache
- No LangSmith
- No multi-workspace switching or invitations
- No DOCX parsing

Acceptance:

- A user must log in before using Knowledge Agent or admin pages
- A normal user cannot list, inspect, retrieve, or cite unauthorized documents
- An admin can manage users, roles, permissions, workspace records, documents, and ingestion jobs
- A document moves through registered, parsing, chunking, embedding, indexing, indexed, failed, deleted, and reindex-needed states as appropriate
- TXT, Markdown, and PDF files can be parsed into chunks with durable document and chunk metadata
- Chroma stores metadata required for permission filters and citation rendering
- RAG query responses include citation metadata suitable for frontend rendering
- The system can run against Neon Postgres through `DATABASE_URL`

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

### V2.2: Retrieval Quality

Goal: improve answer quality by replacing single-path similarity retrieval with a multi-stage retrieval pipeline.

Deliverables:

- Query rewrite service that can produce one or more retrieval queries
- Keyword retrieval for exact terms such as class names, route paths, config keys, version numbers, and identifiers
- Hybrid retrieval combining vector search and keyword search
- Reciprocal Rank Fusion (RRF) for multi-route result merging
- Rerank provider behind a switchable rerank interface
- Context assembler with de-duplication, adjacent chunk expansion, token budget control, metadata preservation, and prompt context formatting
- RAG query debug trace containing rewrite output, vector hits, keyword hits, fusion scores, rerank scores, selected context, and citations
- Frontend citation/source rendering improvements that expose page, chunk, score, rerank score, and metadata clearly

Not included:

- No new admin user-system scope
- No Redis cache
- No local eval runner
- No LangSmith
- No streaming answer endpoint

Acceptance:

- Exact keyword questions can retrieve matching chunks even when semantic similarity alone is weak
- Hybrid results are merged deterministically with RRF
- Rerank can be enabled when `DASHSCOPE_API_KEY` is configured and safely mocked in tests
- Context assembly avoids duplicate chunks and preserves citation metadata
- Query responses can optionally include a debug trace for inspection
- Existing RAG answer behavior remains compatible for normal frontend use

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

### V2.3: Evaluation, Cache, Debug, and Stability

Goal: make the RAG system measurable, cache-aware, debuggable, and operationally safer.

Deliverables:

- Local RAG eval dataset stored in the repository
- Eval runner for retrieval accuracy, answer quality, citation correctness, and hallucination checks
- Redis cache adapter with in-memory fallback for local development
- Cache keys that include user identity, permission scope, workspace, knowledge base version, retrieval strategy version, and model version
- Embedding cache, query rewrite cache, retrieval result cache, and final answer cache
- RAG debug page for inspecting rewrite, retrieval, fusion, rerank, selected context, prompt input, answer, citations, latency, and token usage
- Delete and reindex synchronization across Postgres, Chroma, and Redis cache
- Failure recovery, timeout handling, file size limits, rate limiting, user-facing errors, and structured logs

Not included:

- No LangSmith requirement
- No production queue system
- No real-time collaborative admin features
- No local LLM hosting

Acceptance:

- A fixed eval dataset can be run locally and produces repeatable metrics
- Redis cache reduces repeated work without leaking data across users or permission scopes
- Deleting or reindexing a document invalidates affected Chroma entries and cache entries
- The debug page shows every major retrieval decision used to answer a question
- Failures expose clear status, logs, and user-facing errors without corrupting document state

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

## Future V3: Agent Workflow Enhancements

Goal: improve the existing mock tool-calling agent demos and visible task execution state after the knowledge base upgrade.

Deliverables:

- Browser Agent workflow improvements
- Office Agent workflow improvements
- Richer agent step traces with structured output
- Redis-backed task state if long-running execution needs more durable state
- SSE task event improvements
- Optional LangGraph orchestration for agent state flow

Not included:

- No real browser automation
- No real Office file editing
- No local LLM hosting

Acceptance:

- Browser Agent shows plan, mock search steps, intermediate results, and final answer
- Office Agent shows tool calls and structured final result
- Task status endpoint returns current state
- SSE endpoint streams task progress when a task is running

Verification commands:

```powershell
cd frontend
npm run lint
npm run build
```

```powershell
cd backend
python -m pytest
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
