from __future__ import annotations

import sqlite3

from alembic import command

from app.db.alembic import get_alembic_config


def _configure(monkeypatch, tmp_path) -> str:
    path = tmp_path / "chatbot-migration-0007.sqlite3"
    url = f"sqlite+pysqlite:///{path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("TEST_DATABASE_URL", url)
    return path.as_posix()


def test_migration_0007_creates_durable_jobs(monkeypatch, tmp_path) -> None:
    path = _configure(monkeypatch, tmp_path)
    command.upgrade(get_alembic_config(), "head")
    with sqlite3.connect(path) as connection:
        table = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='chatbot_jobs'"
        ).fetchone()
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    assert table is not None
    assert "uq_chatbot_jobs_dedup_key" in table[0]
    assert "ck_chatbot_jobs_status" in table[0]
    assert version == ("0007_create_chatbot_jobs",)


def test_migration_0007_downgrades_to_0006(monkeypatch, tmp_path) -> None:
    path = _configure(monkeypatch, tmp_path)
    command.upgrade(get_alembic_config(), "head")
    command.downgrade(get_alembic_config(), "0006_create_chatbot_tables")
    with sqlite3.connect(path) as connection:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='chatbot_jobs'"
        ).fetchone()
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    assert table is None
    assert version == ("0006_create_chatbot_tables",)
