# AI Engineer Portfolio System

## 1. Project Goal

Build an interactive AI engineering portfolio website that demonstrates real full-stack AI application ability.

This is not a static resume site. It should behave like a mini AI product where visitors can see, use, and inspect AI workflows.

## 2. Unified Module Scope

The project contains five modules:

| Module | Route | Phase | Purpose |
| --- | --- | --- | --- |
| Portfolio Chat | `/` and chat panel | V1 | Chat with static personal/project profile data |
| Knowledge Agent | `/agents/knowledge` | V2.1-V2.3 | Enterprise knowledge base with authenticated RAG, document management, retrieval quality, citations, eval, cache, and debug tooling |
| Knowledge Admin | `/admin` | V2.1-V2.3 | Manage users, roles, permissions, workspaces, documents, ingestion jobs, and RAG debugging |
| Browser Agent | `/agents/browser` | V3 | Mock web research workflow showing planning, tool calls, and synthesis |
| Office Agent | `/agents/office` | V3 | Mock office automation workflow showing structured tool execution |
| Architecture Visualization | `/architecture` | Baseline | Interactive system and AI workflow visualization |

Portfolio Chat is the lightweight V1 assistant. Knowledge Agent is the main V2 product track. Browser Agent and Office Agent are separate tool-calling demos.

## 3. Page Requirements

| Route | Required Experience |
| --- | --- |
| `/` | Hero section with interactive Agent Workflow and RAG Pipeline previews, plus entry points to all modules |
| `/agents/knowledge` | Authenticated document upload, query input, answer panel, source/citation display, and retrieval errors |
| `/admin` | Authenticated admin workspace for users, roles, permissions, workspaces, documents, ingestion jobs, delete/reindex actions, and RAG debug views |
| `/agents/browser` | Research prompt input, visible plan, mock search steps, final answer |
| `/agents/office` | Workflow input, visible tool steps, structured result |
| `/architecture` | React Flow graph with clickable nodes and detail panel |

## 4. AI Workflow Requirements

All AI-facing modules should expose the workflow, not only the final answer.

Common pipeline:

```text
User Input -> Planner or Prompt Layer -> Tool/Retrieval Layer -> LLM Response -> Visible Result
```

Knowledge Agent requirements:

- Authenticated document upload and document lifecycle management
- TXT, Markdown, and PDF parsing
- Fixed-size chunking for the current baseline, with metadata preserved for later retrieval quality work
- Real embedding generation through a switchable provider, defaulting to Alibaba Cloud Model Studio `text-embedding-v1`
- Chroma vector retrieval with document, chunk, user, workspace, permission, page, title, and chunk index metadata
- Permission-filtered retrieval based on RBAC
- Context assembly with citation-ready source metadata
- DeepSeek answer generation grounded in retrieved context
- V2.2 query rewrite, hybrid retrieval, RRF fusion, `qwen3-rerank`, and improved context assembly
- V2.3 local evaluation, Redis cache, debug views, delete/reindex synchronization, and stability controls

Browser Agent requirements:

- Mock search tool
- Multi-step plan
- Intermediate results
- Final synthesized answer

Office Agent requirements:

- Mock tools such as `generate_report`, `summarize_data`, and `write_email`
- Step-by-step execution output
- Structured final result

## 5. Technology Stack

Frontend:

- Next.js App Router
- TypeScript
- Tailwind CSS
- React Flow
- Framer Motion

Backend:

- FastAPI
- Python
- Pydantic

AI Layer:

- DeepSeek API using OpenAI-compatible chat format
- LangGraph in V3 only
- Prompt templates per module

Storage:

- Chroma for vector storage starting in V2
- Neon Postgres for users, RBAC, workspaces, document lifecycle, chunks, and ingestion jobs starting in V2.1
- Redis for RAG cache starting in V2.3
- Redis for long-running task state and event streaming starting in V3
- No relational database in V1; V2.1 explicitly introduces Postgres for the knowledge base

## 6. Non-Goals

- No local model training
- No local LLM hosting
- No external hosted authentication provider in V2.1
- No complex distributed system
- No real browser automation in MVP Browser Agent
- No real Office file mutation in MVP Office Agent

## 7. Development Principles

- Build one task at a time from `docs/codex_tasks.md`
- Keep implementation modular and interview-explainable
- Prefer visible workflow state over hidden AI behavior
- Keep V1 simple enough to run locally
- Do not introduce future-phase dependencies early
