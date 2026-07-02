# Codex Execution Tasks

This file is the only task execution source of truth for Codex.

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
- Do not require Chroma, Redis, or LangGraph before the phase that introduces them.
- Add or update tests when the task changes backend behavior.

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

---

# Phase 1: Project Initialization

## Task 1: Initialize Frontend

Goal: create a runnable Next.js frontend skeleton.

Allowed changes:

- `frontend/`
- root package metadata only if required by the frontend setup

Requirements:

- Next.js App Router
- TypeScript
- Tailwind CSS
- Routes: `/`, `/agents/knowledge`, `/agents/browser`, `/agents/office`, `/architecture`
- Basic placeholder content for each route

Constraints:

- No API calls
- No AI logic
- No backend integration
- No React Flow yet

Acceptance criteria:

- `frontend` project exists
- all required routes load
- basic navigation exists
- no browser console errors from missing routes

Verification commands:

```powershell
cd frontend
npm run lint
npm run build
npm run dev
```

## Task 2: Initialize Backend

Goal: create a runnable FastAPI backend skeleton.

Allowed changes:

- `backend/`
- `.env.example`

Requirements:

- FastAPI app entry at `backend/app/main.py`
- modular folders from `docs/architecture.md`
- CORS enabled for local frontend development
- standard response envelope
- endpoint: `GET /api/v1/health`

Response data:

```json
{
  "success": true,
  "data": {
    "status": "ok"
  },
  "error": null
}
```

Constraints:

- No DeepSeek integration
- No Chroma
- No Redis
- No business modules beyond health

Acceptance criteria:

- backend starts successfully
- `/api/v1/health` returns the standard envelope
- tests cover the health endpoint

Verification commands:

```powershell
cd backend
python -m pytest
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

## Task 3: Frontend Layout System

Goal: create the base UI layout and navigation.

Allowed changes:

- `frontend/app/`
- `frontend/components/`
- `frontend/styles/`

Requirements:

- navigation between all required routes
- shared page layout wrapper
- placeholder pages for all modules
- responsive desktop and mobile layout

Constraints:

- No API calls
- No AI logic
- No state management beyond local UI state

Acceptance criteria:

- navigation works
- all pages render with consistent layout
- active route or page context is visible

Verification commands:

```powershell
cd frontend
npm run lint
npm run build
npm run dev
```

---

# Phase 2: Portfolio Chat MVP

## Task 4: DeepSeek Client Wrapper

Goal: create an isolated LLM client module.

Allowed changes:

- `backend/app/ai/`
- `backend/app/core/`
- `backend/tests/`
- `.env.example`

Requirements:

- DeepSeek base URL: `https://api.deepseek.com`
- OpenAI-compatible chat request format
- read API key from `DEEPSEEK_API_KEY`
- clear error when API key is missing
- unit tests must mock external network calls

Constraints:

- No route changes except internal imports if needed
- No business prompt logic
- No frontend changes

Acceptance criteria:

- client can be instantiated from settings
- missing key behavior is tested
- successful mocked response is tested

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 5: Portfolio Chat API

Goal: create the backend API for Portfolio Chat.

Allowed changes:

- `backend/app/api/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/app/ai/`
- `backend/tests/`

Endpoint:

- `POST /api/v1/chat/portfolio`

Request:

```json
{
  "message": "string",
  "session_id": "string | null"
}
```

Response data:

```json
{
  "reply": "string",
  "session_id": "string"
}
```

Requirements:

- use static portfolio/profile context
- maintain simple in-memory session history for V1
- return standard response envelope
- tests must mock DeepSeek responses

Constraints:

- No RAG
- No tools
- No Chroma
- No Redis
- No streaming endpoint yet

Acceptance criteria:

- endpoint validates input
- endpoint returns reply and session ID
- session memory works within the running backend process
- tests cover success and validation failure

Verification commands:

```powershell
cd backend
python -m pytest
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Task 6: Portfolio Chat UI

Goal: connect the homepage chat UI to the Portfolio Chat API.

Allowed changes:

- `frontend/app/`
- `frontend/features/portfolio-chat/`
- `frontend/lib/`
- `frontend/types/`

Requirements:

- chat input
- message list
- loading state
- error state
- API helper in `frontend/lib`
- calls `POST /api/v1/chat/portfolio`

Constraints:

- No RAG UI
- No file upload
- No Browser Agent UI behavior
- No Office Agent UI behavior

Acceptance criteria:

- user can send a message from the frontend
- assistant reply is displayed
- errors are visible and recoverable
- UI remains usable on mobile

Verification commands:

```powershell
cd frontend
npm run lint
npm run build
npm run dev
```

---

# Phase 3: Knowledge Agent RAG

## Task 7: Document Ingestion API

Goal: upload or register documents and convert them into deterministic text chunks.

Allowed changes:

- `backend/app/api/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/app/storage/`
- `backend/tests/`

Endpoints:

- `POST /api/v1/rag/documents`
- `POST /api/v1/rag/ingest`

Requirements:

- support plain text input for MVP
- fixed-size chunking with deterministic output
- return document ID and chunk metadata
- tests cover chunking behavior

Constraints:

- No embeddings
- No Chroma writes
- No LLM calls
- No frontend changes

Acceptance criteria:

- text can be ingested into chunks
- same input produces same chunks
- invalid input returns standard error envelope

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 8: Chroma Retrieval Layer

Goal: add vector storage and similarity retrieval.

Allowed changes:

- `backend/app/ai/`
- `backend/app/storage/`
- `backend/app/services/`
- `backend/tests/`
- `.env.example`

Requirements:

- Chroma integration
- embedding wrapper
- store chunks with metadata
- similarity search with configurable `top_k`
- tests use deterministic fake embeddings where possible

Constraints:

- No RAG answer generation yet
- No frontend changes
- No Redis
- No LangGraph

Acceptance criteria:

- chunks can be stored
- relevant chunks can be retrieved
- metadata is preserved

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 9: RAG Query API

Goal: create the Knowledge Agent query endpoint.

Allowed changes:

- `backend/app/api/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/app/ai/`
- `backend/tests/`

Endpoint:

- `POST /api/v1/rag/query`

Request:

```json
{
  "question": "string",
  "collection": "string",
  "top_k": 5
}
```

Response data:

```json
{
  "answer": "string",
  "sources": [
    {
      "doc_id": "string",
      "chunk_id": "string",
      "text": "string",
      "score": 0.0
    }
  ]
}
```

Requirements:

- retrieve relevant chunks
- assemble context
- call DeepSeek with context
- include citations/sources
- tests mock DeepSeek

Constraints:

- No reranking
- No streaming
- No LangGraph
- No frontend changes

Acceptance criteria:

- endpoint returns answer and sources
- empty retrieval is handled gracefully
- source metadata appears in response

Verification commands:

```powershell
cd backend
python -m pytest
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Task 10: Knowledge Agent UI

Goal: build the frontend page for the RAG demo.

Allowed changes:

- `frontend/app/agents/knowledge/`
- `frontend/features/knowledge-agent/`
- `frontend/lib/`
- `frontend/types/`

Requirements:

- text upload or paste area
- ingest action
- question input
- answer panel
- source/citation list
- loading and error states

Constraints:

- No Browser Agent implementation
- No Office Agent implementation
- No architecture graph implementation

Acceptance criteria:

- user can ingest text
- user can ask a question
- answer and sources render clearly
- mobile layout remains usable

Verification commands:

```powershell
cd frontend
npm run lint
npm run build
npm run dev
```

---

# Phase 4: Architecture Visualization

## Task 11: Architecture Graph API

Goal: provide graph data for the architecture visualization page.

Allowed changes:

- `backend/app/api/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/tests/`

Endpoint:

- `GET /api/v1/architecture/graphs/system`

Requirements:

- return React Flow compatible nodes and edges
- include node title, type, phase, and description
- return standard response envelope

Constraints:

- No frontend graph rendering
- No AI calls
- No database

Acceptance criteria:

- endpoint returns stable graph data
- tests cover response shape

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 12: Architecture Visualization UI

Goal: render the architecture graph with React Flow.

Allowed changes:

- `frontend/app/architecture/`
- `frontend/features/architecture-flow/`
- `frontend/lib/`
- `frontend/types/`

Requirements:

- fetch `GET /api/v1/architecture/graphs/system`
- render nodes and edges with React Flow
- clicking a node opens a detail panel
- loading and error states

Constraints:

- No new backend endpoints
- No Agent implementation
- No RAG behavior changes

Acceptance criteria:

- graph renders correctly
- node click behavior works
- layout works on desktop and mobile

Verification commands:

```powershell
cd frontend
npm run lint
npm run build
npm run dev
```

---

# Phase 5: Mock Agent Workflows

## Task 13: Browser Agent API

Goal: implement a mock browser research workflow.

Allowed changes:

- `backend/app/api/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/app/tools/`
- `backend/tests/`

Endpoint:

- `POST /api/v1/agents/browser/run`

Requirements:

- create a plan
- call mock search tool
- return intermediate results
- return final answer
- output structured steps

Constraints:

- No real web browsing
- No external search API
- No frontend changes
- LangGraph is optional for this task only if already introduced safely

Acceptance criteria:

- endpoint returns steps and final answer
- mock tool output is deterministic
- tests cover response shape

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 14: Office Agent API

Goal: implement a mock office automation workflow.

Allowed changes:

- `backend/app/api/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/app/tools/`
- `backend/tests/`

Endpoint:

- `POST /api/v1/agents/office/run`

Requirements:

- support mock tools: `generate_report`, `summarize_data`, `write_email`
- return step-by-step execution
- return structured final output

Constraints:

- No real Office file parsing
- No real file mutation
- No frontend changes

Acceptance criteria:

- endpoint returns steps and final output
- unsupported workflow returns standard error envelope
- tests cover success and unsupported workflow

Verification commands:

```powershell
cd backend
python -m pytest
```

## Task 15: Browser and Office Agent UI

Goal: connect both mock agent pages to their backend APIs.

Allowed changes:

- `frontend/app/agents/browser/`
- `frontend/app/agents/office/`
- `frontend/features/browser-agent/`
- `frontend/features/office-agent/`
- `frontend/lib/`
- `frontend/types/`

Requirements:

- prompt or workflow input
- run button
- visible execution steps
- final result panel
- loading and error states

Constraints:

- No real browser automation
- No real Office file editing
- No new backend behavior

Acceptance criteria:

- Browser Agent page displays plan, steps, and final answer
- Office Agent page displays tool steps and final result
- both pages work on mobile

Verification commands:

```powershell
cd frontend
npm run lint
npm run build
npm run dev
```

## Task 16: Task Events and SSE

Goal: add task status and event streaming for long-running agent workflows.

Allowed changes:

- `backend/app/api/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/app/storage/`
- `backend/app/workers/`
- `backend/tests/`

Endpoints:

- `GET /api/v1/tasks/{task_id}`
- `GET /api/v1/tasks/{task_id}/events`

Requirements:

- task status model
- event model
- Redis-backed storage if Redis is configured
- in-memory fallback allowed for local development
- SSE event stream for task progress

Constraints:

- No production queue system
- No authentication
- No frontend changes unless explicitly requested

Acceptance criteria:

- task status endpoint returns current state
- SSE endpoint streams progress events
- tests cover task state transitions

Verification commands:

```powershell
cd backend
python -m pytest
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
