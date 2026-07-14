from __future__ import annotations

import ast
from pathlib import Path
import sqlite3

from alembic import command

from app.db.alembic import get_alembic_config


def test_migration_0006_identifiers_fit_postgresql_limit() -> None:
    migration_path = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "0006_create_chatbot_tables.py"
    tree = ast.parse(migration_path.read_text(encoding="utf-8"))
    identifiers = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.startswith(("fk_", "uq_", "ix_", "ck_"))
    ]

    assert [name for name in identifiers if len(name) > 63] == []


def _configure_test_db(monkeypatch, tmp_path) -> str:
    db_path = tmp_path / "chatbot-migration-0006.sqlite3"
    database_url = f"sqlite+pysqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TEST_DATABASE_URL", database_url)
    return db_path.as_posix()


def test_chatbot_migration_0006_creates_tables_and_revision(monkeypatch, tmp_path) -> None:
    db_path = _configure_test_db(monkeypatch, tmp_path)

    alembic_config = get_alembic_config()
    command.upgrade(alembic_config, "0006_create_chatbot_tables")

    with sqlite3.connect(db_path) as connection:
        table_rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name IN (
                'chatbot_conversations',
                'chatbot_messages',
                'chatbot_conversation_summaries',
                'chatbot_memories',
                'chatbot_llm_runs'
              )
            ORDER BY name
            """
        ).fetchall()
        version_rows = connection.execute("SELECT version_num FROM alembic_version").fetchall()
        conversation_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'chatbot_conversations'"
        ).fetchone()[0]
        message_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'chatbot_messages'"
        ).fetchone()[0]

    assert [row[0] for row in table_rows] == [
        "chatbot_conversation_summaries",
        "chatbot_conversations",
        "chatbot_llm_runs",
        "chatbot_memories",
        "chatbot_messages",
    ]
    assert version_rows == [("0006_create_chatbot_tables",)]
    assert "fk_chatbot_conversations_user_id_users" in conversation_sql
    assert "ck_chatbot_conversations_status" in conversation_sql
    assert "ck_chatbot_conversations_next_sequence" in conversation_sql
    assert "fk_chatbot_messages_conversation_id_chatbot_conversations" in message_sql
    assert "uq_chatbot_messages_conversation_id_sequence_number" in message_sql
    assert "uq_chatbot_messages_user_id_conversation_id_client_request_id" in message_sql


def test_chatbot_migration_0006_downgrades_cleanly(monkeypatch, tmp_path) -> None:
    db_path = _configure_test_db(monkeypatch, tmp_path)

    command.upgrade(get_alembic_config(), "head")
    command.downgrade(get_alembic_config(), "0005_add_orig_filename_kb_state")

    with sqlite3.connect(db_path) as connection:
        table_rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name LIKE 'chatbot_%'
            """
        ).fetchall()
        version_rows = connection.execute("SELECT version_num FROM alembic_version").fetchall()

    assert table_rows == []
    assert version_rows == [("0005_add_orig_filename_kb_state",)]
