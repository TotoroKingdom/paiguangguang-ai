from __future__ import annotations

from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.ai.deepseek import DeepSeekClient
from app.db.base import Base
from app.db.models import User
from app.main import app
from app.schemas.rag import RagQueryRequest
from app.ai.rerank import RerankResult
from app.services.auth import AuthService, get_auth_service
from app.services.hybrid_retrieval import HybridRetrievalService
from app.services.rag_query import RagQueryService, get_rag_query_service
from app.services.rbac import RBACService, get_rbac_service
from app.db.session import get_db_session


class FakeSearchStore:
    def __init__(self, hits):
        self.hits = list(hits)
        self.calls: list[dict[str, object]] = []

    def search(self, collection_name, query_text, *, top_k=5, access_context=None):
        self.calls.append(
            {
                "collection_name": collection_name,
                "query_text": query_text,
                "top_k": top_k,
                "access_context": access_context,
            }
        )
        hits = list(self.hits)
        if access_context is not None:
            filtered = []
            for hit in hits:
                metadata = getattr(hit, "metadata", {}) or {}
                if access_context.is_system_admin:
                    filtered.append(hit)
                    continue
                workspace_id = metadata.get("workspace_id")
                permission_scope = metadata.get("permission_scope")
                if workspace_id is None or permission_scope is None:
                    if access_context.allow_legacy_metadata:
                        filtered.append(hit)
                    continue
                if access_context.workspace_id is not None and workspace_id != access_context.workspace_id:
                    continue
                if permission_scope in access_context.allowed_permission_scopes:
                    filtered.append(hit)
            hits = filtered
        return hits[:top_k]


class FakeVectorStore(FakeSearchStore):
    pass


class FakeKeywordRetriever(FakeSearchStore):
    pass


class FakeRerankProvider:
    def __init__(self, ranking: dict[str, float] | None = None) -> None:
        self.ranking = dict(ranking or {})
        self.calls: list[dict[str, object]] = []

    def rerank(self, query: str, documents, *, top_n=None):
        self.calls.append({"query": query, "documents": list(documents), "top_n": top_n})
        results = [
            RerankResult(index=index, relevance_score=self.ranking.get(document, 0.0))
            for index, document in enumerate(documents)
        ]
        results.sort(key=lambda item: (-item.relevance_score, item.index))
        if top_n is not None:
            return results[:top_n]
        return results


def _create_session(tmp_path, filename: str) -> Session:
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / filename).as_posix()}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_factory()


def _build_query_service(vector_hits, keyword_hits, handler, rerank_provider=None):
    transport = httpx.MockTransport(handler)
    client = DeepSeekClient(api_key="test-key", transport=transport)
    vector_store = FakeVectorStore(vector_hits)
    keyword_retriever = FakeKeywordRetriever(keyword_hits)
    retrieval_service = HybridRetrievalService(
        vector_store=vector_store,
        keyword_retriever=keyword_retriever,
    )
    return (
        RagQueryService(
            retrieval_service=retrieval_service,
            client=client,
            rerank_provider=rerank_provider,
        ),
        vector_store,
        keyword_retriever,
        rerank_provider,
    )


def _build_test_client(
    session: Session,
    auth_service: AuthService,
    query_service: RagQueryService,
    rbac_service: RBACService | None = None,
) -> TestClient:
    app.dependency_overrides.clear()

    def override_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_rag_query_service] = lambda: query_service
    if rbac_service is not None:
        app.dependency_overrides[get_rbac_service] = lambda: rbac_service
    return TestClient(app)


def _create_user(session: Session, auth_service: AuthService, *, email: str, password: str) -> User:
    return auth_service.create_user(
        session,
        email=email,
        display_name=email.split("@", 1)[0].title(),
        password=password,
        is_active=True,
    )


def test_rag_query_requires_authentication(tmp_path) -> None:
    session = _create_session(tmp_path, "rag-query-auth.sqlite3")
    auth_service = AuthService()

    service, _vector_store, _keyword_retriever, _rerank_provider = _build_query_service(
        [],
        [],
        lambda request: httpx.Response(200, json={}),
    )
    client = _build_test_client(session, auth_service, service)

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
        session.close()

    assert response.status_code == 401
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] == "HTTP_ERROR"


def test_rag_query_rejects_users_without_knowledge_permission(tmp_path) -> None:
    session = _create_session(tmp_path, "rag-query-permission.sqlite3")
    auth_service = AuthService()
    rbac_service = RBACService()
    rbac_service.bootstrap_defaults(session)

    _create_user(session, auth_service, email="reader@example.com", password="Secret123!")

    service, _vector_store, _keyword_retriever, _rerank_provider = _build_query_service(
        [],
        [],
        lambda request: httpx.Response(200, json={}),
    )
    client = _build_test_client(session, auth_service, service, rbac_service)

    try:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "reader@example.com", "password": "Secret123!"},
        )
        token = login_response.json()["data"]["access_token"]
        response = client.post(
            "/api/v1/rag/query",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "question": "How is the project deployed?",
                "collection": "portfolio_knowledge",
                "top_k": 2,
            },
        )
    finally:
        app.dependency_overrides.clear()
        session.close()

    assert response.status_code == 403
    assert response.json()["success"] is False
    assert response.json()["error"]["message"] == "knowledge.query permission required"


def test_rag_query_returns_answer_and_richer_sources(tmp_path) -> None:
    session = _create_session(tmp_path, "rag-query-success.sqlite3")
    auth_service = AuthService()
    rbac_service = RBACService()
    defaults = rbac_service.bootstrap_defaults(session)
    user = _create_user(session, auth_service, email="admin@example.com", password="Secret123!")
    rbac_service.assign_role_to_user(session, user.id, "user")
    rbac_service.add_user_to_workspace(session, user.id, defaults.default_workspace.slug)

    captured_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_bodies.append(request.content.decode("utf-8"))
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

    accessible_hit = SimpleNamespace(
        doc_id="doc-alpha",
        chunk_id="doc-alpha-chunk-0001",
        title="Alpha Notes",
        page_number=3,
        chunk_index=1,
        text="Alpha project notes explain the workflow.",
        score=0.91,
        start_char=0,
        end_char=40,
        metadata={
            "doc_id": "doc-alpha",
            "chunk_id": "doc-alpha-chunk-0001",
            "title": "Alpha Notes",
            "page_number": 3,
            "chunk_index": 1,
            "workspace_id": defaults.default_workspace.id,
            "permission_scope": "workspace",
            "owner_user_id": user.id,
            "content_hash": "hash-alpha",
            "lifecycle_version": 4,
            "start_char": 0,
            "end_char": 40,
        },
    )
    inaccessible_hit = SimpleNamespace(
        doc_id="doc-admin",
        chunk_id="doc-admin-chunk-0002",
        title="Admin Notes",
        page_number=2,
        chunk_index=2,
        text="Admin-only deployment notes.",
        score=0.72,
        start_char=41,
        end_char=80,
        metadata={
            "doc_id": "doc-admin",
            "chunk_id": "doc-admin-chunk-0002",
            "title": "Admin Notes",
            "page_number": 2,
            "chunk_index": 2,
            "workspace_id": defaults.default_workspace.id,
            "permission_scope": "admin",
            "owner_user_id": user.id,
            "content_hash": "hash-admin",
            "lifecycle_version": 4,
            "start_char": 41,
            "end_char": 80,
        },
    )

    rerank_provider = FakeRerankProvider(
        {
            "Alpha project notes explain the workflow.": 0.8,
        }
    )
    service, vector_store, keyword_retriever, _rerank_provider = _build_query_service(
        [accessible_hit, inaccessible_hit],
        [accessible_hit],
        handler,
        rerank_provider=rerank_provider,
    )
    client = _build_test_client(session, auth_service, service, rbac_service)

    try:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "Secret123!"},
        )
        token = login_response.json()["data"]["access_token"]
        response = client.post(
            "/api/v1/rag/query",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "question": "How is the project deployed?",
                "collection": "portfolio_knowledge",
                "top_k": 2,
            },
        )
    finally:
        app.dependency_overrides.clear()
        session.close()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["answer"] == "Use the retrieval context and cite the source chunks."
    assert len(body["data"]["sources"]) == 1
    assert body["data"]["rewrite"]["original_question"] == "How is the project deployed?"
    assert body["data"]["rewrite"]["rewritten_queries"] == []
    assert body["data"]["rewrite"]["metadata"]["status"] == "disabled"

    source = body["data"]["sources"][0]
    assert source["doc_id"] == "doc-alpha"
    assert source["chunk_id"] == "doc-alpha-chunk-0001"
    assert source["title"] == "Alpha Notes"
    assert source["page_number"] == 3
    assert source["chunk_index"] == 1
    assert source["text"] == "Alpha project notes explain the workflow."
    assert source["score"] > 0
    assert source["rerank_score"] == 0.8
    assert source["route_scores"] == {"vector": 0.91, "keyword": 0.91}
    assert source["metadata"]["workspace_id"] == defaults.default_workspace.id
    assert source["metadata"]["permission_scope"] == "workspace"
    assert source["metadata"]["lifecycle_version"] == 4

    assert vector_store.calls == [
        {
            "collection_name": "portfolio_knowledge",
            "query_text": "How is the project deployed?",
            "top_k": 2,
            "access_context": vector_store.calls[0]["access_context"],
        }
    ]
    assert keyword_retriever.calls == [
        {
            "collection_name": "portfolio_knowledge",
            "query_text": "How is the project deployed?",
            "top_k": 2,
            "access_context": keyword_retriever.calls[0]["access_context"],
        }
    ]
    access_context = vector_store.calls[0]["access_context"]
    assert access_context.user_id == user.id
    assert access_context.workspace_id == defaults.default_workspace.id
    assert access_context.allowed_permission_scopes == ("workspace",)
    assert access_context.is_system_admin is False
    assert access_context.allow_legacy_metadata is True
    assert rerank_provider.calls == [
        {
            "query": "How is the project deployed?",
            "documents": [
                "Alpha project notes explain the workflow.",
            ],
            "top_n": 1,
        }
    ]
    assert "Retrieved context:" in captured_bodies[0]
    assert "doc_id=doc-alpha" in captured_bodies[0]
    assert "page=3" in captured_bodies[0]


def test_rag_query_service_returns_sources_without_auth_wrapper() -> None:
    captured_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_bodies.append({})
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

    service, _vector_store, _keyword_retriever, _rerank_provider = _build_query_service([], [], handler)

    result = service.query(
        RagQueryRequest(
            question="What documents exist?",
            collection="portfolio_knowledge",
            top_k=5,
        )
    )

    assert result.answer == "I could not find relevant project context."
    assert result.sources == []
    assert captured_bodies == [{}]


def test_rag_query_applies_rerank_before_prompt_context(tmp_path) -> None:
    session = _create_session(tmp_path, "rag-query-rerank.sqlite3")
    auth_service = AuthService()
    rbac_service = RBACService()
    defaults = rbac_service.bootstrap_defaults(session)
    user = _create_user(session, auth_service, email="rerank@example.com", password="Secret123!")
    rbac_service.assign_role_to_user(session, user.id, "user")
    rbac_service.add_user_to_workspace(session, user.id, defaults.default_workspace.slug)

    captured_bodies: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_bodies.append(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Rerank should reorder the context before answering.",
                        }
                    }
                ]
            },
        )

    alpha_hit = SimpleNamespace(
        doc_id="doc-alpha",
        chunk_id="doc-alpha-chunk-0001",
        title="Alpha Notes",
        page_number=1,
        chunk_index=1,
        text="Alpha deployment notes.",
        score=0.9,
        start_char=0,
        end_char=24,
        metadata={
            "doc_id": "doc-alpha",
            "chunk_id": "doc-alpha-chunk-0001",
            "title": "Alpha Notes",
            "page_number": 1,
            "chunk_index": 1,
            "workspace_id": defaults.default_workspace.id,
            "permission_scope": "workspace",
            "start_char": 0,
            "end_char": 24,
        },
    )
    beta_hit = SimpleNamespace(
        doc_id="doc-beta",
        chunk_id="doc-beta-chunk-0001",
        title="Beta Notes",
        page_number=2,
        chunk_index=1,
        text="Beta deployment notes.",
        score=0.85,
        start_char=0,
        end_char=23,
        metadata={
            "doc_id": "doc-beta",
            "chunk_id": "doc-beta-chunk-0001",
            "title": "Beta Notes",
            "page_number": 2,
            "chunk_index": 1,
            "workspace_id": defaults.default_workspace.id,
            "permission_scope": "workspace",
            "start_char": 0,
            "end_char": 23,
        },
    )
    rerank_provider = FakeRerankProvider(
        {
            "Alpha deployment notes.": 0.2,
            "Beta deployment notes.": 0.9,
        }
    )
    service, _vector_store, _keyword_retriever, _rerank_provider = _build_query_service(
        [alpha_hit, beta_hit],
        [alpha_hit, beta_hit],
        handler,
        rerank_provider=rerank_provider,
    )
    client = _build_test_client(session, auth_service, service, rbac_service)

    try:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "rerank@example.com", "password": "Secret123!"},
        )
        token = login_response.json()["data"]["access_token"]
        response = client.post(
            "/api/v1/rag/query",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "question": "How is deployment organized?",
                "collection": "portfolio_knowledge",
                "top_k": 2,
            },
        )
    finally:
        app.dependency_overrides.clear()
        session.close()

    assert response.status_code == 200
    body = response.json()["data"]
    assert [source["doc_id"] for source in body["sources"]] == ["doc-beta", "doc-alpha"]
    assert body["sources"][0]["rerank_score"] == 0.9
    assert body["sources"][1]["rerank_score"] == 0.2
    assert "doc_id=doc-beta" in captured_bodies[0]
    assert captured_bodies[0].index("doc_id=doc-beta") < captured_bodies[0].index("doc_id=doc-alpha")
