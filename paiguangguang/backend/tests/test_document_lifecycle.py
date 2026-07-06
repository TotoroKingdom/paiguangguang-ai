from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.services.rag_ingestion import RagIngestionService
from app.storage.rag_documents import (
    RagChunkRecord,
    RagDocumentRecord,
    RagDocumentRepository,
    RagIngestionJobRecord,
)
from app.schemas.rag import RagDocumentCreateRequest, RagIngestRequest


def _create_repository(tmp_path, filename: str = "document-lifecycle.sqlite3") -> RagDocumentRepository:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / filename).as_posix()}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return RagDocumentRepository(session_factory=session_factory)


def test_repository_tracks_document_chunk_and_job_lifecycle_states(tmp_path) -> None:
    repository = _create_repository(tmp_path)
    now = datetime.now(timezone.utc)

    document = repository.upsert_document(
        RagDocumentRecord(
            document_id="doc-1",
            title="Lifecycle Notes",
            original_filename="lifecycle-notes.txt",
            text="Lifecycle source text",
            content_hash="hash-1",
            owner_user_id="user-1",
            workspace_id="workspace-1",
            permission_scope="workspace",
            status="registered",
            parse_status="pending",
            chunk_status="pending",
            embedding_status="pending",
            index_status="pending",
            is_deleted=False,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
    )
    assert document.document_id == "doc-1"
    assert document.status == "registered"
    assert document.original_filename == "lifecycle-notes.txt"

    updated = repository.update_document_lifecycle(
        "doc-1",
        status="indexed",
        parse_status="completed",
        chunk_status="completed",
        embedding_status="completed",
        index_status="completed",
    )
    assert updated.status == "indexed"
    assert updated.parse_status == "completed"

    chunk = repository.upsert_chunk(
        RagChunkRecord(
            chunk_id="doc-1-chunk-0000",
            document_id="doc-1",
            chunk_index=0,
            text="Lifecycle chunk",
            start_char=0,
            end_char=15,
            page_number=1,
            metadata={"source": "test"},
        )
    )
    assert chunk.metadata["source"] == "test"

    job = repository.create_ingestion_job(
        RagIngestionJobRecord(
            job_id="job-1",
            document_id="doc-1",
            status="running",
            failure_reason=None,
            started_at=now,
            completed_at=None,
            retry_count=0,
            is_reindex=False,
            created_at=now,
            updated_at=now,
        )
    )
    assert job.status == "running"

    completed_job = repository.update_ingestion_job(
        "job-1",
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    assert completed_job.status == "completed"
    assert completed_job.completed_at is not None

    failed = repository.mark_document_failed("doc-1", "Parse failed")
    assert failed.status == "failed"
    assert failed.error_message == "Parse failed"

    deleted = repository.mark_document_deleted("doc-1")
    assert deleted.status == "deleted"
    assert deleted.is_deleted is True

    reloaded = repository.get_document("doc-1")
    assert reloaded.is_deleted is True
    assert repository.get_chunks("doc-1")[0].chunk_id == "doc-1-chunk-0000"
    assert repository.get_ingestion_job("job-1").status == "completed"


def test_knowledge_base_version_is_persisted_and_monotonic(tmp_path) -> None:
    repository = _create_repository(tmp_path, "kb-version.sqlite3")

    first = repository.get_knowledge_base_version("portfolio_knowledge")
    second = repository.bump_knowledge_base_version("portfolio_knowledge")
    third = repository.get_knowledge_base_version("portfolio_knowledge")
    fourth = repository.bump_knowledge_base_version("portfolio_knowledge")

    assert first == 1
    assert second == 2
    assert third == 2
    assert fourth == 3


def test_ingestion_persists_document_chunks_and_job_state(tmp_path) -> None:
    repository = _create_repository(tmp_path, "ingestion-lifecycle.sqlite3")
    service = RagIngestionService(repository=repository, index_to_vector_store=False)

    registration = service.register_document(
        RagDocumentCreateRequest(
            title="Project Notes",
            original_filename="project-notes.md",
            text="Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau.",
        )
    )

    registered_document = repository.get_document(registration.doc_id)
    assert registered_document.status == "registered"
    assert registered_document.parse_status == "pending"
    assert registered_document.is_deleted is False

    ingestion = service.ingest_document(
        RagIngestRequest(
            doc_id=registration.doc_id,
            chunk_size=30,
            chunk_overlap=5,
        )
    )

    indexed_document = repository.get_document(registration.doc_id)
    assert indexed_document.status == "indexed"
    assert indexed_document.parse_status == "completed"
    assert indexed_document.chunk_status == "completed"
    assert indexed_document.embedding_status == "completed"
    assert indexed_document.index_status == "completed"
    assert indexed_document.original_filename == "project-notes.md"

    chunks = repository.get_chunks(registration.doc_id)
    assert len(chunks) == ingestion.chunk_count
    assert chunks[0].chunk_id == f"{registration.doc_id}-chunk-0000"
    assert chunks[0].metadata["chunk_index"] == 0

    job = repository.get_latest_ingestion_job_for_document(registration.doc_id)
    assert job is not None
    assert job.status == "completed"
    assert job.failure_reason is None
    assert job.retry_count == 0
