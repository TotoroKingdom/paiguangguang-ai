- # AI Engineer Portfolio System

  ## 1. Project Goal

  Build an AI engineering portfolio website that demonstrates strong system design and implementation skills in:

  - LLM application engineering
  - RAG systems
  - Agent orchestration (LangGraph)
  - Tool calling systems
  - AI system visualization

  This is NOT a static portfolio website.

  It is an interactive AI system demo platform.

  The website itself should feel like an AI product.

  ---

  ## 2. Core System Overview

  The system consists of three main AI Agents + one visualization layer:

  ### 1) Enterprise Knowledge Base Agent (RAG Agent)
  - Chat with uploaded enterprise documents
  - Supports semantic retrieval + citation
  - Demonstrates RAG pipeline

  ### 2) Browser Agent (Web Research Agent)
  - Simulates browsing + information gathering workflow
  - Demonstrates tool calling + reasoning
  - Multi-step planning and execution

  ### 3) Office Automation Agent
  - Automates office workflows (reports, emails, data processing)
  - Demonstrates tool use + workflow orchestration

  ---

  ## 3. Homepage Requirement (IMPORTANT)

  The homepage must include a HERO SECTION that visually represents:

  ### 3.1 Agent Workflow Visualization

  Show an interactive flow diagram:

  User Input
  → Intent Analysis
  → Agent Router
  → Selected Agent
  → Tool Execution
  → Final Response

  Agents:
  - Knowledge Agent
  - Browser Agent
  - Office Agent

  ---

  ### 3.2 RAG Pipeline Visualization

  Show RAG flow:

  Document Upload
  → Chunking
  → Embedding
  → Vector Search
  → Retrieval
  → LLM Generation
  → Answer with Citations

  This should be visually interactive (not static text).

  ---

  ## 4. Pages Structure

  ### /
  - Hero section (Agent + RAG visualization)
  - Entry points to 3 agents

  ### /agents/knowledge
  Enterprise Knowledge Base Agent (RAG system demo)

  ### /agents/browser
  Browser Agent (web reasoning simulation)

  ### /agents/office
  Office Automation Agent (workflow + tools)

  ### /architecture
  Full system architecture visualization

  ---

  ## 5. Agent Design Requirements

  All agents must follow a structured pipeline:

  ### Common Architecture:

  User Input
  → Planner (LLM reasoning)
  → Tool Selection (if needed)
  → Execution Layer
  → Response Generator

  ---

  ### 5.1 Knowledge Agent (RAG)

  Must include:

  - Document upload
  - Chunking strategy
  - Embedding generation
  - Vector database retrieval
  - Reranking (optional)
  - Citation in answers

  Must support:
  - multi-document context
  - source tracing

  ---

  ### 5.2 Browser Agent

  Simulates:

  - search planning
  - multi-step reasoning
  - tool calling (mock web search)
  - result aggregation

  Must show:
  - step-by-step reasoning process
  - intermediate results

  ---

  ### 5.3 Office Automation Agent

  Must support workflows like:

  - generate report
  - analyze dataset
  - simulate email writing
  - structured output generation

  Must demonstrate:
  - tool calling
  - workflow orchestration
  - structured outputs

  ---

  ## 6. Technology Stack

  ### Frontend
  - Next.js (App Router)
  - TypeScript
  - Tailwind CSS
  - React Flow (for visualization)
  - Framer Motion (animations)

  ### Backend
  - FastAPI
  - Python

  ### AI Layer
  - DeepSeek API (OpenAI-compatible)
  - Prompt engineering
  - Optional: LangGraph for orchestration

  ### Storage
  - Vector DB: Chroma or Milvus Lite
  - Cache: Redis (optional)

  ---

  ## 7. Key Engineering Requirements

  ### 7.1 RAG System Must Include
  - Chunking strategy
  - Embedding pipeline
  - Vector retrieval
  - Context assembly
  - Answer generation with citations

  ---

  ### 7.2 Agent System Must Include
  - Planner (LLM)
  - Tool router
  - Execution layer
  - State management (optional LangGraph)

  ---

  ### 7.3 Visualization Requirements
  - Interactive graphs (not static images)
  - Clickable nodes
  - Expandable workflow steps
  - Real-time state display

  ---

  ## 8. Non-Goals

  - No fine-tuning models
  - No local LLM hosting
  - No distributed system complexity
  - No authentication system in MVP

  ---

  ## 9. Development Principle

  The system must be:

  - Modular
  - Demo-friendly
  - Interview explainable
  - Production-structured (but simplified)

  ---

  ## 10. Final Outcome

  This project should allow demonstration of:

  - RAG engineering ability
  - Agent system design ability
  - LLM application architecture understanding
  - Full-stack AI system implementation

  The website itself should behave like a mini AI product.