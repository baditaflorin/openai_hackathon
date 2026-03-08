"""Thread-safe helpers for Clipmato record metadata."""
from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
from contextlib import contextmanager
from typing import Callable, TypeVar

import fcntl

from ..config import METADATA_PATH


metadata_path = METADATA_PATH
logger = logging.getLogger(__name__)
_T = TypeVar("_T")


@contextmanager
def _locked_metadata_file():
    """Yield a locked file handle for metadata operations."""
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.seek(0)
        try:
            yield handle
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _read_records_from_handle(handle) -> list[dict]:
    handle.seek(0)
    raw = handle.read().strip()
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
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
    if not metadata_path.exists():
        return []
    try:
        with metadata_path.open("r", encoding="utf-8") as handle:
            return copy.deepcopy(json.load(handle))
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to read metadata; returning empty list")
        return []


def mutate_metadata(mutator: Callable[[list[dict]], _T]) -> _T:
    """Apply a read-modify-write mutation to metadata under a process lock."""
    try:
        with _locked_metadata_file() as handle:
            records = _read_records_from_handle(handle)
            result = mutator(records)
            _atomic_write_records(records)
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
