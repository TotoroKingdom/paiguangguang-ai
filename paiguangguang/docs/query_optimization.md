# Query Optimization

## Goal

Optimize the Knowledge Agent query flow with three scoped changes:

1. Return only the original Chroma-matched chunks as citations/sources, with source count aligned to `top_k` whenever enough matches exist.
2. Expose a backend collection list and let the frontend choose the active collection from a dropdown.
3. Surface cache hits in the UI with Redis indicators for `rewrite`, `retrieval trace`, and `answer`.

## Hard Scope Boundaries

Only touch the Knowledge Agent query path and its direct supporting types/components.

Do not change:

- Admin modules
- Browser Agent modules
- Office Agent modules
- Portfolio Chat modules
- Authentication logic
- RBAC logic
- Ingestion behavior
- Chroma indexing behavior beyond query-side selection and source return shape
- Any unrelated UI layout or styling outside Knowledge Agent query surfaces

## Current Behavior Summary

- `POST /api/v1/rag/query` accepts `question`, `collection`, `top_k`, and `include_debug`.
- Query execution currently:
  - rewrites the question,
  - performs hybrid retrieval,
  - assembles context,
  - may return cached answers,
  - returns `sources` from the assembled selected context.
- The current `ContextAssembler` can include adjacent chunks, which means returned citations are not guaranteed to equal raw Chroma hits.
- The frontend Knowledge Agent currently treats `collection` as a free-form text field rather than a backend-provided list.

## Target Behavior

### 1. Citations and chunks

- `sources` and `debug.citations` must come from the original raw retrieval matches.
- Do not include adjacent chunks in the returned citation set.
- Returned source count should match the effective `top_k` selection when enough results exist.
- If retrieval returns fewer than `top_k` matches, return only the available matches.

### 2. Collection selection

- Add a backend endpoint that returns the collection list at collection granularity.
- The frontend must render this list as a dropdown.
- The user must not be able to query arbitrary unseen collections from the UI.
- Query requests should still send a single selected collection string, but the selection must come from backend-provided options.

### 3. Cache hit visibility

- The frontend must display cache status indicators when a query completes.
- Show separate indicators for:
  - rewrite cache
  - retrieval trace cache
  - answer cache
- Use a Redis-style icon in the query result header or top-right status area.
- If a stage is a cache hit, mark it clearly and independently.
- If a stage is a miss, do not merge it into the other indicators.

## Proposed Backend Changes

### A. Add collection list endpoint

Add `GET /api/v1/rag/collections`.

Responsibilities:

- Read available Chroma collection names from the backend.
- Return a JSON envelope with a stable array of collection names.
- Use the existing `/api/v1` API conventions.

Expected response shape:

```json
{
  "success": true,
  "data": {
    "collections": ["portfolio_knowledge", "another_collection"]
  },
  "error": null
}
```

Implementation notes:

- Keep this endpoint thin.
- Do not expose unrelated storage internals.
- Do not return collection metadata beyond the names needed for selection.

### B. Return raw retrieval citations

Update the query service so `sources` are built from raw retrieval hits, not from adjacent chunk expansion.

Recommended behavior:

- Keep the current retrieval, rerank, and context assembly pipeline for answer generation.
- Build returned citations from the original hit list that came back from retrieval before adjacent expansion.
- Preserve source metadata and `chunk_id`, `doc_id`, `title`, `page_number`, `chunk_index`, `score`, `rerank_score`, `route_scores`, and `metadata`.

Implementation notes:

- Add a clear separation between:
  - raw retrieval hits used for citations
  - assembled context hits used for prompt generation
- Do not let the context assembler decide the public citation set.
- If the current assembled context still needs adjacent chunks for answer quality, that can remain for prompt input, but those extra chunks must not leak into `sources` or `debug.citations`.

### C. Add cache hit metadata to query response

Extend the RAG query response schema with cache status fields, for example:

- `rewrite_cache_hit`
- `retrieval_cache_hit`
- `answer_cache_hit`

If a cleaner structure is preferred, use a nested object such as:

```json
{
  "cache": {
    "rewrite_hit": true,
    "retrieval_trace_hit": true,
    "answer_hit": false
  }
}
```

Implementation notes:

- Preserve existing response fields.
- Do not require `include_debug` to surface the cache indicators.
- Return the indicators on both cache hits and misses so the frontend can render all three badges consistently.
- Keep the actual cache key design unchanged unless required for correctness.

## Proposed Frontend Changes

### A. Replace collection text input with dropdown

Update the Knowledge Agent query UI to:

- fetch collections on page load,
- show a dropdown of backend-provided collection names,
- default to the first returned collection or the current default if the list is empty,
- prevent arbitrary collection text entry.

Implementation notes:

- Keep the rest of the query form unchanged.
- Preserve `top_k` controls and query submission flow.
- If the collection list fetch fails, show a clear inline error and avoid silently inventing values.

### B. Render cache indicators in the query header

Show a compact status area near the top-right of the results panel or query header.

Suggested presentation:

- Redis icon
- `rewrite`
- `retrieval trace`
- `answer`

Each item should independently show:

- hit
- miss
- loading or unavailable state if needed

Implementation notes:

- Make the indicators readable at desktop and mobile widths.
- Do not add this status to unrelated pages.
- Tie the indicators to the latest query response.

## Data Flow

1. Frontend loads collection list from `GET /api/v1/rag/collections`.
2. User picks a collection from the dropdown.
3. Frontend submits query to `POST /api/v1/rag/query`.
4. Backend resolves rewrite cache, retrieval trace cache, and answer cache.
5. Backend returns:
   - answer
   - raw citation sources
   - optional debug payload
   - cache hit indicators
6. Frontend renders:
   - answer text
   - citations from raw hits
   - cache badges

## Tests

### Backend tests

Add or update tests to verify:

- collection list endpoint returns the expected list shape
- query response sources come from raw retrieval hits
- returned citation count matches `top_k` when enough hits exist
- adjacent chunks are not included in `sources` or `debug.citations`
- cache indicators are present and correct for hit/miss combinations

### Frontend tests

Add or update tests to verify:

- collection dropdown renders backend-provided options
- query submission uses the selected collection value
- cache badges render independently for rewrite, retrieval trace, and answer
- failed collection loading is visible to the user

## Acceptance Criteria

- The Knowledge Agent query UI uses a dropdown populated by backend collection names.
- Users cannot free-type unknown collections in the normal UI flow.
- Query responses expose raw Chroma-matched citations only.
- Citation count tracks `top_k` when enough results exist.
- Cache status is visible in the frontend for rewrite, retrieval trace, and answer stages.
- No unrelated modules are changed.

## Non-Goals

- No new retrieval strategy.
- No rerank logic changes.
- No ingestion changes.
- No permission model changes.
- No admin UI work.
- No browser or office agent changes.
- No global style redesign.

## Implementation Order

1. Add backend collection list endpoint.
2. Adjust backend query response to expose raw citation hits and cache status.
3. Update frontend types and API helper for the new response shape.
4. Replace collection text input with dropdown in Knowledge Agent UI.
5. Add cache-hit badges and Redis indicator rendering.
6. Add/adjust tests.

## Verification

Run backend verification:

```powershell
cd backend
python -m pytest
```

Run frontend verification:

```powershell
cd frontend
npm run lint
npm run build
```
