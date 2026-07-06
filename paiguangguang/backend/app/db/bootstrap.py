from __future__ import annotations

from alembic import command
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.db.models import User
from app.db.alembic import get_alembic_config
from app.db.session import build_session_factory
from app.services.auth import AuthService
from app.services.rbac import RBACBootstrapResult, get_rbac_service


def _bootstrap_admin_user(session, settings: Settings, defaults: RBACBootstrapResult) -> None:
    email = settings.admin_user_email.strip().lower()
    password = settings.admin_user_password
    display_name = settings.admin_user_display_name.strip() or "Admin"

    if not email and not password:
        return
    if not email or not password:
        raise ValueError("ADMIN_USER_EMAIL and ADMIN_USER_PASSWORD must both be configured")

    auth_service = AuthService(settings)
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = auth_service.create_user(
            session,
            email=email,
            display_name=display_name,
            password=password,
            is_active=True,
        )
    else:
        if user.display_name != display_name:
            user.display_name = display_name
        if not auth_service.verify_password(password, user.hashed_password):
            user.hashed_password = auth_service.hash_password(password)
        if not user.is_active:
            user.is_active = True
        session.commit()
        session.refresh(user)

    rbac_service = get_rbac_service()
    rbac_service.assign_role_to_user(session, user.id, "system_admin")
    rbac_service.add_user_to_workspace(session, user.id, defaults.default_workspace.slug)


def initialize_database(settings: Settings | None = None) -> None:
    resolved_settings = settings or get_settings()
    if not resolved_settings.database_url and not resolved_settings.test_database_url:
        return

    command.upgrade(get_alembic_config(resolved_settings), "head")

    session_factory = build_session_factory(resolved_settings)
    session = session_factory()
    try:
        defaults = get_rbac_service().bootstrap_defaults(session)
        _bootstrap_admin_user(session, resolved_settings, defaults)
    finally:
        session.close()
