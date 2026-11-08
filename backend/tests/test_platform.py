import asyncio
import json
import secrets
import threading
import time

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.core.security import hash_user_password
from app.db import SessionLocal
from app.main import app
from app.modules.identity.models import User
from app.modules.capabilities.models import CapabilityDefinition, CapabilityVersion
from app.modules.identity.user_service import UserIdentityService
from app.modules.runtime.models import AgentRun
from app.modules.runtime.providers import LLMChunk
from app.modules.runtime.service import RuntimeService
from app.modules.personal.models import McpServer
from app.modules.runtime.mcp_client import McpClient, set_transport_factory
from app.modules.observability.models import AuditEvent
from app.models import Conversation, Message
from app.repositories import utc_now
from app.repositories import OwnerScope
from app.schemas import CapabilityRef, MessageRequest, TurnCreate
from app.services import ConversationService


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
    assert all(item["id"] != capability_id for item in catalog)
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
    assert any(item["id"] == capability_id and item["authorized"] for item in catalog)

    revoked = admin.delete(
        f"/api/v1/admin/capabilities/{capability_id}/grants/{user_id}",
        headers=headers(admin),
    )
    assert revoked.status_code == 204
    catalog = user.get("/api/v1/capabilities").json()["items"]
    assert all(item["id"] != capability_id for item in catalog)
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


def test_real_mode_without_configuration_fails_honestly():
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


def test_runtime_executes_approved_mcp_tool_with_personal_connection():
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
    connected = user.post(
        "/api/v1/me/mcp/connections",
        json={"serverId": server_id, "token": "runtime-token"},
        headers=headers(user),
    )
    assert connected.status_code == 201, connected.text
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
        lambda mode: SlowProvider(delay=0.2, chunks=2),
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
        lambda mode: SlowProvider(delay=0.03, chunks=40),
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
