from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.rag import RagDocumentCreateRequest, RagIngestRequest
from app.services.rag_ingestion import RagIngestionService, chunk_text
from app.storage.rag_documents import RagDocumentRepository
from app.services.rag_ingestion import get_rag_ingestion_service


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
    service = RagIngestionService(repository=repository)
    registration_one = service.register_document(
        RagDocumentCreateRequest(title="Stable Notes", text=text)
    )
    registration_two = service.register_document(
        RagDocumentCreateRequest(title="Stable Notes", text=text)
    )

    assert registration_one.doc_id == registration_two.doc_id
    assert registration_one.content_hash == registration_two.content_hash


def test_register_and_ingest_document_from_text() -> None:
    repository = RagDocumentRepository()
    service = RagIngestionService(repository=repository)

    registration = service.register_document(
        RagDocumentCreateRequest(
            title="Project Notes",
            text="Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau.",
        )
    )

    ingestion = service.ingest_document(
        RagIngestRequest(
            doc_id=registration.doc_id,
            chunk_size=30,
            chunk_overlap=5,
        )
    )

    assert ingestion.doc_id == registration.doc_id
    assert ingestion.chunk_count >= 2
    assert ingestion.chunks[0].chunk_id == f"{registration.doc_id}-chunk-0000"
    assert ingestion.chunks[0].text


def test_rag_endpoints_return_expected_payloads() -> None:
    repository = RagDocumentRepository()
    service = RagIngestionService(repository=repository)
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
        ingest_response = client.post(
            "/api/v1/rag/ingest",
            json={
                "doc_id": doc_id,
                "chunk_size": 25,
                "chunk_overlap": 5,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert register_response.status_code == 200
    assert register_response.json()["success"] is True
    assert ingest_response.status_code == 200
    ingest_body = ingest_response.json()["data"]
    assert ingest_body["doc_id"] == doc_id
    assert ingest_body["chunk_count"] >= 2
    assert ingest_body["chunks"][0]["chunk_id"].startswith(doc_id)


def test_rag_validation_error_is_enveloped() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/rag/ingest", json={"chunk_size": 100, "chunk_overlap": 10})

    assert response.status_code == 422
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
