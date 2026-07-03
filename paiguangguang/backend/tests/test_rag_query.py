from __future__ import annotations

import json

import httpx
from fastapi.testclient import TestClient

from app.ai.deepseek import DeepSeekClient
from app.main import app
from app.schemas.rag import RagQueryRequest
from app.services.rag_query import RagQueryService, get_rag_query_service


class FakeVectorStore:
    def __init__(self, hits):
        self.hits = hits
        self.calls: list[dict[str, object]] = []

    def search(self, collection_name, query_text, *, top_k=5):
        self.calls.append(
            {
                "collection_name": collection_name,
                "query_text": query_text,
                "top_k": top_k,
            }
        )
        return list(self.hits)


def _build_query_service(hits, handler):
    transport = httpx.MockTransport(handler)
    client = DeepSeekClient(api_key="test-key", transport=transport)
    vector_store = FakeVectorStore(hits)
    return RagQueryService(vector_store=vector_store, client=client), vector_store


def test_rag_query_endpoint_returns_answer_and_sources() -> None:
    captured_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_bodies.append(json.loads(request.content.decode()))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Use the retrieval context and cite the source chunks.",
                        }
                    }
                ]
            },
        )

    hits = [
        type(
            "Hit",
            (),
            {
                "doc_id": "doc-alpha",
                "chunk_id": "doc-alpha-chunk-0001",
                "text": "Alpha project notes explain the workflow.",
                "score": 0.91,
                "title": "Alpha Notes",
            },
        )(),
        type(
            "Hit",
            (),
            {
                "doc_id": "doc-beta",
                "chunk_id": "doc-beta-chunk-0002",
                "text": "Beta project notes mention deployment steps.",
                "score": 0.72,
                "title": None,
            },
        )(),
    ]
    service, vector_store = _build_query_service(hits, handler)
    app.dependency_overrides[get_rag_query_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/rag/query",
            json={
                "question": "How is the project deployed?",
                "collection": "portfolio_knowledge",
                "top_k": 2,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["answer"] == "Use the retrieval context and cite the source chunks."
    assert len(body["data"]["sources"]) == 2
    assert body["data"]["sources"][0]["doc_id"] == "doc-alpha"
    assert body["data"]["sources"][0]["chunk_id"] == "doc-alpha-chunk-0001"
    assert body["data"]["sources"][0]["text"] == "Alpha project notes explain the workflow."
    assert body["data"]["sources"][0]["score"] == 0.91
    assert vector_store.calls == [
        {
            "collection_name": "portfolio_knowledge",
            "query_text": "How is the project deployed?",
            "top_k": 2,
        }
    ]
    assert "Retrieved context:" in captured_bodies[0]["messages"][1]["content"]
    assert "doc_id=doc-alpha" in captured_bodies[0]["messages"][1]["content"]


def test_rag_query_endpoint_handles_empty_retrieval_gracefully() -> None:
    captured_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_bodies.append(json.loads(request.content.decode()))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "I could not find relevant project context.",
                        }
                    }
                ]
            },
        )

    service, _vector_store = _build_query_service([], handler)
    app.dependency_overrides[get_rag_query_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/rag/query",
            json={
                "question": "What documents exist?",
                "collection": "portfolio_knowledge",
                "top_k": 5,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["answer"] == "I could not find relevant project context."
    assert body["data"]["sources"] == []
    assert "No relevant context was retrieved." in captured_bodies[0]["messages"][1]["content"]
