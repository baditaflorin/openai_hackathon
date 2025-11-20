import json
import logging
import os
import tempfile
from contextlib import contextmanager

import fcntl

from ..config import METADATA_PATH

# File where metadata records are stored
metadata_path = METADATA_PATH
logger = logging.getLogger(__name__)


@contextmanager
def _locked_metadata_file():
    """Yield a locked file handle for metadata operations."""
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.seek(0)
        try:
            yield fh
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _atomic_write_records(records: list[dict]) -> None:
    """Write records to metadata file atomically to prevent corruption."""
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=metadata_path.parent, prefix="metadata_", suffix=".json")
    try:
        with os.fdopen(fd, "w") as tmp_file:
            json.dump(records, tmp_file, indent=2)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
        os.replace(temp_path, metadata_path)
    except Exception:
        logger.exception("Failed to write metadata atomically")
        # Best effort cleanup of the temporary file
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise

def read_metadata() -> list[dict]:
    """
    Read the metadata.json file and return the list of processed records.
    """
    if not metadata_path.exists():
        return []
    try:
        with metadata_path.open("r") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to read metadata; returning empty list")
        return []

def append_metadata(record: dict) -> None:
    """
    Append a new record to the metadata.json file.
    """
    try:
        with _locked_metadata_file():
            records = read_metadata()
            records.append(record)
            _atomic_write_records(records)
    except Exception:
        logger.exception("Failed to append metadata record")
        raise

def update_metadata(record_id: str, updates: dict) -> None:
    """
    Update an existing record in metadata.json by merging in new fields.
    """
    try:
        with _locked_metadata_file():
            records = read_metadata()
            for rec in records:
                if rec.get("id") == record_id:
                    rec.update(updates)
                    break
            _atomic_write_records(records)
    except Exception:
        logger.exception("Failed to update metadata record", extra={"record_id": record_id})
        raise

def remove_metadata(record_id: str) -> dict | None:
    """
    Remove a record from metadata.json and return the removed record, or None if not found.
    """
    try:
        with _locked_metadata_file():
            records = read_metadata()
            removed = None
            new_records = []
            for rec in records:
                if rec.get("id") == record_id:
                    removed = rec
                else:
                    new_records.append(rec)
            if removed:
                _atomic_write_records(new_records)
            return removed
    except Exception:
        logger.exception("Failed to remove metadata record", extra={"record_id": record_id})
        raise