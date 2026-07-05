from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.rag import (
    RagChunkData,
    RagDocumentCreateRequest,
    RagDocumentData,
    RagIngestData,
    RagIngestRequest,
    RagIngestionJobData,
)
from app.core.config import get_settings
from app.storage.chroma_store import ChromaRagStore, get_chroma_rag_store
from app.storage.rag_documents import (
    RagChunkRecord,
    RagDocumentRecord,
    RagDocumentRepository,
    RagIngestionJobRecord,
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
                    document_id="",
                    chunk_index=index,
                    start_char=start,
                    end_char=end,
                    text=chunk_text_value,
                    page_number=1,
                    metadata={"chunk_index": index, "start_char": start, "end_char": end},
                )
            )
            index += 1
        if end >= total_length:
            break
        start = end - chunk_overlap

    return chunks


class RagIngestionService:
    def __init__(
        self,
        repository: RagDocumentRepository | None = None,
        vector_store: ChromaRagStore | None = None,
        collection_name: str | None = None,
        index_to_vector_store: bool = True,
    ) -> None:
        settings = get_settings()
        self.repository = repository or get_rag_document_repository()
        self.vector_store = (vector_store or get_chroma_rag_store()) if index_to_vector_store else None
        self.collection_name = collection_name or settings.rag_collection_name

    @staticmethod
    def _document_to_data(document: RagDocumentRecord) -> RagDocumentData:
        return RagDocumentData(
            doc_id=document.document_id,
            title=document.title,
            text_length=len(document.text),
            content_hash=document.content_hash,
            owner_user_id=document.owner_user_id,
            workspace_id=document.workspace_id,
            permission_scope=document.permission_scope,
            status=document.status,
            parse_status=document.parse_status,
            chunk_status=document.chunk_status,
            embedding_status=document.embedding_status,
            index_status=document.index_status,
            is_deleted=document.is_deleted,
            error_message=document.error_message,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    @staticmethod
    def _job_to_data(job: RagIngestionJobRecord) -> RagIngestionJobData:
        return RagIngestionJobData(
            job_id=job.job_id,
            document_id=job.document_id,
            status=job.status,
            failure_reason=job.failure_reason,
            started_at=job.started_at,
            completed_at=job.completed_at,
            retry_count=job.retry_count,
            is_reindex=job.is_reindex,
            chunk_size=job.chunk_size,
            chunk_overlap=job.chunk_overlap,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    def register_document(self, request: RagDocumentCreateRequest) -> RagDocumentData:
        normalized_text = normalize_text(request.text)
        content_hash = make_content_hash(request.title, normalized_text)
        doc_id = make_document_id(content_hash)
        document = self.repository.upsert_document(
            RagDocumentRecord(
                document_id=doc_id,
                title=request.title.strip() if request.title else None,
                text=normalized_text,
                content_hash=content_hash,
                status="registered",
                parse_status="pending",
                chunk_status="pending",
                embedding_status="pending",
                index_status="pending",
            )
        )
        return self._document_to_data(document)

    def get_document(self, document_id: str) -> RagDocumentData:
        return self._document_to_data(self.repository.get_document(document_id))

    def get_ingestion_job(self, job_id: str) -> RagIngestionJobData:
        return self._job_to_data(self.repository.get_ingestion_job(job_id))

    def ingest_document(self, request: RagIngestRequest) -> RagIngestData:
        job_id = f"job_{uuid4().hex[:16]}"
        started_at = datetime.now(timezone.utc)
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
                    document_id=doc_id,
                    title=title,
                    text=text,
                    content_hash=content_hash,
                    status="registered",
                    parse_status="pending",
                    chunk_status="pending",
                    embedding_status="pending",
                    index_status="pending",
                )
            )

        self.repository.update_document_lifecycle(
            doc_id,
            status="reindexing" if request.reindex else "parsing",
            parse_status="in_progress",
            chunk_status="pending",
            embedding_status="pending",
            index_status="pending",
        )
        self.repository.create_ingestion_job(
            RagIngestionJobRecord(
                job_id=job_id,
                document_id=doc_id,
                status="running",
                failure_reason=None,
                started_at=started_at,
                completed_at=None,
                retry_count=0,
                is_reindex=request.reindex,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
            )
        )

        try:
            self.repository.update_document_lifecycle(
                doc_id,
                status="chunking",
                parse_status="completed",
                chunk_status="in_progress",
            )
            chunk_records = chunk_text(
                text,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
            )
            chunks = [
                RagChunkRecord(
                    chunk_id=f"{doc_id}-chunk-{chunk.chunk_index:04d}",
                    document_id=doc_id,
                    chunk_index=chunk.chunk_index,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    text=chunk.text,
                    page_number=chunk.page_number,
                    metadata={
                        "chunk_index": chunk.chunk_index,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                    },
                )
                for chunk in chunk_records
            ]
            self.repository.replace_chunks(doc_id, chunks)
            self.repository.update_document_lifecycle(
                doc_id,
                status="embedding",
                chunk_status="completed",
                embedding_status="in_progress",
            )
            if self.vector_store and chunks:
                self.vector_store.index_ingestion(
                    self.collection_name,
                    doc_id=doc_id,
                    title=title,
                    content_hash=content_hash,
                    chunks=chunks,
                )
            self.repository.update_document_lifecycle(
                doc_id,
                status="indexed",
                embedding_status="completed",
                index_status="completed",
            )
            job = self.repository.update_ingestion_job(
                job_id,
                status="completed",
                completed_at=datetime.now(timezone.utc),
            )
            document = self.repository.get_document(doc_id)
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
                document=self._document_to_data(document),
                job=self._job_to_data(job),
            )
        except Exception as exc:
            self.repository.mark_document_failed(doc_id, str(exc))
            self.repository.update_ingestion_job(
                job_id,
                status="failed",
                failure_reason=str(exc),
                completed_at=datetime.now(timezone.utc),
            )
            raise


_RAG_INGESTION_SERVICE = RagIngestionService()


def get_rag_ingestion_service() -> RagIngestionService:
    return _RAG_INGESTION_SERVICE
