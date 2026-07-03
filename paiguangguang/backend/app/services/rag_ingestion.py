from __future__ import annotations

import hashlib

from app.schemas.rag import (
    RagChunkData,
    RagDocumentCreateRequest,
    RagDocumentData,
    RagIngestData,
    RagIngestRequest,
)
from app.storage.rag_documents import (
    RagChunkRecord,
    RagDocumentRecord,
    RagDocumentRepository,
    RagIngestionRecord,
    get_rag_document_repository,
)


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def normalize_title(title: str | None) -> str:
    return title.strip() if title else ""


def make_content_hash(title: str | None, text: str) -> str:
    payload = f"{normalize_title(title)}\n{normalize_text(text)}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def make_document_id(content_hash: str) -> str:
    return f"doc_{content_hash[:12]}"


def chunk_text(text: str, *, chunk_size: int, chunk_overlap: int) -> list[RagChunkRecord]:
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    normalized = normalize_text(text)
    if not normalized:
        return []

    chunks: list[RagChunkRecord] = []
    start = 0
    index = 0
    total_length = len(normalized)

    while start < total_length:
        end = min(total_length, start + chunk_size)
        chunk_text_value = normalized[start:end].strip()
        if chunk_text_value:
            chunks.append(
                RagChunkRecord(
                    chunk_id="",
                    index=index,
                    start_char=start,
                    end_char=end,
                    text=chunk_text_value,
                )
            )
            index += 1
        if end >= total_length:
            break
        start = end - chunk_overlap

    return chunks


class RagIngestionService:
    def __init__(self, repository: RagDocumentRepository | None = None) -> None:
        self.repository = repository or get_rag_document_repository()

    def register_document(self, request: RagDocumentCreateRequest) -> RagDocumentData:
        normalized_text = normalize_text(request.text)
        content_hash = make_content_hash(request.title, normalized_text)
        doc_id = make_document_id(content_hash)
        self.repository.upsert_document(
            RagDocumentRecord(
                doc_id=doc_id,
                title=request.title.strip() if request.title else None,
                text=normalized_text,
                content_hash=content_hash,
            )
        )
        return RagDocumentData(
            doc_id=doc_id,
            title=request.title.strip() if request.title else None,
            text_length=len(normalized_text),
            content_hash=content_hash,
        )

    def ingest_document(self, request: RagIngestRequest) -> RagIngestData:
        if request.doc_id:
            document = self.repository.get_document(request.doc_id)
            title = document.title
            text = document.text
            content_hash = document.content_hash
            doc_id = document.doc_id
        else:
            text = normalize_text(request.text or "")
            content_hash = make_content_hash(request.title, text)
            doc_id = make_document_id(content_hash)
            title = request.title.strip() if request.title else None
            self.repository.upsert_document(
                RagDocumentRecord(
                    doc_id=doc_id,
                    title=title,
                    text=text,
                    content_hash=content_hash,
                )
            )

        chunk_records = chunk_text(
            text,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )
        chunks = [
            RagChunkRecord(
                chunk_id=f"{doc_id}-chunk-{chunk.index:04d}",
                index=chunk.index,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                text=chunk.text,
            )
            for chunk in chunk_records
        ]
        ingestion = RagIngestionRecord(
            doc_id=doc_id,
            title=title,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            chunks=chunks,
        )
        self.repository.upsert_ingestion(ingestion)
        return RagIngestData(
            doc_id=doc_id,
            title=title,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            text_length=len(text),
            chunk_count=len(chunks),
            chunks=[
                RagChunkData(
                    chunk_id=chunk.chunk_id,
                    index=chunk.index,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    text=chunk.text,
                )
                for chunk in chunks
            ],
        )


_RAG_INGESTION_SERVICE = RagIngestionService()


def get_rag_ingestion_service() -> RagIngestionService:
    return _RAG_INGESTION_SERVICE
