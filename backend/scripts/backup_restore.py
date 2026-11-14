"""Create and verify joint SQLite plus user-file backups.

The command is intentionally conservative: a backup fails when a database
record does not have matching file bytes, when an unexpected file is present,
or when a file changes while it is being copied.  Restore also fails closed on
any manifest, database, or checksum mismatch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from app.modules.personal.storage import storage_lock

MANIFEST_NAME = "manifest.json"
MANIFEST_DIGEST_NAME = "manifest.sha256"
DATABASE_NAME = "assistant.db"
FORMAT_VERSION = 1


class BackupError(RuntimeError):
    """Raised when a backup or restore cannot be proven consistent."""


def _resolve(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _read_only_connection(path: Path) -> sqlite3.Connection:
    uri = f"file:{path.as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _hash_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _json_default(value: object) -> str:
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


def _table_names(connection: sqlite3.Connection) -> list[str]:
    return [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]


def _table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [
        row[1]
        for row in connection.execute(f'PRAGMA table_info("{table}")')
    ]


def _table_fingerprint(connection: sqlite3.Connection, table: str) -> str:
    columns = _table_columns(connection, table)
    digest = hashlib.sha256()
    digest.update(json.dumps(columns, ensure_ascii=False).encode("utf-8"))
    select_columns = ", ".join(f'"{column}"' for column in columns)
    order = "rowid" if "rowid" not in columns else ", ".join(
        f'"{column}"' for column in columns
    )
    rows = connection.execute(
        f'SELECT {select_columns} FROM "{table}" ORDER BY {order}'
    )
    for row in rows:
        values = list(row)
        if table == "user_files" and "storage_path" in columns:
            values[columns.index("storage_path")] = "<storage-path>"
        encoded = json.dumps(
            values,
            default=_json_default,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _database_summary(path: Path) -> dict[str, Any]:
    with closing(_read_only_connection(path)) as connection:
        connection.execute("PRAGMA query_only=ON")
        tables = _table_names(connection)
        counts = {
            table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            for table in tables
        }
        alembic_version = None
        if "alembic_version" in tables:
            row = connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()
            alembic_version = row[0] if row else None
        foreign_key_violations = len(
            connection.execute("PRAGMA foreign_key_check").fetchall()
        )
        integrity_check = connection.execute("PRAGMA integrity_check").fetchone()[0]
        size_bytes, sha256 = _hash_file(path)
        return {
            "sizeBytes": size_bytes,
            "sha256": sha256,
            "sqliteVersion": sqlite3.sqlite_version,
            "userVersion": connection.execute("PRAGMA user_version").fetchone()[0],
            "alembicVersion": alembic_version,
            "integrityCheck": integrity_check,
            "foreignKeyViolations": foreign_key_violations,
            "tableCounts": counts,
            "tableFingerprints": {
                table: _table_fingerprint(connection, table) for table in tables
            },
        }


def _sqlite_backup(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    with closing(_read_only_connection(source)) as reader:
        with closing(sqlite3.connect(target)) as writer:
            reader.backup(writer)
            writer.commit()
    os.chmod(target, 0o600)


def _relative_path(root: Path, path: Path) -> str:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        relative = resolved_path.relative_to(resolved_root)
    except ValueError as error:
        raise BackupError(f"file path escapes storage root: {path}") from error
    if not relative.parts:
        raise BackupError(f"storage path points at the root: {path}")
    return relative.as_posix()


def _iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if not root.is_dir():
        raise BackupError(f"storage root is not a directory: {root}")
    result: list[Path] = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise BackupError(f"symlink in storage tree: {path}")
        if path.is_file():
            result.append(path)
        elif not path.is_dir():
            raise BackupError(f"unsupported storage entry: {path}")
    return sorted(result, key=lambda item: _relative_path(root, item))


def _user_file_rows(path: Path) -> dict[str, dict[str, Any]]:
    with closing(_read_only_connection(path)) as connection:
        if "user_files" not in _table_names(connection):
            return {}
        rows = connection.execute(
            "SELECT id, user_id, size_bytes, checksum, storage_path, status "
            "FROM user_files ORDER BY id"
        ).fetchall()
        return {
            row[0]: {
                "id": row[0],
                "userId": row[1],
                "sizeBytes": row[2],
                "sha256": row[3],
                "storagePath": row[4],
                "status": row[5],
            }
            for row in rows
        }


def _validate_backup_destination(storage_root: Path, destination: Path) -> None:
    if destination == storage_root or storage_root in destination.parents:
        raise BackupError("backup destination must be outside the storage root")
    if destination.exists() and any(destination.iterdir()):
        raise BackupError(f"backup destination is not empty: {destination}")


def _write_json(path: Path, value: dict[str, Any]) -> bytes:
    encoded = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    path.write_bytes(encoded)
    os.chmod(path, 0o600)
    return encoded


def _manifest_digest(manifest_bytes: bytes) -> str:
    return hashlib.sha256(manifest_bytes).hexdigest()


def _validate_file_manifest(files: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_path: dict[str, dict[str, Any]] = {}
    by_id: dict[str, dict[str, Any]] = {}
    for item in files:
        relative = str(item.get("relativePath", ""))
        posix_path = PurePosixPath(relative)
        windows_path = PureWindowsPath(relative)
        if (
            not relative
            or posix_path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or ".." in posix_path.parts
            or ".." in windows_path.parts
        ):
            raise BackupError(f"invalid manifest path: {relative}")
        file_id = str(item.get("id", ""))
        if not file_id or relative in by_path or file_id in by_id:
            raise BackupError("duplicate file entry in manifest")
        if len(str(item.get("sha256", ""))) != 64:
            raise BackupError(f"invalid checksum in manifest: {relative}")
        by_path[relative] = item
        by_id[file_id] = item
    return by_id


def create_backup(
    source_db: str | Path,
    storage_root: str | Path,
    destination: str | Path,
) -> dict[str, Any]:
    """Create a verified backup directory and return its non-secret manifest."""

    source = _resolve(source_db)
    root = _resolve(storage_root)
    target = _resolve(destination)
    if not source.is_file():
        raise BackupError(f"source database not found: {source}")
    _validate_backup_destination(root, target)
    target.mkdir(parents=True, exist_ok=True)

    with storage_lock(root):
        database_target = target / DATABASE_NAME
        _sqlite_backup(source, database_target)
        database = _database_summary(database_target)
        rows = _user_file_rows(database_target)
        source_files = _iter_files(root)
        files_by_path: dict[str, Path] = {
            _relative_path(root, path): path for path in source_files
        }
        expected_paths: dict[str, str] = {}
        for row in rows.values():
            row_path = _resolve(row["storagePath"])
            relative = _relative_path(root, row_path)
            if relative in expected_paths:
                raise BackupError(f"duplicate database storage path: {relative}")
            expected_paths[relative] = row["id"]

        if set(files_by_path) != set(expected_paths):
            missing = sorted(set(expected_paths) - set(files_by_path))
            unexpected = sorted(set(files_by_path) - set(expected_paths))
            raise BackupError(
                f"database and storage disagree; missing={missing}; unexpected={unexpected}"
            )

        files_target = target / "files"
        files_target.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(files_target, 0o700)
        manifest_files: list[dict[str, Any]] = []
        for relative, source_path in files_by_path.items():
            file_id = expected_paths[relative]
            row = rows[file_id]
            size_bytes, sha256 = _hash_file(source_path)
            if size_bytes != row["sizeBytes"] or sha256 != row["sha256"]:
                raise BackupError(f"database checksum mismatch: {relative}")
            destination_path = files_target / Path(relative)
            destination_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(destination_path.parent, 0o700)
            shutil.copyfile(source_path, destination_path)
            os.chmod(destination_path, 0o600)
            copied_size, copied_sha256 = _hash_file(destination_path)
            final_size, final_sha256 = _hash_file(source_path)
            if (copied_size, copied_sha256) != (size_bytes, sha256) or (
                final_size,
                final_sha256,
            ) != (size_bytes, sha256):
                raise BackupError(f"file changed during backup: {relative}")
            manifest_files.append(
                {
                    "id": row["id"],
                    "userId": row["userId"],
                    "status": row["status"],
                    "relativePath": relative,
                    "sizeBytes": size_bytes,
                    "sha256": sha256,
                }
            )

        manifest: dict[str, Any] = {
            "formatVersion": FORMAT_VERSION,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "database": database,
            "files": sorted(manifest_files, key=lambda item: item["relativePath"]),
        }
        manifest_bytes = _write_json(target / MANIFEST_NAME, manifest)
        digest = _manifest_digest(manifest_bytes)
        (target / MANIFEST_DIGEST_NAME).write_text(digest + "\n", encoding="ascii")
        os.chmod(target / MANIFEST_DIGEST_NAME, 0o600)
        return manifest


def _load_manifest(backup_dir: Path) -> dict[str, Any]:
    manifest_path = backup_dir / MANIFEST_NAME
    digest_path = backup_dir / MANIFEST_DIGEST_NAME
    if not manifest_path.is_file() or not digest_path.is_file():
        raise BackupError("backup manifest is incomplete")
    manifest_bytes = manifest_path.read_bytes()
    expected_digest = digest_path.read_text(encoding="ascii").strip()
    if _manifest_digest(manifest_bytes) != expected_digest:
        raise BackupError("backup manifest checksum mismatch")
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BackupError("backup manifest is not valid JSON") from error
    if manifest.get("formatVersion") != FORMAT_VERSION:
        raise BackupError("unsupported backup manifest version")
    if not isinstance(manifest.get("files"), list):
        raise BackupError("backup manifest has no file list")
    _validate_file_manifest(manifest["files"])
    return manifest


def _clear_directory(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for child in root.iterdir():
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)
        else:
            raise BackupError(f"unsupported restore entry: {child}")


def _rebase_storage_paths(database: Path, storage_root: Path, files: list[dict[str, Any]]) -> None:
    by_id = _validate_file_manifest(files)
    with sqlite3.connect(database) as connection:
        tables = _table_names(connection)
        if "user_files" not in tables:
            if by_id:
                raise BackupError("manifest has files but restored database has no user_files table")
            return
        rows = connection.execute(
            "SELECT id, user_id, size_bytes, checksum, status FROM user_files"
        ).fetchall()
        if {row[0] for row in rows} != set(by_id):
            raise BackupError("restored database file records do not match manifest")
        for file_id, user_id, size_bytes, checksum, status in rows:
            expected = by_id[file_id]
            if (
                user_id,
                size_bytes,
                checksum,
                status,
            ) != (
                expected["userId"],
                expected["sizeBytes"],
                expected["sha256"],
                expected["status"],
            ):
                raise BackupError(f"restored database file metadata mismatch: {file_id}")
            path = (storage_root / expected["relativePath"]).resolve()
            if storage_root not in path.parents:
                raise BackupError(f"manifest path escapes restore root: {path}")
            connection.execute(
                "UPDATE user_files SET storage_path = ? WHERE id = ?",
                (str(path), file_id),
            )
        connection.commit()


def restore_and_verify(
    backup_dir: str | Path,
    restore_db: str | Path,
    restore_storage: str | Path,
) -> dict[str, Any]:
    """Restore a backup into an isolated target and verify the joint result."""

    backup = _resolve(backup_dir)
    database_source = backup / DATABASE_NAME
    storage_target = _resolve(restore_storage)
    database_target = _resolve(restore_db)
    if not database_source.is_file():
        raise BackupError("backup database is missing")
    manifest = _load_manifest(backup)
    expected_database = manifest.get("database")
    if not isinstance(expected_database, dict):
        raise BackupError("backup database manifest is missing")
    source_size, source_sha256 = _hash_file(database_source)
    if (source_size, source_sha256) != (
        expected_database.get("sizeBytes"),
        expected_database.get("sha256"),
    ):
        raise BackupError("backup database checksum mismatch")
    source_summary = _database_summary(database_source)
    for key in ("integrityCheck", "foreignKeyViolations", "tableCounts", "tableFingerprints"):
        if source_summary[key] != expected_database.get(key):
            raise BackupError(f"backup database {key} does not match manifest")

    files = manifest["files"]
    _validate_file_manifest(files)
    files_source = backup / "files"
    actual_backup_paths = {
        _relative_path(files_source, path): path for path in _iter_files(files_source)
    } if files_source.exists() else {}
    expected_paths = {item["relativePath"] for item in files}
    if actual_backup_paths.keys() != expected_paths:
        raise BackupError("backup file tree does not match manifest")
    for item in files:
        path = actual_backup_paths[item["relativePath"]]
        if _hash_file(path) != (item["sizeBytes"], item["sha256"]):
            raise BackupError(f"backup file checksum mismatch: {item['relativePath']}")

    storage_target.parent.mkdir(parents=True, exist_ok=True)
    with storage_lock(storage_target):
        database_target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{database_target.name}.", suffix=".restore", dir=database_target.parent
        )
        os.close(fd)
        temporary_database = Path(temporary_name)
        try:
            _sqlite_backup(database_source, temporary_database)
            os.replace(temporary_database, database_target)
        finally:
            temporary_database.unlink(missing_ok=True)
        _clear_directory(storage_target)
        for item in files:
            source_path = actual_backup_paths[item["relativePath"]]
            target_path = storage_target / Path(item["relativePath"])
            target_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(target_path.parent, 0o700)
            shutil.copyfile(source_path, target_path)
            os.chmod(target_path, 0o600)
        _rebase_storage_paths(database_target, storage_target, files)

    restored_summary = _database_summary(database_target)
    if restored_summary["integrityCheck"] != "ok":
        raise BackupError("restored database integrity check failed")
    if restored_summary["foreignKeyViolations"] != 0:
        raise BackupError("restored database has foreign-key violations")
    for key in ("tableCounts", "tableFingerprints"):
        if restored_summary[key] != expected_database.get(key):
            raise BackupError(f"restored database {key} does not match backup")
    restored_paths = {
        _relative_path(storage_target, path): path for path in _iter_files(storage_target)
    }
    if restored_paths.keys() != expected_paths:
        raise BackupError("restored file tree does not match backup")
    for item in files:
        if _hash_file(restored_paths[item["relativePath"]]) != (
            item["sizeBytes"],
            item["sha256"],
        ):
            raise BackupError(f"restored file checksum mismatch: {item['relativePath']}")
    restored_rows = _user_file_rows(database_target)
    by_id = _validate_file_manifest(files)
    if set(restored_rows) != set(by_id):
        raise BackupError("restored user file records do not match backup")
    for file_id, row in restored_rows.items():
        expected = by_id[file_id]
        if (
            row["userId"],
            row["sizeBytes"],
            row["sha256"],
            row["status"],
        ) != (
            expected["userId"],
            expected["sizeBytes"],
            expected["sha256"],
            expected["status"],
        ):
            raise BackupError(f"restored user file metadata mismatch: {file_id}")
        expected_path = (storage_target / expected["relativePath"]).resolve()
        if _resolve(row["storagePath"]) != expected_path:
            raise BackupError(f"restored storage path mismatch: {file_id}")

    return {
        "status": "ok",
        "database": {
            "sourceSha256": source_sha256,
            "restoredSha256": restored_summary["sha256"],
            "integrityCheck": restored_summary["integrityCheck"],
            "tableCounts": restored_summary["tableCounts"],
        },
        "fileCount": len(files),
        "filesSha256Verified": True,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--database", required=True)
    create.add_argument("--storage", required=True)
    create.add_argument("--destination", required=True)
    restore = subparsers.add_parser("restore")
    restore.add_argument("--backup", required=True)
    restore.add_argument("--database", required=True)
    restore.add_argument("--storage", required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    try:
        if args.command == "create":
            manifest = create_backup(args.database, args.storage, args.destination)
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "fileCount": len(manifest["files"]),
                        "databaseSha256": manifest["database"]["sha256"],
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(
                json.dumps(
                    restore_and_verify(args.backup, args.database, args.storage),
                    ensure_ascii=False,
                )
            )
    except (BackupError, OSError, sqlite3.Error) as error:
        print(f"backup/restore failed: {error}", file=__import__("sys").stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
