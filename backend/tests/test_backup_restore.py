import sqlite3
import threading
import time
from pathlib import Path

import pytest

from app.modules.personal.storage import storage_lock
from scripts.backup_restore import BackupError, create_backup, restore_and_verify


def create_fixture_database(database: Path, storage_root: Path) -> tuple[str, Path]:
    user_id = "user-backup-1"
    file_id = "file-backup-1"
    file_path = storage_root / user_id / f"{file_id}.bin"
    file_path.parent.mkdir(parents=True)
    file_path.write_bytes(b"private backup content")
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                account_number TEXT NOT NULL
            );
            CREATE TABLE user_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL
            );
            CREATE TABLE user_files (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                checksum TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                deleted_at TEXT
            );
            """
        )
        import hashlib

        checksum = hashlib.sha256(file_path.read_bytes()).hexdigest()
        connection.execute(
            "INSERT INTO users (id, account_number) VALUES (?, ?)",
            (user_id, "9001"),
        )
        connection.execute(
            "INSERT INTO user_sessions (id, user_id, token_hash) VALUES (?, ?, ?)",
            ("session-backup-1", user_id, "session-hash"),
        )
        connection.execute(
            """
            INSERT INTO user_files
              (id, user_id, filename, content_type, size_bytes, checksum,
               storage_path, status, created_at, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file_id,
                user_id,
                "notes.txt",
                "text/plain",
                file_path.stat().st_size,
                checksum,
                str(file_path),
                "active",
                "2026-11-13T00:00:00",
                None,
            ),
        )
    return file_id, file_path


def test_joint_backup_and_isolated_restore_preserves_records_and_content(tmp_path: Path):
    source_db = tmp_path / "source" / "assistant.db"
    source_storage = tmp_path / "source" / "user-files"
    source_db.parent.mkdir()
    file_id, source_file = create_fixture_database(source_db, source_storage)

    backup_dir = tmp_path / "backup"
    manifest = create_backup(source_db, source_storage, backup_dir)
    assert len(manifest["files"]) == 1
    assert manifest["files"][0]["id"] == file_id
    assert (backup_dir / "manifest.json").is_file()
    assert (backup_dir / "manifest.sha256").is_file()

    restored_db = tmp_path / "restored" / "assistant.db"
    restored_storage = tmp_path / "restored" / "user-files"
    result = restore_and_verify(backup_dir, restored_db, restored_storage)

    assert result["status"] == "ok"
    assert result["fileCount"] == 1
    restored_file = restored_storage / "user-backup-1" / "file-backup-1.bin"
    assert restored_file.read_bytes() == source_file.read_bytes()
    with sqlite3.connect(restored_db) as connection:
        assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM user_sessions").fetchone()[0] == 1
        restored_path = connection.execute(
            "SELECT storage_path FROM user_files WHERE id = ?", (file_id,)
        ).fetchone()[0]
    assert Path(restored_path).resolve() == restored_file.resolve()


def test_backup_rejects_database_storage_mismatch(tmp_path: Path):
    source_db = tmp_path / "assistant.db"
    source_storage = tmp_path / "user-files"
    _, source_file = create_fixture_database(source_db, source_storage)
    source_file.parent.mkdir(exist_ok=True)
    (source_file.parent / "orphan.bin").write_bytes(b"untracked")

    with pytest.raises(BackupError, match="database and storage disagree"):
        create_backup(source_db, source_storage, tmp_path / "backup")


def test_restore_rejects_tampered_file_checksum(tmp_path: Path):
    source_db = tmp_path / "assistant.db"
    source_storage = tmp_path / "user-files"
    create_fixture_database(source_db, source_storage)
    backup_dir = tmp_path / "backup"
    create_backup(source_db, source_storage, backup_dir)
    (backup_dir / "files" / "user-backup-1" / "file-backup-1.bin").write_bytes(
        b"tampered"
    )

    with pytest.raises(BackupError, match="backup file checksum mismatch"):
        restore_and_verify(
            backup_dir,
            tmp_path / "restored.db",
            tmp_path / "restored-files",
        )


def test_backup_waits_for_upload_storage_lock(tmp_path: Path):
    source_db = tmp_path / "assistant.db"
    source_storage = tmp_path / "user-files"
    create_fixture_database(source_db, source_storage)
    backup_dir = tmp_path / "backup"
    locked = threading.Event()
    release = threading.Event()

    def hold_writer_lock() -> None:
        with storage_lock(source_storage):
            locked.set()
            release.wait(timeout=5)

    holder = threading.Thread(target=hold_writer_lock)
    holder.start()
    assert locked.wait(timeout=5)

    result: list[object] = []

    def run_backup() -> None:
        try:
            result.append(create_backup(source_db, source_storage, backup_dir))
        except Exception as error:  # pragma: no cover - assertion below reports it
            result.append(error)

    worker = threading.Thread(target=run_backup)
    worker.start()
    time.sleep(0.1)
    assert worker.is_alive()
    release.set()
    holder.join(timeout=5)
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert len(result) == 1
    assert not isinstance(result[0], Exception)
