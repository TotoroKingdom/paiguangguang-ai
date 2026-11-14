import asyncio
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.errors import APIError
from app.core.security import hash_user_password
from app.db import SessionLocal
from app.modules.identity.models import User
from app.modules.identity.user_service import UserPrincipal
from app.modules.personal.models import McpConnection, McpServer, McpServerTool
from app.modules.personal.service import PersonalService
from app.modules.runtime import service as runtime_service_module
from app.modules.runtime.mcp_client import McpTool, mcp_tool_fingerprint
from app.modules.runtime.service import RuntimeService
from app.repositories import utc_now


def _user(session, account: str) -> User:
    now = utc_now()
    user = User(
        account_number=account,
        password_hash=hash_user_password("mcp-test-password"),
        nickname=account,
        role="USER",
        status="ACTIVE",
        version=1,
        authz_version=1,
        created_at=now,
        updated_at=now,
        activated_at=now,
    )
    session.add(user)
    session.flush()
    return user


def _principal(user: User) -> UserPrincipal:
    # _call_mcp only needs the authenticated user's id.  Keeping the principal
    # shape here makes the test exercise the same authorization boundary as the
    # request path without issuing real cookies or sessions.
    return UserPrincipal(user=user, session=SimpleNamespace(scope="FULL"))


def _server(session, *, status: str = "approved") -> McpServer:
    now = utc_now()
    tool_schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
        "additionalProperties": False,
    }
    server = McpServer(
        name="Authorization test MCP",
        description="",
        endpoint_url="https://mcp.example.test/rpc",
        transport="http",
        status=status,
        tools_json="[]",
        created_by="admin",
        created_at=now,
        updated_at=now,
    )
    session.add(server)
    session.flush()
    tool = McpTool(
        name="search",
        description="read-only search",
        input_schema=tool_schema,
    )
    session.add(
        McpServerTool(
            server_id=server.id,
            name=tool.name,
            description=tool.description,
            input_schema_json=json.dumps(tool_schema, separators=(",", ":")),
            output_schema_json="null",
            schema_fingerprint=mcp_tool_fingerprint(tool),
            approval_status="approved",
            risk_class="readonly",
            approval_reason="authorization test",
            approved_by="admin",
            approved_at=now,
            discovered_at=now,
            updated_at=now,
        )
    )
    return server


def _connect(session, user: User, server: McpServer, token: str) -> McpConnection:
    return PersonalService(session).connect_server(user.id, server.id, token)


def test_runtime_rechecks_approved_server_and_blocks_unlisted_mcp_tool(monkeypatch):
    """A published capability cannot bypass the current MCP tool allowlist."""

    with SessionLocal() as session:
        user = _user(session, "mcp-authz-1")
        server = _server(session)
        _connect(session, user, server, "user-one-token")
        session.commit()

        monkeypatch.setattr(
            runtime_service_module, "validate_mcp_url", lambda value: value
        )

        class FakeMcpClient:
            def __init__(self, *_args, **_kwargs):
                pass

            async def call_tool(self, *_args, **_kwargs):
                pytest.fail("an unlisted tool must be rejected before network execution")

        monkeypatch.setattr(runtime_service_module, "McpClient", FakeMcpClient)

        with pytest.raises(APIError) as error:
            asyncio.run(
                RuntimeService(session)._call_mcp(
                    _principal(user),
                    server_id=server.id,
                    tool_name="delete",
                    arguments={},
                )
            )

    assert error.value.status_code == 403
    assert error.value.code == "MCP_TOOL_NOT_ALLOWED"


def test_runtime_does_not_trust_legacy_tools_json_without_approval_rows(monkeypatch):
    with SessionLocal() as session:
        user = _user(session, "mcp-authz-legacy")
        server = _server(session)
        _connect(session, user, server, "legacy-token")
        tool = session.scalar(
            select(McpServerTool).where(McpServerTool.server_id == server.id)
        )
        assert tool is not None
        server.tools_json = json.dumps(
            [
                {
                    "name": "search",
                    "description": "legacy snapshot",
                    "inputSchema": {"type": "object"},
                }
            ]
        )
        session.delete(tool)
        session.commit()

        class FakeMcpClient:
            def __init__(self, *_args, **_kwargs):
                pytest.fail("legacy tools_json must never authorize a runtime call")

        monkeypatch.setattr(runtime_service_module, "McpClient", FakeMcpClient)
        with pytest.raises(APIError) as error:
            asyncio.run(
                RuntimeService(session)._call_mcp(
                    _principal(user),
                    server_id=server.id,
                    tool_name="search",
                    arguments={"query": "policy"},
                )
            )

    assert error.value.code == "MCP_TOOL_NOT_ALLOWED"


def test_runtime_rejects_connection_when_server_is_no_longer_approved(monkeypatch):
    with SessionLocal() as session:
        user = _user(session, "mcp-authz-2")
        server = _server(session)
        _connect(session, user, server, "user-two-token")
        server.status = "disabled"
        session.commit()

        monkeypatch.setattr(
            runtime_service_module, "validate_mcp_url", lambda value: value
        )

        class FakeMcpClient:
            def __init__(self, *_args, **_kwargs):
                pytest.fail("a disabled server must be rejected before network execution")

        monkeypatch.setattr(runtime_service_module, "McpClient", FakeMcpClient)

        with pytest.raises(APIError) as error:
            asyncio.run(
                RuntimeService(session)._call_mcp(
                    _principal(user),
                    server_id=server.id,
                    tool_name="search",
                    arguments={"query": "policy"},
                )
            )

    assert error.value.code == "MCP_SERVER_NOT_APPROVED"


def test_runtime_rejects_legacy_sse_transport_before_network(monkeypatch):
    with SessionLocal() as session:
        user = _user(session, "mcp-authz-sse")
        server = _server(session)
        _connect(session, user, server, "user-sse-token")
        server.transport = "sse"
        session.commit()

        class FakeMcpClient:
            def __init__(self, *_args, **_kwargs):
                pytest.fail("legacy SSE transport must be rejected before network execution")

        monkeypatch.setattr(runtime_service_module, "McpClient", FakeMcpClient)
        with pytest.raises(APIError) as error:
            asyncio.run(
                RuntimeService(session)._call_mcp(
                    _principal(user),
                    server_id=server.id,
                    tool_name="search",
                    arguments={"query": "policy"},
                )
            )

    assert error.value.code == "MCP_TRANSPORT_UNSUPPORTED"


def test_runtime_uses_only_calling_users_mcp_token(monkeypatch):
    seen_tokens: list[str | None] = []

    with SessionLocal() as session:
        user_a = _user(session, "mcp-authz-a")
        user_b = _user(session, "mcp-authz-b")
        server = _server(session)
        _connect(session, user_a, server, "token-a")
        _connect(session, user_b, server, "token-b")
        session.commit()

        monkeypatch.setattr(
            runtime_service_module, "validate_mcp_url", lambda value: value
        )

        class FakeMcpClient:
            def __init__(self, *_args, token=None, **_kwargs):
                seen_tokens.append(token)

            async def list_tools(self):
                return [
                    McpTool(
                        name="search",
                        description="read-only search",
                        input_schema={
                            "type": "object",
                            "properties": {"query": {"type": "string"}},
                            "required": ["query"],
                            "additionalProperties": False,
                        },
                    )
                ]

            async def call_tool(self, name, arguments):
                return {"name": name, "arguments": arguments}

        monkeypatch.setattr(runtime_service_module, "McpClient", FakeMcpClient)
        runtime = RuntimeService(session)
        result_a = asyncio.run(
            runtime._call_mcp(
                _principal(user_a),
                server_id=server.id,
                tool_name="search",
                arguments={"query": "a"},
            )
        )
        result_b = asyncio.run(
            runtime._call_mcp(
                _principal(user_b),
                server_id=server.id,
                tool_name="search",
                arguments={"query": "b"},
            )
        )

    assert result_a["arguments"] == {"query": "a"}
    assert result_b["arguments"] == {"query": "b"}
    assert seen_tokens == ["token-a", "token-b"]
