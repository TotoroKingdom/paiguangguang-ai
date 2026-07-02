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

## V2: Knowledge Agent + Architecture Visualization

Goal: add the real RAG demo and visual architecture explanation.

Deliverables:

- Document upload/register API
- Deterministic text extraction and fixed-size chunking
- Embedding wrapper
- Chroma storage and similarity search
- RAG query API with answer and citations
- Knowledge Agent frontend page
- React Flow architecture page

Not included:

- No Browser Agent implementation
- No Office Agent implementation
- No LangGraph
- No Redis requirement unless explicitly needed by a task

Acceptance:

- Uploaded text can be chunked deterministically
- Chunks can be stored and retrieved from Chroma
- RAG answer includes source metadata
- Architecture graph renders and node detail panel works

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

## V3: Agent Workflows + Task Events

Goal: add mock tool-calling agents and visible task execution state.

Deliverables:

- Browser Agent mock workflow API and UI
- Office Agent mock workflow API and UI
- Agent step traces with structured output
- Redis-backed task state if long-running execution is introduced
- SSE task event endpoint
- Optional LangGraph orchestration for agent state flow

Not included:

- No real browser automation
- No real Office file editing
- No production authentication

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
