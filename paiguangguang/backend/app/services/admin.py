from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import RagChunk as RagChunkModel
from app.db.models import (
    Permission,
    RagDocument as RagDocumentModel,
    RagIngestionJob as RagIngestionJobModel,
    Role,
    RolePermission,
    User,
    UserRole,
    Workspace,
    WorkspaceMembership,
)
from app.schemas.admin import (
    AdminCacheClearDetailRequest,
    AdminCacheClearListRequest,
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
)
from app.schemas.rag import RagIngestRequest
from app.services.auth import AuthService, get_auth_service, user_to_data
from app.storage.cache import (
    CacheAdapter,
    build_admin_detail_cache_key,
    build_admin_list_cache_key,
    build_auth_user_context_cache_key,
    build_entity_cache_prefix,
    get_cache_adapter,
)
from app.services.rag_ingestion import (
    RagIngestionService,
    get_rag_ingestion_service,
    make_content_hash,
    make_document_id,
    normalize_text,
    )
from app.services.rbac import RBACService, get_rbac_service

SortOrder = Literal["asc", "desc"]
AdminModelT = TypeVar("AdminModelT", bound=BaseModel)
ADMIN_READ_CACHE_TTL_SECONDS = 600


@dataclass(frozen=True)
class AdminListQuery:
    page: int
    page_size: int
    sort_by: str
    sort_order: SortOrder


def _user_roles(user: User) -> list[str]:
    return sorted({role.name for role in user.roles})


def _user_workspace_ids(user: User) -> list[str]:
    return sorted({membership.workspace_id for membership in user.workspace_memberships})


def _user_effective_permissions(user: User) -> list[str]:
    return sorted({permission.name for role in user.roles for permission in role.permissions})


def _user_to_admin_data(user: User) -> AdminUserData:
    base = user_to_data(user)
    return AdminUserData.model_validate(
        {
            **base.model_dump(),
            "roles": _user_roles(user),
            "workspace_ids": _user_workspace_ids(user),
            "effective_permissions": _user_effective_permissions(user),
        }
    )


def _role_to_admin_data(role: Role) -> AdminRoleData:
    return AdminRoleData(
        id=role.id,
        name=role.name,
        description=role.description,
        permissions=sorted({permission.name for permission in role.permissions}),
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


def _permission_to_admin_data(permission: Permission) -> AdminPermissionData:
    return AdminPermissionData(
        id=permission.id,
        name=permission.name,
        description=permission.description,
        created_at=permission.created_at,
        updated_at=permission.updated_at,
    )


def _workspace_to_admin_data(workspace: Workspace) -> AdminWorkspaceData:
    return AdminWorkspaceData(
        id=workspace.id,
        slug=workspace.slug,
        name=workspace.name,
        is_default=workspace.is_default,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


def _document_to_admin_data(model: RagDocumentModel) -> AdminDocumentData:
    return AdminDocumentData(
        doc_id=model.document_id,
        title=model.title,
        original_filename=model.original_filename,
        text_length=len(model.text),
        content_hash=model.content_hash,
        owner_user_id=model.owner_user_id,
        workspace_id=model.workspace_id,
        permission_scope=model.permission_scope,
        status=model.status,
        parse_status=model.parse_status,
        chunk_status=model.chunk_status,
        embedding_status=model.embedding_status,
        index_status=model.index_status,
        is_deleted=model.is_deleted,
        error_message=model.error_message,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _paginate_admin_query(
    session: Session,
    model: type,
    *,
    page: int,
    page_size: int,
    sort_by: str | None,
    sort_order: str,
    allowed_sort_by: set[str] | frozenset[str],
    default_sort_by: str,
) -> AdminListQuery:
    return normalize_admin_list_query(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        allowed_sort_by=allowed_sort_by,
        default_sort_by=default_sort_by,
    )


def _build_paged_data(
    session: Session,
    model: type,
    *,
    page: int,
    page_size: int,
    sort_by: str | None,
    sort_order: str,
    allowed_sort_by: set[str] | frozenset[str],
    default_sort_by: str,
    item_mapper,
) -> AdminPagedData:
    query = _paginate_admin_query(
        session,
        model,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        allowed_sort_by=allowed_sort_by,
        default_sort_by=default_sort_by,
    )
    sort_column = getattr(model, query.sort_by)
    ordering = sort_column.asc() if query.sort_order == "asc" else sort_column.desc()
    total = session.scalar(select(func.count()).select_from(model)) or 0
    items = session.scalars(
        select(model)
        .order_by(ordering)
        .offset((query.page - 1) * query.page_size)
        .limit(query.page_size)
    ).all()
    return AdminPagedData(
        items=[item_mapper(item) for item in items],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


def normalize_admin_list_query(
    *,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_order: str = "desc",
    allowed_sort_by: set[str] | frozenset[str],
    default_sort_by: str | None = None,
    default_sort_order: SortOrder = "desc",
) -> AdminListQuery:
    if page < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page must be at least 1")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="page_size must be between 1 and 100")
    if sort_order not in {"asc", "desc"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sort_order must be asc or desc")

    normalized_sort_by = sort_by or default_sort_by
    if normalized_sort_by is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="sort_by is required")
    if normalized_sort_by not in allowed_sort_by:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid sort_by: {normalized_sort_by}")

    return AdminListQuery(
        page=page,
        page_size=page_size,
        sort_by=normalized_sort_by,
        sort_order=sort_order if sort_order in {"asc", "desc"} else default_sort_order,
    )


def _job_to_admin_data(model: RagIngestionJobModel) -> AdminIngestionJobData:
    return AdminIngestionJobData(
        job_id=model.job_id,
        document_id=model.document_id,
        status=model.status,
        failure_reason=model.failure_reason,
        started_at=model.started_at,
        completed_at=model.completed_at,
        retry_count=model.retry_count,
        is_reindex=model.is_reindex,
        chunk_size=model.chunk_size,
        chunk_overlap=model.chunk_overlap,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@dataclass
class AdminService:
    auth_service: AuthService
    rbac_service: RBACService
    rag_service: RagIngestionService
    cache: CacheAdapter | None = None

    def __post_init__(self) -> None:
        if self.cache is None:
            self.cache = get_cache_adapter()

    def _get_cached_model(self, cache_key: str, schema: type[AdminModelT]) -> AdminModelT | None:
        assert self.cache is not None
        cached = self.cache.get(cache_key)
        if cached is None:
            return None
        return schema.model_validate(cached)

    def _set_cached_model(self, cache_key: str, data: BaseModel) -> None:
        assert self.cache is not None
        self.cache.set(cache_key, data.model_dump(mode="json"), ttl_seconds=ADMIN_READ_CACHE_TTL_SECONDS)

    def _invalidate_admin_entity_cache(self, entity: str, *, entity_id: str | None = None) -> None:
        assert self.cache is not None
        if entity_id is not None:
            self.cache.delete(build_admin_detail_cache_key(entity, entity_id))
        self.cache.delete_prefix(build_entity_cache_prefix("admin", entity=entity, kind="list"))

    def _invalidate_user_context_cache(self, user_id: str) -> None:
        assert self.cache is not None
        self.cache.delete(build_auth_user_context_cache_key(user_id))

    def _invalidate_user_contexts_for_role(self, session: Session, role_id: str) -> None:
        user_ids = session.scalars(select(UserRole.user_id).where(UserRole.role_id == role_id)).all()
        for user_id in user_ids:
            self._invalidate_user_context_cache(user_id)

    def _invalidate_user_contexts_for_permission(self, session: Session, permission_id: str) -> None:
        role_ids = session.scalars(select(RolePermission.role_id).where(RolePermission.permission_id == permission_id)).all()
        if not role_ids:
            return
        user_ids = session.scalars(
            select(UserRole.user_id).where(UserRole.role_id.in_(role_ids))
        ).all()
        for user_id in user_ids:
            self._invalidate_user_context_cache(user_id)

    def _invalidate_user_contexts_for_workspace(self, session: Session, workspace_id: str) -> None:
        user_ids = session.scalars(
            select(WorkspaceMembership.user_id).where(WorkspaceMembership.workspace_id == workspace_id)
        ).all()
        for user_id in user_ids:
            self._invalidate_user_context_cache(user_id)

    def clear_entity_list_cache(
        self,
        entity: str,
        *,
        page: int | None = None,
        page_size: int | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> dict[str, str]:
        del page, page_size, sort_by, sort_order
        assert self.cache is not None
        self.cache.delete_prefix(build_entity_cache_prefix("admin", entity=entity, kind="list"))
        return {"cleared": "list", "entity": entity}

    def clear_entity_detail_cache(self, entity: str, entity_id: str) -> dict[str, str]:
        assert self.cache is not None
        self.cache.delete(build_admin_detail_cache_key(entity, entity_id))
        return {"cleared": "detail", "entity": entity, "entity_id": entity_id}

    def require_permission(self, session: Session, user: User, permission_name: str) -> None:
        if not self.rbac_service.has_permission(session, user.id, permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{permission_name} permission required",
            )

    def list_users(
        self,
        session: Session,
        *,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> AdminPagedData[AdminUserData]:
        query = normalize_admin_list_query(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            allowed_sort_by={"email", "display_name", "is_active", "updated_at", "created_at"},
            default_sort_by="created_at",
        )
        cache_key = build_admin_list_cache_key(
            "users",
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        cached = self._get_cached_model(cache_key, AdminPagedData[AdminUserData])
        if cached is not None:
            return cached
        data = _build_paged_data(
            session,
            User,
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            allowed_sort_by={"email", "display_name", "is_active", "updated_at", "created_at"},
            default_sort_by="created_at",
            item_mapper=_user_to_admin_data,
        )
        self._set_cached_model(cache_key, data)
        return data

    def get_user(self, session: Session, user_id: str) -> AdminUserData:
        cache_key = build_admin_detail_cache_key("users", user_id)
        cached = self._get_cached_model(cache_key, AdminUserData)
        if cached is not None:
            return cached
        user = session.get(User, user_id)
        if user is None:
            raise KeyError(user_id)
        data = _user_to_admin_data(user)
        self._set_cached_model(cache_key, data)
        return data

    def _apply_user_relationships(
        self,
        session: Session,
        user: User,
        *,
        roles: list[str] | None,
        workspace_slugs: list[str] | None,
    ) -> None:
        if roles is not None:
            session.execute(delete(UserRole).where(UserRole.user_id == user.id))
            for role_name in roles:
                role = session.scalar(select(Role).where(Role.name == role_name))
                if role is None:
                    raise KeyError(role_name)
                session.add(UserRole(user_id=user.id, role_id=role.id))

        if workspace_slugs is not None:
            session.execute(delete(WorkspaceMembership).where(WorkspaceMembership.user_id == user.id))
            for workspace_slug in workspace_slugs:
                workspace = session.scalar(select(Workspace).where(Workspace.slug == workspace_slug))
                if workspace is None:
                    raise KeyError(workspace_slug)
                session.add(WorkspaceMembership(user_id=user.id, workspace_id=workspace.id))

    def create_user(self, session: Session, request: AdminUserCreateRequest) -> AdminUserData:
        user = self.auth_service.create_user(
            session,
            email=request.email,
            display_name=request.display_name,
            password=request.password,
            is_active=request.is_active,
        )
        self._apply_user_relationships(
            session,
            user,
            roles=request.roles,
            workspace_slugs=request.workspace_slugs,
        )
        session.commit()
        session.refresh(user)
        self._invalidate_admin_entity_cache("users", entity_id=user.id)
        return _user_to_admin_data(user)

    def update_user(self, session: Session, user_id: str, request: AdminUserUpdateRequest) -> AdminUserData:
        user = session.get(User, user_id)
        if user is None:
            raise KeyError(user_id)
        if request.display_name is not None:
            user.display_name = request.display_name
        if request.password is not None:
            user.hashed_password = self.auth_service.hash_password(request.password)
        if request.is_active is not None:
            user.is_active = request.is_active
        self._apply_user_relationships(
            session,
            user,
            roles=request.roles,
            workspace_slugs=request.workspace_slugs,
        )
        session.commit()
        session.refresh(user)
        self._invalidate_admin_entity_cache("users", entity_id=user.id)
        self._invalidate_user_context_cache(user.id)
        return _user_to_admin_data(user)

    def delete_user(self, session: Session, user_id: str) -> AdminUserData:
        user = session.get(User, user_id)
        if user is None:
            raise KeyError(user_id)
        snapshot = _user_to_admin_data(user)
        session.execute(delete(UserRole).where(UserRole.user_id == user.id))
        session.execute(delete(WorkspaceMembership).where(WorkspaceMembership.user_id == user.id))
        session.execute(delete(User).where(User.id == user.id))
        session.commit()
        self._invalidate_admin_entity_cache("users", entity_id=user.id)
        self._invalidate_user_context_cache(user.id)
        return snapshot

    def disable_user(self, session: Session, user_id: str) -> AdminUserData:
        return self.update_user(session, user_id, AdminUserUpdateRequest(is_active=False))

    def activate_user(self, session: Session, user_id: str) -> AdminUserData:
        return self.update_user(session, user_id, AdminUserUpdateRequest(is_active=True))

    def list_roles(
        self,
        session: Session,
        *,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> AdminPagedData[AdminRoleData]:
        query = normalize_admin_list_query(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            allowed_sort_by={"name", "updated_at", "created_at"},
            default_sort_by="name",
            default_sort_order="asc",
        )
        cache_key = build_admin_list_cache_key(
            "roles",
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        cached = self._get_cached_model(cache_key, AdminPagedData[AdminRoleData])
        if cached is not None:
            return cached
        data = _build_paged_data(
            session,
            Role,
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            allowed_sort_by={"name", "updated_at", "created_at"},
            default_sort_by="name",
            item_mapper=_role_to_admin_data,
        )
        self._set_cached_model(cache_key, data)
        return data

    def get_role(self, session: Session, role_id: str) -> AdminRoleData:
        cache_key = build_admin_detail_cache_key("roles", role_id)
        cached = self._get_cached_model(cache_key, AdminRoleData)
        if cached is not None:
            return cached
        role = session.get(Role, role_id)
        if role is None:
            raise KeyError(role_id)
        data = _role_to_admin_data(role)
        self._set_cached_model(cache_key, data)
        return data

    def _apply_role_permissions(
        self,
        session: Session,
        role: Role,
        permissions: list[str] | None,
    ) -> None:
        if permissions is None:
            return
        session.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
        for permission_name in permissions:
            permission = session.scalar(select(Permission).where(Permission.name == permission_name))
            if permission is None:
                raise KeyError(permission_name)
            session.add(RolePermission(role_id=role.id, permission_id=permission.id))

    def create_role(self, session: Session, request: AdminRoleCreateRequest) -> AdminRoleData:
        role = Role(name=request.name, description=request.description)
        session.add(role)
        session.flush()
        self._apply_role_permissions(session, role, request.permissions)
        session.commit()
        session.refresh(role)
        self._invalidate_admin_entity_cache("roles", entity_id=role.id)
        return _role_to_admin_data(role)

    def update_role(self, session: Session, role_id: str, request: AdminRoleUpdateRequest) -> AdminRoleData:
        role = session.get(Role, role_id)
        if role is None:
            raise KeyError(role_id)
        if request.name is not None:
            role.name = request.name
        if request.description is not None:
            role.description = request.description
        self._apply_role_permissions(session, role, request.permissions)
        session.commit()
        session.refresh(role)
        self._invalidate_admin_entity_cache("roles", entity_id=role.id)
        self._invalidate_user_contexts_for_role(session, role.id)
        return _role_to_admin_data(role)

    def delete_role(self, session: Session, role_id: str) -> AdminRoleData:
        role = session.get(Role, role_id)
        if role is None:
            raise KeyError(role_id)
        snapshot = _role_to_admin_data(role)
        affected_user_ids = session.scalars(select(UserRole.user_id).where(UserRole.role_id == role.id)).all()
        session.execute(delete(UserRole).where(UserRole.role_id == role.id))
        session.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
        session.execute(delete(Role).where(Role.id == role.id))
        session.commit()
        self._invalidate_admin_entity_cache("roles", entity_id=role.id)
        for user_id in affected_user_ids:
            self._invalidate_user_context_cache(user_id)
        return snapshot

    def list_permissions(
        self,
        session: Session,
        *,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> AdminPagedData[AdminPermissionData]:
        query = normalize_admin_list_query(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            allowed_sort_by={"name", "updated_at", "created_at"},
            default_sort_by="name",
            default_sort_order="asc",
        )
        cache_key = build_admin_list_cache_key(
            "permissions",
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        cached = self._get_cached_model(cache_key, AdminPagedData[AdminPermissionData])
        if cached is not None:
            return cached
        data = _build_paged_data(
            session,
            Permission,
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            allowed_sort_by={"name", "updated_at", "created_at"},
            default_sort_by="name",
            item_mapper=_permission_to_admin_data,
        )
        self._set_cached_model(cache_key, data)
        return data

    def get_permission(self, session: Session, permission_id: str) -> AdminPermissionData:
        cache_key = build_admin_detail_cache_key("permissions", permission_id)
        cached = self._get_cached_model(cache_key, AdminPermissionData)
        if cached is not None:
            return cached
        permission = session.get(Permission, permission_id)
        if permission is None:
            raise KeyError(permission_id)
        data = _permission_to_admin_data(permission)
        self._set_cached_model(cache_key, data)
        return data

    def create_permission(self, session: Session, request: AdminPermissionCreateRequest) -> AdminPermissionData:
        permission = Permission(name=request.name, description=request.description)
        session.add(permission)
        session.commit()
        session.refresh(permission)
        self._invalidate_admin_entity_cache("permissions", entity_id=permission.id)
        return _permission_to_admin_data(permission)

    def update_permission(
        self,
        session: Session,
        permission_id: str,
        request: AdminPermissionUpdateRequest,
    ) -> AdminPermissionData:
        permission = session.get(Permission, permission_id)
        if permission is None:
            raise KeyError(permission_id)
        if request.name is not None:
            permission.name = request.name
        if request.description is not None:
            permission.description = request.description
        session.commit()
        session.refresh(permission)
        self._invalidate_admin_entity_cache("permissions", entity_id=permission.id)
        self._invalidate_user_contexts_for_permission(session, permission.id)
        return _permission_to_admin_data(permission)

    def delete_permission(self, session: Session, permission_id: str) -> AdminPermissionData:
        permission = session.get(Permission, permission_id)
        if permission is None:
            raise KeyError(permission_id)
        snapshot = _permission_to_admin_data(permission)
        affected_role_ids = session.scalars(
            select(RolePermission.role_id).where(RolePermission.permission_id == permission.id)
        ).all()
        affected_user_ids = session.scalars(
            select(UserRole.user_id).where(UserRole.role_id.in_(affected_role_ids))
        ).all()
        session.execute(delete(RolePermission).where(RolePermission.permission_id == permission.id))
        session.execute(delete(Permission).where(Permission.id == permission.id))
        session.commit()
        self._invalidate_admin_entity_cache("permissions", entity_id=permission.id)
        for user_id in affected_user_ids:
            self._invalidate_user_context_cache(user_id)
        return snapshot

    def list_workspaces(
        self,
        session: Session,
        *,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> AdminPagedData[AdminWorkspaceData]:
        query = normalize_admin_list_query(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            allowed_sort_by={"slug", "name", "is_default", "updated_at", "created_at"},
            default_sort_by="slug",
            default_sort_order="asc",
        )
        cache_key = build_admin_list_cache_key(
            "workspaces",
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        cached = self._get_cached_model(cache_key, AdminPagedData[AdminWorkspaceData])
        if cached is not None:
            return cached
        data = _build_paged_data(
            session,
            Workspace,
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            allowed_sort_by={"slug", "name", "is_default", "updated_at", "created_at"},
            default_sort_by="slug",
            item_mapper=_workspace_to_admin_data,
        )
        self._set_cached_model(cache_key, data)
        return data

    def get_workspace(self, session: Session, workspace_id: str) -> AdminWorkspaceData:
        cache_key = build_admin_detail_cache_key("workspaces", workspace_id)
        cached = self._get_cached_model(cache_key, AdminWorkspaceData)
        if cached is not None:
            return cached
        workspace = session.get(Workspace, workspace_id)
        if workspace is None:
            raise KeyError(workspace_id)
        data = _workspace_to_admin_data(workspace)
        self._set_cached_model(cache_key, data)
        return data

    def create_workspace(self, session: Session, request: AdminWorkspaceCreateRequest) -> AdminWorkspaceData:
        if request.is_default:
            for workspace in session.scalars(select(Workspace).where(Workspace.is_default.is_(True))).all():
                workspace.is_default = False
        workspace = Workspace(slug=request.slug, name=request.name, is_default=request.is_default)
        session.add(workspace)
        session.commit()
        session.refresh(workspace)
        self._invalidate_admin_entity_cache("workspaces", entity_id=workspace.id)
        return _workspace_to_admin_data(workspace)

    def update_workspace(
        self,
        session: Session,
        workspace_id: str,
        request: AdminWorkspaceUpdateRequest,
    ) -> AdminWorkspaceData:
        workspace = session.get(Workspace, workspace_id)
        if workspace is None:
            raise KeyError(workspace_id)
        if request.slug is not None:
            workspace.slug = request.slug
        if request.name is not None:
            workspace.name = request.name
        if request.is_default is not None:
            if request.is_default:
                for other_workspace in session.scalars(select(Workspace).where(Workspace.is_default.is_(True))).all():
                    other_workspace.is_default = False
            workspace.is_default = request.is_default
        session.commit()
        session.refresh(workspace)
        self._invalidate_admin_entity_cache("workspaces", entity_id=workspace.id)
        self._invalidate_user_contexts_for_workspace(session, workspace.id)
        return _workspace_to_admin_data(workspace)

    def delete_workspace(self, session: Session, workspace_id: str) -> AdminWorkspaceData:
        workspace = session.get(Workspace, workspace_id)
        if workspace is None:
            raise KeyError(workspace_id)
        snapshot = _workspace_to_admin_data(workspace)
        affected_user_ids = session.scalars(
            select(WorkspaceMembership.user_id).where(WorkspaceMembership.workspace_id == workspace.id)
        ).all()
        session.execute(delete(WorkspaceMembership).where(WorkspaceMembership.workspace_id == workspace.id))
        session.execute(delete(Workspace).where(Workspace.id == workspace.id))
        session.commit()
        self._invalidate_admin_entity_cache("workspaces", entity_id=workspace.id)
        for user_id in affected_user_ids:
            self._invalidate_user_context_cache(user_id)
        return snapshot

    def list_documents(
        self,
        session: Session,
        *,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> AdminPagedData[AdminDocumentData]:
        query = normalize_admin_list_query(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            allowed_sort_by={
                "title",
                "original_filename",
                "status",
                "owner_user_id",
                "workspace_id",
                "updated_at",
                "created_at",
            },
            default_sort_by="updated_at",
        )
        cache_key = build_admin_list_cache_key(
            "documents",
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        cached = self._get_cached_model(cache_key, AdminPagedData[AdminDocumentData])
        if cached is not None:
            return cached
        data = _build_paged_data(
            session,
            RagDocumentModel,
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            allowed_sort_by={
                "title",
                "original_filename",
                "status",
                "owner_user_id",
                "workspace_id",
                "updated_at",
                "created_at",
            },
            default_sort_by="updated_at",
            item_mapper=_document_to_admin_data,
        )
        self._set_cached_model(cache_key, data)
        return data

    def get_document(self, session: Session, document_id: str) -> AdminDocumentData:
        cache_key = build_admin_detail_cache_key("documents", document_id)
        cached = self._get_cached_model(cache_key, AdminDocumentData)
        if cached is not None:
            return cached
        document = session.scalar(select(RagDocumentModel).where(RagDocumentModel.document_id == document_id))
        if document is None:
            raise KeyError(document_id)
        data = _document_to_admin_data(document)
        self._set_cached_model(cache_key, data)
        return data

    def create_document(self, session: Session, request: AdminDocumentCreateRequest) -> AdminDocumentData:
        normalized_text = normalize_text(request.text)
        title = request.title.strip() if request.title else None
        if title is None and request.original_filename:
            title = Path(request.original_filename).stem or None
        content_hash = make_content_hash(title, normalized_text)
        document_id = make_document_id(content_hash)
        document = RagDocumentModel(
            document_id=document_id,
            title=title,
            original_filename=request.original_filename.strip() if request.original_filename else None,
            text=normalized_text,
            content_hash=content_hash,
            owner_user_id=request.owner_user_id,
            workspace_id=request.workspace_id,
            permission_scope=request.permission_scope,
            status="registered",
            parse_status="pending",
            chunk_status="pending",
            embedding_status="pending",
            index_status="pending",
        )
        session.add(document)
        session.commit()
        session.refresh(document)
        self._invalidate_admin_entity_cache("documents", entity_id=document.document_id)
        return _document_to_admin_data(document)

    def update_document(
        self,
        session: Session,
        document_id: str,
        request: AdminDocumentUpdateRequest,
    ) -> AdminDocumentData:
        document = session.scalar(select(RagDocumentModel).where(RagDocumentModel.document_id == document_id))
        if document is None:
            raise KeyError(document_id)
        if request.title is not None:
            document.title = request.title.strip()
        if request.original_filename is not None:
            document.original_filename = request.original_filename.strip()
        if request.text is not None:
            document.text = normalize_text(request.text)
            document.content_hash = make_content_hash(request.title or document.title, document.text)
        if request.owner_user_id is not None:
            document.owner_user_id = request.owner_user_id
        if request.workspace_id is not None:
            document.workspace_id = request.workspace_id
        if request.permission_scope is not None:
            document.permission_scope = request.permission_scope
        if request.status is not None:
            document.status = request.status
        if request.parse_status is not None:
            document.parse_status = request.parse_status
        if request.chunk_status is not None:
            document.chunk_status = request.chunk_status
        if request.embedding_status is not None:
            document.embedding_status = request.embedding_status
        if request.index_status is not None:
            document.index_status = request.index_status
        if request.error_message is not None:
            document.error_message = request.error_message
        if request.is_deleted is not None:
            document.is_deleted = request.is_deleted
        session.commit()
        session.refresh(document)
        self._invalidate_admin_entity_cache("documents", entity_id=document.document_id)
        return _document_to_admin_data(document)

    def delete_document(self, session: Session, document_id: str) -> AdminDocumentData:
        document = session.scalar(select(RagDocumentModel).where(RagDocumentModel.document_id == document_id))
        if document is None:
            raise KeyError(document_id)
        snapshot = _document_to_admin_data(document)
        session.execute(delete(RagChunkModel).where(RagChunkModel.document_id == document_id))
        session.execute(delete(RagIngestionJobModel).where(RagIngestionJobModel.document_id == document_id))
        session.execute(delete(RagDocumentModel).where(RagDocumentModel.document_id == document_id))
        session.commit()
        self._invalidate_admin_entity_cache("documents", entity_id=document_id)
        self.rag_service.purge_document_artifacts(document_id)
        return snapshot

    def restore_document(self, session: Session, document_id: str) -> AdminDocumentData:
        document = session.scalar(select(RagDocumentModel).where(RagDocumentModel.document_id == document_id))
        if document is None:
            raise KeyError(document_id)
        document.status = "registered"
        document.parse_status = "pending"
        document.chunk_status = "pending"
        document.embedding_status = "pending"
        document.index_status = "pending"
        document.is_deleted = False
        document.error_message = None
        session.commit()
        session.refresh(document)
        self._invalidate_admin_entity_cache("documents", entity_id=document.document_id)
        return _document_to_admin_data(document)

    def reindex_document(
        self,
        session: Session,
        document_id: str,
        *,
        rag_service: RagIngestionService | None = None,
    ) -> AdminDocumentData:
        document = session.scalar(select(RagDocumentModel).where(RagDocumentModel.document_id == document_id))
        if document is None:
            raise KeyError(document_id)
        service = rag_service or self.rag_service
        latest_job = session.scalar(
            select(RagIngestionJobModel)
            .where(RagIngestionJobModel.document_id == document_id)
            .order_by(RagIngestionJobModel.created_at.desc(), RagIngestionJobModel.updated_at.desc())
        )
        request = RagIngestRequest(
            doc_id=document_id,
            chunk_size=latest_job.chunk_size if latest_job and latest_job.chunk_size else 800,
            chunk_overlap=latest_job.chunk_overlap if latest_job and latest_job.chunk_overlap else 120,
            reindex=True,
        )
        service.ingest_document(request)
        session.refresh(document)
        self._invalidate_admin_entity_cache("documents", entity_id=document_id)
        return _document_to_admin_data(document)

    def list_jobs(
        self,
        session: Session,
        *,
        page: int = 1,
        page_size: int = 20,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> AdminPagedData[AdminIngestionJobData]:
        return _build_paged_data(
            session,
            RagIngestionJobModel,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            allowed_sort_by={"status", "document_id", "created_at", "updated_at"},
            default_sort_by="created_at",
            item_mapper=_job_to_admin_data,
        )

    def get_job(self, session: Session, job_id: str) -> AdminIngestionJobData:
        job = session.scalar(select(RagIngestionJobModel).where(RagIngestionJobModel.job_id == job_id))
        if job is None:
            raise KeyError(job_id)
        return _job_to_admin_data(job)

    def update_job(
        self,
        session: Session,
        job_id: str,
        request: AdminIngestionJobUpdateRequest,
    ) -> AdminIngestionJobData:
        job = session.scalar(select(RagIngestionJobModel).where(RagIngestionJobModel.job_id == job_id))
        if job is None:
            raise KeyError(job_id)
        if request.status is not None:
            job.status = request.status
        if request.failure_reason is not None:
            job.failure_reason = request.failure_reason
        if request.retry_count is not None:
            job.retry_count = request.retry_count
        if request.is_reindex is not None:
            job.is_reindex = request.is_reindex
        if request.chunk_size is not None:
            job.chunk_size = request.chunk_size
        if request.chunk_overlap is not None:
            job.chunk_overlap = request.chunk_overlap
        session.commit()
        session.refresh(job)
        return _job_to_admin_data(job)


_ADMIN_SERVICE = AdminService(
    auth_service=get_auth_service(),
    rbac_service=get_rbac_service(),
    rag_service=get_rag_ingestion_service(),
)


def get_admin_service() -> AdminService:
    return _ADMIN_SERVICE
