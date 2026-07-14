from __future__ import annotations

import sqlite3

from alembic import command
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.bootstrap import initialize_database
from app.db.alembic import get_alembic_config
from app.db.models import Role, User, Workspace
from app.db.session import get_db_session, resolve_database_url
from app.services.auth import AuthService


def test_settings_load_database_url_and_test_override(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://app_user:app_pass@db.example.com/app_db",
    )
    monkeypatch.setenv("TEST_DATABASE_URL", "sqlite+pysqlite:///./test-db.sqlite3")

    settings = get_settings()

    assert settings.database_url == (
        "postgresql+psycopg://app_user:app_pass@db.example.com/app_db"
    )
    assert settings.test_database_url == "sqlite+pysqlite:///./test-db.sqlite3"


def test_resolve_database_url_keeps_postgres_password(monkeypatch) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://app_user:app_pass@db.example.com/app_db",
    )
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)

    resolved_url = resolve_database_url()

    assert resolved_url == "postgresql+psycopg://app_user:app_pass@db.example.com/app_db"


def test_settings_load_admin_bootstrap_configuration(monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_USER_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_USER_PASSWORD", "Secret123!")
    monkeypatch.setenv("ADMIN_USER_DISPLAY_NAME", "Primary Admin")

    settings = get_settings()

    assert settings.admin_user_email == "admin@example.com"
    assert settings.admin_user_password == "Secret123!"
    assert settings.admin_user_display_name == "Primary Admin"


def test_settings_load_login_private_key_path(monkeypatch, tmp_path) -> None:
    key_path = tmp_path / "login-private-key.pem"
    monkeypatch.setenv("AUTH_LOGIN_PRIVATE_KEY_PATH", str(key_path))

    settings = get_settings()

    assert settings.auth_login_private_key_path == str(key_path)


def test_database_session_dependency_uses_test_database_url(monkeypatch, tmp_path) -> None:
    test_db_path = tmp_path / "task17.sqlite3"
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://app_user:app_pass@db.example.com/app_db",
    )
    monkeypatch.setenv("TEST_DATABASE_URL", f"sqlite+pysqlite:///{test_db_path.as_posix()}")

    session_generator = get_db_session()
    session = next(session_generator)

    assert isinstance(session, Session)
    assert str(session.get_bind().url) == f"sqlite+pysqlite:///{test_db_path.as_posix()}"

    session_generator.close()


def test_alembic_upgrade_runs_against_test_database_url(monkeypatch, tmp_path) -> None:
    test_db_path = tmp_path / "alembic-task17.sqlite3"
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://app_user:app_pass@db.example.com/app_db",
    )
    monkeypatch.setenv("TEST_DATABASE_URL", f"sqlite+pysqlite:///{test_db_path.as_posix()}")

    alembic_config = get_alembic_config()
    command.upgrade(alembic_config, "head")

    assert test_db_path.exists()
    with sqlite3.connect(test_db_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
        ).fetchall()

    assert rows == [("alembic_version",)]


def test_initialize_database_runs_migrations_and_bootstraps_defaults(monkeypatch, tmp_path) -> None:
    test_db_path = tmp_path / "bootstrap-task17.sqlite3"
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://app_user:app_pass@db.example.com/app_db",
    )
    monkeypatch.setenv("TEST_DATABASE_URL", f"sqlite+pysqlite:///{test_db_path.as_posix()}")
    monkeypatch.setenv("ADMIN_USER_EMAIL", "admin@example.com")
    monkeypatch.setenv("ADMIN_USER_PASSWORD", "Secret123!")
    monkeypatch.setenv("ADMIN_USER_DISPLAY_NAME", "Primary Admin")

    initialize_database()
    initialize_database()

    assert test_db_path.exists()
    alembic_config = get_alembic_config()
    engine_url = alembic_config.get_main_option("sqlalchemy.url")
    assert engine_url == f"sqlite+pysqlite:///{test_db_path.as_posix()}"

    session_generator = get_db_session()
    session = next(session_generator)
    try:
        default_workspace = session.query(Workspace).filter(Workspace.slug == "default").one_or_none()
        role_names = sorted(role.name for role in session.query(Role).all())
        admin_user = session.query(User).filter(User.email == "admin@example.com").one_or_none()
        auth_service = AuthService()
        authenticated_user = auth_service.authenticate_user(session, "admin@example.com", "Secret123!")
    finally:
        session_generator.close()

    assert default_workspace is not None
    assert default_workspace.is_default is True
    assert role_names == ["document_admin", "system_admin", "user"]
    assert admin_user is not None
    assert admin_user.display_name == "Primary Admin"
    assert admin_user.is_active is True
    assert admin_user.hashed_password.startswith("$pbkdf2-sha256$")
    assert admin_user.hashed_password != "Secret123!"
    assert authenticated_user is not None
    assert any(role.name == "system_admin" for role in admin_user.roles)
    assert any(membership.workspace_id == default_workspace.id for membership in admin_user.workspace_memberships)
