import json
import threading
from pathlib import Path

import pytest

from clipmato import config
from clipmato.utils import metadata


@pytest.fixture(autouse=True)
def temp_metadata_file(tmp_path, monkeypatch):
    path = Path(tmp_path / "metadata.json")
    monkeypatch.setattr(config, "METADATA_PATH", path, raising=False)
    monkeypatch.setattr(metadata, "metadata_path", path, raising=False)
    return path


def test_concurrent_appends_produce_valid_json(temp_metadata_file):
    barrier = threading.Barrier(5)
    threads = []

    def worker(idx: int):
        barrier.wait()
        metadata.append_metadata({"id": f"item-{idx}", "value": idx})

    for i in range(5):
        thread = threading.Thread(target=worker, args=(i,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    with temp_metadata_file.open() as fh:
        records = json.load(fh)

    assert len(records) == 5
    assert {rec["id"] for rec in records} == {f"item-{i}" for i in range(5)}


def test_concurrent_writes_keep_json_valid(temp_metadata_file):
    initial_records = [
        {"id": "keep", "value": 1},
        {"id": "update", "value": 2},
        {"id": "remove", "value": 3},
    ]
    temp_metadata_file.write_text(json.dumps(initial_records, indent=2))

    barrier = threading.Barrier(4)
    threads = []

    def append_worker():
        barrier.wait()
        metadata.append_metadata({"id": "new", "value": 99})

    def update_worker():
        barrier.wait()
        metadata.update_metadata("update", {"value": 200})

    def remove_worker():
        barrier.wait()
        metadata.remove_metadata("remove")

    def another_append():
        barrier.wait()
        metadata.append_metadata({"id": "extra", "value": 42})

    for target in (append_worker, update_worker, remove_worker, another_append):
        thread = threading.Thread(target=target)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    with temp_metadata_file.open() as fh:
        records = json.load(fh)

    ids = {rec["id"] for rec in records}
    assert ids == {"keep", "update", "new", "extra"}
    assert next(rec for rec in records if rec["id"] == "update")["value"] == 200
