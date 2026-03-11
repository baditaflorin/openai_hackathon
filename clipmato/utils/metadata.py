"""Thread-safe helpers for Clipmato record metadata."""
from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from contextlib import contextmanager
from typing import Callable, TypeVar

import fcntl

from ..config import METADATA_PATH


metadata_path = METADATA_PATH
metadata_lock_path = metadata_path.with_suffix(f"{metadata_path.suffix}.lock")
logger = logging.getLogger(__name__)
_T = TypeVar("_T")


@dataclass(slots=True)
class _MetadataSnapshot:
    mtime_ns: int | None
    size: int | None
    records: list[dict]


class MetadataCache:
    """Per-process metadata cache invalidated by file size and mtime."""

    def __init__(self) -> None:
        self._snapshot = _MetadataSnapshot(mtime_ns=None, size=None, records=[])

    def _stat_signature(self) -> tuple[int | None, int | None]:
        if not metadata_path.exists():
            return None, None
        stat = metadata_path.stat()
        return stat.st_mtime_ns, stat.st_size

    def _read_from_disk(self) -> list[dict]:
        records = _read_records_unlocked()
        self._snapshot = _MetadataSnapshot(
            mtime_ns=self._stat_signature()[0],
            size=self._stat_signature()[1],
            records=records,
        )
        return records

    def warm(self) -> None:
        """Preload metadata into memory."""
        self.records()

    def records(self) -> list[dict]:
        """Return a detached record list, reloading when the file changed."""
        mtime_ns, size = self._stat_signature()
        if (mtime_ns, size) != (self._snapshot.mtime_ns, self._snapshot.size):
            self._read_from_disk()
        return copy.deepcopy(self._snapshot.records)

    def write_through(self, records: list[dict]) -> None:
        """Update the cache immediately after a successful write."""
        mtime_ns, size = self._stat_signature()
        self._snapshot = _MetadataSnapshot(
            mtime_ns=mtime_ns,
            size=size,
            records=copy.deepcopy(records),
        )


metadata_cache = MetadataCache()


@contextmanager
def _locked_metadata_file():
    """Yield a locked file handle for metadata operations."""
    metadata_lock_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield handle
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _read_records_unlocked() -> list[dict]:
    if not metadata_path.exists():
        return []
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to decode metadata; treating it as empty")
        return []


def _atomic_write_records(records: list[dict]) -> None:
    """Write metadata atomically to prevent corruption."""
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=metadata_path.parent, prefix="metadata_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            json.dump(records, tmp_file, indent=2)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(temp_path, metadata_path)
    except Exception:
        logger.exception("Failed to write metadata atomically")
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


def read_metadata() -> list[dict]:
    """Read the metadata file and return a detached list of records."""
    try:
        return metadata_cache.records()
    except Exception:
        logger.exception("Failed to read metadata; returning empty list")
        return []


def mutate_metadata(mutator: Callable[[list[dict]], _T]) -> _T:
    """Apply a read-modify-write mutation to metadata under a process lock."""
    try:
        with _locked_metadata_file() as handle:
            _ = handle  # lock lifetime only
            records = _read_records_unlocked()
            result = mutator(records)
            _atomic_write_records(records)
            metadata_cache.write_through(records)
            return copy.deepcopy(result)
    except Exception:
        logger.exception("Failed to mutate metadata")
        raise


def append_metadata(record: dict) -> None:
    """Append a new record to the metadata file."""

    def _append(records: list[dict]) -> None:
        records.append(copy.deepcopy(record))

    mutate_metadata(_append)


def update_metadata(record_id: str, updates: dict) -> dict | None:
    """Merge updates into an existing record and return the updated record."""

    def _update(records: list[dict]) -> dict | None:
        for rec in records:
            if rec.get("id") == record_id:
                rec.update(copy.deepcopy(updates))
                return copy.deepcopy(rec)
        return None

    return mutate_metadata(_update)


def get_metadata_record(record_id: str) -> dict | None:
    """Return a detached record by ID, if present."""
    for rec in read_metadata():
        if rec.get("id") == record_id:
            return copy.deepcopy(rec)
    return None


def remove_metadata(record_id: str) -> dict | None:
    """Remove a record from metadata and return it, or None if not found."""

    def _remove(records: list[dict]) -> dict | None:
        for index, rec in enumerate(records):
            if rec.get("id") == record_id:
                removed = records.pop(index)
                return copy.deepcopy(removed)
        return None

    return mutate_metadata(_remove)
