# Admin RAG Backend and Admin Documents UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the admin document lifecycle, RAG cache/versioning, retrieval fusion, and admin documents UI changes described in the 2026-07-07 design spec.

**Architecture:** Make the backend contract authoritative first: add the document metadata and lifecycle semantics in the database, service layer, and API, then update ingestion, cache keys, and retrieval traces to reflect the new KB/versioning model. After the backend contract is stable, update the admin documents page to use the new metadata and provide the upload/delete/pagination experience in Chinese.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Redis-compatible cache adapters, ChromaDB, Next.js App Router, React, TypeScript, Tailwind CSS, Pytest, Jest/TypeScript tooling already present in the repo.

## Global Constraints

- Preserve `title` as a user-facing display field and add `original_filename` as the persisted uploaded file name.
- Redis-backed cache namespaces must remain separate for rewrite, retrieval trace, and answer caching.
- Cache keys must include `kb_version`, `retrieval_strategy_version`, and `model_version`.
- Cache TTLs are `rewrite: 10 minutes`, `retrieval trace: 30 minutes`, and `answer: 60 minutes`.
- Successful vector-store ingestion advances `kb_version`; failed ingestion does not.
- Document deletion must be permanent removal of the document record and related artifacts, not a logical-delete presentation.
- Admin documents UI copy must be Chinese and the page must use the available shell width.

---

### Task 1: Backend document metadata and admin document contract

**Files:**
- Modify: `backend/app/db/models.py`
- Modify: `backend/app/schemas/rag.py`
- Modify: `backend/app/schemas/admin.py`
- Modify: `backend/app/storage/rag_documents.py`
- Modify: `backend/app/services/rag_ingestion.py`
- Modify: `backend/app/services/admin.py`
- Modify: `backend/app/api/v1/admin.py`
- Modify: `backend/alembic/versions/0004_create_rag_lifecycle_tables.py`
- Modify: `backend/tests/test_admin_api.py`

**Interfaces:**
- Consumes: `RagDocumentRecord`, `RagDocumentData`, `AdminDocumentData`, `AdminDocumentCreateRequest`, `AdminDocumentUpdateRequest`, `AdminService.create_document`, `AdminService.delete_document`, admin document endpoints.
- Produces: `original_filename` on document models and responses, permanent delete behavior, document creation/update paths that preserve file-name metadata.

- [ ] **Step 1: Add failing tests for `original_filename` and permanent delete behavior**

```python
def test_admin_document_create_and_delete_preserve_original_filename(client):
    response = client.post(
        "/api/v1/admin/documents",
        json={
            "title": "Display title",
            "original_filename": "uploaded-report.pdf",
            "text": "Document body",
        },
    )
    assert response.json()["data"]["original_filename"] == "uploaded-report.pdf"

    delete_response = client.delete(f"/api/v1/admin/documents/{response.json()['data']['doc_id']}")
    assert delete_response.json()["data"]["is_deleted"] is False
```

- [ ] **Step 2: Run the focused backend tests and confirm the new assertions fail**

Run: `pytest backend/tests/test_admin_api.py -k document -v`
Expected: fail because `original_filename` is missing and delete still behaves like a logical delete.

- [ ] **Step 3: Implement the model, schema, repository, service, API, and migration changes**

```python
# backend/app/db/models.py
class RagDocument(Base):
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

# backend/app/schemas/rag.py
class RagDocumentData(BaseModel):
    original_filename: str | None = None

# backend/app/services/admin.py
def delete_document(...):
    session.execute(delete(RagChunkModel).where(RagChunkModel.document_id == document_id))
    session.execute(delete(RagIngestionJobModel).where(RagIngestionJobModel.document_id == document_id))
    session.execute(delete(RagDocumentModel).where(RagDocumentModel.document_id == document_id))
```

- [ ] **Step 4: Re-run the focused backend tests until they pass**

Run: `pytest backend/tests/test_admin_api.py -k document -v`
Expected: pass, with `original_filename` in responses and hard deletion removing the document row.

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models.py backend/app/schemas/rag.py backend/app/schemas/admin.py backend/app/storage/rag_documents.py backend/app/services/rag_ingestion.py backend/app/services/admin.py backend/app/api/v1/admin.py backend/alembic/versions/0004_create_rag_lifecycle_tables.py backend/tests/test_admin_api.py
git commit -m "feat: add document filename metadata and hard delete"
```

### Task 2: Backend cache versioning, TTLs, ingestion version bump, and retrieval fusion

**Files:**
- Modify: `backend/app/storage/cache.py`
- Modify: `backend/app/services/rag_cache.py`
- Modify: `backend/app/services/rag_ingestion.py`
- Modify: `backend/app/services/hybrid_retrieval.py`
- Modify: `backend/app/storage/chroma_store.py`
- Modify: `backend/app/storage/keyword_retriever.py`
- Modify: `backend/app/storage/rag_search.py`
- Modify: `backend/app/services/rag_query.py`
- Modify: `backend/app/schemas/rag.py`
- Modify: `backend/tests/test_rag_cache_integration.py`
- Modify: `backend/tests/test_hybrid_retrieval.py`
- Modify: `backend/tests/test_rag_query.py`

**Interfaces:**
- Consumes: cache adapter, ingestion service, vector store, keyword retriever, query rewrite service, RagQueryService.
- Produces: versioned cache keys with TTL, active-cache backend diagnostics, BM25/direct-match/vector fusion, trace data with route scores and hit-rate metadata.

- [ ] **Step 1: Add failing tests for TTL/versioned cache keys and retrieval trace shape**
- [ ] **Step 2: Run the targeted cache/retrieval tests and confirm failures**
- [ ] **Step 3: Implement cache TTL/versioned key generation and backend visibility**
- [ ] **Step 4: Implement ingestion version bump and retrieval route fusion/traces**
- [ ] **Step 5: Re-run the targeted tests until they pass**
- [ ] **Step 6: Commit**

### Task 3: Admin documents frontend upload, localization, layout, and pagination

**Files:**
- Modify: `frontend/features/admin/admin-document-management.tsx`
- Modify: `frontend/lib/admin.ts`
- Modify: `frontend/types/admin.ts`
- Modify: `frontend/app/admin/documents/page.tsx` if needed
- Modify: `frontend/features/admin/admin-pagination.tsx` if pagination needs contract changes
- Modify: `frontend/tests` if frontend tests exist in repo

**Interfaces:**
- Consumes: admin document list/detail/delete/reindex APIs and document metadata.
- Produces: Chinese admin documents UI, upload form, visible `original_filename`, and pagination that refetches the selected page.

- [ ] **Step 1: Add failing frontend assertions for Chinese labels, upload metadata, and page change behavior**
- [ ] **Step 2: Run the relevant frontend test/lint command and confirm the failures**
- [ ] **Step 3: Implement the upload form, localized copy, full-width layout, and pagination fixes**
- [ ] **Step 4: Re-run frontend verification until green**
- [ ] **Step 5: Commit**

## Self-Review

- Backend contract gaps: document filename metadata, hard delete, cache/versioning, ingestion version bump, retrieval fusion, and traceability are all covered by Tasks 1 and 2.
- Frontend gaps: the document page localization, upload flow, original filename column, and pagination are covered by Task 3.
- Placeholder scan: no `TBD` or vague "add appropriate" statements remain in the concrete Task 1 steps.
- Type consistency: `original_filename` is introduced once and reused consistently across the backend response and frontend type layers.

