from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import RateLimitConfig, get_rate_limiter
from app.db.session import get_db_session
from app.schemas.admin import (
    AdminDocumentCreateRequest,
    AdminDocumentData,
    AdminDocumentUpdateRequest,
    AdminPagedData,
    AdminIngestionJobData,
    AdminIngestionJobUpdateRequest,
    AdminPermissionCreateRequest,
    AdminPermissionData,
    AdminPermissionUpdateRequest,
    AdminRoleCreateRequest,
    AdminRoleData,
    AdminRoleUpdateRequest,
    AdminUserCreateRequest,
    AdminUserData,
    AdminUserUpdateRequest,
    AdminWorkspaceCreateRequest,
    AdminWorkspaceData,
    AdminWorkspaceUpdateRequest,
    AdminCacheClearDetailRequest,
    AdminCacheClearListRequest,
)
from app.schemas.common import ApiResponse
from app.services.document_parser import DocumentParser, DocumentParseError
from app.services.admin import AdminService, get_admin_service
from app.services.auth import User, get_current_user
from app.services.rag_ingestion import RagIngestionService, get_rag_ingestion_service
from app.services.rbac import RBACService, get_rbac_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _apply_rate_limit(operation: str, key: str) -> None:
    settings = get_settings()
    get_rate_limiter().check(
        key,
        RateLimitConfig(
            max_requests=settings.rag_rate_limit_max_requests,
            window_seconds=settings.rag_rate_limit_window_seconds,
        ),
        operation=operation,
    )


def _require_permission(
    service: AdminService,
    session: Session,
    user: User,
    permission_name: str,
    rbac_service: RBACService,
) -> None:
    service.require_permission(session, user, permission_name)


def _handle_key_error(exc: KeyError, entity_name: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{entity_name} {exc.args[0]} not found")


def _permission_for_cache_entity(entity: str) -> str:
    normalized = entity.strip().lower()
    if normalized == "users":
        return "user.manage"
    if normalized in {"roles", "permissions"}:
        return "role.manage"
    if normalized == "workspaces":
        return "workspace.manage"
    if normalized == "documents":
        return "document.delete"
    raise HTTPException(status_code=400, detail=f"Unsupported cache entity: {entity}")


@router.get("/users", response_model=ApiResponse[AdminPagedData[AdminUserData]])
def list_users(
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_order: str = "desc",
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminPagedData[AdminUserData]]:
    _require_permission(service, session, current_user, "user.manage", rbac_service)
    return ApiResponse(data=service.list_users(session, page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order))


@router.get("/users/{user_id}", response_model=ApiResponse[AdminUserData])
def get_user(
    user_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminUserData]:
    _require_permission(service, session, current_user, "user.manage", rbac_service)
    try:
        return ApiResponse(data=service.get_user(session, user_id))
    except KeyError as exc:
        raise _handle_key_error(exc, "User") from exc


@router.post("/users", response_model=ApiResponse[AdminUserData])
def create_user(
    request: AdminUserCreateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminUserData]:
    _require_permission(service, session, current_user, "user.manage", rbac_service)
    try:
        return ApiResponse(data=service.create_user(session, request))
    except KeyError as exc:
        raise _handle_key_error(exc, "Role or workspace") from exc


@router.patch("/users/{user_id}", response_model=ApiResponse[AdminUserData])
def update_user(
    user_id: str,
    request: AdminUserUpdateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminUserData]:
    _require_permission(service, session, current_user, "user.manage", rbac_service)
    try:
        return ApiResponse(data=service.update_user(session, user_id, request))
    except KeyError as exc:
        raise _handle_key_error(exc, "User, role, or workspace") from exc


@router.delete("/users/{user_id}", response_model=ApiResponse[AdminUserData])
def delete_user(
    user_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminUserData]:
    _require_permission(service, session, current_user, "user.manage", rbac_service)
    try:
        return ApiResponse(data=service.delete_user(session, user_id))
    except KeyError as exc:
        raise _handle_key_error(exc, "User") from exc


@router.post("/users/{user_id}/activate", response_model=ApiResponse[AdminUserData])
def activate_user(
    user_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminUserData]:
    _require_permission(service, session, current_user, "user.manage", rbac_service)
    try:
        return ApiResponse(data=service.activate_user(session, user_id))
    except KeyError as exc:
        raise _handle_key_error(exc, "User") from exc


@router.get("/roles", response_model=ApiResponse[AdminPagedData[AdminRoleData]])
def list_roles(
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_order: str = "asc",
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminPagedData[AdminRoleData]]:
    _require_permission(service, session, current_user, "role.manage", rbac_service)
    return ApiResponse(data=service.list_roles(session, page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order))


@router.get("/roles/{role_id}", response_model=ApiResponse[AdminRoleData])
def get_role(
    role_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminRoleData]:
    _require_permission(service, session, current_user, "role.manage", rbac_service)
    try:
        return ApiResponse(data=service.get_role(session, role_id))
    except KeyError as exc:
        raise _handle_key_error(exc, "Role") from exc


@router.post("/roles", response_model=ApiResponse[AdminRoleData])
def create_role(
    request: AdminRoleCreateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminRoleData]:
    _require_permission(service, session, current_user, "role.manage", rbac_service)
    try:
        return ApiResponse(data=service.create_role(session, request))
    except KeyError as exc:
        raise _handle_key_error(exc, "Permission") from exc


@router.patch("/roles/{role_id}", response_model=ApiResponse[AdminRoleData])
def update_role(
    role_id: str,
    request: AdminRoleUpdateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminRoleData]:
    _require_permission(service, session, current_user, "role.manage", rbac_service)
    try:
        return ApiResponse(data=service.update_role(session, role_id, request))
    except KeyError as exc:
        raise _handle_key_error(exc, "Role or permission") from exc


@router.delete("/roles/{role_id}", response_model=ApiResponse[AdminRoleData])
def delete_role(
    role_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminRoleData]:
    _require_permission(service, session, current_user, "role.manage", rbac_service)
    try:
        return ApiResponse(data=service.delete_role(session, role_id))
    except KeyError as exc:
        raise _handle_key_error(exc, "Role") from exc


@router.get("/permissions", response_model=ApiResponse[AdminPagedData[AdminPermissionData]])
def list_permissions(
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_order: str = "asc",
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminPagedData[AdminPermissionData]]:
    _require_permission(service, session, current_user, "role.manage", rbac_service)
    return ApiResponse(data=service.list_permissions(session, page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order))


@router.get("/permissions/{permission_id}", response_model=ApiResponse[AdminPermissionData])
def get_permission(
    permission_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminPermissionData]:
    _require_permission(service, session, current_user, "role.manage", rbac_service)
    try:
        return ApiResponse(data=service.get_permission(session, permission_id))
    except KeyError as exc:
        raise _handle_key_error(exc, "Permission") from exc


@router.post("/permissions", response_model=ApiResponse[AdminPermissionData])
def create_permission(
    request: AdminPermissionCreateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminPermissionData]:
    _require_permission(service, session, current_user, "role.manage", rbac_service)
    return ApiResponse(data=service.create_permission(session, request))


@router.patch("/permissions/{permission_id}", response_model=ApiResponse[AdminPermissionData])
def update_permission(
    permission_id: str,
    request: AdminPermissionUpdateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminPermissionData]:
    _require_permission(service, session, current_user, "role.manage", rbac_service)
    try:
        return ApiResponse(data=service.update_permission(session, permission_id, request))
    except KeyError as exc:
        raise _handle_key_error(exc, "Permission") from exc


@router.delete("/permissions/{permission_id}", response_model=ApiResponse[AdminPermissionData])
def delete_permission(
    permission_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminPermissionData]:
    _require_permission(service, session, current_user, "role.manage", rbac_service)
    try:
        return ApiResponse(data=service.delete_permission(session, permission_id))
    except KeyError as exc:
        raise _handle_key_error(exc, "Permission") from exc


@router.get("/workspaces", response_model=ApiResponse[AdminPagedData[AdminWorkspaceData]])
def list_workspaces(
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_order: str = "asc",
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminPagedData[AdminWorkspaceData]]:
    _require_permission(service, session, current_user, "workspace.manage", rbac_service)
    return ApiResponse(data=service.list_workspaces(session, page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order))


@router.get("/workspaces/{workspace_id}", response_model=ApiResponse[AdminWorkspaceData])
def get_workspace(
    workspace_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminWorkspaceData]:
    _require_permission(service, session, current_user, "workspace.manage", rbac_service)
    try:
        return ApiResponse(data=service.get_workspace(session, workspace_id))
    except KeyError as exc:
        raise _handle_key_error(exc, "Workspace") from exc


@router.post("/workspaces", response_model=ApiResponse[AdminWorkspaceData])
def create_workspace(
    request: AdminWorkspaceCreateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminWorkspaceData]:
    _require_permission(service, session, current_user, "workspace.manage", rbac_service)
    return ApiResponse(data=service.create_workspace(session, request))


@router.patch("/workspaces/{workspace_id}", response_model=ApiResponse[AdminWorkspaceData])
def update_workspace(
    workspace_id: str,
    request: AdminWorkspaceUpdateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminWorkspaceData]:
    _require_permission(service, session, current_user, "workspace.manage", rbac_service)
    try:
        return ApiResponse(data=service.update_workspace(session, workspace_id, request))
    except KeyError as exc:
        raise _handle_key_error(exc, "Workspace") from exc


@router.delete("/workspaces/{workspace_id}", response_model=ApiResponse[AdminWorkspaceData])
def delete_workspace(
    workspace_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminWorkspaceData]:
    _require_permission(service, session, current_user, "workspace.manage", rbac_service)
    try:
        return ApiResponse(data=service.delete_workspace(session, workspace_id))
    except KeyError as exc:
        raise _handle_key_error(exc, "Workspace") from exc


@router.get("/documents", response_model=ApiResponse[AdminPagedData[AdminDocumentData]])
def list_documents(
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_order: str = "desc",
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminPagedData[AdminDocumentData]]:
    _require_permission(service, session, current_user, "document.delete", rbac_service)
    return ApiResponse(data=service.list_documents(session, page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order))


@router.get("/documents/{document_id}", response_model=ApiResponse[AdminDocumentData])
def get_document(
    document_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminDocumentData]:
    _require_permission(service, session, current_user, "document.delete", rbac_service)
    try:
        return ApiResponse(data=service.get_document(session, document_id))
    except KeyError as exc:
        raise _handle_key_error(exc, "Document") from exc


@router.post("/documents", response_model=ApiResponse[AdminDocumentData])
def create_document(
    request: AdminDocumentCreateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminDocumentData]:
    _require_permission(service, session, current_user, "document.delete", rbac_service)
    return ApiResponse(data=service.create_document(session, request))


@router.post("/documents/upload", response_model=ApiResponse[AdminDocumentData])
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    owner_user_id: str | None = Form(default=None),
    workspace_id: str | None = Form(default=None),
    permission_scope: str | None = Form(default=None),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminDocumentData]:
    _require_permission(service, session, current_user, "document.upload", rbac_service)
    raw_name = file.filename or ""
    if not raw_name.strip():
        raise HTTPException(status_code=400, detail="file filename is required")

    parser = DocumentParser()
    try:
        content = await file.read()
        parsed = parser.parse(raw_name, content)
    except DocumentParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ApiResponse(
        data=service.create_document(
            session,
            AdminDocumentCreateRequest(
                title=title,
                original_filename=raw_name,
                text=parsed.normalized_text,
                owner_user_id=owner_user_id,
                workspace_id=workspace_id,
                permission_scope=permission_scope,
            ),
        )
    )


@router.patch("/documents/{document_id}", response_model=ApiResponse[AdminDocumentData])
def update_document(
    document_id: str,
    request: AdminDocumentUpdateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminDocumentData]:
    _require_permission(service, session, current_user, "document.delete", rbac_service)
    try:
        return ApiResponse(data=service.update_document(session, document_id, request))
    except KeyError as exc:
        raise _handle_key_error(exc, "Document") from exc


@router.delete("/documents/{document_id}", response_model=ApiResponse[AdminDocumentData])
def delete_document(
    document_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminDocumentData]:
    _require_permission(service, session, current_user, "document.delete", rbac_service)
    try:
        return ApiResponse(data=service.delete_document(session, document_id))
    except KeyError as exc:
        raise _handle_key_error(exc, "Document") from exc


@router.post("/documents/{document_id}/restore", response_model=ApiResponse[AdminDocumentData])
def restore_document(
    document_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminDocumentData]:
    _require_permission(service, session, current_user, "document.delete", rbac_service)
    try:
        return ApiResponse(data=service.restore_document(session, document_id))
    except KeyError as exc:
        raise _handle_key_error(exc, "Document") from exc


@router.post("/documents/{document_id}/reindex", response_model=ApiResponse[AdminDocumentData])
def reindex_document(
    document_id: str,
    http_request: Request,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rag_service: RagIngestionService = Depends(get_rag_ingestion_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminDocumentData]:
    del http_request
    _require_permission(service, session, current_user, "document.reindex", rbac_service)
    _apply_rate_limit("Document reindex", f"rag:reindex:{current_user.id}")
    try:
        return ApiResponse(data=service.reindex_document(session, document_id, rag_service=rag_service))
    except KeyError as exc:
        raise _handle_key_error(exc, "Document") from exc


@router.get("/ingestion-jobs", response_model=ApiResponse[AdminPagedData[AdminIngestionJobData]])
def list_ingestion_jobs(
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_order: str = "desc",
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminPagedData[AdminIngestionJobData]]:
    _require_permission(service, session, current_user, "document.delete", rbac_service)
    return ApiResponse(data=service.list_jobs(session, page=page, page_size=page_size, sort_by=sort_by, sort_order=sort_order))


@router.get("/ingestion-jobs/{job_id}", response_model=ApiResponse[AdminIngestionJobData])
def get_ingestion_job(
    job_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminIngestionJobData]:
    _require_permission(service, session, current_user, "document.delete", rbac_service)
    try:
        return ApiResponse(data=service.get_job(session, job_id))
    except KeyError as exc:
        raise _handle_key_error(exc, "Ingestion job") from exc


@router.patch("/ingestion-jobs/{job_id}", response_model=ApiResponse[AdminIngestionJobData])
def update_ingestion_job(
    job_id: str,
    request: AdminIngestionJobUpdateRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[AdminIngestionJobData]:
    _require_permission(service, session, current_user, "document.delete", rbac_service)
    try:
        return ApiResponse(data=service.update_job(session, job_id, request))
    except KeyError as exc:
        raise _handle_key_error(exc, "Ingestion job") from exc


@router.post("/cache/clear-list", response_model=ApiResponse[dict[str, str]])
def clear_admin_list_cache(
    request: AdminCacheClearListRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[dict[str, str]]:
    _require_permission(service, session, current_user, _permission_for_cache_entity(request.entity), rbac_service)
    return ApiResponse(
        data=service.clear_entity_list_cache(
            request.entity,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            sort_order=request.sort_order,
        )
    )


@router.post("/cache/clear-detail", response_model=ApiResponse[dict[str, str]])
def clear_admin_detail_cache(
    request: AdminCacheClearDetailRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    service: AdminService = Depends(get_admin_service),
    rbac_service: RBACService = Depends(get_rbac_service),
) -> ApiResponse[dict[str, str]]:
    _require_permission(service, session, current_user, _permission_for_cache_entity(request.entity), rbac_service)
    return ApiResponse(data=service.clear_entity_detail_cache(request.entity, request.entity_id))
