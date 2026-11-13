import json
from datetime import timezone

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.identity.dependencies import (
    require_active_user,
    require_creator,
    require_unified_admin,
    require_user_csrf,
)
from app.modules.identity.user_service import UserPrincipal
from app.modules.observability.service import record_audit
from app.modules.personal.schemas import (
    FileListResponse,
    FileView,
    McpConnectionCreate,
    McpConnectionListResponse,
    McpConnectionView,
    McpServerCreate,
    McpServerListResponse,
    McpServerView,
    ReviewRequest,
    SkillCreate,
    SkillListResponse,
    SkillUpdate,
    SkillView,
)
from app.modules.personal.service import MAX_FILE_BYTES, PersonalService
from app.modules.runtime.mcp_client import McpClient, validate_mcp_url
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


def _server(item) -> McpServerView:
    return McpServerView(
        id=item.id,
        name=item.name,
        description=item.description,
        status=item.status,
        transport=item.transport,
        tools=json.loads(item.tools_json or "[]"),
        createdAt=item.created_at.replace(tzinfo=timezone.utc),
        reviewedAt=item.reviewed_at.replace(tzinfo=timezone.utc)
        if item.reviewed_at
        else None,
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
        items=[_server(item) for item in PersonalService(session).list_servers()]
    )


@admin_router.get("/servers", response_model=McpServerListResponse)
def admin_list_mcp_servers(
    _: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    return McpServerListResponse(
        items=[
            _server(item)
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
    return _server(item)


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
    return _server(item)


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
    return _server(item)


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
    return _server(item)


@admin_router.post("/servers/{server_id}/discover", response_model=McpServerView)
async def discover_mcp_tools(
    server_id: str,
    request: Request,
    principal: UserPrincipal = Depends(require_unified_admin),
    session: Session = Depends(get_db),
):
    require_user_csrf(request, principal)
    service = PersonalService(session)
    server = service.get_server(server_id)
    endpoint = validate_mcp_url(server.endpoint_url)
    try:
        tools = await McpClient(endpoint, timeout=20).list_tools()
    except Exception as error:
        from app.core.errors import APIError

        if isinstance(error, APIError):
            raise
        raise APIError(502, "MCP_DISCOVERY_FAILED", "MCP 工具发现失败") from error
    server.tools_json = json.dumps(
        [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
            }
            for tool in tools
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
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
    return _server(server)


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
