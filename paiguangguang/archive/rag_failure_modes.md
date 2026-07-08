# RAG Failure Modes and Recovery

This document describes the main failure modes introduced for Task 44 and how the backend responds.

## Configurable limits

- `DOCUMENT_MAX_FILE_SIZE_BYTES` limits upload size during document parsing.
- `RAG_RATE_LIMIT_MAX_REQUESTS` and `RAG_RATE_LIMIT_WINDOW_SECONDS` control throttling for expensive RAG endpoints.

## Failure modes

### Oversized file

- The document parser rejects input above the configured file-size limit.
- Recovery: reduce the upload size or raise the limit through configuration.

### Timeout during external model calls

- Embedding, rerank, and answer generation calls can time out.
- The API returns a clear timeout response instead of a generic server error.
- Recovery: retry the request after the external service recovers or increase the upstream timeout if appropriate.

### Rate limiting

- Ingestion, query, and admin reindex endpoints apply in-memory request throttling.
- Recovery: retry after the configured window expires.

### Retrieval or rerank failure

- Retrieval pipeline failures are surfaced as retrieval errors.
- Recovery: retry after fixing the retrieval backend, vector index, or model configuration.

### External model failure

- Provider errors from embedding, rerank, or DeepSeek calls are surfaced as external model errors.
- Recovery: verify credentials, model availability, and network connectivity.

### Ingestion failure

- If ingestion fails after lifecycle changes start, the document is marked failed and the job records the failure reason.
- Recovery: fix the underlying issue and re-run ingestion or reindexing.

## Logging

- Ingestion and query stages emit structured JSON logs.
- Relevant events include start, completion, cache hit, timeout, and failure markers.
