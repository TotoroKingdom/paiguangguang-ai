"""Cross-process coordination for the user-file storage tree."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def storage_lock(storage_root: str | Path) -> Iterator[None]:
    """Serialize file writes/deletes with backup snapshots.

    The lock file lives next to the storage directory so it is not included in
    the user-file manifest.  POSIX deployments use ``flock``; Windows test
    runs use the equivalent one-byte ``msvcrt`` lock.
    """

    root = Path(storage_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root.parent / f".{root.name}.backup.lock"
    with lock_path.open("a+b") as handle:
        # The deployment backup helper may run as root while the API runs as
        # the unprivileged ``app`` user.  The lock carries no data, so it can
        # be shared by both identities.
        os.chmod(lock_path, 0o666)
        if os.name == "nt":
            import msvcrt

            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
