from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Iterator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import RagChunk as RagChunkModel
from app.db.models import RagDocument as RagDocumentModel
from app.db.models import RagIngestionJob as RagIngestionJobModel
from app.db.session import build_session_factory


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class RagDocumentRecord:
    document_id: str
    title: str | None
    text: str
    content_hash: str
    owner_user_id: str | None = None
    workspace_id: str | None = None
    permission_scope: str | None = None
    status: str = "registered"
    parse_status: str = "pending"
    chunk_status: str = "pending"
    embedding_status: str = "pending"
    index_status: str = "pending"
    is_deleted: bool = False
    error_message: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    @property
    def doc_id(self) -> str:
        return self.document_id


@dataclass(frozen=True, init=False)
class RagChunkRecord:
    chunk_id: str
    document_id: str
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    page_number: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __init__(
        self,
        *,
        chunk_id: str,
        document_id: str = "",
        chunk_index: int | None = None,
        index: int | None = None,
        text: str,
        start_char: int,
        end_char: int,
        page_number: int | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        resolved_index = chunk_index if chunk_index is not None else index
        if resolved_index is None:
            raise TypeError("chunk_index or index must be provided")
        object.__setattr__(self, "chunk_id", chunk_id)
        object.__setattr__(self, "document_id", document_id)
        object.__setattr__(self, "chunk_index", resolved_index)
        object.__setattr__(self, "text", text)
        object.__setattr__(self, "start_char", start_char)
        object.__setattr__(self, "end_char", end_char)
        object.__setattr__(self, "page_number", page_number)
        object.__setattr__(self, "metadata", dict(metadata or {}))

    @property
    def doc_id(self) -> str:
        return self.document_id

    @property
    def index(self) -> int:
        return self.chunk_index


@dataclass(frozen=True)
class RagIngestionJobRecord:
    job_id: str
    document_id: str
    status: str
    failure_reason: str | None
    started_at: datetime | None
    completed_at: datetime | None
    retry_count: int = 0
    is_reindex: bool = False
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    @property
    def doc_id(self) -> str:
        return self.document_id


RagIngestionRecord = RagIngestionJobRecord


class RagDocumentRepository:
    def __init__(self, session_factory: sessionmaker[Session] | None = None) -> None:
        self._session_factory = session_factory
        self._documents: dict[str, RagDocumentRecord] = {}
        self._chunks: dict[str, list[RagChunkRecord]] = {}
        self._ingestion_jobs: dict[str, RagIngestionJobRecord] = {}
        self._lock = Lock()

    @contextmanager
    def _session(self) -> Iterator[Session] | Iterator[None]:
        if self._session_factory is None:
            yield None
            return

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @property
    def uses_database(self) -> bool:
        return self._session_factory is not None

    @staticmethod
    def _document_from_model(model: RagDocumentModel) -> RagDocumentRecord:
        return RagDocumentRecord(
            document_id=model.document_id,
            title=model.title,
            text=model.text,
            content_hash=model.content_hash,
            owner_user_id=model.owner_user_id,
            workspace_id=model.workspace_id,
            permission_scope=model.permission_scope,
            status=model.status,
            parse_status=model.parse_status,
            chunk_status=model.chunk_status,
            embedding_status=model.embedding_status,
            index_status=model.index_status,
            is_deleted=model.is_deleted,
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _chunk_from_model(model: RagChunkModel) -> RagChunkRecord:
        return RagChunkRecord(
            chunk_id=model.chunk_id,
            document_id=model.document_id,
            chunk_index=model.chunk_index,
            text=model.text,
            start_char=model.start_char,
            end_char=model.end_char,
            page_number=model.page_number,
            metadata=dict(model.chunk_metadata or {}),
        )

    @staticmethod
    def _job_from_model(model: RagIngestionJobModel) -> RagIngestionJobRecord:
        return RagIngestionJobRecord(
            job_id=model.job_id,
            document_id=model.document_id,
            status=model.status,
            failure_reason=model.failure_reason,
            started_at=model.started_at,
            completed_at=model.completed_at,
            retry_count=model.retry_count,
            is_reindex=model.is_reindex,
            chunk_size=model.chunk_size,
            chunk_overlap=model.chunk_overlap,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def upsert_document(self, document: RagDocumentRecord) -> RagDocumentRecord:
        if self.uses_database:
            with self._session() as session:
                assert session is not None
                model = session.scalar(
                    select(RagDocumentModel).where(RagDocumentModel.document_id == document.document_id)
                )
                if model is None:
                    model = RagDocumentModel(document_id=document.document_id, text=document.text, content_hash=document.content_hash)
                    session.add(model)
                model.title = document.title
                model.text = document.text
                model.content_hash = document.content_hash
                model.owner_user_id = document.owner_user_id
                model.workspace_id = document.workspace_id
                model.permission_scope = document.permission_scope
                model.status = document.status
                model.parse_status = document.parse_status
                model.chunk_status = document.chunk_status
                model.embedding_status = document.embedding_status
                model.index_status = document.index_status
                model.is_deleted = document.is_deleted
                model.error_message = document.error_message
                model.updated_at = document.updated_at or _utcnow()
                session.flush()
                session.refresh(model)
                return self._document_from_model(model)

        with self._lock:
            self._documents[document.document_id] = document
        return document

    def get_document(self, document_id: str) -> RagDocumentRecord:
        if self.uses_database:
            with self._session() as session:
                assert session is not None
                model = session.scalar(
                    select(RagDocumentModel).where(RagDocumentModel.document_id == document_id)
                )
                if model is None:
                    raise KeyError(document_id)
                return self._document_from_model(model)

        with self._lock:
            document = self._documents.get(document_id)
        if document is None:
            raise KeyError(document_id)
        return document

    def update_document_lifecycle(
        self,
        document_id: str,
        *,
        status: str | None = None,
        parse_status: str | None = None,
        chunk_status: str | None = None,
        embedding_status: str | None = None,
        index_status: str | None = None,
        error_message: str | None = None,
        is_deleted: bool | None = None,
    ) -> RagDocumentRecord:
        if self.uses_database:
            with self._session() as session:
                assert session is not None
                model = session.scalar(
                    select(RagDocumentModel).where(RagDocumentModel.document_id == document_id)
                )
                if model is None:
                    raise KeyError(document_id)
                if status is not None:
                    model.status = status
                if parse_status is not None:
                    model.parse_status = parse_status
                if chunk_status is not None:
                    model.chunk_status = chunk_status
                if embedding_status is not None:
                    model.embedding_status = embedding_status
                if index_status is not None:
                    model.index_status = index_status
                if error_message is not None:
                    model.error_message = error_message
                if is_deleted is not None:
                    model.is_deleted = is_deleted
                model.updated_at = _utcnow()
                session.flush()
                session.refresh(model)
                return self._document_from_model(model)

        with self._lock:
            document = self._documents.get(document_id)
            if document is None:
                raise KeyError(document_id)
            updated = RagDocumentRecord(
                document_id=document.document_id,
                title=document.title,
                text=document.text,
                content_hash=document.content_hash,
                owner_user_id=document.owner_user_id,
                workspace_id=document.workspace_id,
                permission_scope=document.permission_scope,
                status=status or document.status,
                parse_status=parse_status or document.parse_status,
                chunk_status=chunk_status or document.chunk_status,
                embedding_status=embedding_status or document.embedding_status,
                index_status=index_status or document.index_status,
                is_deleted=document.is_deleted if is_deleted is None else is_deleted,
                error_message=error_message if error_message is not None else document.error_message,
                created_at=document.created_at,
                updated_at=_utcnow(),
            )
            self._documents[document_id] = updated
            return updated

    def mark_document_failed(self, document_id: str, error_message: str) -> RagDocumentRecord:
        return self.update_document_lifecycle(
            document_id,
            status="failed",
            error_message=error_message,
        )

    def mark_document_deleted(self, document_id: str) -> RagDocumentRecord:
        return self.update_document_lifecycle(
            document_id,
            status="deleted",
            is_deleted=True,
        )

    def upsert_chunk(self, chunk: RagChunkRecord) -> RagChunkRecord:
        if self.uses_database:
            with self._session() as session:
                assert session is not None
                model = session.scalar(
                    select(RagChunkModel).where(RagChunkModel.chunk_id == chunk.chunk_id)
                )
                if model is None:
                    model = RagChunkModel(chunk_id=chunk.chunk_id, document_id=chunk.document_id)
                    session.add(model)
                model.document_id = chunk.document_id
                model.chunk_index = chunk.chunk_index
                model.text = chunk.text
                model.start_char = chunk.start_char
                model.end_char = chunk.end_char
                model.page_number = chunk.page_number
                model.chunk_metadata = dict(chunk.metadata)
                model.updated_at = _utcnow()
                session.flush()
                session.refresh(model)
                return self._chunk_from_model(model)

        with self._lock:
            chunks = self._chunks.setdefault(chunk.document_id, [])
            chunks = [existing for existing in chunks if existing.chunk_id != chunk.chunk_id]
            chunks.append(chunk)
            chunks.sort(key=lambda item: item.chunk_index)
            self._chunks[chunk.document_id] = chunks
        return chunk

    def replace_chunks(self, document_id: str, chunks: list[RagChunkRecord]) -> list[RagChunkRecord]:
        if self.uses_database:
            with self._session() as session:
                assert session is not None
                session.execute(delete(RagChunkModel).where(RagChunkModel.document_id == document_id))
                stored: list[RagChunkRecord] = []
                for chunk in chunks:
                    model = RagChunkModel(
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        chunk_index=chunk.chunk_index,
                        text=chunk.text,
                        start_char=chunk.start_char,
                        end_char=chunk.end_char,
                        page_number=chunk.page_number,
                        chunk_metadata=dict(chunk.metadata),
                    )
                    session.add(model)
                    stored.append(chunk)
                session.flush()
                return stored

        with self._lock:
            self._chunks[document_id] = sorted(chunks, key=lambda item: item.chunk_index)
        return list(chunks)

    def get_chunks(self, document_id: str) -> list[RagChunkRecord]:
        if self.uses_database:
            with self._session() as session:
                assert session is not None
                models = session.scalars(
                    select(RagChunkModel)
                    .where(RagChunkModel.document_id == document_id)
                    .order_by(RagChunkModel.chunk_index)
                ).all()
                return [self._chunk_from_model(model) for model in models]

        with self._lock:
            return list(self._chunks.get(document_id, []))

    def create_ingestion_job(self, job: RagIngestionJobRecord) -> RagIngestionJobRecord:
        if self.uses_database:
            with self._session() as session:
                assert session is not None
                model = RagIngestionJobModel(
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
                )
                session.add(model)
                session.flush()
                session.refresh(model)
                return self._job_from_model(model)

        with self._lock:
            self._ingestion_jobs[job.job_id] = job
        return job

    def update_ingestion_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        failure_reason: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        retry_count: int | None = None,
        is_reindex: bool | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> RagIngestionJobRecord:
        if self.uses_database:
            with self._session() as session:
                assert session is not None
                model = session.scalar(
                    select(RagIngestionJobModel).where(RagIngestionJobModel.job_id == job_id)
                )
                if model is None:
                    raise KeyError(job_id)
                if status is not None:
                    model.status = status
                if failure_reason is not None:
                    model.failure_reason = failure_reason
                if started_at is not None:
                    model.started_at = started_at
                if completed_at is not None:
                    model.completed_at = completed_at
                if retry_count is not None:
                    model.retry_count = retry_count
                if is_reindex is not None:
                    model.is_reindex = is_reindex
                if chunk_size is not None:
                    model.chunk_size = chunk_size
                if chunk_overlap is not None:
                    model.chunk_overlap = chunk_overlap
                model.updated_at = _utcnow()
                session.flush()
                session.refresh(model)
                return self._job_from_model(model)

        with self._lock:
            job = self._ingestion_jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            updated = RagIngestionJobRecord(
                job_id=job.job_id,
                document_id=job.document_id,
                status=status or job.status,
                failure_reason=failure_reason if failure_reason is not None else job.failure_reason,
                started_at=started_at if started_at is not None else job.started_at,
                completed_at=completed_at if completed_at is not None else job.completed_at,
                retry_count=retry_count if retry_count is not None else job.retry_count,
                is_reindex=job.is_reindex if is_reindex is None else is_reindex,
                chunk_size=chunk_size if chunk_size is not None else job.chunk_size,
                chunk_overlap=chunk_overlap if chunk_overlap is not None else job.chunk_overlap,
                created_at=job.created_at,
                updated_at=_utcnow(),
            )
            self._ingestion_jobs[job_id] = updated
            return updated

    def get_ingestion_job(self, job_id: str) -> RagIngestionJobRecord:
        if self.uses_database:
            with self._session() as session:
                assert session is not None
                model = session.scalar(
                    select(RagIngestionJobModel).where(RagIngestionJobModel.job_id == job_id)
                )
                if model is None:
                    raise KeyError(job_id)
                return self._job_from_model(model)

        with self._lock:
            job = self._ingestion_jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        return job

    def get_latest_ingestion_job_for_document(self, document_id: str) -> RagIngestionJobRecord | None:
        if self.uses_database:
            with self._session() as session:
                assert session is not None
                model = session.scalar(
                    select(RagIngestionJobModel)
                    .where(RagIngestionJobModel.document_id == document_id)
                    .order_by(RagIngestionJobModel.created_at.desc(), RagIngestionJobModel.updated_at.desc())
                )
                return self._job_from_model(model) if model is not None else None

        with self._lock:
            jobs = [job for job in self._ingestion_jobs.values() if job.document_id == document_id]
        if not jobs:
            return None
        return sorted(jobs, key=lambda item: (item.created_at, item.updated_at), reverse=True)[0]

    def upsert_ingestion(self, ingestion: RagIngestionJobRecord) -> RagIngestionJobRecord:
        existing = self.get_latest_ingestion_job_for_document(ingestion.document_id)
        if existing is None or existing.job_id != ingestion.job_id:
            return self.create_ingestion_job(ingestion)
        return self.update_ingestion_job(
            ingestion.job_id,
            status=ingestion.status,
            failure_reason=ingestion.failure_reason,
            started_at=ingestion.started_at,
            completed_at=ingestion.completed_at,
            retry_count=ingestion.retry_count,
            is_reindex=ingestion.is_reindex,
            chunk_size=ingestion.chunk_size,
            chunk_overlap=ingestion.chunk_overlap,
        )

    def get_ingestion(self, document_id: str) -> RagIngestionJobRecord:
        job = self.get_latest_ingestion_job_for_document(document_id)
        if job is None:
            raise KeyError(document_id)
        return job

    def clear(self) -> None:
        if self.uses_database:
            with self._session() as session:
                assert session is not None
                session.execute(delete(RagIngestionJobModel))
                session.execute(delete(RagChunkModel))
                session.execute(delete(RagDocumentModel))
                session.flush()
            return

        with self._lock:
            self._documents.clear()
            self._chunks.clear()
            self._ingestion_jobs.clear()


def _build_default_repository() -> RagDocumentRepository:
    settings = get_settings()
    if settings.test_database_url or settings.database_url:
        return RagDocumentRepository(session_factory=build_session_factory())
    return RagDocumentRepository()


_RAG_DOCUMENT_REPOSITORY = _build_default_repository()


def get_rag_document_repository() -> RagDocumentRepository:
    return _RAG_DOCUMENT_REPOSITORY
