# Admin and RAG Backend Redesign Spec

## Overview

This change set addresses two connected areas in one implementation stream:

1. Admin document management needs a usable upload and delete flow, clearer pagination behavior, and a fully localized Chinese UI.
2. The RAG backend needs versioned Redis caching, a stronger retrieval strategy, and traceability for document ingestion and chunk-level recall quality.

The implementation order is backend-first, then frontend polish that depends on the backend contract.

## Goals

- Make admin document management usable end to end.
- Preserve the original uploaded file name separately from the document title.
- Ensure admin pagination moves to the next page correctly and reloads data.
- Use Redis for `rewrite`, `retrieval trace`, and `answer` caches when configured.
- Version all RAG caches by knowledge base state and retrieval strategy state.
- Update `kb_version` after a document successfully enters the vector store.
- Set cache TTLs so cached entries expire automatically.
- Replace the retrieval flow with BM25 plus vector retrieval fusion, and keep a direct text-match path for exact terms.
- Expose chunk hit-rate and route-level hit counts in retrieval traces.

## Current State

- The admin documents page is present, but most visible text is still English and the layout leaves unused space.
- Document pagination exists, but the page state and data loading flow are fragile.
- Document deletion is modeled as soft delete in the backend.
- Document upload is missing from the admin documents experience.
- The cache layer supports Redis, but it silently falls back to in-memory cache when Redis is not reachable.
- Query rewrite, retrieval trace, and answer caching already exist, but the cache key versioning is incomplete for the requested KB lifecycle semantics.
- Retrieval currently combines vector and keyword paths, but it does not explicitly model BM25 or a direct text-match route in the fusion trace.

## Proposed Design

### 1. Document Metadata and Upload

Add a dedicated `original_filename` field to the document model and expose it in admin APIs.

Rules:

- `original_filename` stores the file name exactly as uploaded, separate from `title`.
- `title` remains a display field and may be user-editable.
- If the user uploads a file without providing a title, the backend may derive a fallback title from the file name, but `original_filename` must remain unchanged.
- Admin document list and detail responses must include `original_filename`.
- Delete behavior is a hard delete: remove the document record and its associated vector/cache artifacts instead of only toggling `is_deleted`.

Upload flow:

- The admin documents page gets an upload control.
- The UI sends `multipart/form-data` with the uploaded file, optional title, and optional ownership metadata.
- The backend reads the file name from the uploaded file object and stores it in `original_filename`.
- The backend creates or updates the document record, then runs ingestion.
- The stored file name is shown in the table and detail panel.

### 2. Admin Documents UX

Make the admin documents page a full-bleed layout inside the admin shell.

UI requirements:

- Use Chinese labels, descriptions, placeholders, empty states, and error messages.
- Rework the page so both the left list panel and the right detail panel use the available width.
- Add a visible `原始文件名` column to the documents table.
- Keep `标题` as a distinct column.
- Make delete buttons execute real deletion, not logical-delete presentation logic.
- Make pagination buttons update the current page and trigger a refetch for the new page.

### 3. Redis Cache Versioning and TTL

Versioned cache keys must include:

- `kb_version`
- `retrieval_strategy_version`
- `model_version`

Cache namespaces remain separated by purpose:

- `rag:rewrite`
- `rag:retrieval`
- `rag:answer`

TTL policy:

- `rewrite`: 10 minutes
- `retrieval trace`: 30 minutes
- `answer`: 60 minutes

Cache behavior:

- Redis is the primary backend when configured and reachable.
- If Redis cannot be initialized, the system may fall back to in-memory cache for local operation, but the runtime must surface which backend is active.
- The application must expose or log cache backend selection so a developer can tell whether Redis is actually being used.

KB version behavior:

- `kb_version` is a persisted, monotonically increasing knowledge base version scoped to the active collection or knowledge base, not a process-local counter.
- A successful ingestion that reaches the vector store increments or updates `kb_version`.
- Cache keys that depend on `kb_version` become invalid naturally once the version changes.
- Reingest and reindex operations should advance the version, while failed ingest must not.

### 4. Retrieval Strategy

Replace the current retrieval flow with a three-route recall strategy:

- BM25 retrieval
- vector retrieval
- direct text-match retrieval

Fusion behavior:

- Each route returns candidate chunks.
- Candidates are merged by `(doc_id, chunk_id)`.
- Each chunk retains per-route scores in `route_scores`.
- Fusion rank should favor chunks that are recalled by multiple routes.
- Direct text-match should capture exact file names, identifiers, paths, version strings, and quoted phrases.

Trace behavior:

- Retrieval trace must report queries, per-route hits, fusion hits, and route scores.
- The trace must also include chunk hit-rate information.
- The trace data should make it obvious which route contributed to each selected chunk.
- Chunk hit-rate is defined as `selected_unique_chunks / recalled_unique_chunks` for the final fused result, where `selected_unique_chunks` counts distinct `(doc_id, chunk_id)` pairs in the top-k fused output and `recalled_unique_chunks` counts distinct `(doc_id, chunk_id)` pairs observed across all routes for the same query batch.

### 5. Query Rewrite and Answer Cache

Query rewrite remains as a preprocessing stage, but its cache is versioned and TTL-bound.

Answer caching remains authorized and scoped, but must use the same versioned cache key rules.

The response cache metadata should continue to show:

- rewrite hit
- retrieval trace hit
- answer hit

### 6. Observability and Diagnostics

The system should make it clear when Redis is not actually active.

Minimum diagnostic surface:

- cache backend selection in logs or a health/debug endpoint
- `kb_version` value in runtime diagnostics
- retrieval trace details that show route-level recall contribution
- chunk hit-rate metrics in debug output

## Implementation Steps

### Step 1: Backend schema and API changes

- Add `original_filename` to the document schema and persistence model.
- Accept file name metadata in document creation and upload flows.
- Return `original_filename` from admin document list and detail endpoints.
- Change document delete semantics to permanent removal rather than logical delete.

### Step 2: Ingestion and KB versioning

- Update ingestion so a successful vector-store write bumps `kb_version`.
- Ensure failed ingestion does not advance the version.
- Make reindex flows advance the version.

### Step 3: Cache changes

- Add TTL handling to rewrite, retrieval trace, and answer cache writes.
- Include version fields in cache key generation.
- Add runtime visibility into active cache backend.

### Step 4: Retrieval rewrite

- Add BM25 recall as a first-class route.
- Add direct text-match recall as a separate route.
- Keep vector recall and merge all routes into one fused result.
- Extend retrieval traces to report route scores and chunk hit rates.
- BM25 is the lexical recall path for general term matching, while direct text-match stays reserved for exact substrings and identifiers.

### Step 5: Admin frontend follow-up

- Localize the admin documents page to Chinese.
- Add upload UI and show `原始文件名` separately.
- Fix pagination button behavior to fetch the next page.
- Make delete actions reflect real deletion behavior.
- Rework the layout so the page uses the available width.

## Testing Plan

Backend tests:

- cache key versioning includes `kb_version`, `retrieval_strategy_version`, and `model_version`
- Redis TTL is applied to each cache namespace
- cache backend selection is reported correctly
- successful ingestion advances `kb_version`
- failed ingestion does not advance `kb_version`
- BM25 and direct text-match routes participate in fusion
- retrieval trace exposes route-level scores and chunk hit-rate data

Frontend tests:

- pagination advances to the next page
- documents table renders `原始文件名`
- upload flow sends and displays file name metadata
- delete action removes the record from the active list after success
- Chinese labels and empty states appear on the admin documents page

## Acceptance Criteria

- Admin documents page shows the original file name separately from title.
- Uploading a file preserves its file name.
- Delete removes the document record instead of only hiding it in the UI or toggling a soft-delete flag.
- Pagination buttons actually move between pages.
- Redis-backed caches are versioned and expire according to TTL.
- `kb_version` changes after successful vector ingestion.
- Retrieval uses BM25 plus vector fusion plus direct text-match recall.
- Retrieval trace exposes chunk hit-rate and route contribution data.

## Scope Notes

- This spec keeps the whole work in one document, but the implementation is still expected to happen in the step order above.
- The frontend step is intentionally last because it depends on the backend contract for upload metadata, pagination, and document lifecycle behavior.
