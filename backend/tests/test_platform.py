import asyncio
import json
import secrets
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select

from app.config import settings
from app.core.security import hash_user_password
from app.core.errors import APIError
from app.db import SessionLocal
from app.main import app
from app.modules.identity.models import User
from app.modules.capabilities.models import CapabilityDefinition, CapabilityVersion
from app.modules.identity.user_service import UserIdentityService
from app.modules.runtime.models import AgentRun, RunStep
from app.modules.runtime.providers import LLMChunk, build_provider
from app.modules.runtime.service import RuntimeService
from app.modules.personal.models import McpServer
from app.modules.runtime.mcp_client import McpClient, set_transport_factory
from app.modules.observability.models import AuditEvent
from app.models import Conversation, Message
from app.repositories import utc_now
from app.repositories import OwnerScope
from app.schemas import CapabilityRef, MessageRequest, TurnCreate
from app.services import ConversationService


@contextmanager
def local_openai_server(*, chunks: list[str], status: int = 200, done: bool = True):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *args) -> None:
            return

        def do_POST(self) -> None:
            length = int(self.headers.get("content-length", "0"))
            if length:
                self.rfile.read(length)
            if status >= 400:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"upstream unavailable"}')
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for chunk in chunks:
                payload = json.dumps(
                    {"choices": [{"delta": {"content": chunk}}]},
                    ensure_ascii=False,
                )
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
            if done:
                self.wfile.write(b"data: [DONE]\n\n")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


@contextmanager
def local_mcp_server():
    seen_headers: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *args) -> None:
            return

        def do_POST(self) -> None:
            length = int(self.headers.get("content-length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            seen_headers.append(self.headers.get("authorization", ""))
            method = body.get("method")
            if method == "tools/list":
                result = {
                    "tools": [
                        {
                            "name": "http-search",
                            "description": "HTTP MCP search",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"query": {"type": "string"}},
                            },
                        }
                    ]
                }
            else:
                result = {
                    "content": [{"type": "text", "text": "http-mcp-ok"}],
                    "isError": False,
                }
            payload = json.dumps(
                {"jsonrpc": "2.0", "id": body.get("id"), "result": result}
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1], seen_headers
    finally:
        server.shutdown()
        server.server_close()


def new_client() -> TestClient:
    return TestClient(app)


def make_user(account: str, role: str = "USER", password: str = "userpass") -> str:
    with SessionLocal() as session:
        now = utc_now()
        existing = session.scalar(select(User).where(User.account_number == account))
        if existing is not None:
            existing.role = role
            existing.status = "ACTIVE"
            existing.password_hash = hash_user_password(password)
            existing.authz_version += 1
            session.commit()
            return existing.id
        user = User(
            account_number=account,
            password_hash=hash_user_password(password),
            nickname="",
            role=role,
            status="ACTIVE",
            version=1,
            authz_version=1,
            created_at=now,
            updated_at=now,
            activated_at=now,
        )
        session.add(user)
        session.commit()
        return user.id


def login(client: TestClient, account: str, password: str = "userpass") -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"accountNumber": account, "password": password},
        headers={"origin": "http://testserver"},
    )
    assert response.status_code == 200, response.text


def headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get(settings.user_csrf_cookie_name)
    assert token
    return {"origin": "http://testserver", "x-csrf-token": token}


def create_conversation(client: TestClient) -> str:
    request_headers = {"origin": "http://testserver"}
    if client.cookies.get(settings.user_csrf_cookie_name):
        request_headers = headers(client)
    response = client.post(
        "/api/v1/conversations",
        json={"title": "运行测试"},
        headers=request_headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def creator_tool_flow() -> tuple[str, str]:
    creator_id = make_user("700", role="CREATOR")
    admin_id = make_user("1", role="ADMIN", password="adminpass123")
    creator = new_client()
    login(creator, "700")
    created = creator.post(
        "/api/v1/creator/capabilities",
        json={
            "kind": "tool",
            "name": "服务器时间",
            "description": "只读查询服务器时间",
            "category": "系统",
            "icon": "clock",
            "steps": [],
            "tools": [],
            "content": None,
            "config": {"executor": "system", "tool": "system.current_time"},
            "changelog": "初始版本",
        },
        headers=headers(creator),
    )
    assert created.status_code == 201, created.text
    capability_id = created.json()["id"]
    tested = creator.post(
        f"/api/v1/creator/capabilities/{capability_id}/test",
        json={},
        headers=headers(creator),
    )
    assert tested.status_code == 200, tested.text
    assert tested.json()["testStatus"] == "passed"
    submitted = creator.post(
        f"/api/v1/creator/capabilities/{capability_id}/submit",
        json={"reason": "请审核"},
        headers=headers(creator),
    )
    assert submitted.status_code == 200
    assert submitted.json()["reviewStatus"] == "submitted"
    return capability_id, creator_id


def approve_and_release(capability_id: str) -> None:
    make_user("1", role="ADMIN", password="adminpass123")
    admin = new_client()
    login(admin, "1", "adminpass123")
    approved = admin.post(
        f"/api/v1/admin/capabilities/{capability_id}/approve",
        json={"reason": "通过"},
        headers=headers(admin),
    )
    assert approved.status_code == 200, approved.text
    released = admin.post(
        f"/api/v1/admin/governance/capabilities/{capability_id}/release",
        json={"changelog": "发布"},
        headers=headers(admin),
    )
    assert released.status_code == 200, released.text
    assert released.json()["status"] == "published"


def test_creator_capability_requires_test_review_release_and_grant():
    capability_id, creator_id = creator_tool_flow()
    approve_and_release(capability_id)

    user_id = make_user("800")
    user = new_client()
    login(user, "800")
    catalog = user.get("/api/v1/capabilities").json()["items"]
    hidden = next(item for item in catalog if item["id"] == capability_id)
    assert hidden["authorized"] is False
    assert hidden["blockedReason"] == "no_permission"
    assert hidden["primaryAction"] == "request_access"
    blocked = user.post(
        f"/api/v1/conversations/{create_conversation(user)}/turns",
        json={
            "clientTurnId": "turn-blocked",
            "text": "现在几点",
            "capability": {"id": capability_id, "kind": "tool", "name": "服务器时间"},
            "attachments": [],
            "request": {
                "conversationId": None,
                "clientTurnId": "turn-blocked",
                "text": "现在几点",
                "capability": {"id": capability_id, "kind": "tool", "name": "服务器时间"},
                "fileIds": [],
                "simulateFailure": False,
            },
        },
        headers={"origin": "http://testserver"},
    )
    assert blocked.status_code == 403

    admin = new_client()
    login(admin, "1", "adminpass123")
    granted = admin.post(
        f"/api/v1/admin/capabilities/{capability_id}/grants",
        json={"userId": user_id},
        headers=headers(admin),
    )
    assert granted.status_code == 204
    catalog = user.get("/api/v1/capabilities").json()["items"]
    granted = next(item for item in catalog if item["id"] == capability_id)
    assert granted["authorized"] is True
    assert granted["blockedReason"] == "none"
    assert granted["primaryAction"] == "use"

    revoked = admin.delete(
        f"/api/v1/admin/capabilities/{capability_id}/grants/{user_id}",
        headers=headers(admin),
    )
    assert revoked.status_code == 204
    catalog = user.get("/api/v1/capabilities").json()["items"]
    revoked_item = next(item for item in catalog if item["id"] == capability_id)
    assert revoked_item["authorized"] is False
    assert revoked_item["blockedReason"] == "no_permission"
    denied = user.post(
        f"/api/v1/conversations/{create_conversation(user)}/turns",
        json={
            "clientTurnId": "turn-revoked",
            "text": "撤权后继续调用",
            "capability": {"id": capability_id, "kind": "tool", "name": "服务器时间"},
            "attachments": [],
            "request": {
                "conversationId": None,
                "clientTurnId": "turn-revoked",
                "text": "撤权后继续调用",
                "capability": {"id": capability_id, "kind": "tool", "name": "服务器时间"},
                "fileIds": [],
                "simulateFailure": False,
            },
        },
        headers=headers(user),
    )
    assert denied.status_code == 403


def test_runtime_executes_readonly_tool_and_persists_run_and_steps():
    capability_id, _ = creator_tool_flow()
    approve_and_release(capability_id)
    user_id = make_user("801")
    admin = new_client()
    login(admin, "1", "adminpass123")
    admin.post(
        f"/api/v1/admin/capabilities/{capability_id}/grants",
        json={"userId": user_id},
        headers=headers(admin),
    )
    user = new_client()
    login(user, "801")
    conversation_id = create_conversation(user)
    result = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": conversation_id,
            "clientTurnId": "live-1",
            "text": "请告诉我服务器时间",
            "capabilityId": capability_id,
            "capabilityKind": "tool",
            "toolArguments": {},
            "mode": "fake",
        },
        headers=headers(user),
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["run"]["status"] == "completed"
    assert body["run"]["mode"] == "fake"
    assert any(step["type"] == "tool" for step in body["run"]["steps"])
    assert "FakeProvider" in body["run"]["outputText"]
    detail = user.get(f"/api/v1/conversations/{conversation_id}").json()
    assert detail["messages"][-1]["status"] == "complete"
    assert "FakeProvider" in detail["messages"][-1]["content"]
    quota = user.get("/api/v1/assistant/runs/quota").json()
    assert quota["limit"] >= 1
    assert quota["used"] >= 1
    assert quota["remaining"] == max(quota["limit"] - quota["used"], 0)

    other = new_client()
    make_user("802")
    login(other, "802")
    assert other.get(f"/api/v1/assistant/runs/{body['run']['id']}").status_code == 404


def test_real_mode_without_configuration_fails_honestly(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_base_url", "")
    monkeypatch.setattr(settings, "llm_model", "")
    monkeypatch.setattr(settings, "llm_api_key", None)
    user_id = make_user("803")
    user = new_client()
    login(user, "803")
    conversation_id = create_conversation(user)
    response = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": conversation_id,
            "clientTurnId": "real-1",
            "text": "真实模型测试",
            "mode": "openai",
        },
        headers=headers(user),
    )
    assert response.status_code == 200
    assert response.json()["run"]["status"] in {"failed", "timed_out"}
    assert response.json()["run"]["errorCode"] == "REAL_PROVIDER_NOT_CONFIGURED"
    runs = user.get("/api/v1/assistant/runs").json()["items"]
    assert runs[0]["status"] != "completed"


def test_private_skills_and_files_are_owner_isolated():
    make_user("804")
    make_user("805")
    owner = new_client()
    login(owner, "804")
    skill = owner.post(
        "/api/v1/me/skills",
        json={"name": "我的研究模板", "description": "私人", "contentMd": "# 私人内容"},
        headers=headers(owner),
    )
    assert skill.status_code == 201, skill.text
    uploaded = owner.post(
        "/api/v1/me/files",
        files={"file": ("notes.txt", b"private content", "text/plain")},
        headers=headers(owner),
    )
    assert uploaded.status_code == 201, uploaded.text
    file_id = uploaded.json()["id"]
    assert owner.get(f"/api/v1/me/files/{file_id}/content").content == b"private content"

    intruder = new_client()
    login(intruder, "805")
    assert intruder.get("/api/v1/me/skills").json()["items"] == []
    assert intruder.get(f"/api/v1/me/files/{file_id}/content").status_code == 404
    assert intruder.post(
        "/api/v1/me/files",
        files={"file": ("../evil.txt", b"x", "text/plain")},
        headers=headers(intruder),
    ).status_code in {201, 422}


def test_personal_skill_runs_only_for_its_owner():
    owner_id = make_user("808")
    make_user("809")
    owner = new_client()
    login(owner, "808")
    skill = owner.post(
        "/api/v1/me/skills",
        json={
            "name": "周报整理",
            "description": "把要点整理成周报",
            "contentMd": "输出固定三段：进展、风险、下一步。",
        },
        headers=headers(owner),
    )
    assert skill.status_code == 201, skill.text
    conversation_id = create_conversation(owner)
    result = owner.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": conversation_id,
            "clientTurnId": "personal-skill-1",
            "text": "整理本周工作",
            "capabilityId": skill.json()["id"],
            "capabilityKind": "skill",
            "mode": "fake",
        },
        headers=headers(owner),
    )
    assert result.status_code == 200, result.text
    assert result.json()["run"]["status"] == "completed"
    assert "周报整理" in result.json()["run"]["outputText"]

    other = new_client()
    login(other, "809")
    other_conversation = create_conversation(other)
    denied = other.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": other_conversation,
            "clientTurnId": "personal-skill-2",
            "text": "读取别人的技能",
            "capabilityId": skill.json()["id"],
            "capabilityKind": "skill",
            "mode": "fake",
        },
        headers=headers(other),
    )
    assert denied.status_code == 404


def test_mcp_connections_only_use_approved_servers_and_hide_tokens():
    make_user("806")
    make_user("807")
    with SessionLocal() as session:
        server = McpServer(
            name="平台批准服务",
            description="",
            endpoint_url="https://mcp.example.com/rpc",
            transport="http",
            status="approved",
            tools_json="[]",
            created_by="admin",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        pending = McpServer(
            name="未批准服务",
            description="",
            endpoint_url="https://pending.example.com/rpc",
            transport="http",
            status="pending",
            tools_json="[]",
            created_by="creator",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add_all([server, pending])
        session.commit()
        approved_id = server.id
        pending_id = pending.id

    first = new_client()
    login(first, "806")
    servers = first.get("/api/v1/mcp/servers").json()["items"]
    assert [item["id"] for item in servers] == [approved_id]
    connection = first.post(
        "/api/v1/me/mcp/connections",
        json={"serverId": approved_id, "token": "secret-token-value"},
        headers=headers(first),
    )
    assert connection.status_code == 201, connection.text
    assert "secret-token-value" not in connection.text
    rejected = first.post(
        "/api/v1/me/mcp/connections",
        json={"serverId": pending_id, "token": "x"},
        headers=headers(first),
    )
    assert rejected.status_code == 403

    second = new_client()
    login(second, "807")
    assert second.get("/api/v1/me/mcp/connections").json()["items"] == []
    assert second.delete(
        f"/api/v1/me/mcp/connections/{connection.json()['id']}",
        headers=headers(second),
    ).status_code == 404


def mcp_handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    method = body.get("method")
    if method == "tools/list":
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": "search",
                            "description": "Search approved knowledge",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"query": {"type": "string"}},
                                "required": ["query"],
                            },
                        }
                    ]
                },
            },
        )
    if method == "tools/call":
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "content": [{"type": "text", "text": "mcp-ok"}],
                    "isError": False,
                },
            },
        )
    return httpx.Response(400, json={"error": "unknown method"})


class SlowProvider:
    name = "slow-fake"

    def __init__(self, *, delay: float = 0.05, chunks: int = 20):
        self.delay = delay
        self.chunks = chunks

    async def stream(self, messages, *, tools=None):
        for _ in range(self.chunks):
            await asyncio.sleep(self.delay)
            yield LLMChunk(text="x")
        yield LLMChunk(done=True)


def test_mcp_client_lists_and_calls_tools_with_bearer_token():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return mcp_handler(request)

    client = McpClient(
        "https://mcp.example.com/rpc",
        token="private-token",
        transport=httpx.MockTransport(handler),
    )
    tools = asyncio.run(client.list_tools())
    assert [tool.name for tool in tools] == ["search"]
    result = asyncio.run(client.call_tool("search", {"query": "policy"}))
    assert result["content"][0]["text"] == "mcp-ok"
    assert all(
        request.headers["Authorization"] == "Bearer private-token" for request in captured
    )


def test_admin_discovers_mcp_tools_into_the_approved_server():
    make_user("1", role="ADMIN", password="adminpass123")
    with SessionLocal() as session:
        server = McpServer(
            name="Discovery Server",
            description="",
            endpoint_url="https://example.com/rpc",
            transport="http",
            status="approved",
            tools_json="[]",
            created_by="admin",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(server)
        session.commit()
        server_id = server.id
    admin = new_client()
    login(admin, "1", "adminpass123")
    set_transport_factory(lambda: httpx.MockTransport(mcp_handler))
    try:
        discovered = admin.post(
            f"/api/v1/admin/mcp/servers/{server_id}/discover",
            json={},
            headers=headers(admin),
        )
    finally:
        set_transport_factory(None)
    assert discovered.status_code == 200, discovered.text
    assert discovered.json()["tools"][0]["name"] == "search"


def test_runtime_executes_approved_mcp_tool_with_personal_connection(monkeypatch):
    make_user("1", role="ADMIN", password="adminpass123")
    with SessionLocal() as session:
        server = McpServer(
            name="Runtime MCP",
            description="",
            endpoint_url="https://example.com/rpc",
            transport="http",
            status="approved",
            tools_json=json.dumps(
                [{"name": "search", "description": "Search", "inputSchema": {}}]
            ),
            created_by="admin",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(server)
        session.commit()
        server_id = server.id

    creator_id = make_user("900", role="CREATOR")
    creator = new_client()
    login(creator, "900")
    created = creator.post(
        "/api/v1/creator/capabilities",
        json={
            "kind": "tool",
            "name": "MCP 知识检索",
            "description": "调用已批准 MCP 只读工具",
            "category": "知识",
            "icon": "search",
            "steps": [],
            "tools": [],
            "content": None,
            "config": {
                "executor": "mcp",
                "mcpServerId": server_id,
                "mcpTool": "search",
            },
            "changelog": "MCP runtime",
        },
        headers=headers(creator),
    )
    assert created.status_code == 201, created.text
    capability_id = created.json()["id"]
    tested = creator.post(
        f"/api/v1/creator/capabilities/{capability_id}/test",
        json={},
        headers=headers(creator),
    )
    assert tested.status_code == 200, tested.text
    assert tested.json()["testStatus"] == "passed"
    creator.post(
        f"/api/v1/creator/capabilities/{capability_id}/submit",
        json={"reason": "MCP 审核"},
        headers=headers(creator),
    )
    admin = new_client()
    login(admin, "1", "adminpass123")
    admin.post(
        f"/api/v1/admin/capabilities/{capability_id}/approve",
        json={"reason": "通过"},
        headers=headers(admin),
    )
    admin.post(
        f"/api/v1/admin/governance/capabilities/{capability_id}/release",
        json={"changelog": "发布 MCP 工具"},
        headers=headers(admin),
    )
    user_id = make_user("901")
    admin.post(
        f"/api/v1/admin/capabilities/{capability_id}/grants",
        json={"userId": user_id},
        headers=headers(admin),
    )
    user = new_client()
    login(user, "901")
    before_connection = next(
        item
        for item in user.get("/api/v1/capabilities").json()["items"]
        if item["id"] == capability_id
    )
    assert before_connection["blockedReason"] == "needs_mcp_connection"
    assert before_connection["primaryAction"] == "connect"
    connected = user.post(
        "/api/v1/me/mcp/connections",
        json={"serverId": server_id, "token": "runtime-token"},
        headers=headers(user),
    )
    assert connected.status_code == 201, connected.text
    after_connection = next(
        item
        for item in user.get("/api/v1/capabilities").json()["items"]
        if item["id"] == capability_id
    )
    assert after_connection["blockedReason"] == "none"
    assert after_connection["primaryAction"] == "use"
    conversation_id = create_conversation(user)
    set_transport_factory(lambda: httpx.MockTransport(mcp_handler))
    try:
        result = user.post(
            "/api/v1/assistant/runs",
            json={
                "conversationId": conversation_id,
                "clientTurnId": "mcp-runtime-1",
                "text": "查询知识库",
                "capabilityId": capability_id,
                "capabilityKind": "tool",
                "toolArguments": {"query": "policy"},
                "mode": "fake",
            },
            headers=headers(user),
        )
    finally:
        set_transport_factory(None)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["run"]["status"] == "completed"
    assert any(step["type"] == "mcp" for step in body["run"]["steps"])
    assert "mcp-ok" in body["run"]["outputText"]

    removed = user.delete(
        f"/api/v1/me/mcp/connections/{connected.json()['id']}",
        headers=headers(user),
    )
    assert removed.status_code == 204
    no_connection = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": create_conversation(user),
            "clientTurnId": "mcp-runtime-2",
            "text": "断开后调用",
            "capabilityId": capability_id,
            "capabilityKind": "tool",
            "toolArguments": {},
            "mode": "fake",
        },
        headers=headers(user),
    )
    assert no_connection.json()["run"]["status"] == "failed"
    assert no_connection.json()["run"]["errorCode"] == "MCP_CONNECTION_REQUIRED"

    user.post(
        "/api/v1/me/mcp/connections",
        json={"serverId": server_id, "token": "runtime-token"},
        headers=headers(user),
    )
    with SessionLocal() as session:
        server = session.get(McpServer, server_id)
        server.endpoint_url = "http://127.0.0.1:1/rpc"
        session.commit()
    monkeypatch.setattr(
        "app.modules.runtime.service.validate_mcp_url", lambda value: value
    )
    network_failure = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": create_conversation(user),
            "clientTurnId": "mcp-runtime-network",
            "text": "MCP 网络不可达",
            "capabilityId": capability_id,
            "capabilityKind": "tool",
            "toolArguments": {},
            "mode": "fake",
        },
        headers=headers(user),
    )
    assert network_failure.json()["run"]["status"] == "failed"
    assert network_failure.json()["run"]["errorCode"] == "MCP_UNAVAILABLE"

    admin.post(
        f"/api/v1/admin/mcp/servers/{server_id}/disable",
        json={"reason": "E2E 停用"},
        headers=headers(admin),
    )
    disabled_server = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": create_conversation(user),
            "clientTurnId": "mcp-runtime-3",
            "text": "Server 停用后调用",
            "capabilityId": capability_id,
            "capabilityKind": "tool",
            "toolArguments": {},
            "mode": "fake",
        },
        headers=headers(user),
    )
    assert disabled_server.json()["run"]["status"] == "failed"
    assert disabled_server.json()["run"]["errorCode"] == "MCP_SERVER_NOT_APPROVED"


def test_runtime_times_out_and_persists_terminal_state(monkeypatch):
    make_user("910")
    client = new_client()
    login(client, "910")
    conversation_id = create_conversation(client)
    monkeypatch.setattr(
        "app.modules.runtime.service.build_provider",
        lambda _mode=None: SlowProvider(delay=0.2, chunks=2),
    )
    monkeypatch.setattr("app.config.settings.llm_timeout_seconds", 0.05)
    response = client.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": conversation_id,
            "clientTurnId": "timeout-1",
            "text": "触发超时",
            "mode": "fake",
        },
        headers=headers(client),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["run"]["status"] == "timed_out"
    assert body["run"]["errorCode"] == "RUN_TIMEOUT"
    detail = client.get(f"/api/v1/conversations/{conversation_id}").json()
    assert detail["messages"][-1]["status"] == "error"


def test_runtime_cancel_is_observed_between_chunks(monkeypatch):
    make_user("911")
    monkeypatch.setattr(
        "app.modules.runtime.service.build_provider",
        lambda _mode=None: SlowProvider(delay=0.03, chunks=40),
    )
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.account_number == "911"))
        issued = UserIdentityService(session).login(
            "911", "userpass", client_ip="test", user_agent="test"
        )
        scope = OwnerScope(owner_id="", user_id=user.id)
        conversation = ConversationService(session).create(scope, "取消测试")
        turn = TurnCreate(
            clientTurnId="cancel-1",
            text="慢速执行",
            capability=None,
            attachments=[],
            request=MessageRequest(
                conversationId=conversation.id,
                clientTurnId="cancel-1",
                text="慢速执行",
            ),
        )
        turn_result = ConversationService(session).create_turn(
            scope, conversation.id, turn
        )
        service = RuntimeService(session)
        run = service.create_run(
            issued.principal,
            conversation_id=conversation.id,
            version_id="",
            capability_id="",
            input_text="慢速执行",
            mode="fake",
        )
        run_id = run.id
        assistant_id = turn_result.assistantMessage.id
        conversation_id = conversation.id

        def consume() -> None:
            async def run_stream() -> None:
                async for _ in service.stream(
                    run,
                    principal=issued.principal,
                    scope=scope,
                    assistant_message_id=assistant_id,
                    payload=turn,
                ):
                    pass

            asyncio.run(run_stream())

        worker = threading.Thread(target=consume)
        worker.start()
        time.sleep(0.12)
        with SessionLocal() as updater:
            row = updater.get(AgentRun, run_id)
            row.cancel_requested = True
            updater.commit()
        worker.join(timeout=10)
        assert not worker.is_alive()

    with SessionLocal() as check:
        final = check.get(AgentRun, run_id)
        message = check.get(Message, assistant_id)
        assert final.status == "cancelled"
        assert message.status == "stopped"
        assert check.get(Conversation, conversation_id) is not None


def test_reject_disable_restore_transitions_and_audit():
    make_user("1", role="ADMIN", password="adminpass123")
    admin = new_client()
    login(admin, "1", "adminpass123")
    pending = new_client().post(
        "/api/v1/auth/register",
        json={
            "password": "pendingpass",
            "passwordConfirm": "pendingpass",
            "nickname": "待拒绝用户",
        },
        headers={"origin": "http://testserver", "idempotency-key": secrets.token_urlsafe(24)},
    )
    assert pending.status_code == 201
    pending_user = pending.json()["user"]
    rejected = admin.post(
        f"/api/v1/admin/users/{pending_user['id']}/reject",
        json={"expectedVersion": pending_user["version"], "reason": "资料不完整"},
        headers=headers(admin),
    )
    assert rejected.status_code == 200
    assert rejected.json()["user"]["status"] == "REJECTED"
    rejected_login = new_client().post(
        "/api/v1/auth/login",
        json={
            "accountNumber": pending_user["accountNumber"],
            "password": "pendingpass",
        },
        headers={"origin": "http://testserver"},
    )
    assert rejected_login.status_code == 401

    active_id = make_user("921")
    current = admin.get(f"/api/v1/admin/users/{active_id}").json()
    disabled = admin.post(
        f"/api/v1/admin/users/{active_id}/disable",
        json={"expectedVersion": current["version"], "reason": "临时停用"},
        headers=headers(admin),
    )
    assert disabled.status_code == 200
    assert disabled.json()["user"]["status"] == "DISABLED"
    disabled_login = new_client().post(
        "/api/v1/auth/login",
        json={"accountNumber": "921", "password": "userpass"},
        headers={"origin": "http://testserver"},
    )
    assert disabled_login.status_code == 403
    assert disabled_login.json()["error"]["code"] == "ACCOUNT_NOT_ACTIVE"

    current = admin.get(f"/api/v1/admin/users/{active_id}").json()
    restored = admin.post(
        f"/api/v1/admin/users/{active_id}/restore",
        json={"expectedVersion": current["version"], "reason": "恢复使用"},
        headers=headers(admin),
    )
    assert restored.status_code == 200
    assert restored.json()["user"]["status"] == "ACTIVE"
    restored_login = new_client().post(
        "/api/v1/auth/login",
        json={"accountNumber": "921", "password": "userpass"},
        headers={"origin": "http://testserver"},
    )
    assert restored_login.status_code == 200

    with SessionLocal() as session:
        actions = {
            item.action
            for item in session.scalars(
                select(AuditEvent).where(
                    AuditEvent.action.in_(
                        ("admin.user.reject", "admin.user.disable", "admin.user.restore")
                    )
                )
            )
        }
    assert actions == {
        "admin.user.reject",
        "admin.user.disable",
        "admin.user.restore",
    }


def test_agent_locks_dependency_versions_across_draft_changes():
    tool_id, creator_id = creator_tool_flow()
    approve_and_release(tool_id)
    with SessionLocal() as session:
        tool_versions = list(
            session.scalars(
                select(CapabilityVersion).where(
                    CapabilityVersion.capability_id == tool_id
                )
            )
        )
        tool_version = next(
            version for version in tool_versions if version.status == "published"
        )
        tool_version_id = tool_version.id

    creator = new_client()
    login(creator, "700")
    agent = creator.post(
        "/api/v1/creator/capabilities",
        json={
            "kind": "agent",
            "name": "依赖锁定 Agent",
            "description": "锁定工具版本",
            "category": "测试",
            "icon": "agent",
            "steps": [],
            "tools": [],
            "content": None,
            "config": {
                "dependencies": [
                    {"id": tool_id, "versionId": tool_version_id, "kind": "tool"}
                ]
            },
            "changelog": "锁定 v1",
        },
        headers=headers(creator),
    )
    assert agent.status_code == 201, agent.text
    agent_id = agent.json()["id"]
    tested = creator.post(
        f"/api/v1/creator/capabilities/{agent_id}/test",
        json={},
        headers=headers(creator),
    )
    assert tested.status_code == 200, tested.text
    assert tested.json()["testStatus"] == "passed"
    creator.post(
        f"/api/v1/creator/capabilities/{agent_id}/submit",
        json={"reason": "依赖锁定审核"},
        headers=headers(creator),
    )

    admin = new_client()
    login(admin, "1", "adminpass123")
    admin.post(
        f"/api/v1/admin/capabilities/{agent_id}/approve",
        json={"reason": "通过"},
        headers=headers(admin),
    )
    admin.post(
        f"/api/v1/admin/governance/capabilities/{agent_id}/release",
        json={"changelog": "发布 Agent v1"},
        headers=headers(admin),
    )
    user_id = make_user("930")
    admin.post(
        f"/api/v1/admin/capabilities/{agent_id}/grants",
        json={"userId": user_id},
        headers=headers(admin),
    )

    user = new_client()
    login(user, "930")
    first = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": create_conversation(user),
            "clientTurnId": "agent-lock-1",
            "text": "运行锁定 Agent",
            "capabilityId": agent_id,
            "capabilityKind": "agent",
            "mode": "fake",
        },
        headers=headers(user),
    )
    assert first.status_code == 200, first.text
    agent_step = next(
        step for step in first.json()["run"]["steps"] if step["type"] == "agent"
    )
    assert agent_step["output"]["dependencies"][0]["versionId"] == tool_version_id

    creator.patch(
        f"/api/v1/creator/capabilities/{tool_id}",
        json={
            "name": "服务器时间（草稿 v2）",
            "config": {"executor": "system", "tool": "system.current_time"},
        },
        headers=headers(creator),
    )
    second = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": create_conversation(user),
            "clientTurnId": "agent-lock-2",
            "text": "草稿变更后再次运行",
            "capabilityId": agent_id,
            "capabilityKind": "agent",
            "mode": "fake",
        },
        headers=headers(user),
    )
    assert second.status_code == 200, second.text
    second_step = next(
        step for step in second.json()["run"]["steps"] if step["type"] == "agent"
    )
    assert second_step["output"]["dependencies"][0]["versionId"] == tool_version_id


def test_revocation_after_turn_creation_blocks_execution():
    capability_id, creator_id = creator_tool_flow()
    approve_and_release(capability_id)
    user_id = make_user("940")
    admin = new_client()
    login(admin, "1", "adminpass123")
    admin.post(
        f"/api/v1/admin/capabilities/{capability_id}/grants",
        json={"userId": user_id},
        headers=headers(admin),
    )

    with SessionLocal() as session:
        user = session.get(User, user_id)
        issued = UserIdentityService(session).login(
            "940", "userpass", client_ip="test", user_agent="test"
        )
        scope = OwnerScope(owner_id="", user_id=user_id)
        conversation = ConversationService(session).create(scope, "撤权执行")
        turn = TurnCreate(
            clientTurnId="revoke-1",
            text="撤权后执行",
            capability=CapabilityRef(
                id=capability_id, kind="tool", name="服务器时间"
            ),
            attachments=[],
            request=MessageRequest(
                conversationId=conversation.id,
                clientTurnId="revoke-1",
                text="撤权后执行",
                capability=CapabilityRef(
                    id=capability_id, kind="tool", name="服务器时间"
                ),
            ),
        )
        turn_result = ConversationService(session).create_turn(
            scope, conversation.id, turn
        )
        service = RuntimeService(session)
        run = service.create_run(
            issued.principal,
            conversation_id=conversation.id,
            version_id="",
            capability_id=capability_id,
            input_text="撤权后执行",
            mode="fake",
        )
        run_id = run.id

        revoked = admin.delete(
            f"/api/v1/admin/capabilities/{capability_id}/grants/{user_id}",
            headers=headers(admin),
        )
        assert revoked.status_code == 204

        async def consume() -> list[dict]:
            events = []
            async for event in service.stream(
                run,
                principal=issued.principal,
                scope=scope,
                assistant_message_id=turn_result.assistantMessage.id,
                payload=turn,
            ):
                events.append(event)
            return events

        events = asyncio.run(consume())

    with SessionLocal() as check:
        final = check.get(AgentRun, run_id)
        assert final.status == "failed"
        assert final.error_code == "CAPABILITY_REVOKED"
        assert any(event.get("code") == "CAPABILITY_REVOKED" for event in events)


def test_agent_v2_uses_new_dependency_but_old_run_keeps_v1():
    tool_id, creator_id = creator_tool_flow()
    approve_and_release(tool_id)
    creator = new_client()
    login(creator, "700")
    admin = new_client()
    login(admin, "1", "adminpass123")

    def published_version(capability_id: str) -> CapabilityVersion:
        with SessionLocal() as session:
            return next(
                version
                for version in session.scalars(
                    select(CapabilityVersion).where(
                        CapabilityVersion.capability_id == capability_id
                    )
                )
                if version.status == "published"
            )

    tool_v1 = published_version(tool_id)
    agent = creator.post(
        "/api/v1/creator/capabilities",
        json={
            "kind": "agent",
            "name": "版本切换 Agent",
            "description": "验证 v1/v2 依赖切换",
            "category": "测试",
            "icon": "agent",
            "steps": [],
            "tools": [],
            "content": None,
            "config": {
                "dependencies": [
                    {"id": tool_id, "versionId": tool_v1.id, "kind": "tool"}
                ]
            },
            "changelog": "Agent v1",
        },
        headers=headers(creator),
    )
    assert agent.status_code == 201, agent.text
    agent_id = agent.json()["id"]
    creator.post(
        f"/api/v1/creator/capabilities/{agent_id}/test",
        json={},
        headers=headers(creator),
    )
    creator.post(
        f"/api/v1/creator/capabilities/{agent_id}/submit",
        json={"reason": "Agent v1"},
        headers=headers(creator),
    )
    admin.post(
        f"/api/v1/admin/capabilities/{agent_id}/approve",
        json={"reason": "通过"},
        headers=headers(admin),
    )
    admin.post(
        f"/api/v1/admin/governance/capabilities/{agent_id}/release",
        json={"changelog": "Agent v1"},
        headers=headers(admin),
    )
    user_id = make_user("950")
    admin.post(
        f"/api/v1/admin/capabilities/{agent_id}/grants",
        json={"userId": user_id},
        headers=headers(admin),
    )
    user = new_client()
    login(user, "950")
    first = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": create_conversation(user),
            "clientTurnId": "agent-v1-run",
            "text": "运行 Agent v1",
            "capabilityId": agent_id,
            "capabilityKind": "agent",
            "mode": "fake",
        },
        headers=headers(user),
    )
    assert first.status_code == 200, first.text
    old_run_id = first.json()["run"]["id"]
    first_dependency = next(
        step for step in first.json()["run"]["steps"] if step["type"] == "agent"
    )["output"]["dependencies"][0]
    assert first_dependency["versionId"] == tool_v1.id

    patched = creator.patch(
        f"/api/v1/creator/capabilities/{tool_id}",
        json={
            "name": "服务器时间 v2",
            "config": {"executor": "system", "tool": "system.current_time"},
        },
        headers=headers(creator),
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["draftVersion"] == 2
    tested_v2 = creator.post(
        f"/api/v1/creator/capabilities/{tool_id}/test",
        json={},
        headers=headers(creator),
    )
    assert tested_v2.status_code == 200, tested_v2.text
    submitted_v2 = creator.post(
        f"/api/v1/creator/capabilities/{tool_id}/submit",
        json={"reason": "Tool v2"},
        headers=headers(creator),
    )
    assert submitted_v2.status_code == 200, submitted_v2.text
    approved_v2 = admin.post(
        f"/api/v1/admin/capabilities/{tool_id}/approve",
        json={"reason": "通过"},
        headers=headers(admin),
    )
    assert approved_v2.status_code == 200, approved_v2.text
    released_v2 = admin.post(
        f"/api/v1/admin/governance/capabilities/{tool_id}/release",
        json={"changelog": "Tool v2"},
        headers=headers(admin),
    )
    assert released_v2.status_code == 200, released_v2.text
    tool_v2 = published_version(tool_id)
    assert tool_v2.version == 2

    creator.patch(
        f"/api/v1/creator/capabilities/{agent_id}",
        json={
            "config": {
                "dependencies": [
                    {"id": tool_id, "versionId": tool_v2.id, "kind": "tool"}
                ]
            }
        },
        headers=headers(creator),
    )
    creator.post(
        f"/api/v1/creator/capabilities/{agent_id}/test",
        json={},
        headers=headers(creator),
    )
    creator.post(
        f"/api/v1/creator/capabilities/{agent_id}/submit",
        json={"reason": "Agent v2"},
        headers=headers(creator),
    )
    admin.post(
        f"/api/v1/admin/capabilities/{agent_id}/approve",
        json={"reason": "通过"},
        headers=headers(admin),
    )
    admin.post(
        f"/api/v1/admin/governance/capabilities/{agent_id}/release",
        json={"changelog": "Agent v2"},
        headers=headers(admin),
    )
    second = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": create_conversation(user),
            "clientTurnId": "agent-v2-run",
            "text": "运行 Agent v2",
            "capabilityId": agent_id,
            "capabilityKind": "agent",
            "mode": "fake",
        },
        headers=headers(user),
    )
    assert second.status_code == 200, second.text
    second_dependency = next(
        step for step in second.json()["run"]["steps"] if step["type"] == "agent"
    )["output"]["dependencies"][0]
    assert second_dependency["versionId"] == tool_v2.id

    with SessionLocal() as session:
        old_step = session.scalar(
            select(RunStep).where(
                RunStep.run_id == old_run_id, RunStep.step_type == "agent"
            )
        )
        assert old_step is not None
        assert json.loads(old_step.output_json)["dependencies"][0][
            "versionId"
        ] == tool_v1.id


def test_openai_compatible_provider_streams_from_local_server(monkeypatch):
    make_user("960")
    user = new_client()
    login(user, "960")
    conversation_id = create_conversation(user)
    with local_openai_server(chunks=["真实", "适配"]) as port:
        monkeypatch.setattr(settings, "llm_provider", "openai")
        monkeypatch.setattr(settings, "llm_base_url", f"http://127.0.0.1:{port}/v1")
        monkeypatch.setattr(settings, "llm_model", "local-test-model")
        monkeypatch.setattr(settings, "llm_api_key", SecretStr("local-test-key"))
        response = user.post(
            "/api/v1/assistant/runs",
            json={
                "conversationId": conversation_id,
                "clientTurnId": "openai-local-1",
                "text": "本地 SSE 模型",
                "mode": "openai",
            },
            headers=headers(user),
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["run"]["status"] == "completed"
    assert body["run"]["outputText"] == "真实适配"
    assert body["run"]["provider"] == "openai"


def test_client_cannot_override_the_server_configured_provider(monkeypatch):
    make_user("966")
    user = new_client()
    login(user, "966")
    conversation_id = create_conversation(user)
    with local_openai_server(chunks=["服务端", "Provider"]) as port:
        monkeypatch.setattr(settings, "llm_provider", "openai")
        monkeypatch.setattr(settings, "llm_base_url", f"http://127.0.0.1:{port}/v1")
        monkeypatch.setattr(settings, "llm_model", "local-test-model")
        monkeypatch.setattr(settings, "llm_api_key", SecretStr("local-test-key"))
        response = user.post(
            "/api/v1/assistant/runs",
            json={
                "conversationId": conversation_id,
                "clientTurnId": "provider-trust-boundary",
                "text": "客户端请求 fake，但服务端应使用真实配置",
                "mode": "fake",
            },
            headers=headers(user),
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["run"]["status"] == "completed"
    assert body["run"]["provider"] == "openai"
    assert body["run"]["outputText"] == "服务端Provider"
    assert "FakeProvider" not in body["run"]["outputText"]


def test_initial_and_retry_use_the_same_configured_provider(monkeypatch):
    make_user("967")
    user = new_client()
    login(user, "967")
    conversation_id = create_conversation(user)
    with local_openai_server(chunks=[], status=503) as port:
        monkeypatch.setattr(settings, "llm_provider", "openai")
        monkeypatch.setattr(settings, "llm_base_url", f"http://127.0.0.1:{port}/v1")
        monkeypatch.setattr(settings, "llm_model", "local-test-model")
        monkeypatch.setattr(settings, "llm_api_key", SecretStr("local-test-key"))
        first = user.post(
            "/api/v1/assistant/runs",
            json={
                "conversationId": conversation_id,
                "clientTurnId": "provider-retry-first",
                "text": "初次执行使用服务端 Provider",
                "mode": "fake",
            },
            headers=headers(user),
        )
        assert first.status_code == 200, first.text
        assert first.json()["run"]["errorCode"] == "LLM_UPSTREAM_ERROR"
        assistant_id = user.get(f"/api/v1/conversations/{conversation_id}").json()["messages"][-1]["id"]
        retry = user.post(
            "/api/v1/assistant/runs/retry/stream",
            json={
                "conversationId": conversation_id,
                "messageId": assistant_id,
                "mode": "fake",
            },
            headers=headers(user),
        )
    assert retry.status_code == 200
    assert '"code": "LLM_UPSTREAM_ERROR"' in retry.text
    assert "FakeProvider" not in retry.text


def test_test_environment_can_run_the_server_configured_fake_provider(monkeypatch):
    make_user("968")
    user = new_client()
    login(user, "968")
    conversation_id = create_conversation(user)
    monkeypatch.setattr(settings, "environment", "test")
    monkeypatch.setattr(settings, "llm_provider", "fake")
    response = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": conversation_id,
            "clientTurnId": "test-fake-provider",
            "text": "测试环境 Fake",
            "mode": "openai",
        },
        headers=headers(user),
    )
    assert response.status_code == 200, response.text
    assert response.json()["run"]["status"] == "completed"
    assert response.json()["run"]["provider"] == "fake"


def test_missing_real_model_fails_without_falling_back_to_fake(monkeypatch):
    make_user("969")
    user = new_client()
    login(user, "969")
    conversation_id = create_conversation(user)
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_base_url", "")
    monkeypatch.setattr(settings, "llm_model", "")
    monkeypatch.setattr(settings, "llm_api_key", None)
    response = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": conversation_id,
            "clientTurnId": "missing-real-model",
            "text": "没有配置真实模型",
            "mode": "fake",
        },
        headers=headers(user),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["run"]["status"] == "failed"
    assert body["run"]["errorCode"] == "REAL_PROVIDER_NOT_CONFIGURED"
    assert "FakeProvider" not in body["run"]["outputText"]
    assert "FakeProvider" not in body["assistantMessage"]["content"]


def test_production_runtime_rejects_a_fake_provider(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "llm_provider", "fake")
    with pytest.raises(APIError) as error:
        build_provider()
    assert error.value.code == "REAL_PROVIDER_NOT_CONFIGURED"


def test_openai_compatible_provider_surfaces_upstream_error(monkeypatch):
    make_user("961")
    user = new_client()
    login(user, "961")
    conversation_id = create_conversation(user)
    with local_openai_server(chunks=[], status=503) as port:
        monkeypatch.setattr(settings, "llm_provider", "openai")
        monkeypatch.setattr(settings, "llm_base_url", f"http://127.0.0.1:{port}/v1")
        monkeypatch.setattr(settings, "llm_model", "local-test-model")
        monkeypatch.setattr(settings, "llm_api_key", SecretStr("local-test-key"))
        response = user.post(
            "/api/v1/assistant/runs",
            json={
                "conversationId": conversation_id,
                "clientTurnId": "openai-local-2",
                "text": "上游错误",
                "mode": "openai",
            },
            headers=headers(user),
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["run"]["status"] == "failed"
    assert body["run"]["errorCode"] == "LLM_UPSTREAM_ERROR"


def test_mcp_client_over_real_local_http():
    with local_mcp_server() as (port, seen_headers):
        client = McpClient(
            f"http://127.0.0.1:{port}/rpc",
            token="http-private-token",
            timeout=5,
        )
        tools = asyncio.run(client.list_tools())
        result = asyncio.run(client.call_tool("http-search", {"query": "policy"}))
    assert tools[0].name == "http-search"
    assert result["content"][0]["text"] == "http-mcp-ok"
    assert seen_headers == ["Bearer http-private-token"] * 2


def test_openai_provider_network_error_is_explicit(monkeypatch):
    make_user("962")
    user = new_client()
    login(user, "962")
    conversation_id = create_conversation(user)
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_base_url", "http://127.0.0.1:1/v1")
    monkeypatch.setattr(settings, "llm_model", "unreachable-model")
    monkeypatch.setattr(settings, "llm_api_key", SecretStr("local-test-key"))
    response = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": conversation_id,
            "clientTurnId": "openai-network-error",
            "text": "不可达模型",
            "mode": "openai",
        },
        headers=headers(user),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["run"]["status"] == "failed"
    assert body["run"]["errorCode"] == "LLM_UNAVAILABLE"


def test_openai_provider_truncated_stream_is_not_success(monkeypatch):
    make_user("965")
    user = new_client()
    login(user, "965")
    conversation_id = create_conversation(user)
    with local_openai_server(chunks=["部分输出"], done=False) as port:
        monkeypatch.setattr(settings, "llm_provider", "openai")
        monkeypatch.setattr(settings, "llm_base_url", f"http://127.0.0.1:{port}/v1")
        monkeypatch.setattr(settings, "llm_model", "local-test-model")
        monkeypatch.setattr(settings, "llm_api_key", SecretStr("local-test-key"))
        response = user.post(
            "/api/v1/assistant/runs",
            json={
                "conversationId": conversation_id,
                "clientTurnId": "openai-truncated",
                "text": "中断流",
                "mode": "openai",
            },
            headers=headers(user),
        )
    assert response.status_code == 200
    body = response.json()
    assert body["run"]["status"] == "failed"
    assert body["run"]["errorCode"] == "LLM_STREAM_TRUNCATED"


def test_retry_reuses_assistant_message_without_duplicate_user_turn(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_base_url", "")
    monkeypatch.setattr(settings, "llm_model", "")
    monkeypatch.setattr(settings, "llm_api_key", None)
    make_user("963")
    user = new_client()
    login(user, "963")
    conversation_id = create_conversation(user)
    first = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": conversation_id,
            "clientTurnId": "retry-first",
            "text": "第一次失败",
            "mode": "openai",
        },
        headers=headers(user),
    )
    assert first.status_code == 200
    assert first.json()["run"]["status"] == "failed"
    detail = user.get(f"/api/v1/conversations/{conversation_id}").json()
    assert len(detail["messages"]) == 2
    assistant = detail["messages"][-1]
    assert assistant["role"] == "assistant"
    assert assistant["status"] == "error"

    retried = user.post(
        "/api/v1/assistant/runs/retry/stream",
        json={
            "conversationId": conversation_id,
            "messageId": assistant["id"],
            "mode": "fake",
        },
        headers=headers(user),
    )
    assert retried.status_code == 200
    assert '"code": "REAL_PROVIDER_NOT_CONFIGURED"' in retried.text
    after = user.get(f"/api/v1/conversations/{conversation_id}").json()
    assert len(after["messages"]) == 2
    assert after["messages"][-1]["id"] == assistant["id"]
    assert after["messages"][-1]["status"] == "error"
    assert "FakeProvider" not in after["messages"][-1]["content"]
    duplicate = user.post(
        "/api/v1/assistant/runs/retry/stream",
        json={
            "conversationId": conversation_id,
            "messageId": assistant["id"],
            "mode": "fake",
        },
        headers=headers(user),
    )
    assert duplicate.status_code == 200
    assert '"code": "REAL_PROVIDER_NOT_CONFIGURED"' in duplicate.text


def test_capability_blocked_reasons_follow_priority(monkeypatch):
    capability_id, creator_id = creator_tool_flow()
    approve_and_release(capability_id)
    user_id = make_user("970")
    admin = new_client()
    login(admin, "1", "adminpass123")
    admin.post(
        f"/api/v1/admin/capabilities/{capability_id}/grants",
        json={"userId": user_id},
        headers=headers(admin),
    )
    user = new_client()
    login(user, "970")
    item = next(
        item
        for item in user.get("/api/v1/capabilities").json()["items"]
        if item["id"] == capability_id
    )
    assert item["blockedReason"] == "none"
    assert item["primaryAction"] == "use"

    with SessionLocal() as session:
        definition = session.get(CapabilityDefinition, capability_id)
        definition.test_status = "failed"
        session.commit()
    item = next(
        item
        for item in user.get("/api/v1/capabilities").json()["items"]
        if item["id"] == capability_id
    )
    assert item["blockedReason"] == "not_ready"
    assert item["primaryAction"] == "unavailable"

    with SessionLocal() as session:
        definition = session.get(CapabilityDefinition, capability_id)
        definition.test_status = "passed"
        session.commit()
    monkeypatch.setattr(settings, "llm_daily_request_limit", 0)
    item = next(
        item
        for item in user.get("/api/v1/capabilities").json()["items"]
        if item["id"] == capability_id
    )
    assert item["blockedReason"] == "budget_exhausted"
    assert item["primaryAction"] == "budget"


def test_concurrent_retry_only_starts_one_run(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_base_url", "")
    monkeypatch.setattr(settings, "llm_model", "")
    monkeypatch.setattr(settings, "llm_api_key", None)
    make_user("964")
    setup = new_client()
    login(setup, "964")
    conversation_id = create_conversation(setup)
    failed = setup.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": conversation_id,
            "clientTurnId": "retry-race-first",
            "text": "并发重试",
            "mode": "openai",
        },
        headers=headers(setup),
    )
    assert failed.status_code == 200
    monkeypatch.setattr(
        "app.modules.runtime.service.build_provider",
        lambda _mode=None: SlowProvider(delay=0.03, chunks=40),
    )
    detail = setup.get(f"/api/v1/conversations/{conversation_id}").json()
    message_id = detail["messages"][-1]["id"]
    results: list[int] = []
    lock = threading.Lock()

    def retry_once() -> None:
        client = new_client()
        login(client, "964")
        response = client.post(
            "/api/v1/assistant/runs/retry/stream",
            json={
                "conversationId": conversation_id,
                "messageId": message_id,
                "mode": "fake",
            },
            headers=headers(client),
        )
        with lock:
            results.append(response.status_code)

    workers = [threading.Thread(target=retry_once) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    assert sorted(results) == [200, 409]
    final = setup.get(f"/api/v1/conversations/{conversation_id}").json()
    assert final["messages"][-1]["status"] == "complete"
    assert len(final["messages"]) == 2


def test_cancel_completed_run_is_idempotent_noop():
    make_user("980")
    user = new_client()
    login(user, "980")
    conversation_id = create_conversation(user)
    completed = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": conversation_id,
            "clientTurnId": "cancel-noop",
            "text": "完成后取消",
            "mode": "fake",
        },
        headers=headers(user),
    )
    assert completed.status_code == 200
    run_id = completed.json()["run"]["id"]
    assert completed.json()["run"]["status"] == "completed"
    cancelled = user.post(
        f"/api/v1/assistant/runs/{run_id}/cancel",
        json={},
        headers=headers(user),
    )
    assert cancelled.status_code == 200
    with SessionLocal() as session:
        row = session.get(AgentRun, run_id)
        assert row.status == "completed"
        assert row.cancel_requested is False


def test_inflight_run_finishes_but_revoked_user_cannot_start_another(monkeypatch):
    capability_id, creator_id = creator_tool_flow()
    approve_and_release(capability_id)
    user_id = make_user("990")
    admin = new_client()
    login(admin, "1", "adminpass123")
    admin.post(
        f"/api/v1/admin/capabilities/{capability_id}/grants",
        json={"userId": user_id},
        headers=headers(admin),
    )

    started = threading.Event()

    class SignalingProvider:
        name = "signaling"

        async def stream(self, messages, *, tools=None):
            started.set()
            for _ in range(5):
                await asyncio.sleep(0.05)
                yield LLMChunk(text="x")
            yield LLMChunk(done=True)

    monkeypatch.setattr(
        "app.modules.runtime.service.build_provider",
        lambda _mode=None: SignalingProvider(),
    )
    result: dict = {}

    def run_once() -> None:
        client = new_client()
        login(client, "990")
        conversation_id = create_conversation(client)
        response = client.post(
            "/api/v1/assistant/runs",
            json={
                "conversationId": conversation_id,
                "clientTurnId": "inflight-revoke",
                "text": "执行中撤权",
                "capabilityId": capability_id,
                "capabilityKind": "tool",
                "mode": "fake",
            },
            headers=headers(client),
        )
        result["response"] = response

    worker = threading.Thread(target=run_once)
    worker.start()
    assert started.wait(5)
    revoked = admin.delete(
        f"/api/v1/admin/capabilities/{capability_id}/grants/{user_id}",
        headers=headers(admin),
    )
    assert revoked.status_code == 204
    worker.join(timeout=10)
    assert not worker.is_alive()
    assert result["response"].status_code == 200
    assert result["response"].json()["run"]["status"] == "completed"

    after = new_client()
    login(after, "990")
    denied = after.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": create_conversation(after),
            "clientTurnId": "after-revoke",
            "text": "撤权后新执行",
            "capabilityId": capability_id,
            "capabilityKind": "tool",
            "mode": "fake",
        },
        headers=headers(after),
    )
    assert denied.status_code == 403


def test_failed_run_is_not_auto_retried(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "llm_base_url", "")
    monkeypatch.setattr(settings, "llm_model", "")
    monkeypatch.setattr(settings, "llm_api_key", None)
    make_user("991")
    user = new_client()
    login(user, "991")
    conversation_id = create_conversation(user)
    failed = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": conversation_id,
            "clientTurnId": "no-auto-retry",
            "text": "失败后不得自动重试",
            "mode": "openai",
        },
        headers=headers(user),
    )
    assert failed.status_code == 200
    assert failed.json()["run"]["status"] == "failed"
    time.sleep(0.2)
    runs = user.get("/api/v1/assistant/runs").json()["items"]
    assert len(runs) == 1
    detail = user.get(f"/api/v1/conversations/{conversation_id}").json()
    assert len(detail["messages"]) == 2
    assert detail["messages"][-1]["status"] == "error"


def test_audit_failure_rolls_back_account_and_review_status(monkeypatch):
    make_user("1", role="ADMIN", password="adminpass123")
    admin = new_client()
    login(admin, "1", "adminpass123")
    pending = new_client().post(
        "/api/v1/auth/register",
        json={
            "password": "pendingpass",
            "passwordConfirm": "pendingpass",
            "nickname": "审计回滚",
        },
        headers={"origin": "http://testserver", "idempotency-key": secrets.token_urlsafe(24)},
    )
    pending_user = pending.json()["user"]
    monkeypatch.setattr(
        "app.modules.identity.user_service.record_audit",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("audit failed")),
    )
    with pytest.raises(RuntimeError):
        admin.post(
            f"/api/v1/admin/users/{pending_user['id']}/activate",
            json={"expectedVersion": pending_user["version"], "reason": "激活"},
            headers=headers(admin),
        )
    with SessionLocal() as session:
        row = session.get(User, pending_user["id"])
        assert row.status == "PENDING"
        assert row.version == pending_user["version"]
    monkeypatch.undo()

    capability_id, creator_id = creator_tool_flow()
    creator = new_client()
    login(creator, "700")
    creator.post(
        f"/api/v1/creator/capabilities/{capability_id}/test",
        json={},
        headers=headers(creator),
    )
    creator.post(
        f"/api/v1/creator/capabilities/{capability_id}/submit",
        json={"reason": "审核"},
        headers=headers(creator),
    )
    with SessionLocal() as session:
        assert session.get(CapabilityDefinition, capability_id).review_status == "submitted"
    admin = new_client()
    login(admin, "1", "adminpass123")
    monkeypatch.setattr(
        "app.modules.capabilities.router.record_audit",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("audit failed")),
    )
    with pytest.raises(RuntimeError):
        admin.post(
            f"/api/v1/admin/capabilities/{capability_id}/approve",
            json={"reason": "通过"},
            headers=headers(admin),
        )
    with SessionLocal() as session:
        row = session.get(CapabilityDefinition, capability_id)
        assert row.review_status == "submitted"


def test_creator_run_summary_is_scoped_to_owned_capabilities():
    capability_id, creator_id = creator_tool_flow()
    approve_and_release(capability_id)
    user_id = make_user("995")
    admin = new_client()
    login(admin, "1", "adminpass123")
    admin.post(
        f"/api/v1/admin/capabilities/{capability_id}/grants",
        json={"userId": user_id},
        headers=headers(admin),
    )
    user = new_client()
    login(user, "995")
    run = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": create_conversation(user),
            "clientTurnId": "creator-summary-run",
            "text": "运行创作者能力",
            "capabilityId": capability_id,
            "capabilityKind": "tool",
            "mode": "fake",
        },
        headers=headers(user),
    )
    assert run.status_code == 200
    assert run.json()["run"]["status"] == "completed"

    creator = new_client()
    login(creator, "700")
    summary = creator.get("/api/v1/creator/runs/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["total"] >= 1
    assert body["statuses"]["completed"] >= 1
    assert body["recent"][0]["capabilityId"] == capability_id
    assert "outputText" not in body["recent"][0]

    make_user("701", role="CREATOR")
    other = new_client()
    login(other, "701")
    assert other.get("/api/v1/creator/runs/summary").json()["total"] == 0


def test_rejected_capability_can_be_edited_tested_and_resubmitted():
    capability_id, _ = creator_tool_flow()
    admin = new_client()
    login(admin, "1", "adminpass123")
    rejected = admin.post(
        f"/api/v1/admin/capabilities/{capability_id}/reject",
        json={"reason": "说明需要补充"},
        headers=headers(admin),
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["reviewStatus"] == "rejected"

    creator = new_client()
    login(creator, "700")
    updated = creator.patch(
        f"/api/v1/creator/capabilities/{capability_id}",
        json={"description": "已补充失败路径与只读边界"},
        headers=headers(creator),
    )
    assert updated.status_code == 200, updated.text
    tested = creator.post(
        f"/api/v1/creator/capabilities/{capability_id}/test",
        json={},
        headers=headers(creator),
    )
    assert tested.status_code == 200
    assert tested.json()["testStatus"] == "passed"
    resubmitted = creator.post(
        f"/api/v1/creator/capabilities/{capability_id}/submit",
        json={"reason": "已按驳回意见修改"},
        headers=headers(creator),
    )
    assert resubmitted.status_code == 200, resubmitted.text
    assert resubmitted.json()["reviewStatus"] == "submitted"


def test_disabled_agent_dependency_blocks_new_runs_without_rewriting_history():
    tool_id, _ = creator_tool_flow()
    approve_and_release(tool_id)
    with SessionLocal() as session:
        tool_version = session.scalar(
            select(CapabilityVersion).where(
                CapabilityVersion.capability_id == tool_id,
                CapabilityVersion.status == "published",
            )
        )
        assert tool_version is not None
        tool_version_id = tool_version.id

    creator = new_client()
    login(creator, "700")
    agent = creator.post(
        "/api/v1/creator/capabilities",
        json={
            "kind": "agent",
            "name": "依赖停用测试 Agent",
            "description": "验证依赖停用后的新执行拒绝",
            "category": "测试",
            "icon": "agent",
            "steps": [],
            "tools": [],
            "content": "使用已锁定工具版本。",
            "config": {
                "dependencies": [
                    {"id": tool_id, "versionId": tool_version_id, "kind": "tool"}
                ]
            },
            "changelog": "依赖版本",
        },
        headers=headers(creator),
    )
    assert agent.status_code == 201, agent.text
    agent_id = agent.json()["id"]
    creator.post(
        f"/api/v1/creator/capabilities/{agent_id}/test",
        json={},
        headers=headers(creator),
    )
    creator.post(
        f"/api/v1/creator/capabilities/{agent_id}/submit",
        json={"reason": "审核 Agent"},
        headers=headers(creator),
    )
    admin = new_client()
    login(admin, "1", "adminpass123")
    admin.post(
        f"/api/v1/admin/capabilities/{agent_id}/approve",
        json={"reason": "通过"},
        headers=headers(admin),
    )
    admin.post(
        f"/api/v1/admin/governance/capabilities/{agent_id}/release",
        json={"changelog": "发布 Agent"},
        headers=headers(admin),
    )
    user_id = make_user("997")
    admin.post(
        f"/api/v1/admin/capabilities/{agent_id}/grants",
        json={"userId": user_id},
        headers=headers(admin),
    )
    user = new_client()
    login(user, "997")
    first = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": create_conversation(user),
            "clientTurnId": "dependency-before-disable",
            "text": "依赖可用时执行",
            "capabilityId": agent_id,
            "capabilityKind": "agent",
            "mode": "fake",
        },
        headers=headers(user),
    )
    assert first.status_code == 200, first.text
    assert first.json()["run"]["status"] == "completed"
    first_run_id = first.json()["run"]["id"]

    disabled = admin.post(
        f"/api/v1/admin/governance/capabilities/{tool_id}/retire",
        json={},
        headers=headers(admin),
    )
    assert disabled.status_code == 200, disabled.text
    blocked = user.post(
        "/api/v1/assistant/runs",
        json={
            "conversationId": create_conversation(user),
            "clientTurnId": "dependency-after-disable",
            "text": "依赖停用后执行",
            "capabilityId": agent_id,
            "capabilityKind": "agent",
            "mode": "fake",
        },
        headers=headers(user),
    )
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["run"]["status"] == "failed"
    assert blocked.json()["run"]["errorCode"] == "AGENT_DEPENDENCY_UNAVAILABLE"
    with SessionLocal() as session:
        historical = session.get(AgentRun, first_run_id)
        assert historical is not None
        assert historical.status == "completed"
