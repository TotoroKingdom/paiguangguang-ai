from __future__ import annotations

from collections.abc import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.main import app as fastapi_app
from app.db.session import get_db_session
from app.services.admin import AdminService, get_admin_service
from app.services.auth import AuthService, get_auth_service
from app.storage.rag_documents import RagDocumentRepository
from app.storage.cache import (
    InMemoryCacheAdapter,
    build_admin_detail_cache_key,
    build_admin_list_cache_key,
    build_auth_user_context_cache_key,
)
from app.services.rag_ingestion import RagIngestionService, get_rag_ingestion_service
from app.services.rbac import RBACService, get_rbac_service


def _build_test_app(
    session: Session,
    auth_service: AuthService,
    rbac_service: RBACService,
    rag_service: RagIngestionService,
    admin_service: AdminService | None = None,
) -> FastAPI:
    app = fastapi_app
    app.dependency_overrides.clear()

    def override_db_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_rbac_service] = lambda: rbac_service
    app.dependency_overrides[get_rag_ingestion_service] = lambda: rag_service
    if admin_service is not None:
        app.dependency_overrides[get_admin_service] = lambda: admin_service
    return app


def _create_session(tmp_path, filename: str):
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / filename).as_posix()}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_factory(), session_factory


def _create_user(auth_service: AuthService, session: Session, *, email: str, password: str):
    return auth_service.create_user(
        session,
        email=email,
        display_name=email.split("@", 1)[0].title(),
        password=password,
        is_active=True,
    )


class TrackingVectorStore:
    def __init__(self) -> None:
        self.index_calls: list[dict[str, object]] = []
        self.delete_calls: list[dict[str, object]] = []

    def index_ingestion(self, collection_name, *, doc_id, title, content_hash, chunks, lifecycle_version=1):
        self.index_calls.append(
            {
                "collection_name": collection_name,
                "doc_id": doc_id,
                "title": title,
                "content_hash": content_hash,
                "chunk_ids": [chunk.chunk_id for chunk in chunks],
                "lifecycle_version": lifecycle_version,
            }
        )
        return len(chunks)

    def delete_document(self, collection_name, *, doc_id):
        self.delete_calls.append({"collection_name": collection_name, "doc_id": doc_id})


def test_admin_api_supports_document_lifecycle_and_catalog_management(tmp_path) -> None:
    session, session_factory = _create_session(tmp_path, "admin-api.sqlite3")
    auth_service = AuthService()
    rbac_service = RBACService()
    defaults = rbac_service.bootstrap_defaults(session)
    admin_user = _create_user(auth_service, session, email="admin@example.com", password="Secret123!")
    normal_user = _create_user(auth_service, session, email="reader@example.com", password="Secret123!")
    rbac_service.assign_role_to_user(session, admin_user.id, "system_admin")
    rbac_service.assign_role_to_user(session, normal_user.id, "user")
    rbac_service.add_user_to_workspace(session, admin_user.id, defaults.default_workspace.slug)
    rbac_service.add_user_to_workspace(session, normal_user.id, defaults.default_workspace.slug)

    vector_store = TrackingVectorStore()
    rag_service = RagIngestionService(
        repository=RagDocumentRepository(session_factory=session_factory),
        vector_store=vector_store,  # type: ignore[arg-type]
    )
    app = _build_test_app(session, auth_service, rbac_service, rag_service)
    client = TestClient(app)

    try:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "Secret123!"},
        )
        token = login_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        users_response = client.get(
            "/api/v1/admin/users?page=1&page_size=2&sort_by=email&sort_order=asc",
            headers=headers,
        )
        assert users_response.status_code == 200
        users_payload = users_response.json()["data"]
        assert users_payload["page"] == 1
        assert users_payload["page_size"] == 2
        assert users_payload["total"] >= 2
        users = users_payload["items"]
        assert {user["email"] for user in users} >= {"admin@example.com", "reader@example.com"}

        created_user_response = client.post(
            "/api/v1/admin/users",
            headers=headers,
            json={
                "email": "editor@example.com",
                "display_name": "Editor",
                "password": "Secret123!",
                "roles": ["user"],
                "workspace_slugs": [defaults.default_workspace.slug],
            },
        )
        assert created_user_response.status_code == 200
        created_user = created_user_response.json()["data"]
        assert created_user["email"] == "editor@example.com"
        assert created_user["roles"] == ["user"]
        assert created_user["effective_permissions"] == [
            "document.upload",
            "document.view",
            "knowledge.query",
        ]

        created_user_detail_response = client.get(
            f"/api/v1/admin/users/{created_user['id']}",
            headers=headers,
        )
        assert created_user_detail_response.status_code == 200
        assert created_user_detail_response.json()["data"]["effective_permissions"] == [
            "document.upload",
            "document.view",
            "knowledge.query",
        ]

        updated_user_response = client.patch(
            f"/api/v1/admin/users/{created_user['id']}",
            headers=headers,
            json={"display_name": "Editor Updated", "roles": ["document_admin"]},
        )
        assert updated_user_response.status_code == 200
        assert updated_user_response.json()["data"]["display_name"] == "Editor Updated"
        assert updated_user_response.json()["data"]["roles"] == ["document_admin"]
        assert updated_user_response.json()["data"]["effective_permissions"] == [
            "document.delete",
            "document.reindex",
            "document.upload",
            "document.view",
            "knowledge.query",
        ]

        activated_user_response = client.post(
            f"/api/v1/admin/users/{created_user['id']}/activate",
            headers=headers,
        )
        assert activated_user_response.status_code == 200
        assert activated_user_response.json()["data"]["is_active"] is True

        deleted_user_response = client.delete(
            f"/api/v1/admin/users/{created_user['id']}",
            headers=headers,
        )
        assert deleted_user_response.status_code == 200
        assert deleted_user_response.json()["data"]["email"] == "editor@example.com"

        deleted_user_detail_response = client.get(
            f"/api/v1/admin/users/{created_user['id']}",
            headers=headers,
        )
        assert deleted_user_detail_response.status_code == 404

        roles_response = client.get(
            "/api/v1/admin/roles?page=1&page_size=1&sort_by=name&sort_order=asc",
            headers=headers,
        )
        assert roles_response.status_code == 200
        roles_payload = roles_response.json()["data"]
        assert roles_payload["page"] == 1
        assert roles_payload["page_size"] == 1
        assert roles_payload["total"] >= 3
        assert len(roles_payload["items"]) == 1
        assert roles_payload["items"][0]["name"] == "document_admin"

        created_role_response = client.post(
            "/api/v1/admin/roles",
            headers=headers,
            json={
                "name": "docs_auditor",
                "description": "Audits document state",
                "permissions": ["document.view"],
            },
        )
        assert created_role_response.status_code == 200
        created_role = created_role_response.json()["data"]
        assert created_role["name"] == "docs_auditor"
        assert created_role["permissions"] == ["document.view"]

        updated_role_response = client.patch(
            f"/api/v1/admin/roles/{created_role['id']}",
            headers=headers,
            json={
                "description": "Audits document and job state",
                "permissions": ["document.view", "document.delete"],
            },
        )
        assert updated_role_response.status_code == 200
        assert updated_role_response.json()["data"]["permissions"] == [
            "document.delete",
            "document.view",
        ]

        deleted_role_response = client.delete(
            f"/api/v1/admin/roles/{created_role['id']}",
            headers=headers,
        )
        assert deleted_role_response.status_code == 200
        assert deleted_role_response.json()["data"]["name"] == "docs_auditor"

        permissions_response = client.get(
            "/api/v1/admin/permissions?page=1&page_size=2&sort_by=name&sort_order=asc",
            headers=headers,
        )
        assert permissions_response.status_code == 200
        permissions_payload = permissions_response.json()["data"]
        assert permissions_payload["page"] == 1
        assert permissions_payload["page_size"] == 2
        assert permissions_payload["total"] >= 8
        assert len(permissions_payload["items"]) == 2
        assert permissions_payload["items"][0]["name"] == "document.delete"

        created_permission_response = client.post(
            "/api/v1/admin/permissions",
            headers=headers,
            json={"name": "document.audit", "description": "Audit documents"},
        )
        assert created_permission_response.status_code == 200
        created_permission = created_permission_response.json()["data"]
        assert created_permission["name"] == "document.audit"

        updated_permission_response = client.patch(
            f"/api/v1/admin/permissions/{created_permission['id']}",
            headers=headers,
            json={"name": "document.audit.logs", "description": "Audit document logs"},
        )
        assert updated_permission_response.status_code == 200
        assert updated_permission_response.json()["data"]["name"] == "document.audit.logs"

        deleted_permission_response = client.delete(
            f"/api/v1/admin/permissions/{created_permission['id']}",
            headers=headers,
        )
        assert deleted_permission_response.status_code == 200
        assert deleted_permission_response.json()["data"]["name"] == "document.audit.logs"

        workspaces_response = client.get(
            "/api/v1/admin/workspaces?page=1&page_size=1&sort_by=slug&sort_order=asc",
            headers=headers,
        )
        assert workspaces_response.status_code == 200
        workspaces_payload = workspaces_response.json()["data"]
        assert workspaces_payload["page"] == 1
        assert workspaces_payload["page_size"] == 1
        assert workspaces_payload["total"] >= 1
        assert len(workspaces_payload["items"]) == 1
        assert workspaces_payload["items"][0]["slug"] == defaults.default_workspace.slug

        created_workspace_response = client.post(
            "/api/v1/admin/workspaces",
            headers=headers,
            json={"slug": "docs", "name": "Docs Workspace", "is_default": False},
        )
        assert created_workspace_response.status_code == 200
        created_workspace = created_workspace_response.json()["data"]
        assert created_workspace["slug"] == "docs"

        updated_workspace_response = client.patch(
            f"/api/v1/admin/workspaces/{created_workspace['id']}",
            headers=headers,
            json={"name": "Docs Workspace Updated", "is_default": True},
        )
        assert updated_workspace_response.status_code == 200
        assert updated_workspace_response.json()["data"]["is_default"] is True

        deleted_workspace_response = client.delete(
            f"/api/v1/admin/workspaces/{created_workspace['id']}",
            headers=headers,
        )
        assert deleted_workspace_response.status_code == 200
        assert deleted_workspace_response.json()["data"]["slug"] == "docs"

        uploaded_document_response = client.post(
            "/api/v1/admin/documents/upload",
            headers=headers,
            files={
                "file": (
                    "uploaded-notes.txt",
                    b"Uploaded document body for admin validation.",
                    "text/plain",
                )
            },
            data={
                "title": "Uploaded Notes",
                "owner_user_id": admin_user.id,
                "workspace_id": defaults.default_workspace.id,
                "permission_scope": "workspace",
            },
        )
        assert uploaded_document_response.status_code == 200
        uploaded_document = uploaded_document_response.json()["data"]
        assert uploaded_document["title"] == "Uploaded Notes"
        assert uploaded_document["original_filename"] == "uploaded-notes.txt"

        document_create_response = client.post(
            "/api/v1/admin/documents",
            headers=headers,
            json={
                "title": "Admin Notes",
                "original_filename": "admin-notes.md",
                "text": "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu.",
                "owner_user_id": admin_user.id,
                "workspace_id": defaults.default_workspace.id,
                "permission_scope": "workspace",
            },
        )
        assert document_create_response.status_code == 200
        created_document = document_create_response.json()["data"]
        assert created_document["status"] == "registered"
        assert created_document["original_filename"] == "admin-notes.md"

        document_detail_response = client.get(
            f"/api/v1/admin/documents/{created_document['doc_id']}",
            headers=headers,
        )
        assert document_detail_response.status_code == 200
        assert document_detail_response.json()["data"]["title"] == "Admin Notes"
        assert document_detail_response.json()["data"]["original_filename"] == "admin-notes.md"

        document_update_response = client.patch(
            f"/api/v1/admin/documents/{created_document['doc_id']}",
            headers=headers,
            json={"title": "Admin Notes Updated", "status": "indexed"},
        )
        assert document_update_response.status_code == 200
        assert document_update_response.json()["data"]["title"] == "Admin Notes Updated"
        assert document_update_response.json()["data"]["status"] == "indexed"

        reindex_response = client.post(
            f"/api/v1/admin/documents/{created_document['doc_id']}/reindex",
            headers=headers,
        )
        assert reindex_response.status_code == 200
        assert reindex_response.json()["data"]["status"] == "indexed"
        assert vector_store.delete_calls == [
            {"collection_name": rag_service.collection_name, "doc_id": created_document["doc_id"]}
        ]
        assert vector_store.index_calls[-1]["lifecycle_version"] == 2

        documents_response = client.get(
            "/api/v1/admin/documents?page=1&page_size=1&sort_by=updated_at&sort_order=desc",
            headers=headers,
        )
        assert documents_response.status_code == 200
        documents_payload = documents_response.json()["data"]
        assert documents_payload["page"] == 1
        assert documents_payload["page_size"] == 1
        assert documents_payload["total"] >= 1
        assert len(documents_payload["items"]) == 1
        assert documents_payload["items"][0]["doc_id"] == created_document["doc_id"]

        document_delete_response = client.delete(
            f"/api/v1/admin/documents/{created_document['doc_id']}",
            headers=headers,
        )
        assert document_delete_response.status_code == 200
        assert document_delete_response.json()["data"]["doc_id"] == created_document["doc_id"]
        assert vector_store.delete_calls[-1] == {
            "collection_name": rag_service.collection_name,
            "doc_id": created_document["doc_id"],
        }

        deleted_document_detail_response = client.get(
            f"/api/v1/admin/documents/{created_document['doc_id']}",
            headers=headers,
        )
        assert deleted_document_detail_response.status_code == 404

        document_restore_response = client.post(
            f"/api/v1/admin/documents/{created_document['doc_id']}/restore",
            headers=headers,
        )
        assert document_restore_response.status_code == 404

        jobs_response = client.get(
            "/api/v1/admin/ingestion-jobs?page=1&page_size=1&sort_by=created_at&sort_order=desc",
            headers=headers,
        )
        assert jobs_response.status_code == 200
        jobs_payload = jobs_response.json()["data"]
        assert jobs_payload["page"] == 1
        assert jobs_payload["page_size"] == 1
        assert jobs_payload["total"] == 0
        assert jobs_payload["items"] == []
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_admin_api_denies_non_admin_users_across_endpoint_groups(tmp_path) -> None:
    session, session_factory = _create_session(tmp_path, "admin-api-deny.sqlite3")
    auth_service = AuthService()
    rbac_service = RBACService()
    defaults = rbac_service.bootstrap_defaults(session)
    reader = _create_user(auth_service, session, email="reader@example.com", password="Secret123!")
    rbac_service.assign_role_to_user(session, reader.id, "user")
    rbac_service.add_user_to_workspace(session, reader.id, defaults.default_workspace.slug)

    rag_service = RagIngestionService(
        repository=RagDocumentRepository(session_factory=session_factory),
        index_to_vector_store=False,
    )
    app = _build_test_app(session, auth_service, rbac_service, rag_service)
    client = TestClient(app)

    try:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "reader@example.com", "password": "Secret123!"},
        )
        token = login_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        denied_paths = [
            "/api/v1/admin/users",
            "/api/v1/admin/roles",
            "/api/v1/admin/permissions",
            "/api/v1/admin/workspaces",
            "/api/v1/admin/documents",
            "/api/v1/admin/ingestion-jobs",
        ]
        for path in denied_paths:
            response = client.get(path, headers=headers)
            assert response.status_code == 403
            assert response.json()["success"] is False
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_admin_user_reads_use_cache_on_repeated_requests(monkeypatch, tmp_path) -> None:
    session, session_factory = _create_session(tmp_path, "admin-api-cache.sqlite3")
    auth_service = AuthService()
    rbac_service = RBACService()
    defaults = rbac_service.bootstrap_defaults(session)
    admin_user = _create_user(auth_service, session, email="admin@example.com", password="Secret123!")
    target_user = _create_user(auth_service, session, email="cached@example.com", password="Secret123!")
    rbac_service.assign_role_to_user(session, admin_user.id, "system_admin")
    rbac_service.assign_role_to_user(session, target_user.id, "user")
    rbac_service.add_user_to_workspace(session, admin_user.id, defaults.default_workspace.slug)
    rbac_service.add_user_to_workspace(session, target_user.id, defaults.default_workspace.slug)

    cache = InMemoryCacheAdapter()
    monkeypatch.setattr("app.services.auth.get_cache_adapter", lambda settings=None: cache, raising=False)
    monkeypatch.setattr("app.services.admin.get_cache_adapter", lambda settings=None: cache, raising=False)

    rag_service = RagIngestionService(
        repository=RagDocumentRepository(session_factory=session_factory),
        index_to_vector_store=False,
    )
    admin_service = AdminService(
        auth_service=auth_service,
        rbac_service=rbac_service,
        rag_service=rag_service,
    )
    app = _build_test_app(session, auth_service, rbac_service, rag_service, admin_service=admin_service)
    client = TestClient(app)

    try:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "Secret123!"},
        )
        token = login_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        first_list_response = client.get(
            "/api/v1/admin/users?page=1&page_size=20&sort_by=email&sort_order=asc",
            headers=headers,
        )
        assert first_list_response.status_code == 200

        monkeypatch.setattr(
            "app.services.admin._build_paged_data",
            lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("list query should be served from cache")),
        )
        second_list_response = client.get(
            "/api/v1/admin/users?page=1&page_size=20&sort_by=email&sort_order=asc",
            headers=headers,
        )
        assert second_list_response.status_code == 200
        assert second_list_response.json()["data"] == first_list_response.json()["data"]

        first_detail_response = client.get(
            f"/api/v1/admin/users/{target_user.id}",
            headers=headers,
        )
        assert first_detail_response.status_code == 200

        original_get = session.get

        def fail_user_lookup(entity, ident, *args, **kwargs):
            if entity.__name__ == "User" and ident == target_user.id:
                raise AssertionError("detail lookup should be served from cache")
            return original_get(entity, ident, *args, **kwargs)

        monkeypatch.setattr(session, "get", fail_user_lookup)
        second_detail_response = client.get(
            f"/api/v1/admin/users/{target_user.id}",
            headers=headers,
        )
        assert second_detail_response.status_code == 200
        assert second_detail_response.json()["data"] == first_detail_response.json()["data"]
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_admin_cache_cleanup_endpoints_clear_requested_entries(monkeypatch, tmp_path) -> None:
    session, session_factory = _create_session(tmp_path, "admin-api-cache-clear.sqlite3")
    auth_service = AuthService()
    rbac_service = RBACService()
    defaults = rbac_service.bootstrap_defaults(session)
    admin_user = _create_user(auth_service, session, email="admin@example.com", password="Secret123!")
    target_user = _create_user(auth_service, session, email="cached@example.com", password="Secret123!")
    rbac_service.assign_role_to_user(session, admin_user.id, "system_admin")
    rbac_service.assign_role_to_user(session, target_user.id, "user")
    rbac_service.add_user_to_workspace(session, admin_user.id, defaults.default_workspace.slug)
    rbac_service.add_user_to_workspace(session, target_user.id, defaults.default_workspace.slug)

    cache = InMemoryCacheAdapter()
    monkeypatch.setattr("app.services.auth.get_cache_adapter", lambda settings=None: cache, raising=False)
    monkeypatch.setattr("app.services.admin.get_cache_adapter", lambda settings=None: cache, raising=False)

    rag_service = RagIngestionService(
        repository=RagDocumentRepository(session_factory=session_factory),
        index_to_vector_store=False,
    )
    admin_service = AdminService(
        auth_service=auth_service,
        rbac_service=rbac_service,
        rag_service=rag_service,
    )
    app = _build_test_app(session, auth_service, rbac_service, rag_service, admin_service=admin_service)
    client = TestClient(app)

    try:
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "Secret123!"},
        )
        token = login_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        list_response = client.get(
            "/api/v1/admin/users?page=1&page_size=20&sort_by=email&sort_order=asc",
            headers=headers,
        )
        assert list_response.status_code == 200
        detail_response = client.get(f"/api/v1/admin/users/{target_user.id}", headers=headers)
        assert detail_response.status_code == 200

        list_key = build_admin_list_cache_key("users", page=1, page_size=20, sort_by="email", sort_order="asc")
        detail_key = build_admin_detail_cache_key("users", target_user.id)
        assert cache.get(list_key) is not None
        assert cache.get(detail_key) is not None

        clear_list_response = client.post(
            "/api/v1/admin/cache/clear-list",
            headers=headers,
            json={"entity": "users", "page": 1, "page_size": 20, "sort_by": "email", "sort_order": "asc"},
        )
        assert clear_list_response.status_code == 200
        assert clear_list_response.json()["data"] == {"cleared": "list", "entity": "users"}

        clear_detail_response = client.post(
            "/api/v1/admin/cache/clear-detail",
            headers=headers,
            json={"entity": "users", "entity_id": target_user.id},
        )
        assert clear_detail_response.status_code == 200
        assert clear_detail_response.json()["data"] == {
            "cleared": "detail",
            "entity": "users",
            "entity_id": target_user.id,
        }

        assert cache.get(list_key) is None
        assert cache.get(detail_key) is None
    finally:
        app.dependency_overrides.clear()
        session.close()


def test_admin_user_relationship_changes_invalidate_cached_user_context(monkeypatch, tmp_path) -> None:
    session, session_factory = _create_session(tmp_path, "admin-api-context-invalidate.sqlite3")
    auth_service = AuthService()
    rbac_service = RBACService()
    defaults = rbac_service.bootstrap_defaults(session)
    admin_user = _create_user(auth_service, session, email="admin@example.com", password="Secret123!")
    target_user = _create_user(auth_service, session, email="cached@example.com", password="Secret123!")
    rbac_service.assign_role_to_user(session, admin_user.id, "system_admin")
    rbac_service.assign_role_to_user(session, target_user.id, "user")
    rbac_service.add_user_to_workspace(session, admin_user.id, defaults.default_workspace.slug)
    rbac_service.add_user_to_workspace(session, target_user.id, defaults.default_workspace.slug)

    cache = InMemoryCacheAdapter()
    monkeypatch.setattr("app.services.auth.get_cache_adapter", lambda settings=None: cache, raising=False)
    monkeypatch.setattr("app.services.admin.get_cache_adapter", lambda settings=None: cache, raising=False)

    rag_service = RagIngestionService(
        repository=RagDocumentRepository(session_factory=session_factory),
        index_to_vector_store=False,
    )
    admin_service = AdminService(
        auth_service=auth_service,
        rbac_service=rbac_service,
        rag_service=rag_service,
    )
    app = _build_test_app(session, auth_service, rbac_service, rag_service, admin_service=admin_service)
    client = TestClient(app)

    try:
        target_login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "cached@example.com", "password": "Secret123!"},
        )
        target_token = target_login_response.json()["data"]["access_token"]
        target_headers = {"Authorization": f"Bearer {target_token}"}
        assert client.get("/api/v1/auth/me", headers=target_headers).status_code == 200

        target_context_key = build_auth_user_context_cache_key(target_user.id)
        assert cache.get(target_context_key) is not None

        admin_login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "Secret123!"},
        )
        admin_token = admin_login_response.json()["data"]["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        update_response = client.patch(
            f"/api/v1/admin/users/{target_user.id}",
            headers=admin_headers,
            json={"roles": ["document_admin"]},
        )
        assert update_response.status_code == 200
        assert cache.get(target_context_key) is None
    finally:
        app.dependency_overrides.clear()
        session.close()
