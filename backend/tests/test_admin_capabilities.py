import secrets
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select

from app.config import Settings, settings
from app.core.security import hash_password
from app.db import SessionLocal
from app.main import app
from app.modules.capabilities import router as capabilities_router
from app.modules.identity.service import login_limiter
from app.modules.identity.models import AdminSession, AdminUser
from app.repositories import utc_now

TEST_ADMIN_PASSWORD = secrets.token_urlsafe(24)
TEST_VIEWER_PASSWORD = secrets.token_urlsafe(24)
TEST_LIMITED_PASSWORD = secrets.token_urlsafe(24)
WRONG_PASSWORD = f"invalid-{secrets.token_urlsafe(12)}"


def create_admin(
    username: str = "admin", password: str = TEST_ADMIN_PASSWORD, role: str = "admin"
) -> None:
    with SessionLocal() as session:
        existing = session.scalar(select(AdminUser).where(AdminUser.username == username))
        now = utc_now()
        if existing is None:
            session.add(
                AdminUser(
                    username=username,
                    password_hash=hash_password(password),
                    role=role,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
        session.commit()


def login(client: TestClient, username: str = "admin", password: str = TEST_ADMIN_PASSWORD) -> str:
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": username, "password": password},
        headers={"origin": "http://testserver"},
    )
    assert response.status_code == 200, response.text
    token = client.cookies.get(settings.admin_csrf_cookie_name)
    assert token
    return token


def mutation_headers(csrf: str) -> dict[str, str]:
    return {"origin": "http://testserver", "x-csrf-token": csrf}


def create_capability(client: TestClient, csrf: str, **overrides) -> dict:
    payload = {
        "kind": "tool",
        "name": "财务对账",
        "description": "核对流水与总账的差异。",
        "category": "财务",
        "icon": "database",
        "steps": ["读取流水", "比对总账", "输出差异"],
        "tools": [],
        "config": {"executor": "http", "endpoint": "", "timeoutSeconds": 20},
        "changelog": "初始草稿",
    }
    payload.update(overrides)
    response = client.post(
        "/api/v1/admin/capabilities",
        json=payload,
        headers=mutation_headers(csrf),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_settings_reflect_the_server_runtime_without_leaking_keys(monkeypatch):
    create_admin()
    client = TestClient(app)
    login(client)

    monkeypatch.setattr(settings, "llm_provider", "fake")
    fake_settings = client.get("/api/v1/admin/settings")
    assert fake_settings.status_code == 200, fake_settings.text
    assert fake_settings.json()["executionMode"] == "fake"
    assert any(
        "Agent Runtime" in note for note in fake_settings.json()["notes"]
    )
    assert all(
        "未接入真实 LLM" not in note for note in fake_settings.json()["notes"]
    )

    secret = "provider-key-must-not-appear"
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_api_key", SecretStr(secret))
    real_settings = client.get("/api/v1/admin/settings")
    assert real_settings.status_code == 200, real_settings.text
    assert real_settings.json()["executionMode"] == "openai"
    assert secret not in real_settings.text


def test_admin_login_session_logout_and_csrf():
    create_admin()
    client = TestClient(app)

    assert client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": WRONG_PASSWORD},
        headers={"origin": "http://testserver"},
    ).status_code == 401
    login_response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "admin", "password": TEST_ADMIN_PASSWORD},
        headers={"origin": "http://testserver"},
    )
    assert login_response.status_code == 200
    cookie_headers = "\n".join(login_response.headers.get_list("set-cookie")).lower()
    assert "httponly" in cookie_headers
    assert "samesite=strict" in cookie_headers
    with SessionLocal() as session:
        stored = session.scalar(select(AdminUser).where(AdminUser.username == "admin"))
        assert stored is not None
        assert stored.password_hash.startswith("pbkdf2_sha256$")
        assert TEST_ADMIN_PASSWORD not in stored.password_hash
    csrf = client.cookies.get(settings.admin_csrf_cookie_name)
    assert csrf
    session = client.get("/api/v1/admin/auth/session")
    assert session.status_code == 200
    assert session.json()["user"]["username"] == "admin"
    assert client.get("/api/v1/admin/capabilities").status_code == 200

    assert client.post(
        "/api/v1/admin/capabilities",
        json={
            "kind": "tool",
            "name": "无 CSRF",
        },
        headers={"origin": "http://testserver"},
    ).status_code == 403
    assert client.post(
        "/api/v1/admin/auth/logout",
        json={},
        headers={"origin": "http://testserver"},
    ).status_code == 403
    assert client.post(
        "/api/v1/admin/auth/logout",
        json={},
        headers=mutation_headers(csrf),
    ).status_code == 204
    assert client.get("/api/v1/admin/auth/session").status_code == 401


def test_unauthenticated_and_non_admin_are_rejected():
    anonymous = TestClient(app)
    assert anonymous.get("/api/v1/admin/capabilities").status_code == 401
    assert anonymous.get("/api/v1/admin/overview").status_code == 401

    create_admin("viewer", TEST_VIEWER_PASSWORD, role="viewer")
    viewer = TestClient(app)
    response = viewer.post(
        "/api/v1/admin/auth/login",
        json={"username": "viewer", "password": TEST_VIEWER_PASSWORD},
        headers={"origin": "http://testserver"},
    )
    assert response.status_code == 403


def test_login_rate_limit_locks_a_repeated_failure_source(monkeypatch):
    create_admin("limited", TEST_LIMITED_PASSWORD)
    login_limiter.reset("testclient:limited")
    monkeypatch.setattr(settings, "admin_login_max_attempts", 2)
    monkeypatch.setattr(settings, "admin_login_lock_seconds", 60)
    client = TestClient(app)
    for _ in range(2):
        assert client.post(
            "/api/v1/admin/auth/login",
            json={"username": "limited", "password": WRONG_PASSWORD},
            headers={"origin": "http://testserver"},
        ).status_code == 401
    assert client.post(
        "/api/v1/admin/auth/login",
        json={"username": "limited", "password": WRONG_PASSWORD},
        headers={"origin": "http://testserver"},
    ).status_code == 423


def test_expired_admin_session_is_rejected():
    create_admin()
    client = TestClient(app)
    login(client)
    with SessionLocal() as session:
        record = session.scalar(select(AdminSession))
        assert record is not None
        record.expires_at = utc_now() - timedelta(seconds=1)
        session.commit()
    assert client.get("/api/v1/admin/auth/session").status_code == 401
    assert client.get("/api/v1/admin/capabilities").status_code == 401


def test_production_requires_secure_admin_cookie():
    insecure = Settings(
        environment="production",
        database_url="sqlite:///./production-check.db",
        owner_cookie_secret="x" * 40,
        owner_cookie_secure=True,
        admin_cookie_secure=False,
        allowed_origins="https://example.com",
    )
    with pytest.raises(RuntimeError, match="ASSISTANT_ADMIN_COOKIE_SECURE"):
        insecure.validate_runtime()

    secure = Settings(
        environment="production",
        database_url="sqlite:///./production-check.db",
        owner_cookie_secret="x" * 40,
        owner_cookie_secure=True,
        admin_cookie_secure=True,
            user_cookie_secure=True,
            demo_catalog_enabled=False,
            llm_provider="openai",
            llm_base_url="https://llm.example.com/v1",
            llm_model="approved-test-model",
            llm_api_key="test-key",
        allowed_origins="https://example.com",
    )
    secure.validate_runtime()


def test_production_rejects_fake_llm_and_http_origins():
    base = dict(
        environment="production",
        database_url="sqlite:///./production-check.db",
        owner_cookie_secret="x" * 40,
        owner_cookie_secure=True,
        admin_cookie_secure=True,
        user_cookie_secure=True,
        demo_catalog_enabled=False,
        llm_provider="openai",
        llm_base_url="https://llm.example.com/v1",
        llm_model="approved-test-model",
        llm_api_key="test-key",
        allowed_origins="https://example.com",
    )
    fake = Settings(**{**base, "llm_provider": "fake"})
    with pytest.raises(RuntimeError, match="ASSISTANT_LLM_PROVIDER"):
        fake.validate_runtime()

    http_origin = Settings(**{**base, "allowed_origins": "http://example.com"})
    with pytest.raises(RuntimeError, match="HTTPS origins only"):
        http_origin.validate_runtime()

    missing_key = Settings(**{**base, "llm_api_key": None})
    with pytest.raises(RuntimeError, match="ASSISTANT_LLM_API_KEY"):
        missing_key.validate_runtime()


def test_capability_draft_publish_disable_and_immutable_versions():
    create_admin()
    client = TestClient(app)
    csrf = login(client)
    detail = create_capability(client, csrf)
    capability_id = detail["id"]
    assert detail["status"] == "draft"
    assert detail["draft"]["version"] == 1
    assert all(
        item["id"] != capability_id
        for item in client.get("/api/v1/capabilities").json()["items"]
    )

    published = client.post(
        f"/api/v1/admin/capabilities/{capability_id}/publish",
        json={"versionId": detail["draft"]["id"], "changelog": "发布 V1"},
        headers=mutation_headers(csrf),
    )
    assert published.status_code == 200, published.text
    assert published.json()["status"] == "published"
    assert published.json()["published"]["snapshot"]["name"] == "财务对账"
    public = client.get("/api/v1/capabilities").json()["items"]
    assert any(item["id"] == capability_id for item in public)

    edited = client.patch(
        f"/api/v1/admin/capabilities/{capability_id}",
        json={
            "name": "财务对账 V2",
            "steps": ["读取流水", "比对总账", "输出差异", "生成复核单"],
        },
        headers=mutation_headers(csrf),
    )
    assert edited.status_code == 200, edited.text
    edited_detail = edited.json()
    assert edited_detail["status"] == "published"
    assert edited_detail["published"]["version"] == 1
    assert edited_detail["published"]["snapshot"]["name"] == "财务对账"
    assert edited_detail["draft"]["version"] == 2
    assert edited_detail["draft"]["snapshot"]["name"] == "财务对账 V2"
    assert client.get("/api/v1/capabilities").json()["items"]
    assert next(
        item for item in client.get("/api/v1/capabilities").json()["items"]
        if item["id"] == capability_id
    )["name"] == "财务对账"

    published_v2 = client.post(
        f"/api/v1/admin/capabilities/{capability_id}/publish",
        json={"versionId": edited_detail["draft"]["id"], "changelog": "发布 V2"},
        headers=mutation_headers(csrf),
    )
    assert published_v2.status_code == 200, published_v2.text
    assert published_v2.json()["publishedVersion"] == 2
    assert next(
        item for item in client.get("/api/v1/capabilities").json()["items"]
        if item["id"] == capability_id
    )["name"] == "财务对账 V2"

    duplicate_publish = client.post(
        f"/api/v1/admin/capabilities/{capability_id}/publish",
        json={"versionId": edited_detail["draft"]["id"]},
        headers=mutation_headers(csrf),
    )
    assert duplicate_publish.status_code == 409

    disabled = client.post(
        f"/api/v1/admin/capabilities/{capability_id}/disable",
        json={},
        headers=mutation_headers(csrf),
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["status"] == "disabled"
    assert all(
        item["id"] != capability_id for item in client.get("/api/v1/capabilities").json()["items"]
    )
    assert client.get(f"/api/v1/capabilities/{capability_id}").status_code == 404

    releases = client.get("/api/v1/admin/releases").json()["items"]
    assert any(
        item["capabilityId"] == capability_id and item["status"] == "retired"
        for item in releases
    )
    audits = client.get("/api/v1/admin/audit-events").json()["items"]
    assert any(item["action"] == "capability.published" for item in audits)
    assert any(item["action"] == "capability.disabled" for item in audits)


def test_publication_rolls_back_when_audit_write_fails(monkeypatch):
    create_admin()
    client = TestClient(app, raise_server_exceptions=False)
    csrf = login(client)
    detail = create_capability(client, csrf, name="事务回滚能力")

    def fail_audit(*_args, **_kwargs):
        raise RuntimeError("audit storage unavailable")

    monkeypatch.setattr(capabilities_router, "record_audit", fail_audit)
    response = client.post(
        f"/api/v1/admin/capabilities/{detail['id']}/publish",
        json={"versionId": detail["draft"]["id"]},
        headers=mutation_headers(csrf),
    )
    assert response.status_code == 500

    rolled_back = client.get(f"/api/v1/admin/capabilities/{detail['id']}").json()
    assert rolled_back["status"] == "draft"
    assert rolled_back["published"] is None
    assert rolled_back["draft"]["id"] == detail["draft"]["id"]
    assert all(
        item["id"] != detail["id"]
        for item in client.get("/api/v1/capabilities").json()["items"]
    )
    audit_events = client.get("/api/v1/admin/audit-events").json()["items"]
    assert all(
        not (
            event["action"] == "capability.published"
            and event["resourceId"] == detail["id"]
        )
        for event in audit_events
    )


def test_conversation_rejects_unknown_or_disabled_capability_and_records_runs():
    create_admin()
    client = TestClient(app)
    conversation = client.post("/api/v1/conversations", json={"title": "能力准入"}).json()

    def turn(capability: dict, turn_id: str):
        return client.post(
            f"/api/v1/conversations/{conversation['id']}/turns",
            json={
                "clientTurnId": turn_id,
                "text": "执行任务",
                "capability": capability,
                "attachments": [],
                "request": {
                    "conversationId": conversation["id"],
                    "text": "执行任务",
                    "capability": capability,
                    "fileIds": [],
                    "simulateFailure": False,
                },
            },
        )

    assert turn({"id": "not-a-capability", "kind": "tool", "name": "伪造"}, "t1").status_code == 422
    accepted = turn({"id": "tool-1", "kind": "tool", "name": "伪造名称"}, "t2")
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["userMessage"]["capability"]["name"] == "网页搜索"

    csrf = login(client)
    detail = create_capability(client, csrf)
    client.post(
        f"/api/v1/admin/capabilities/{detail['id']}/publish",
        json={"versionId": detail["draft"]["id"]},
        headers=mutation_headers(csrf),
    )
    client.post(
        f"/api/v1/admin/capabilities/{detail['id']}/disable",
        json={},
        headers=mutation_headers(csrf),
    )
    assert turn(
        {"id": detail["id"], "kind": "tool", "name": "财务对账"}, "t3"
    ).status_code == 422

    overview = client.get("/api/v1/admin/overview")
    assert overview.status_code == 200
    assert overview.json()["totalRuns"] >= 1
    runs = client.get("/api/v1/admin/runs")
    assert runs.status_code == 200
    assert runs.json()["items"][0]["mode"] == "demo"


def test_admin_settings_exposes_no_secrets():
    create_admin()
    client = TestClient(app)
    login(client)
    response = client.get("/api/v1/admin/settings")
    assert response.status_code == 200
    body = response.text.lower()
    assert "password" not in body
    assert "secret" not in body
    assert TEST_ADMIN_PASSWORD.lower() not in body


def test_public_catalog_hides_admin_configuration_and_drafts():
    create_admin()
    client = TestClient(app)
    csrf = login(client)
    detail = create_capability(
        client,
        csrf,
        kind="agent",
        name="内部提示词智能体",
        icon="agent",
        config={"model": "internal-model", "systemPrompt": "不可公开的内部提示词"},
    )
    assert client.get(f"/api/v1/capabilities/{detail['id']}").status_code == 404
    client.post(
        f"/api/v1/admin/capabilities/{detail['id']}/publish",
        json={"versionId": detail["draft"]["id"]},
        headers=mutation_headers(csrf),
    )
    response = client.get(f"/api/v1/capabilities/{detail['id']}")
    assert response.status_code == 200
    assert "config" not in response.json()
    assert "systemPrompt" not in response.text
    listed = next(
        item
        for item in client.get("/api/v1/capabilities").json()["items"]
        if item["id"] == detail["id"]
    )
    assert "config" not in listed
