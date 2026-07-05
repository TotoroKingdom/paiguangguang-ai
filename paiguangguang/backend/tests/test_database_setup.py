from __future__ import annotations

import sqlite3

from alembic import command
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.alembic import get_alembic_config
from app.db.session import get_db_session


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
