- 

- ```
  # Codex Execution Tasks (Production-Ready Version)
  
  This file is the ONLY execution source of truth for Codex.
  
  RULES (MANDATORY):
  - Execute ONE task at a time
  - NEVER implement future tasks
  - NEVER redesign architecture
  - MUST follow architecture.md strictly
  - If unclear, STOP and ask instead of guessing
  - Do NOT refactor unrelated code
  - Keep changes minimal and scoped
  
  ---
  
  # Phase 1 - Project Initialization
  
  ---
  
  ## Task 1: Initialize Frontend (Next.js)
  
  ### Goal
  Create runnable frontend project skeleton.
  
  ### Tech Stack
  - Next.js App Router
  - TypeScript
  - Tailwind CSS
  
  ### Required Structure
  ```

  frontend/
   app/
   components/
   lib/

  ```
  ### Pages
  - `/`
  - `/agents/knowledge`
  - `/agents/browser`
  - `/agents/office`
  - `/architecture`
  
  ### Constraints
  - NO API calls
  - NO AI logic
  - NO backend integration
  
  ### Acceptance Criteria
  - [ ] `npm run dev` runs successfully
  - [ ] All routes accessible
  - [ ] No console errors
  - [ ] Basic navigation exists
  
  ---
  
  ## Task 2: Initialize Backend (FastAPI)
  
  ### Goal
  Create backend skeleton.
  
  ### Requirements
  - FastAPI
  - uvicorn
  - modular structure
  
  ### Required endpoints
  - GET `/health`
  
  ### Response format (MANDATORY)
  ```json
  {
    "success": true,
    "data": {},
    "error": null
  }
  ```

  ### Acceptance Criteria

  -  backend starts successfully
  -  /health returns correct JSON
  -  CORS enabled
  -  clean modular structure

  ------

  ## Task 3: Frontend Layout System

  ### Goal

  Create base UI layout only.

  ### Requirements

  - Navigation bar
  - Page layout wrapper
  - Placeholder pages

  ### Constraints

  - NO API calls
  - NO AI logic
  - NO state management complexity

  ### Acceptance Criteria

  -  navigation works
  -  all pages render
  -  layout consistent

  ------

  # Phase 2 - Portfolio Chat (MVP AI)

  ------

  ## Task 4: DeepSeek Client Wrapper

  ### Goal

  Create LLM client module.

  ### Requirements

  - OpenAI-compatible API format
  - base_url: https://api.deepseek.com

  ### Output

  - reusable client module

  ### Acceptance Criteria

  -  can send request to DeepSeek
  -  returns valid response
  -  isolated module (no business logic)

  ------

  ## Task 5: Portfolio Chat API

  ### Endpoint

  POST `/api/v1/chat/portfolio`

  ### Input

  ```
  {
    "message": "string",
    "session_id": "string"
  }
  ```

  ### Output

  ```
  {
    "reply": "string",
    "session_id": "string"
  }
  ```

  ### Constraints

  - NO RAG
  - NO tools
  - NO external knowledge base
  - Only static prompt + memory

  ### Acceptance Criteria

  -  chat works end-to-end
  -  session memory works
  -  stable responses

  ------

  # Phase 3 - RAG System

  ------

  ## Task 6: Document Ingestion

  ### Goal

  Upload + preprocess documents

  ### Steps

  - file upload API
  - extract raw text
  - chunk text (fixed-size chunking)

  ### Output

  ```
  {
    "doc_id": "string",
    "chunks": ["string"]
  }
  ```

  ### Acceptance Criteria

  -  file upload works
  -  chunking correct
  -  deterministic output

  ------

  ## Task 7: Vector Database (Chroma)

  ### Goal

  Implement embedding storage + retrieval

  ### Requirements

  - Chroma DB integration
  - embedding wrapper
  - similarity search (top-k)

  ### Acceptance Criteria

  -  store embeddings
  -  retrieve relevant chunks
  -  consistent results

  ------

  ## Task 8: RAG Query API

  ### Endpoint

  POST `/api/v1/rag/query`

  ### Flow

  query → retrieve → assemble context → LLM → answer

  ### Output

  ```
  {
    "answer": "string",
    "sources": ["string"]
  }
  ```

  ### Acceptance Criteria

  -  correct retrieval
  -  answer relevant
  -  sources included

  ------

  # Phase 4 - Agent System (Simplified First)

  ------

  ## Task 9: Office Agent (Mock Workflow)

  ### Goal

  Simulate tool-based workflow

  ### Tools (mock only)

  - generate_report
  - summarize_data

  ### Output format

  ```
  {
    "steps": [
      {
        "action": "string",
        "result": "string"
      }
    ]
  }
  ```

  ### Acceptance Criteria

  -  step-by-step execution visible
  -  tools simulated correctly

  ------

  ## Task 10: Browser Agent (Mock Reasoning)

  ### Goal

  Simulate multi-step reasoning

  ### Flow

  plan → search(mock) → summarize

  ### Output must include:

  - reasoning steps
  - intermediate results
  - final answer

  ### Acceptance Criteria

  -  reasoning trace visible
  -  output structured

  ------

  # Phase 5 - Visualization

  ------

  ## Task 11: Architecture Visualization (React Flow)

  ### Goal

  Visual system architecture

  ### Nodes

  - User
  - Router
  - Knowledge Agent
  - Browser Agent
  - Office Agent
  - RAG Pipeline

  ### Requirements

  - clickable nodes
  - detail panel on click

  ### Acceptance Criteria

  -  graph renders correctly
  -  interactive behavior works
  -  no runtime errors

  ------

  # GLOBAL RULES (CRITICAL)

  1. NEVER implement multiple tasks at once
  2. NEVER modify architecture.md unless explicitly instructed
  3. ALWAYS keep changes minimal and scoped
  4. IF uncertain → STOP and ask
  5. DO NOT optimize prematurely---