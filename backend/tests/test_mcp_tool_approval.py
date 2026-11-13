import asyncio
import json
import socket
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.errors import APIError
from app.core.security import hash_user_password
from app.db import SessionLocal
from app.main import app
from app.modules.identity.models import User
from app.modules.identity.user_service import UserPrincipal
from app.modules.observability.models import AuditEvent
from app.modules.personal.models import McpServer, McpServerTool
from app.modules.personal.router import _sync_discovered_tools
from app.modules.personal.service import PersonalService
from app.modules.runtime.mcp_client import (
    McpClient,
    McpTool,
    mcp_tool_fingerprint,
    set_transport_factory,
)
from app.modules.runtime.service import RuntimeService
from app.repositories import utc_now


def _admin() -> str:
    with SessionLocal() as session:
        now = utc_now()
        user = User(
            account_number="9101",
            password_hash=hash_user_password("mcp-policy-password"),
            nickname="MCP policy admin",
            role="ADMIN",
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


def _user(account_number: str) -> str:
    with SessionLocal() as session:
        now = utc_now()
        user = User(
            account_number=account_number,
            password_hash=hash_user_password("mcp-user-password"),
            nickname="MCP user",
            role="USER",
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


def _server_with_tool() -> tuple[str, str]:
    with SessionLocal() as session:
        now = utc_now()
        tool_schema = {
            "type": "object",
            "properties": {"query": {"type": "string"}},
        }
        discovered = McpTool(
            name="search",
            description="Search",
            input_schema=tool_schema,
        )
        server = McpServer(
            name="MCP policy server",
            description="",
            endpoint_url="https://mcp.example.test/rpc",
            transport="http",
            status="approved",
            tools_json="[]",
            created_by="admin",
            created_at=now,
            updated_at=now,
        )
        session.add(server)
        session.flush()
        tool = McpServerTool(
            server_id=server.id,
            name=discovered.name,
            description=discovered.description,
            input_schema_json=json.dumps(tool_schema),
            output_schema_json="null",
            schema_fingerprint=mcp_tool_fingerprint(discovered),
            approval_status="pending",
            risk_class="unknown",
            discovered_at=now,
            updated_at=now,
        )
        session.add(tool)
        session.commit()
        return server.id, tool.id


def _login(
    client: TestClient,
    account_number: str = "9101",
    password: str = "mcp-policy-password",
) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"accountNumber": account_number, "password": password},
        headers={"origin": "http://testserver"},
    )
    assert response.status_code == 200, response.text
    csrf = client.cookies.get("paiguangguang_csrf")
    assert csrf
    return {"origin": "http://testserver", "x-csrf-token": csrf}


class _LocalRouteTransport(httpx.AsyncBaseTransport):
    """Route a validated public test hostname to the controlled local server."""

    def __init__(self):
        self._inner = httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        routed_url = request.url.copy_with(host="127.0.0.1")
        routed_request = httpx.Request(
            request.method,
            routed_url,
            headers=request.headers,
            content=request.content,
            extensions=request.extensions,
        )
        return await self._inner.handle_async_request(routed_request)

    async def aclose(self) -> None:
        await self._inner.aclose()


@contextmanager
def _controlled_streamable_server(
    tools: list[dict],
    *,
    initialize_status: int = 200,
    expire_tools_list: bool = False,
    require_token: str = "",
):
    state = {
        "tools": tools,
        "tool_error": False,
        "requests": [],
    }

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args):
            return

        def do_POST(self):  # noqa: N802 - stdlib handler hook
            length = int(self.headers.get("content-length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            headers = {key.lower(): value for key, value in self.headers.items()}
            method = str(body.get("method", ""))
            state["requests"].append((method, headers, body))
            if method == "initialize" and initialize_status != 200:
                self._send_json(
                    {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32000}},
                    status=initialize_status,
                )
                return
            if expire_tools_list and method == "tools/list":
                self._send_json(
                    {"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32001}},
                    status=404,
                )
                return
            if method == "initialize":
                self._send_json(
                    {
                        "jsonrpc": "2.0",
                        "id": body["id"],
                        "result": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {"tools": {}},
                            "serverInfo": {"name": "controlled-local", "version": "1"},
                        },
                    },
                    headers={"Mcp-Session-Id": "controlled-session"},
                )
                return
            if method == "notifications/initialized":
                self.send_response(202)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if method == "tools/list":
                self._send_json(
                    {
                        "jsonrpc": "2.0",
                        "id": body["id"],
                        "result": {"tools": state["tools"]},
                    }
                )
                return
            if method == "tools/call":
                if require_token and headers.get("authorization") != f"Bearer {require_token}":
                    self._send_json(
                        {"jsonrpc": "2.0", "id": body["id"], "error": {"code": -32002}},
                        status=401,
                    )
                    return
                self._send_json(
                    {
                        "jsonrpc": "2.0",
                        "id": body["id"],
                        "result": {
                            "content": [{"type": "text", "text": "controlled-ok"}],
                            "isError": state["tool_error"],
                        },
                    }
                )
                return
            self.send_error(400)

        def _send_json(
            self,
            value: dict,
            *,
            status: int = 200,
            headers: dict[str, str] | None = None,
        ):
            encoded = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_port, state
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def _public_test_dns(monkeypatch):
    original_getaddrinfo = socket.getaddrinfo

    def resolve(host, port, *args, **kwargs):
        if host == "mcp.example.test":
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    ("93.184.216.34", port),
                )
            ]
        return original_getaddrinfo(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", resolve)


def test_tool_approval_requires_admin_reason_csrf_and_creates_audit():
    admin_id = _admin()
    _user("9102")
    server_id, tool_id = _server_with_tool()
    regular = TestClient(app)
    regular_headers = _login(regular, "9102", "mcp-user-password")
    forbidden = regular.post(
        f"/api/v1/admin/mcp/servers/{server_id}/tools/search/approve",
        json={"riskClass": "readonly", "reason": "not an admin"},
        headers=regular_headers,
    )
    assert forbidden.status_code == 403

    client = TestClient(app)
    headers = _login(client)

    missing_csrf = client.post(
        f"/api/v1/admin/mcp/servers/{server_id}/tools/search/approve",
        json={"riskClass": "readonly", "reason": "read-only review"},
        headers={"origin": "http://testserver"},
    )
    assert missing_csrf.status_code == 403

    missing_reason = client.post(
        f"/api/v1/admin/mcp/servers/{server_id}/tools/search/approve",
        json={"riskClass": "readonly"},
        headers=headers,
    )
    assert missing_reason.status_code == 422
    missing_risk = client.post(
        f"/api/v1/admin/mcp/servers/{server_id}/tools/search/approve",
        json={"reason": "read-only review"},
        headers=headers,
    )
    assert missing_risk.status_code == 422

    approved = client.post(
        f"/api/v1/admin/mcp/servers/{server_id}/tools/search/approve",
        json={"riskClass": "readonly", "reason": "read-only review"},
        headers=headers,
    )
    assert approved.status_code == 200, approved.text
    tool_view = approved.json()["tools"][0]
    assert tool_view["approvalStatus"] == "approved"
    assert tool_view["riskClass"] == "readonly"
    assert tool_view["approvalReason"] == "read-only review"

    with SessionLocal() as session:
        tool = session.get(McpServerTool, tool_id)
        assert tool is not None
        assert tool.approved_by == admin_id
        audit = session.scalar(
            select(AuditEvent).where(AuditEvent.action == "admin.mcp.tool.approve")
        )
        assert audit is not None
        assert len(json.loads(audit.detail_json)["schemaFingerprint"]) == 64


def test_write_risk_is_rejected_and_unapproved_tools_remain_default_deny():
    _admin()
    server_id, _ = _server_with_tool()
    client = TestClient(app)
    headers = _login(client)
    write = client.post(
        f"/api/v1/admin/mcp/servers/{server_id}/tools/search/approve",
        json={"riskClass": "write", "reason": "unsafe"},
        headers=headers,
    )
    assert write.status_code == 422
    with SessionLocal() as session:
        tool = session.scalar(
            select(McpServerTool).where(
                McpServerTool.server_id == server_id,
                McpServerTool.name == "search",
            )
        )
        assert tool is not None
        assert tool.approval_status == "pending"
        assert tool.risk_class == "unknown"


def test_discovery_schema_change_invalidates_existing_approval_and_ignores_hints():
    with SessionLocal() as session:
        now = utc_now()
        server = McpServer(
            name="MCP schema policy server",
            description="",
            endpoint_url="https://mcp.example.test/rpc",
            transport="http",
            status="approved",
            tools_json="[]",
            created_by="admin",
            created_at=now,
            updated_at=now,
        )
        session.add(server)
        session.flush()
        first = SimpleNamespace(
            name="search",
            description="Search",
            input_schema={"type": "object", "properties": {"q": {"type": "string"}}},
            output_schema=None,
        )
        _sync_discovered_tools(session, server, [first])
        row = session.scalar(select(McpServerTool).where(McpServerTool.server_id == server.id))
        assert row is not None
        row.approval_status = "approved"
        row.risk_class = "readonly"
        row.approved_by = "admin"
        session.commit()
        first_fingerprint = row.schema_fingerprint

        # The remote readOnlyHint is intentionally not part of the approval
        # input; a schema change still resets the administrative decision.
        changed = SimpleNamespace(
            name="search",
            description="Search",
            input_schema={
                "type": "object",
                "properties": {"q": {"type": "string"}, "limit": {"type": "integer"}},
            },
            output_schema=None,
        )
        _sync_discovered_tools(session, server, [changed])
        session.refresh(row)
        assert row.approval_status == "pending"
        assert row.risk_class == "unknown"
        assert row.approved_by == ""
        assert row.schema_fingerprint != first_fingerprint
        session.refresh(server)
        assert server.tool_revision == 2


def test_removed_tool_cannot_be_approved_and_reappears_pending():
    _admin()
    server_id, tool_id = _server_with_tool()
    tool_schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
    }
    discovered = McpTool(
        name="search",
        description="Search",
        input_schema=tool_schema,
    )
    with SessionLocal() as session:
        server = session.get(McpServer, server_id)
        tool = session.get(McpServerTool, tool_id)
        assert server is not None
        assert tool is not None
        tool.approval_status = "approved"
        tool.risk_class = "readonly"
        tool.approved_by = "admin"
        session.commit()
        _sync_discovered_tools(session, server, [])
        session.commit()
        assert tool.approval_status == "removed"

    client = TestClient(app)
    headers = _login(client)
    rejected = client.post(
        f"/api/v1/admin/mcp/servers/{server_id}/tools/search/approve",
        json={"riskClass": "readonly", "reason": "stale approval"},
        headers=headers,
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "MCP_TOOL_REMOVED"

    with SessionLocal() as session:
        server = session.get(McpServer, server_id)
        tool = session.get(McpServerTool, tool_id)
        assert server is not None
        assert tool is not None
        _sync_discovered_tools(session, server, [discovered])
        session.commit()
        assert tool.approval_status == "pending"
        assert tool.risk_class == "unknown"
        assert tool.approved_by == ""


def test_disable_tool_removes_it_from_public_snapshot():
    admin_id = _admin()
    server_id, _ = _server_with_tool()
    client = TestClient(app)
    headers = _login(client)
    missing_csrf = client.post(
        f"/api/v1/admin/mcp/servers/{server_id}/tools/search/disable",
        json={"reason": "manual deny"},
        headers={"origin": "http://testserver"},
    )
    assert missing_csrf.status_code == 403
    disabled = client.post(
        f"/api/v1/admin/mcp/servers/{server_id}/tools/search/disable",
        json={"reason": "manual deny"},
        headers=headers,
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["tools"][0]["approvalStatus"] == "disabled"
    public = client.get("/api/v1/mcp/servers").json()["items"]
    exposed = next(item for item in public if item["id"] == server_id)
    assert exposed["tools"] == []
    with SessionLocal() as session:
        audit = session.scalar(
            select(AuditEvent).where(AuditEvent.action == "admin.mcp.tool.disable")
        )
        assert audit is not None
        assert audit.actor_id == admin_id


def test_only_streamable_http_transport_can_be_created():
    _admin()
    client = TestClient(app)
    headers = _login(client)
    rejected = client.post(
        "/api/v1/admin/mcp/servers",
        json={
            "name": "Legacy SSE",
            "description": "",
            "endpointUrl": "https://mcp.example.test/sse",
            "transport": "sse",
        },
        headers=headers,
    )
    assert rejected.status_code == 422

    with SessionLocal() as session:
        legacy = McpServer(
            name="Legacy persisted SSE",
            description="",
            endpoint_url="https://mcp.example.test/sse",
            transport="sse",
            status="approved",
            tools_json="[]",
            created_by="admin",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(legacy)
        session.commit()
        legacy_id = legacy.id
    discovery = client.post(
        f"/api/v1/admin/mcp/servers/{legacy_id}/discover",
        json={},
        headers=headers,
    )
    assert discovery.status_code == 422
    public_ids = {
        item["id"] for item in client.get("/api/v1/mcp/servers").json()["items"]
    }
    assert legacy_id not in public_ids


def test_controlled_http_discovery_approval_drift_and_runtime_call(monkeypatch):
    search_schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
        "additionalProperties": False,
    }
    write_schema = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "additionalProperties": False,
    }
    write_output_schema = {
        "type": "object",
        "properties": {"written": {"type": "boolean"}},
        "required": ["written"],
        "additionalProperties": False,
    }
    tools = [
        {
            "name": "search",
            "description": "Read-only search",
            "inputSchema": search_schema,
            "annotations": {"readOnlyHint": True},
        },
        {
            "name": "write",
            "description": "Write operation",
            "inputSchema": write_schema,
            "outputSchema": write_output_schema,
            "annotations": {"readOnlyHint": True},
        },
    ]
    _public_test_dns(monkeypatch)
    with _controlled_streamable_server(tools, require_token="runtime-user-token") as (
        port,
        state,
    ):
        _admin()
        admin = TestClient(app)
        headers = _login(admin)
        created = admin.post(
            "/api/v1/admin/mcp/servers",
            json={
                "name": "Controlled MCP",
                "description": "",
                "endpointUrl": f"http://mcp.example.test:{port}/rpc",
                "transport": "http",
            },
            headers=headers,
        )
        assert created.status_code == 201, created.text
        server_id = created.json()["id"]
        set_transport_factory(lambda: _LocalRouteTransport())
        try:
            discovered = admin.post(
                f"/api/v1/admin/mcp/servers/{server_id}/discover",
                json={},
                headers=headers,
            )
            assert discovered.status_code == 200, discovered.text
            discovered_tools = {
                item["name"]: item for item in discovered.json()["tools"]
            }
            assert discovered_tools["search"]["approvalStatus"] == "pending"
            assert discovered_tools["search"]["riskClass"] == "unknown"
            assert discovered_tools["search"]["inputSchema"] == search_schema
            assert discovered_tools["search"]["outputSchema"] is None
            assert discovered_tools["write"]["approvalStatus"] == "pending"
            assert discovered_tools["write"]["riskClass"] == "unknown"
            assert discovered_tools["write"]["outputSchema"] == write_output_schema
            with SessionLocal() as session:
                persisted_tools = list(
                    session.scalars(
                        select(McpServerTool).where(
                            McpServerTool.server_id == server_id
                        )
                    )
                )
                persisted = {tool.name: tool for tool in persisted_tools}
                assert persisted["search"].approval_status == "pending"
                assert persisted["search"].risk_class == "unknown"
                assert len(persisted["search"].schema_fingerprint) == 64
                assert (
                    json.loads(persisted["write"].output_schema_json)
                    == write_output_schema
                )

            before_approval = next(
                item
                for item in admin.get("/api/v1/mcp/servers").json()["items"]
                if item["id"] == server_id
            )
            assert before_approval["tools"] == []

            approved = admin.post(
                f"/api/v1/admin/mcp/servers/{server_id}/tools/search/approve",
                json={"riskClass": "readonly", "reason": "verified read-only"},
                headers=headers,
            )
            assert approved.status_code == 200, approved.text
            approved_tools = {
                item["name"]: item for item in approved.json()["tools"]
            }
            assert approved_tools["search"]["approvalStatus"] == "approved"
            approved_fingerprint = approved_tools["search"]["schemaFingerprint"]

            write_approval = admin.post(
                f"/api/v1/admin/mcp/servers/{server_id}/tools/write/approve",
                json={"riskClass": "write", "reason": "must stay denied"},
                headers=headers,
            )
            assert write_approval.status_code == 422

            exposed = next(
                item
                for item in admin.get("/api/v1/mcp/servers").json()["items"]
                if item["id"] == server_id
            )
            assert [item["name"] for item in exposed["tools"]] == ["search"]

            user_id = _user("9103")
            with SessionLocal() as session:
                user = session.get(User, user_id)
                assert user is not None
                PersonalService(session).connect_server(
                    user.id,
                    server_id,
                    "runtime-user-token",
                )
                runtime = RuntimeService(session)
                principal = UserPrincipal(
                    user=user,
                    session=SimpleNamespace(scope="FULL"),
                )
                result = asyncio.run(
                    runtime._call_mcp(
                        principal,
                        server_id=server_id,
                        tool_name="search",
                        arguments={"query": "policy"},
                    )
                )
            assert result["content"][0]["text"] == "controlled-ok"
            tool_calls = [
                request for request in state["requests"] if request[0] == "tools/call"
            ]
            assert len(tool_calls) == 1
            assert tool_calls[0][1]["authorization"] == "Bearer runtime-user-token"

            with SessionLocal() as session:
                user = session.get(User, user_id)
                assert user is not None
                runtime = RuntimeService(session)
                principal = UserPrincipal(
                    user=user,
                    session=SimpleNamespace(scope="FULL"),
                )
                with pytest.raises(APIError) as denied_write:
                    asyncio.run(
                        runtime._call_mcp(
                            principal,
                            server_id=server_id,
                            tool_name="write",
                            arguments={"value": "blocked"},
                        )
                    )
            assert denied_write.value.code == "MCP_TOOL_NOT_ALLOWED"

            state["tools"][0]["inputSchema"] = {
                **search_schema,
                "properties": {
                    **search_schema["properties"],
                    "limit": {"type": "integer"},
                },
            }
            with SessionLocal() as session:
                user = session.get(User, user_id)
                assert user is not None
                runtime = RuntimeService(session)
                principal = UserPrincipal(
                    user=user,
                    session=SimpleNamespace(scope="FULL"),
                )
                with pytest.raises(APIError) as drift:
                    asyncio.run(
                        runtime._call_mcp(
                            principal,
                            server_id=server_id,
                            tool_name="search",
                            arguments={"query": "policy"},
                        )
                    )
            assert drift.value.code == "MCP_TOOL_SCHEMA_DRIFT"
            assert len(
                [request for request in state["requests"] if request[0] == "tools/call"]
            ) == 1

            rediscovered = admin.post(
                f"/api/v1/admin/mcp/servers/{server_id}/discover",
                json={},
                headers=headers,
            )
            assert rediscovered.status_code == 200, rediscovered.text
            reset_tool = next(
                item
                for item in rediscovered.json()["tools"]
                if item["name"] == "search"
            )
            assert reset_tool["approvalStatus"] == "pending"
            assert reset_tool["riskClass"] == "unknown"
            assert reset_tool["schemaFingerprint"] != approved_fingerprint
        finally:
            set_transport_factory(None)


def test_controlled_local_http_authentication_failure(monkeypatch):
    _public_test_dns(monkeypatch)
    with _controlled_streamable_server([], initialize_status=401) as (port, _state):
        client = McpClient(
            f"http://mcp.example.test:{port}/rpc",
            transport=_LocalRouteTransport(),
            timeout=3,
        )
        with pytest.raises(APIError) as error:
            asyncio.run(client.initialize())
    assert error.value.code == "MCP_AUTH_FAILED"


def test_controlled_local_http_session_expiry(monkeypatch):
    _public_test_dns(monkeypatch)
    with _controlled_streamable_server([], expire_tools_list=True) as (port, _state):
        client = McpClient(
            f"http://mcp.example.test:{port}/rpc",
            transport=_LocalRouteTransport(),
            timeout=3,
        )
        with pytest.raises(APIError) as error:
            asyncio.run(client.list_tools())
    assert error.value.code == "MCP_SESSION_EXPIRED"


def test_controlled_local_http_tool_is_error(monkeypatch):
    _public_test_dns(monkeypatch)
    tools = [
        {
            "name": "search",
            "description": "Search",
            "inputSchema": {"type": "object"},
        }
    ]
    with _controlled_streamable_server(tools) as (port, state):
        state["tool_error"] = True
        client = McpClient(
            f"http://mcp.example.test:{port}/rpc",
            transport=_LocalRouteTransport(),
            timeout=3,
        )
        asyncio.run(client.list_tools())
        with pytest.raises(APIError) as error:
            asyncio.run(client.call_tool("search", {}))
    assert error.value.code == "MCP_TOOL_FAILED"
