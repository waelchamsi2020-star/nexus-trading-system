"""Cross-process lease that prevents two NEXUS send authorities at once."""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Self


class ExecutionAuthorityBusy(RuntimeError):
    """Another process currently owns the broker-send authority."""


class ExecutionAuthorityLease:
    """OS-managed exclusive lock; the OS releases it automatically on exit/crash."""

    def __init__(self, path: str | Path, *, owner: str):
        self.path = Path(path)
        self.owner = str(owner)
        self.file = None

    def acquire(self) -> ExecutionAuthorityLease:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open("a+b")
        try:
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b" ")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            stream.close()
            raise ExecutionAuthorityBusy("Another process owns NEXUS execution authority") from exc
        stream.seek(0)
        stream.truncate()
        stream.write(json.dumps({"pid": os.getpid(), "owner": self.owner}).encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
        self.file = stream
        return self

    def release(self) -> None:
        stream, self.file = self.file, None
        if stream is None:
            return
        try:
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()

    def __enter__(self) -> Self:
        return self.acquire()

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()


def authority_lock_path(data_dir: str | Path) -> Path:
    """Stable shared path for desktop and demo_live processes using one profile."""
    return Path(data_dir) / "execution-authority.lock"


def isolated_test_lock_path() -> Path:
    """Unique path for in-memory test stores, which have no shared profile."""
    return Path(tempfile.gettempdir()) / f"nexus-test-authority-{os.getpid()}-{uuid.uuid4().hex}.lock"
