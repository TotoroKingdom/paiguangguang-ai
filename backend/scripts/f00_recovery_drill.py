"""Read-only F00 evidence tool: snapshot, integrity check, restore and schema diff.

This script never opens the source database in write mode. It copies through the
SQLite backup API into an isolated directory, then reports aggregate counts only.
Pass ``--storage`` to add the verified database plus user-file recovery drill
implemented by ``scripts.backup_restore``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

try:
    from scripts.backup_restore import create_backup, restore_and_verify
except ModuleNotFoundError:  # Supports direct execution from backend/scripts.
    from backup_restore import create_backup, restore_and_verify

TABLES = [
    "conversations",
    "messages",
    "admin_users",
    "admin_sessions",
    "capability_definitions",
    "capability_versions",
    "capability_dependencies",
    "capability_runs",
    "audit_events",
    "users",
    "user_sessions",
    "user_recovery_codes",
    "account_sequences",
    "registration_idempotency",
    "admin_user_links",
    "auth_rate_events",
]


def snapshot(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    uri = f"file:{source.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as reader:
        with sqlite3.connect(target) as writer:
            reader.backup(writer)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def table_names(connection: sqlite3.Connection) -> list[str]:
    return [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]


def schema(connection: sqlite3.Connection) -> dict[str, object]:
    result: dict[str, object] = {}
    for table in table_names(connection):
        columns = [
            {
                "name": row[1],
                "type": row[2],
                "notnull": row[3],
                "default": row[4],
                "pk": row[5],
            }
            for row in connection.execute(f'PRAGMA table_info("{table}")')
        ]
        indexes = [
            {
                "name": row[1],
                "unique": row[2],
                "columns": [
                    item[2]
                    for item in connection.execute(f'PRAGMA index_info("{row[1]}")')
                ],
            }
            for row in connection.execute(f'PRAGMA index_list("{table}")')
        ]
        result[table] = {"columns": columns, "indexes": indexes}
    return result


def report(path: Path) -> dict[str, object]:
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA query_only=ON")
        tables = table_names(connection)
        counts = {}
        for table in tables:
            counts[table] = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        result: dict[str, object] = {
            "path": str(path),
            "sizeBytes": path.stat().st_size,
            "sha256": file_hash(path),
            "sqliteVersion": sqlite3.sqlite_version,
            "userVersion": connection.execute("PRAGMA user_version").fetchone()[0],
            "hasAlembicVersion": "alembic_version" in tables,
            "alembicVersion": (
                connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
                if "alembic_version" in tables
                else None
            ),
            "integrityCheck": connection.execute("PRAGMA integrity_check").fetchone()[0],
            "foreignKeyViolations": len(
                connection.execute("PRAGMA foreign_key_check").fetchall()
            ),
            "counts": counts,
            "ownerBuckets": {
                str(row[0]): row[1]
                for row in connection.execute(
                    "SELECT conversation_count, COUNT(*) FROM ("
                    "SELECT owner_id, COUNT(*) AS conversation_count FROM conversations GROUP BY owner_id"
                    ") GROUP BY conversation_count ORDER BY conversation_count"
                )
            }
            if "conversations" in tables
            else {},
            "orphanMessages": (
                connection.execute(
                    "SELECT COUNT(*) FROM messages m LEFT JOIN conversations c "
                    "ON c.id = m.conversation_id WHERE c.id IS NULL"
                ).fetchone()[0]
                if {"messages", "conversations"}.issubset(tables)
                else None
            ),
        }
        result["schema"] = schema(connection)
        return result


def diff_schema(left: dict[str, object], right: dict[str, object]) -> dict[str, object]:
    left_tables = set(left)
    right_tables = set(right)
    differences: dict[str, object] = {
        "onlyLeft": sorted(left_tables - right_tables),
        "onlyRight": sorted(right_tables - left_tables),
        "changed": [],
    }
    for table in sorted(left_tables & right_tables):
        if left[table] != right[table]:
            differences["changed"].append(table)
    return differences


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--compare", default="")
    parser.add_argument("--storage", default="")
    args = parser.parse_args()
    source = Path(args.source)
    workdir = Path(args.workdir)
    if not source.exists():
        raise SystemExit(f"source database not found: {source}")

    backup = workdir / "snapshot.db"
    restored = workdir / "restored.db"
    snapshot(source, backup)
    snapshot(backup, restored)
    original = report(backup)
    replica = report(restored)
    result = {
        "source": str(source),
        "backup": {key: value for key, value in original.items() if key != "schema"},
        "restore": {key: value for key, value in replica.items() if key != "schema"},
        "restoreMatchesSnapshot": {
            "sha256": original["sha256"] == replica["sha256"],
            "counts": original["counts"] == replica["counts"],
            "schema": original["schema"] == replica["schema"],
        },
    }
    if args.compare:
        compared = report(Path(args.compare))
        result["compareTo"] = str(args.compare)
        result["schemaDiff"] = diff_schema(original["schema"], compared["schema"])
    if args.storage:
        joint_backup = workdir / "joint-backup"
        joint_restore_db = workdir / "joint-restored.db"
        joint_restore_storage = workdir / "joint-restored-user-files"
        manifest = create_backup(source, Path(args.storage), joint_backup)
        result["jointBackup"] = {
            "fileCount": len(manifest["files"]),
            "databaseSha256": manifest["database"]["sha256"],
        }
        result["jointRestore"] = restore_and_verify(
            joint_backup, joint_restore_db, joint_restore_storage
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
