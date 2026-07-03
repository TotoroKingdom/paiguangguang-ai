from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class RagDocumentCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    text: str = Field(min_length=1, max_length=200_000)


class RagDocumentData(BaseModel):
    doc_id: str
    title: str | None
    text_length: int
    content_hash: str


class RagIngestRequest(BaseModel):
    doc_id: str | None = Field(default=None, min_length=1, max_length=128)
    title: str | None = Field(default=None, max_length=200)
    text: str | None = Field(default=None, min_length=1, max_length=200_000)
    chunk_size: int = Field(default=800, ge=1, le=4000)
    chunk_overlap: int = Field(default=120, ge=0, le=1000)

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


class RagQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    collection: str = Field(min_length=1, max_length=128)
    top_k: int = Field(default=5, ge=1, le=20)


class RagSourceData(BaseModel):
    doc_id: str
    chunk_id: str
    text: str
    score: float


class RagQueryData(BaseModel):
    answer: str
    sources: list[RagSourceData]
