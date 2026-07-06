from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class RagDocumentCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    text: str = Field(min_length=1, max_length=200_000)


class RagDocumentData(BaseModel):
    doc_id: str
    title: str | None
    text_length: int
    content_hash: str
    owner_user_id: str | None = None
    workspace_id: str | None = None
    permission_scope: str | None = None
    status: str
    parse_status: str
    chunk_status: str
    embedding_status: str
    index_status: str
    is_deleted: bool
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class RagIngestRequest(BaseModel):
    doc_id: str | None = Field(default=None, min_length=1, max_length=128)
    title: str | None = Field(default=None, max_length=200)
    text: str | None = Field(default=None, min_length=1, max_length=200_000)
    chunk_size: int = Field(default=800, ge=1, le=4000)
    chunk_overlap: int = Field(default=120, ge=0, le=1000)
    reindex: bool = False

    @model_validator(mode="after")
    def ensure_source(self) -> "RagIngestRequest":
        if not self.doc_id and not self.text:
            raise ValueError("Either doc_id or text must be provided")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        return self


class RagChunkData(BaseModel):
    chunk_id: str
    index: int
    start_char: int
    end_char: int
    text: str


class RagIngestData(BaseModel):
    doc_id: str
    title: str | None
    chunk_size: int
    chunk_overlap: int
    text_length: int
    chunk_count: int
    chunks: list[RagChunkData]
    document: RagDocumentData
    job: "RagIngestionJobData"


class RagIngestionJobData(BaseModel):
    job_id: str
    document_id: str
    status: str
    failure_reason: str | None
    started_at: datetime | None
    completed_at: datetime | None
    retry_count: int
    is_reindex: bool
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    created_at: datetime
    updated_at: datetime


class RagCollectionsData(BaseModel):
    collections: list[str] = Field(default_factory=list)


class RagQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    collection: str = Field(min_length=1, max_length=128)
    top_k: int = Field(default=5, ge=1, le=20)
    include_debug: bool = False


class RagQueryRewriteMetadata(BaseModel):
    enabled: bool
    model: str | None = None
    status: str
    fallback_reason: str | None = None
    rewritten_query_count: int = 0


class RagQueryRewriteData(BaseModel):
    original_question: str
    rewritten_queries: list[str] = Field(default_factory=list)
    metadata: RagQueryRewriteMetadata


class RagSourceData(BaseModel):
    doc_id: str
    chunk_id: str
    title: str | None = None
    page_number: int | None = None
    chunk_index: int = 0
    text: str
    score: float
    rerank_score: float | None = None
    route_scores: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)


class RagQueryData(BaseModel):
    answer: str
    sources: list[RagSourceData]
    rewrite: RagQueryRewriteData | None = None
    debug: RagQueryDebugData | None = None
    cache: "RagQueryCacheData" = Field(default_factory=lambda: RagQueryCacheData())


class RagQueryDebugData(BaseModel):
    rewrites: RagQueryRewriteData | None = None
    vector_hits: list[RagSourceData] = Field(default_factory=list)
    keyword_hits: list[RagSourceData] = Field(default_factory=list)
    fusion: list[RagSourceData] = Field(default_factory=list)
    rerank: list[RagSourceData] = Field(default_factory=list)
    selected_context: list[RagSourceData] = Field(default_factory=list)
    citations: list[RagSourceData] = Field(default_factory=list)
    latency_ms: int
    model_usage: dict[str, object] = Field(default_factory=dict)


class RagQueryCacheData(BaseModel):
    rewrite_hit: bool = False
    retrieval_trace_hit: bool = False
    answer_hit: bool = False


RagIngestData.model_rebuild()
RagQueryData.model_rebuild()
