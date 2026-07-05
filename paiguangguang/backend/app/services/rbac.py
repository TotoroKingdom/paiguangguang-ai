from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Permission, Role, RolePermission, User, UserRole, Workspace, WorkspaceMembership

DEFAULT_WORKSPACE_SLUG = "default"
DEFAULT_WORKSPACE_NAME = "Default Workspace"

BASELINE_PERMISSIONS: tuple[tuple[str, str], ...] = (
    ("document.upload", "Upload documents"),
    ("document.view", "View documents"),
    ("document.delete", "Delete documents"),
    ("document.reindex", "Reindex documents"),
    ("knowledge.query", "Query knowledge base"),
    ("user.manage", "Manage users"),
    ("role.manage", "Manage roles"),
    ("workspace.manage", "Manage workspaces"),
)

ROLE_PERMISSION_MATRIX: dict[str, tuple[str, ...]] = {
    "user": ("document.upload", "document.view", "knowledge.query"),
    "document_admin": (
        "document.upload",
        "document.view",
        "document.delete",
        "document.reindex",
        "knowledge.query",
    ),
    "system_admin": tuple(permission for permission, _ in BASELINE_PERMISSIONS),
}

BASELINE_ROLE_DESCRIPTIONS: dict[str, str] = {
    "user": "Default knowledge base user",
    "document_admin": "Document lifecycle administrator",
    "system_admin": "System administrator",
}


@dataclass(frozen=True)
class RBACBootstrapResult:
    default_workspace: Workspace
    roles: dict[str, Role]
    permissions: dict[str, Permission]


class RBACService:
    def _get_or_create_workspace(
        self,
        session: Session,
        *,
        slug: str,
        name: str,
        is_default: bool,
    ) -> Workspace:
        workspace = session.scalar(select(Workspace).where(Workspace.slug == slug))
        if workspace is not None:
            if workspace.name != name or workspace.is_default != is_default:
                workspace.name = name
                workspace.is_default = is_default
                session.commit()
                session.refresh(workspace)
            return workspace

        workspace = Workspace(slug=slug, name=name, is_default=is_default)
        session.add(workspace)
        session.commit()
        session.refresh(workspace)
        return workspace

    def _get_or_create_role(
        self,
        session: Session,
        *,
        name: str,
        description: str | None,
    ) -> Role:
        role = session.scalar(select(Role).where(Role.name == name))
        if role is not None:
            if role.description != description:
                role.description = description
                session.commit()
                session.refresh(role)
            return role

        role = Role(name=name, description=description)
        session.add(role)
        session.commit()
        session.refresh(role)
        return role

    def _get_or_create_permission(
        self,
        session: Session,
        *,
        name: str,
        description: str | None,
    ) -> Permission:
        permission = session.scalar(select(Permission).where(Permission.name == name))
        if permission is not None:
            if permission.description != description:
                permission.description = description
                session.commit()
                session.refresh(permission)
            return permission

        permission = Permission(name=name, description=description)
        session.add(permission)
        session.commit()
        session.refresh(permission)
        return permission

    def bootstrap_defaults(self, session: Session) -> RBACBootstrapResult:
        default_workspace = self._get_or_create_workspace(
            session,
            slug=DEFAULT_WORKSPACE_SLUG,
            name=DEFAULT_WORKSPACE_NAME,
            is_default=True,
        )

        permissions: dict[str, Permission] = {}
        for permission_name, description in BASELINE_PERMISSIONS:
            permissions[permission_name] = self._get_or_create_permission(
                session,
                name=permission_name,
                description=description,
            )

        roles: dict[str, Role] = {}
        for role_name, permission_names in ROLE_PERMISSION_MATRIX.items():
            role = self._get_or_create_role(
                session,
                name=role_name,
                description=BASELINE_ROLE_DESCRIPTIONS[role_name],
            )
            roles[role_name] = role

            existing_permission_ids = {permission.id for permission in role.permissions}
            for permission_name in permission_names:
                permission = permissions[permission_name]
                if permission.id not in existing_permission_ids:
                    session.add(RolePermission(role_id=role.id, permission_id=permission.id))
                    existing_permission_ids.add(permission.id)

        session.commit()
        session.refresh(default_workspace)
        for role_name, role in list(roles.items()):
            session.refresh(role)
            roles[role_name] = role

        return RBACBootstrapResult(
            default_workspace=default_workspace,
            roles=roles,
            permissions=permissions,
        )

    def list_workspace_slugs(self, session: Session) -> list[str]:
        result = session.scalars(select(Workspace.slug).order_by(Workspace.slug))
        return list(result)

    def list_role_names(self, session: Session) -> list[str]:
        result = session.scalars(select(Role.name).order_by(Role.name))
        return list(result)

    def assign_role_to_user(self, session: Session, user_id: str, role_name: str) -> None:
        user = session.get(User, user_id)
        if user is None:
            raise KeyError(user_id)

        role = session.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            raise KeyError(role_name)

        existing = session.scalar(
            select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role.id)
        )
        if existing is None:
            session.add(UserRole(user_id=user_id, role_id=role.id))
            session.commit()

    def add_user_to_workspace(self, session: Session, user_id: str, workspace_slug: str) -> None:
        user = session.get(User, user_id)
        if user is None:
            raise KeyError(user_id)

        workspace = session.scalar(select(Workspace).where(Workspace.slug == workspace_slug))
        if workspace is None:
            raise KeyError(workspace_slug)

        existing = session.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.user_id == user_id,
                WorkspaceMembership.workspace_id == workspace.id,
            )
        )
        if existing is None:
            session.add(WorkspaceMembership(user_id=user_id, workspace_id=workspace.id))
            session.commit()

    def has_permission(self, session: Session, user_id: str, permission_name: str) -> bool:
        query = (
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id, Permission.name == permission_name)
        )
        return session.scalar(query) is not None


_RBAC_SERVICE = RBACService()


def get_rbac_service() -> RBACService:
    return _RBAC_SERVICE
