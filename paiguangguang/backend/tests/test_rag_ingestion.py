from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.rag import RagDocumentCreateRequest, RagIngestRequest
from app.services.rag_ingestion import RagIngestionService, chunk_text
from app.services.rag_cache import build_authorized_cache_key, remember_document_cache_keys
from app.storage.rag_documents import RagDocumentRepository
from app.storage.cache import InMemoryCacheAdapter
from app.services.rag_ingestion import get_rag_ingestion_service


class ObservingVectorStore:
    def __init__(self, repository: RagDocumentRepository, *, fail: bool = False) -> None:
        self.repository = repository
        self.fail = fail
        self.calls: list[dict[str, object]] = []
        self.delete_calls: list[dict[str, object]] = []
        self.during_status: dict[str, object] | None = None

    def index_ingestion(self, collection_name, *, doc_id, title, content_hash, chunks, lifecycle_version=1):
        document = self.repository.get_document(doc_id)
        job = self.repository.get_latest_ingestion_job_for_document(doc_id)
        self.during_status = {
            "document_status": document.status,
            "parse_status": document.parse_status,
            "chunk_status": document.chunk_status,
            "embedding_status": document.embedding_status,
            "index_status": document.index_status,
            "job_status": job.status if job is not None else None,
        }
        self.calls.append(
            {
                "collection_name": collection_name,
                "doc_id": doc_id,
                "title": title,
                "content_hash": content_hash,
                "chunks": list(chunks),
            }
        )
        if self.fail:
            raise RuntimeError("Vector indexing failed")
        return len(chunks)

    def delete_document(self, collection_name, *, doc_id):
        self.delete_calls.append({"collection_name": collection_name, "doc_id": doc_id})


def test_chunk_text_is_deterministic() -> None:
    text = "This is a fairly long paragraph designed to prove the chunking output is stable. " * 12

    first = chunk_text(text, chunk_size=120, chunk_overlap=20)
    second = chunk_text(text, chunk_size=120, chunk_overlap=20)

    assert first == second
    assert len(first) > 1
    assert all(chunk.text for chunk in first)
    assert first[0].index == 0
    assert first[0].start_char == 0

    repository = RagDocumentRepository()
    service = RagIngestionService(repository=repository, index_to_vector_store=False)
    registration_one = service.register_document(
        RagDocumentCreateRequest(title="Stable Notes", text=text)
    )
    registration_two = service.register_document(
        RagDocumentCreateRequest(title="Stable Notes", text=text)
    )

    assert registration_one.doc_id == registration_two.doc_id
    assert registration_one.content_hash == registration_two.content_hash
    assert registration_one.status == "registered"
    assert registration_one.parse_status == "pending"
    assert registration_one.index_status == "pending"


def test_register_ingest_and_fetch_document_and_job_state() -> None:
    repository = RagDocumentRepository()
    vector_store = ObservingVectorStore(repository)
    service = RagIngestionService(repository=repository, vector_store=vector_store)  # type: ignore[arg-type]
    app.dependency_overrides[get_rag_ingestion_service] = lambda: service
    client = TestClient(app)

    try:
        register_response = client.post(
            "/api/v1/rag/documents",
            json={
                "title": "Spec Notes",
                "text": "One two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen.",
            },
        )
        doc_id = register_response.json()["data"]["doc_id"]

        before_response = client.get(f"/api/v1/rag/documents/{doc_id}")
        ingest_response = client.post(
            "/api/v1/rag/ingest",
            json={
                "doc_id": doc_id,
                "chunk_size": 25,
                "chunk_overlap": 5,
            },
        )
        job_id = ingest_response.json()["data"]["job"]["job_id"]
        after_document_response = client.get(f"/api/v1/rag/documents/{doc_id}")
        job_response = client.get(f"/api/v1/rag/ingestion-jobs/{job_id}")
    finally:
        app.dependency_overrides.clear()

    assert register_response.status_code == 200
    register_body = register_response.json()["data"]
    assert register_body["doc_id"] == doc_id
    assert register_body["status"] == "registered"
    assert register_body["parse_status"] == "pending"
    assert register_body["is_deleted"] is False

    assert before_response.status_code == 200
    assert before_response.json()["data"]["status"] == "registered"

    assert ingest_response.status_code == 200
    ingest_body = ingest_response.json()["data"]
    assert ingest_body["doc_id"] == doc_id
    assert ingest_body["document"]["status"] == "indexed"
    assert ingest_body["job"]["status"] == "completed"
    assert ingest_body["job"]["is_reindex"] is False
    assert ingest_body["job"]["failure_reason"] is None
    assert ingest_body["chunk_count"] >= 2
    assert ingest_body["chunks"][0]["chunk_id"].startswith(doc_id)

    assert vector_store.during_status is not None
    assert vector_store.during_status["document_status"] == "embedding"
    assert vector_store.during_status["parse_status"] == "completed"
    assert vector_store.during_status["chunk_status"] == "completed"
    assert vector_store.during_status["embedding_status"] == "in_progress"

    assert after_document_response.status_code == 200
    after_document_body = after_document_response.json()["data"]
    assert after_document_body["status"] == "indexed"
    assert after_document_body["parse_status"] == "completed"
    assert after_document_body["chunk_status"] == "completed"
    assert after_document_body["embedding_status"] == "completed"
    assert after_document_body["index_status"] == "completed"

    assert job_response.status_code == 200
    job_body = job_response.json()["data"]
    assert job_body["job_id"] == job_id
    assert job_body["document_id"] == doc_id
    assert job_body["status"] == "completed"
    assert job_body["completed_at"] is not None


def test_failed_ingestion_records_failure_and_leaves_document_inspectable() -> None:
    repository = RagDocumentRepository()
    vector_store = ObservingVectorStore(repository, fail=True)
    service = RagIngestionService(repository=repository, vector_store=vector_store)  # type: ignore[arg-type]
    app.dependency_overrides[get_rag_ingestion_service] = lambda: service
    client = TestClient(app)

    try:
        register_response = client.post(
            "/api/v1/rag/documents",
            json={
                "title": "Broken Notes",
                "text": "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau.",
            },
        )
        doc_id = register_response.json()["data"]["doc_id"]
        ingest_response = client.post(
            "/api/v1/rag/ingest",
            json={
                "doc_id": doc_id,
                "chunk_size": 30,
                "chunk_overlap": 5,
            },
        )
        document_response = client.get(f"/api/v1/rag/documents/{doc_id}")
        job_id = repository.get_latest_ingestion_job_for_document(doc_id).job_id
        job_response = client.get(f"/api/v1/rag/ingestion-jobs/{job_id}")
    finally:
        app.dependency_overrides.clear()

    assert ingest_response.status_code == 502
    assert ingest_response.json()["success"] is False
    assert ingest_response.json()["error"]["code"] == "EXTERNAL_MODEL_ERROR"
    assert "Vector indexing failed" in ingest_response.json()["error"]["message"]

    assert document_response.status_code == 200
    document_body = document_response.json()["data"]
    assert document_body["status"] == "failed"
    assert document_body["error_message"] == "Embedding failed: Vector indexing failed"
    assert document_body["is_deleted"] is False

    assert job_response.status_code == 200
    job_body = job_response.json()["data"]
    assert job_body["status"] == "failed"
    assert job_body["failure_reason"] == "Embedding failed: Vector indexing failed"
    assert job_body["completed_at"] is not None


def test_reindex_creates_new_job_without_changing_document_id() -> None:
    repository = RagDocumentRepository()
    vector_store = ObservingVectorStore(repository)
    service = RagIngestionService(repository=repository, vector_store=vector_store)  # type: ignore[arg-type]
    app.dependency_overrides[get_rag_ingestion_service] = lambda: service
    client = TestClient(app)

    try:
        register_response = client.post(
            "/api/v1/rag/documents",
            json={
                "title": "Reindex Notes",
                "text": "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau.",
            },
        )
        doc_id = register_response.json()["data"]["doc_id"]
        first_ingest_response = client.post(
            "/api/v1/rag/ingest",
            json={
                "doc_id": doc_id,
                "chunk_size": 30,
                "chunk_overlap": 5,
            },
        )
        first_job_id = first_ingest_response.json()["data"]["job"]["job_id"]
        reindex_response = client.post(
            "/api/v1/rag/ingest",
            json={
                "doc_id": doc_id,
                "chunk_size": 30,
                "chunk_overlap": 5,
                "reindex": True,
            },
        )
        reindex_job_id = reindex_response.json()["data"]["job"]["job_id"]
        document_response = client.get(f"/api/v1/rag/documents/{doc_id}")
        first_job_response = client.get(f"/api/v1/rag/ingestion-jobs/{first_job_id}")
        reindex_job_response = client.get(f"/api/v1/rag/ingestion-jobs/{reindex_job_id}")
    finally:
        app.dependency_overrides.clear()

    assert first_ingest_response.status_code == 200
    assert reindex_response.status_code == 200
    assert reindex_job_id != first_job_id

    reindex_body = reindex_response.json()["data"]
    assert reindex_body["doc_id"] == doc_id
    assert reindex_body["job"]["is_reindex"] is True
    assert reindex_body["document"]["status"] == "indexed"

    assert document_response.status_code == 200
    assert document_response.json()["data"]["status"] == "indexed"

    assert first_job_response.status_code == 200
    assert first_job_response.json()["data"]["status"] == "completed"
    assert first_job_response.json()["data"]["is_reindex"] is False

    assert reindex_job_response.status_code == 200
    assert reindex_job_response.json()["data"]["status"] == "completed"
    assert reindex_job_response.json()["data"]["is_reindex"] is True


def test_reindex_clears_old_vector_entries_and_bumps_lifecycle_version() -> None:
    repository = RagDocumentRepository()
    vector_store = ObservingVectorStore(repository)
    service = RagIngestionService(repository=repository, vector_store=vector_store)  # type: ignore[arg-type]

    registration = service.register_document(
        RagDocumentCreateRequest(
            title="Versioned Notes",
            text="Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau.",
        )
    )

    first = service.ingest_document(
        RagIngestRequest(
            doc_id=registration.doc_id,
            chunk_size=30,
            chunk_overlap=5,
        )
    )
    second = service.ingest_document(
        RagIngestRequest(
            doc_id=registration.doc_id,
            chunk_size=30,
            chunk_overlap=5,
            reindex=True,
        )
    )

    assert first.chunk_count == second.chunk_count
    assert vector_store.delete_calls == [{"collection_name": service.collection_name, "doc_id": registration.doc_id}]
    assert vector_store.calls[-1]["chunks"][0].metadata["lifecycle_version"] == 3
    assert repository.get_chunks(registration.doc_id)[0].metadata["lifecycle_version"] == 3


def test_purge_document_artifacts_invalidates_document_cache_entries() -> None:
    repository = RagDocumentRepository()
    vector_store = ObservingVectorStore(repository)
    service = RagIngestionService(repository=repository, vector_store=vector_store)  # type: ignore[arg-type]
    cache = InMemoryCacheAdapter()
    service.cache_adapter = cache

    registration = service.register_document(
        RagDocumentCreateRequest(
            title="Cache Notes",
            text="Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau.",
        )
    )

    answer_key = build_authorized_cache_key(
        "rag:answer",
        access_context=type("Ctx", (), {"workspace_id": "workspace-1", "user_id": "user-1", "allowed_permission_scopes": ("workspace",)})(),
        knowledge_base_version="portfolio-knowledge-base",
        retrieval_strategy_version="rewrite-hybrid-rerank-v1",
        model_version="deepseek-chat",
        payload={"question": "What is the doc about?"},
    )
    retrieval_key = build_authorized_cache_key(
        "rag:retrieval",
        access_context=type("Ctx", (), {"workspace_id": "workspace-1", "user_id": "user-1", "allowed_permission_scopes": ("workspace",)})(),
        knowledge_base_version="portfolio-knowledge-base",
        retrieval_strategy_version="rewrite-hybrid-rerank-v1",
        model_version="deepseek-chat",
        payload={"question": "What is the doc about?"},
    )
    assert answer_key is not None
    assert retrieval_key is not None
    cache.set(answer_key, {"answer": "cached"})
    cache.set(retrieval_key, {"fusion_hits": []})
    remember_document_cache_keys(cache, registration.doc_id, [answer_key, retrieval_key])

    service.purge_document_artifacts(registration.doc_id)

    assert cache.get(answer_key) is None
    assert cache.get(retrieval_key) is None
    assert vector_store.delete_calls == [{"collection_name": service.collection_name, "doc_id": registration.doc_id}]


def test_rag_validation_error_is_enveloped() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/rag/ingest", json={"chunk_size": 100, "chunk_overlap": 10})

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
