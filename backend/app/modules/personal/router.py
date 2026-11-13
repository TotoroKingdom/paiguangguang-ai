import json
from datetime import timezone

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.db import get_db
from app.modules.identity.dependencies import (
    require_active_user,
    require_creator,
    require_unified_admin,
    require_user_csrf,
)
from app.modules.identity.user_service import UserPrincipal
from app.modules.observability.service import record_audit
from app.modules.personal.models import McpConnection, McpServer, McpServerTool
from app.modules.personal.schemas import (
    FileListResponse,
    FileView,
    McpConnectionCreate,
    McpConnectionListResponse,
    McpConnectionView,
    McpServerCreate,
    McpServerListResponse,
    McpServerView,
    McpToolApprovalRequest,
    McpToolDisableRequest,
    ReviewRequest,
    SkillCreate,
    SkillListResponse,
    SkillUpdate,
    SkillView,
)
from app.modules.personal.service import MAX_FILE_BYTES, PersonalService
from app.modules.runtime.mcp_client import (
    MCP_TRANSPORT_STREAMABLE_HTTP,
    McpClient,
    mcp_tool_fingerprint,
    validate_mcp_url,
)
from app.owner import require_json_request
from app.repositories import utc_now

me_router = APIRouter(prefix="/me", tags=["personal"])
mcp_router = APIRouter(prefix="/mcp", tags=["mcp"])
admin_router = APIRouter(prefix="/admin/mcp", tags=["admin-mcp"])
creator_router = APIRouter(prefix="/creator/mcp", tags=["creator-mcp"])


def _skill(item) -> SkillView:
    return SkillView(
        id=item.id,
        name=item.name,
        description=item.description,
        contentMd=item.content_md,
        version=item.version,
        createdAt=item.created_at.replace(tzinfo=timezone.utc),
        updatedAt=item.updated_at.replace(tzinfo=timezone.utc),
    )


def _file(item) -> FileView:
    return FileView(
        id=item.id,
        filename=item.filename,
        contentType=item.content_type,
        sizeBytes=item.size_bytes,
        checksum=item.checksum,
        createdAt=item.created_at.replace(tzinfo=timezone.utc),
    )


def _tool_view(item: McpServerTool) -> dict:
    try:
        input_schema = json.loads(item.input_schema_json or "{}")
    except (TypeError, ValueError):
        input_schema = {}
    try:
        output_schema = json.loads(item.output_schema_json or "null")
    except (TypeError, ValueError):
        output_schema = None
    return {
        "name": item.name,
        "description": item.description,
        "inputSchema": input_schema,
        "outputSchema": output_schema,
        "schemaFingerprint": item.schema_fingerprint,
        "approvalStatus": item.approval_status,
        "riskClass": item.risk_class,
        "approvedBy": item.approved_by or None,
        "approvedAt": item.approved_at.isoformat() if item.approved_at else None,
        "approvalReason": item.approval_reason,
    }


def _server(
    item: McpServer,
    session: Session,
    *,
    include_unapproved: bool = False,
) -> McpServerView:
    statement = select(McpServerTool).where(McpServerTool.server_id == item.id)
    if not include_unapproved:
        statement = statement.where(
            McpServerTool.approval_status == "approved",
            McpServerTool.risk_class == "readonly",
        )
    rows = list(session.scalars(statement.order_by(McpServerTool.name)))
    return McpServerView(
        id=item.id,
        name=item.name,
        description=item.description,
        status=item.status,
        transport=item.transport,
        tools=[_tool_view(row) for row in rows],
        createdAt=item.created_at.replace(tzinfo=timezone.utc),
        reviewedAt=item.reviewed_at.replace(tzinfo=timezone.utc)
        if item.reviewed_at
        else None,
    )


def _sync_discovered_tools(session: Session, server: McpServer, discovered) -> None:
    """Persist the exact discovery snapshot and invalidate changed approvals."""
    now = utc_now()
    existing = {
        row.name: row
        for row in session.scalars(
            select(McpServerTool).where(McpServerTool.server_id == server.id)
        )
    }
    seen: set[str] = set()
    for tool in discovered:
        output_schema = tool.output_schema
        fingerprint = mcp_tool_fingerprint(tool)
        row = existing.get(tool.name)
        if row is None:
            row = McpServerTool(
                server_id=server.id,
                name=tool.name,
                description=tool.description,
                input_schema_json=json.dumps(tool.input_schema, ensure_ascii=False, separators=(",", ":")),
                output_schema_json=json.dumps(output_schema, ensure_ascii=False, separators=(",", ":")),
                schema_fingerprint=fingerprint,
                approval_status="pending",
                risk_class="unknown",
                discovered_at=now,
                updated_at=now,
            )
            session.add(row)
            existing[tool.name] = row
        elif row.schema_fingerprint != fingerprint or row.approval_status == "removed":
            row.description = tool.description
            row.input_schema_json = json.dumps(tool.input_schema, ensure_ascii=False, separators=(",", ":"))
            row.output_schema_json = json.dumps(output_schema, ensure_ascii=False, separators=(",", ":"))
            row.schema_fingerprint = fingerprint
            row.approval_status = "pending"
            row.risk_class = "unknown"
            row.approval_reason = ""
            row.approved_by = ""
            row.approved_at = None
            row.discovered_at = now
        row.updated_at = now
        seen.add(tool.name)

    # A removed tool must never remain executable through an old snapshot.
    for name, row in existing.items():
        if name not in seen:
            row.approval_status = "removed"
            row.risk_class = "unknown"
            row.approval_reason = "工具已从最新发现中移除"
            row.approved_by = ""
            row.approved_at = None
            row.updated_at = now

    server.tool_revision = int(server.tool_revision or 0) + 1
    session.flush()
    rows = [
        row
        for row in existing.values()
        if row.name in seen
        and row.approval_status == "approved"
        and row.risk_class == "readonly"
    ]
    server.tools_json = json.dumps(
        [_tool_view(row) for row in sorted(rows, key=lambda item: item.name)],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _connection(connection, server) -> McpConnectionView:
    return McpConnectionView(
        id=connection.id,
        serverId=server.id,
        serverName=server.name,
        status=connection.status,
        hasCredential=bool(connection.credential_ciphertext or connection.credential_ref),
        createdAt=connection.created_at.replace(tzinfo=timezone.utc),
        lastUsedAt=connection.last_used_at.replace(tzinfo=timezone.utc)
        if connection.last_used_at
        else None,
    )


@me_router.get("/skills", response_model=SkillListResponse)
def list_skills(
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    return SkillListResponse(
        items=[_skill(item) for item in PersonalService(session).list_skills(principal.user.id)]
    )


@me_router.post("/skills", response_model=SkillView, status_code=201)
def create_skill(
    payload: SkillCreate,
    request: Request,
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    item = PersonalService(session).create_skill(
        principal.user.id, payload.name, payload.description, payload.contentMd
    )
    return _skill(item)


@me_router.put("/skills/{skill_id}", response_model=SkillView)
def update_skill(
    skill_id: str,
    payload: SkillUpdate,
    request: Request,
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    item = PersonalService(session).update_skill(
        principal.user.id, skill_id, payload.name, payload.description, payload.contentMd
    )
    return _skill(item)


@me_router.delete("/skills/{skill_id}", status_code=204)
def delete_skill(
    skill_id: str,
    request: Request,
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    require_user_csrf(request, principal)
    PersonalService(session).delete_skill(principal.user.id, skill_id)
    return None


@me_router.get("/files", response_model=FileListResponse)
def list_files(
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    return FileListResponse(
        items=[_file(item) for item in PersonalService(session).list_files(principal.user.id)]
    )


@me_router.post("/files", response_model=FileView, status_code=201)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    require_user_csrf(request, principal)
    data = await file.read(MAX_FILE_BYTES + 1)
    item = PersonalService(session).save_file(
        principal.user.id, file.filename or "", file.content_type or "", data
    )
    return _file(item)


@me_router.get("/files/{file_id}/content")
def download_file(
    file_id: str,
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    item, data = PersonalService(session).read_file(principal.user.id, file_id)
    return Response(
        content=data,
        media_type=item.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{item.filename.encode("ascii", "ignore").decode() or "file"}"'
        },
    )


@me_router.delete("/files/{file_id}", status_code=204)
def delete_file(
    file_id: str,
    request: Request,
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    require_user_csrf(request, principal)
    PersonalService(session).delete_file(principal.user.id, file_id)
    return None


@mcp_router.get("/servers", response_model=McpServerListResponse)
def list_mcp_servers(
    _: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    return McpServerListResponse(
        items=[_server(item, session) for item in PersonalService(session).list_servers()]
    )


@admin_router.get("/servers", response_model=McpServerListResponse)
def admin_list_mcp_servers(
    _: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    return McpServerListResponse(
        items=[
            _server(item, session, include_unapproved=True)
            for item in PersonalService(session).list_servers(approved_only=False)
        ]
    )


@admin_router.post("/servers", response_model=McpServerView, status_code=201)
def admin_create_mcp_server(
    payload: McpServerCreate,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    item = PersonalService(session).create_server(
        name=payload.name,
        description=payload.description,
        endpoint_url=payload.endpointUrl,
        transport=payload.transport,
        created_by=principal.user.id,
        status="approved",
    )
    item.reviewed_by = principal.user.id
    item.reviewed_at = item.created_at
    session.commit()
    return _server(item, session, include_unapproved=True)


@creator_router.post("/servers", response_model=McpServerView, status_code=201)
def creator_submit_mcp_server(
    payload: McpServerCreate,
    request: Request,
    principal: UserPrincipal = Depends(require_creator),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    item = PersonalService(session).create_server(
        name=payload.name,
        description=payload.description,
        endpoint_url=payload.endpointUrl,
        transport=payload.transport,
        created_by=principal.user.id,
        status="pending",
    )
    return _server(item, session)


@admin_router.post("/servers/{server_id}/approve", response_model=McpServerView)
def approve_mcp_server(
    server_id: str,
    payload: ReviewRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    item = PersonalService(session).review_server(
        server_id, "approve", actor_id=principal.user.id
    )
    record_audit(
        session,
        actor_type="user",
        actor_id=principal.user.id,
        action="admin.mcp.approve",
        resource_type="mcp_server",
        resource_id=item.id,
        detail={"reason": payload.reason},
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return _server(item, session, include_unapproved=True)


@admin_router.post("/servers/{server_id}/disable", response_model=McpServerView)
def disable_mcp_server(
    server_id: str,
    payload: ReviewRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    item = PersonalService(session).review_server(
        server_id, "disable", actor_id=principal.user.id
    )
    record_audit(
        session,
        actor_type="user",
        actor_id=principal.user.id,
        action="admin.mcp.disable",
        resource_type="mcp_server",
        resource_id=item.id,
        detail={"reason": payload.reason},
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return _server(item, session, include_unapproved=True)


@admin_router.post("/servers/{server_id}/discover", response_model=McpServerView)
async def discover_mcp_tools(
    server_id: str,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    service = PersonalService(session)
    server = service.get_server(server_id)
    if server.transport != MCP_TRANSPORT_STREAMABLE_HTTP:
        raise APIError(
            422,
            "MCP_TRANSPORT_UNSUPPORTED",
            "MCP 仅支持 Streamable HTTP transport",
        )
    endpoint = validate_mcp_url(server.endpoint_url)
    try:
        tools = await McpClient(endpoint, timeout=20).list_tools()
    except Exception as error:
        if isinstance(error, APIError):
            raise
        raise APIError(502, "MCP_DISCOVERY_FAILED", "MCP 工具发现失败") from error
    _sync_discovered_tools(session, server, tools)
    server.updated_at = utc_now()
    record_audit(
        session,
        actor_type="user",
        actor_id=principal.user.id,
        action="admin.mcp.discover",
        resource_type="mcp_server",
        resource_id=server.id,
        detail={"tools": len(tools)},
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return _server(server, session, include_unapproved=True)


def _refresh_tool_json(session: Session, server: McpServer) -> None:
    rows = list(
        session.scalars(
            select(McpServerTool)
            .where(
                McpServerTool.server_id == server.id,
                McpServerTool.approval_status == "approved",
                McpServerTool.risk_class == "readonly",
            )
            .order_by(McpServerTool.name)
        )
    )
    server.tools_json = json.dumps(
        [_tool_view(row) for row in rows], ensure_ascii=False, separators=(",", ":")
    )


@admin_router.post(
    "/servers/{server_id}/tools/{tool_name}/approve",
    response_model=McpServerView,
)
def approve_mcp_tool(
    server_id: str,
    tool_name: str,
    payload: McpToolApprovalRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    name = tool_name.strip()
    row = session.scalar(
        select(McpServerTool).where(
            McpServerTool.server_id == server_id, McpServerTool.name == name
        )
    )
    if row is None:
        raise APIError(404, "MCP_TOOL_NOT_FOUND", "MCP 工具尚未发现")
    if row.approval_status == "removed":
        raise APIError(
            409,
            "MCP_TOOL_REMOVED",
            "MCP 工具已从最新发现中移除，必须重新发现",
        )
    server = session.get(McpServer, server_id)
    if server is None:
        raise APIError(404, "NOT_FOUND", "MCP Server 不存在")
    now = utc_now()
    row.approval_status = "approved"
    row.risk_class = payload.riskClass
    row.approval_reason = payload.reason.strip()
    row.approved_by = principal.user.id
    row.approved_at = now
    row.updated_at = now
    _refresh_tool_json(session, server)
    record_audit(
        session,
        actor_type="user",
        actor_id=principal.user.id,
        action="admin.mcp.tool.approve",
        resource_type="mcp_server_tool",
        resource_id=row.id,
        detail={
            "serverId": server.id,
            "toolName": row.name,
            "riskClass": row.risk_class,
            "schemaFingerprint": row.schema_fingerprint,
            "reason": row.approval_reason,
        },
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return _server(server, session, include_unapproved=True)


@admin_router.post(
    "/servers/{server_id}/tools/{tool_name}/disable",
    response_model=McpServerView,
)
def disable_mcp_tool(
    server_id: str,
    tool_name: str,
    payload: McpToolDisableRequest,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    name = tool_name.strip()
    row = session.scalar(
        select(McpServerTool).where(
            McpServerTool.server_id == server_id, McpServerTool.name == name
        )
    )
    if row is None:
        raise APIError(404, "MCP_TOOL_NOT_FOUND", "MCP 工具尚未发现")
    server = session.get(McpServer, server_id)
    if server is None:
        raise APIError(404, "NOT_FOUND", "MCP Server 不存在")
    row.approval_status = "disabled"
    row.risk_class = "unknown"
    row.approval_reason = payload.reason.strip()
    row.approved_by = ""
    row.approved_at = None
    row.updated_at = utc_now()
    _refresh_tool_json(session, server)
    record_audit(
        session,
        actor_type="user",
        actor_id=principal.user.id,
        action="admin.mcp.tool.disable",
        resource_type="mcp_server_tool",
        resource_id=row.id,
        detail={
            "serverId": server.id,
            "toolName": row.name,
            "schemaFingerprint": row.schema_fingerprint,
            "reason": row.approval_reason,
        },
        client_ip=request.client.host if request.client else "",
    )
    session.commit()
    return _server(server, session, include_unapproved=True)


@me_router.get("/mcp/connections", response_model=McpConnectionListResponse)
def list_connections(
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    return McpConnectionListResponse(
        items=[
            _connection(connection, server)
            for connection, server in PersonalService(session).list_connections(
                principal.user.id
            )
        ]
    )


@me_router.post("/mcp/connections", response_model=McpConnectionView, status_code=201)
def connect_mcp(
    payload: McpConnectionCreate,
    request: Request,
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    require_json_request(request)
    require_user_csrf(request, principal)
    service = PersonalService(session)
    connection = service.connect_server(
        principal.user.id, payload.serverId, payload.token
    )
    return _connection(connection, service.get_server(connection.server_id))


@me_router.delete("/mcp/connections/{connection_id}", status_code=204)
def delete_mcp_connection(
    connection_id: str,
    request: Request,
    principal: UserPrincipal = Depends(require_active_user),
    session: Session = Depends(get_db),
):
    require_user_csrf(request, principal)
    PersonalService(session).delete_connection(principal.user.id, connection_id)
    return None
