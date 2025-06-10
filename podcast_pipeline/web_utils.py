import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
uploads_dir = BASE_DIR / "uploads"
metadata_path = uploads_dir / "metadata.json"

def read_metadata() -> list[dict]:
    """
    Read the metadata.json file and return the list of processed records.
    """
    if metadata_path.exists():
        return json.loads(metadata_path.read_text())
    return []

def append_metadata(record: dict) -> None:
    """
    Append a new record to the metadata.json file.
    """
    records = read_metadata()
    records.append(record)
    metadata_path.write_text(json.dumps(records, indent=2))

def update_metadata(record_id: str, updates: dict) -> None:
    """
    Update an existing record in metadata.json by merging in new fields.
    """
    records = read_metadata()
    for rec in records:
        if rec.get("id") == record_id:
            rec.update(updates)
            break
    metadata_path.write_text(json.dumps(records, indent=2))

def remove_metadata(record_id: str) -> dict | None:
    """
    Remove a record from metadata.json and return the removed record, or None if not found.
    """
    records = read_metadata()
    removed = None
    new_records = []
    for rec in records:
        if rec.get("id") == record_id:
            removed = rec
        else:
            new_records.append(rec)
    if removed:
        metadata_path.write_text(json.dumps(new_records, indent=2))
    return removed