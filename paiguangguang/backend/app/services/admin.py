from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

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
    AdminDocumentCreateRequest,
    AdminDocumentData,
    AdminDocumentUpdateRequest,
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
from app.services.rag_ingestion import (
    RagIngestionService,
    get_rag_ingestion_service,
    make_content_hash,
    make_document_id,
    normalize_text,
)
from app.services.rbac import RBACService, get_rbac_service


def _user_roles(user: User) -> list[str]:
    return sorted({role.name for role in user.roles})


def _user_workspace_ids(user: User) -> list[str]:
    return sorted({membership.workspace_id for membership in user.workspace_memberships})


def _user_to_admin_data(user: User) -> AdminUserData:
    base = user_to_data(user)
    return AdminUserData.model_validate(
        {
            **base.model_dump(),
            "roles": _user_roles(user),
            "workspace_ids": _user_workspace_ids(user),
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

    def require_permission(self, session: Session, user: User, permission_name: str) -> None:
        if not self.rbac_service.has_permission(session, user.id, permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{permission_name} permission required",
            )

    def list_users(self, session: Session) -> list[AdminUserData]:
        users = session.scalars(select(User).order_by(User.created_at.desc())).all()
        return [_user_to_admin_data(user) for user in users]

    def get_user(self, session: Session, user_id: str) -> AdminUserData:
        user = session.get(User, user_id)
        if user is None:
            raise KeyError(user_id)
        return _user_to_admin_data(user)

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
        return _user_to_admin_data(user)

    def disable_user(self, session: Session, user_id: str) -> AdminUserData:
        return self.update_user(session, user_id, AdminUserUpdateRequest(is_active=False))

    def list_roles(self, session: Session) -> list[AdminRoleData]:
        roles = session.scalars(select(Role).order_by(Role.name)).all()
        return [_role_to_admin_data(role) for role in roles]

    def get_role(self, session: Session, role_id: str) -> AdminRoleData:
        role = session.get(Role, role_id)
        if role is None:
            raise KeyError(role_id)
        return _role_to_admin_data(role)

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
        return _role_to_admin_data(role)

    def delete_role(self, session: Session, role_id: str) -> AdminRoleData:
        role = session.get(Role, role_id)
        if role is None:
            raise KeyError(role_id)
        snapshot = _role_to_admin_data(role)
        session.execute(delete(UserRole).where(UserRole.role_id == role.id))
        session.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
        session.execute(delete(Role).where(Role.id == role.id))
        session.commit()
        return snapshot

    def list_permissions(self, session: Session) -> list[AdminPermissionData]:
        permissions = session.scalars(select(Permission).order_by(Permission.name)).all()
        return [_permission_to_admin_data(permission) for permission in permissions]

    def get_permission(self, session: Session, permission_id: str) -> AdminPermissionData:
        permission = session.get(Permission, permission_id)
        if permission is None:
            raise KeyError(permission_id)
        return _permission_to_admin_data(permission)

    def create_permission(self, session: Session, request: AdminPermissionCreateRequest) -> AdminPermissionData:
        permission = Permission(name=request.name, description=request.description)
        session.add(permission)
        session.commit()
        session.refresh(permission)
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
        return _permission_to_admin_data(permission)

    def delete_permission(self, session: Session, permission_id: str) -> AdminPermissionData:
        permission = session.get(Permission, permission_id)
        if permission is None:
            raise KeyError(permission_id)
        snapshot = _permission_to_admin_data(permission)
        session.execute(delete(RolePermission).where(RolePermission.permission_id == permission.id))
        session.execute(delete(Permission).where(Permission.id == permission.id))
        session.commit()
        return snapshot

    def list_workspaces(self, session: Session) -> list[AdminWorkspaceData]:
        workspaces = session.scalars(select(Workspace).order_by(Workspace.slug)).all()
        return [_workspace_to_admin_data(workspace) for workspace in workspaces]

    def get_workspace(self, session: Session, workspace_id: str) -> AdminWorkspaceData:
        workspace = session.get(Workspace, workspace_id)
        if workspace is None:
            raise KeyError(workspace_id)
        return _workspace_to_admin_data(workspace)

    def create_workspace(self, session: Session, request: AdminWorkspaceCreateRequest) -> AdminWorkspaceData:
        if request.is_default:
            for workspace in session.scalars(select(Workspace).where(Workspace.is_default.is_(True))).all():
                workspace.is_default = False
        workspace = Workspace(slug=request.slug, name=request.name, is_default=request.is_default)
        session.add(workspace)
        session.commit()
        session.refresh(workspace)
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
        return _workspace_to_admin_data(workspace)

    def delete_workspace(self, session: Session, workspace_id: str) -> AdminWorkspaceData:
        workspace = session.get(Workspace, workspace_id)
        if workspace is None:
            raise KeyError(workspace_id)
        snapshot = _workspace_to_admin_data(workspace)
        session.execute(delete(WorkspaceMembership).where(WorkspaceMembership.workspace_id == workspace.id))
        session.execute(delete(Workspace).where(Workspace.id == workspace.id))
        session.commit()
        return snapshot

    def list_documents(self, session: Session) -> list[AdminDocumentData]:
        documents = session.scalars(select(RagDocumentModel).order_by(RagDocumentModel.updated_at.desc())).all()
        return [_document_to_admin_data(document) for document in documents]

    def get_document(self, session: Session, document_id: str) -> AdminDocumentData:
        document = session.scalar(select(RagDocumentModel).where(RagDocumentModel.document_id == document_id))
        if document is None:
            raise KeyError(document_id)
        return _document_to_admin_data(document)

    def create_document(self, session: Session, request: AdminDocumentCreateRequest) -> AdminDocumentData:
        normalized_text = normalize_text(request.text)
        content_hash = make_content_hash(request.title, normalized_text)
        document_id = make_document_id(content_hash)
        document = RagDocumentModel(
            document_id=document_id,
            title=request.title.strip() if request.title else None,
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
        return _document_to_admin_data(document)

    def delete_document(self, session: Session, document_id: str) -> AdminDocumentData:
        document = session.scalar(select(RagDocumentModel).where(RagDocumentModel.document_id == document_id))
        if document is None:
            raise KeyError(document_id)
        document.status = "deleted"
        document.is_deleted = True
        session.commit()
        session.refresh(document)
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
        return _document_to_admin_data(document)

    def list_jobs(self, session: Session) -> list[AdminIngestionJobData]:
        jobs = session.scalars(select(RagIngestionJobModel).order_by(RagIngestionJobModel.created_at.desc())).all()
        return [_job_to_admin_data(job) for job in jobs]

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
