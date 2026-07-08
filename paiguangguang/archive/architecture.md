# Architecture

## 1. System Overview

```mermaid
flowchart LR
  U[User Browser] --> FE[Next.js Frontend]
  FE --> API[FastAPI Backend]

  API --> Core[Core API Layer]
  API --> AI[AI Orchestration Layer]
  API --> Store[Storage Layer]

  Core --> Auth[Auth and RBAC]
  Core --> Admin[Admin APIs]
  AI --> DeepSeek[DeepSeek API<br/>OpenAI Compatible]
  AI --> DashScope[Alibaba Model Studio<br/>Embedding and Rerank]
  AI --> Portfolio[Portfolio Chat Service]
  AI --> RAG[RAG Service]
  AI --> Agents[Agent Services]
  AI --> Tools[Tool Calling Layer]

  RAG --> Chroma[(Chroma Vector DB)]
  RAG --> Postgres[(Neon Postgres)]
  Auth --> Postgres
  Admin --> Postgres
  RAG --> RedisCache[(Redis RAG Cache)]
  Agents --> Tools
  Agents --> Redis[(Redis Task State)]
  Store --> Chroma
  Store --> Postgres
  Store --> RedisCache
  Store --> Redis

  Tools --> Browser[Mock Browser Search Tool]
  Tools --> Office[Mock Office Tools]
```

## 2. Layer Responsibilities

| Layer | Responsibility |
| --- | --- |
| Frontend | Pages, navigation, chat UI, upload UI, workflow visualization, API client |
| Backend API | FastAPI routes, request validation, response envelope, CORS, error handling |
| Auth and RBAC | JWT login, current user, role/permission checks, default workspace membership |
| Admin APIs | User, role, permission, workspace, document, and ingestion job management |
| Services | Business orchestration for chat, RAG, agents, tasks, and architecture graph data |
| AI Layer | DeepSeek client, Alibaba embedding/rerank providers, prompts, RAG pipeline, and future LangGraph workflow support |
| Tools | Mock browser search, mock office tools, retrieval tools |
| Storage | Chroma vector database, Neon Postgres knowledge base state, Redis RAG cache in V2.3, Redis task/event state for agent workflows when configured |

## 3. Directory Structure

```text
paiguangguang/
  frontend/
    app/
      page.tsx
      admin/
      agents/
      architecture/
    components/
    features/
      admin/
      portfolio-chat/
      knowledge-agent/
      browser-agent/
      office-agent/
      architecture-flow/
    lib/
    styles/
    types/
    public/

  backend/
    app/
      main.py
      core/
      api/
      schemas/
      services/
      ai/
      db/
      storage/
      tools/
      workers/
      utils/
    alembic/
    evals/
    tests/

  docs/
    PROJECT_SPEC.md
    architecture.md
    roadmap.md
    codex_tasks.md

  docker/
  .env.example
  README.md
```

## 4. Folder Responsibilities

| Folder | Responsibility |
| --- | --- |
| `frontend/app` | Next.js routes and page entry files |
| `frontend/components` | Reusable UI components only |
| `frontend/features` | Module-specific UI and client-side behavior |
| `frontend/lib` | API client, config, shared helpers |
| `frontend/types` | Shared frontend TypeScript types |
| `backend/app/core` | Settings, logging, CORS, errors, response envelope |
| `backend/app/api` | FastAPI routers grouped by module |
| `backend/app/schemas` | Pydantic request and response models |
| `backend/app/services` | Business logic and orchestration |
| `backend/app/ai` | LLM client, prompts, RAG pipeline, LangGraph workflows |
| `backend/app/db` | SQLAlchemy models, sessions, repositories, and Alembic metadata for Postgres |
| `backend/app/storage` | Chroma and Redis adapters |
| `backend/app/tools` | Agent-callable mock tools |
| `backend/app/workers` | Long-running task runners for task and agent workflows |

## 5. API Conventions

All JSON APIs use `/api/v1` prefix.

Standard JSON response envelope:

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

Error response envelope:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error"
  }
}
```

SSE endpoints may stream event payloads and do not need the JSON envelope per event.

## 6. FastAPI Route Design

| Method | Path | Phase | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/v1/health` | V1 | Health check |
| `POST` | `/api/v1/chat/portfolio` | V1 | Portfolio Chat request |
| `POST` | `/api/v1/auth/login` | V2.1 | Login and return JWT access token |
| `GET` | `/api/v1/auth/me` | V2.1 | Return the authenticated user |
| `POST` | `/api/v1/rag/documents` | V2.1 | Upload or register a document with lifecycle state |
| `POST` | `/api/v1/rag/ingest` | V2.1 | Start or run a tracked ingestion job |
| `GET` | `/api/v1/rag/documents/{document_id}` | V2.1 | Read document lifecycle state |
| `GET` | `/api/v1/rag/ingestion-jobs/{job_id}` | V2.1 | Read ingestion job state |
| `POST` | `/api/v1/rag/query` | V2.1-V2.3 | Retrieve permitted context and answer with citations, optional debug trace in V2.2 |
| `GET` | `/api/v1/rag/collections` | V2.1 | List Chroma collections |
| `GET/POST/PATCH/DELETE` | `/api/v1/admin/users` | V2.1 | Manage users |
| `GET/POST/PATCH/DELETE` | `/api/v1/admin/roles` | V2.1 | Manage roles |
| `GET/POST/PATCH/DELETE` | `/api/v1/admin/permissions` | V2.1 | Manage permissions |
| `GET/POST/PATCH/DELETE` | `/api/v1/admin/workspaces` | V2.1 | Manage workspace records |
| `GET/POST/PATCH/DELETE` | `/api/v1/admin/documents` | V2.1 | Manage document lifecycle and delete/reindex actions |
| `GET/PATCH` | `/api/v1/admin/ingestion-jobs` | V2.1 | Manage ingestion jobs |
| `GET` | `/api/v1/architecture/graphs/system` | Baseline | Return React Flow nodes and edges |
| `POST` | `/api/v1/agents/browser/run` | Baseline | Run mock Browser Agent workflow |
| `POST` | `/api/v1/agents/office/run` | Baseline | Run mock Office Agent workflow |
| `GET` | `/api/v1/tasks/{task_id}` | Baseline | Read long-running task state |
| `GET` | `/api/v1/tasks/{task_id}/events` | Baseline | Stream task events with SSE |

## 7. Request and Response Contracts

Portfolio Chat request:

```json
{
  "message": "string",
  "session_id": "string | null"
}
```

Portfolio Chat data:

```json
{
  "reply": "string",
  "session_id": "string"
}
```

RAG query request:

```json
{
  "question": "string",
  "collection": "string",
  "top_k": 5
}
```

RAG query data:

```json
{
  "answer": "string",
  "sources": [
    {
      "document_id": "string",
      "chunk_id": "string",
      "title": "string | null",
      "page_number": 1,
      "chunk_index": 0,
      "text": "string",
      "score": 0.0,
      "rerank_score": null,
      "metadata": {}
    }
  ]
}
```

V2.2 optional debug extension:

```json
{
  "include_debug": true,
  "debug": {
    "rewrites": [],
    "vector_hits": [],
    "keyword_hits": [],
    "fusion": [],
    "rerank": [],
    "selected_context": [],
    "latency_ms": 0,
    "model_usage": {}
  }
}
```

Agent run data:

```json
{
  "task_id": "string",
  "steps": [
    {
      "action": "string",
      "input": {},
      "result": {}
    }
  ],
  "final": {}
}
```

## 8. Implementation Constraints

- V1 must not require Chroma, Redis, LangGraph, file uploads, or real tools.
- V2.1 adds Postgres, JWT auth, RBAC, document lifecycle, real embeddings, Chroma metadata, permission-filtered RAG, citations, and admin management.
- V2.2 adds query rewrite, hybrid retrieval, RRF fusion, rerank, improved context assembly, and optional query debug traces.
- V2.3 adds local eval, Redis RAG cache, RAG debug UI, delete/reindex synchronization, and stability controls.
- Existing mock agent and task event endpoints are baseline portfolio demos. Future V3 work may extend those workflows with LangGraph-style orchestration and richer task execution behavior.
- Frontend must call backend through `frontend/lib` API helpers, not direct scattered fetch calls.
- Backend route handlers should stay thin and delegate logic to services.

## 9. Risk Controls

- DeepSeek API may differ from OpenAI in streaming, error shape, and model parameters, so all calls must go through one backend client wrapper.
- Alibaba Model Studio embedding and rerank behavior must be isolated behind provider wrappers and mocked in tests.
- Authentication and RBAC checks must happen before RAG retrieval so unauthorized chunks are never returned or exposed in debug traces.
- RAG quality depends on chunking, metadata, and source tracing, so V2 tasks must keep deterministic chunk IDs and citation metadata.
- Chroma persistence paths and embedding behavior must be testable locally, with fake embeddings used in unit tests where possible.
- Redis cache should not be introduced before V2.3, and Redis task state/SSE should remain agent-workflow scope rather than RAG V2 scope.
- Frontend and backend response shapes must stay aligned through `frontend/types` and `backend/app/schemas`.
- Agent demos must show steps and tool outputs, not only final answers, otherwise the portfolio loses its engineering proof.
