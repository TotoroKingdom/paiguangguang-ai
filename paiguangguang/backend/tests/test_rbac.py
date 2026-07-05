from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import User
from app.services.rbac import RBACService


def _create_session(tmp_path, filename: str = "rbac.sqlite3"):
    engine = create_engine(f"sqlite+pysqlite:///{(tmp_path / filename).as_posix()}")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return session_factory()


def test_bootstrap_defaults_creates_default_workspace_and_baseline_access_matrix(tmp_path) -> None:
    session = _create_session(tmp_path)
    service = RBACService()

    defaults = service.bootstrap_defaults(session)

    assert defaults.default_workspace.slug == "default"
    assert defaults.default_workspace.name == "Default Workspace"
    assert defaults.roles["user"].name == "user"
    assert defaults.roles["document_admin"].name == "document_admin"
    assert defaults.roles["system_admin"].name == "system_admin"
    assert service.list_workspace_slugs(session) == ["default"]
    assert service.list_role_names(session) == [
        "document_admin",
        "system_admin",
        "user",
    ]

    session.close()


def test_permission_matrix_allows_and_denies_deterministically(tmp_path) -> None:
    session = _create_session(tmp_path, "permission-matrix.sqlite3")
    service = RBACService()
    service.bootstrap_defaults(session)

    user = User(
        email="editor@example.com",
        display_name="Editor",
        hashed_password="hashed",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    assert service.has_permission(session, user.id, "document.upload") is False

    service.assign_role_to_user(session, user.id, "user")
    assert service.has_permission(session, user.id, "document.upload") is True
    assert service.has_permission(session, user.id, "document.delete") is False

    service.assign_role_to_user(session, user.id, "document_admin")
    assert service.has_permission(session, user.id, "document.delete") is True
    assert service.has_permission(session, user.id, "workspace.manage") is False

    service.assign_role_to_user(session, user.id, "system_admin")
    assert service.has_permission(session, user.id, "workspace.manage") is True
    assert service.has_permission(session, user.id, "role.manage") is True

    session.close()
