from __future__ import annotations

from clipmato.services.record_queries import RecordQueryService


class DummyMetadataService:
    def __init__(self, records):
        self._records = records

    def read(self):
        return list(self._records)


class DummyProgressService:
    def enrich(self, records):
        enriched = []
        for record in records:
            item = dict(record)
            item.setdefault("progress", 100)
            item.setdefault("stage", "complete")
            enriched.append(item)
        return enriched


def test_record_query_service_sorts_recent_records_descending():
    service = RecordQueryService()
    metadata = DummyMetadataService(
        [
            {"id": "rec-1", "filename": "one.wav", "upload_time": "2026-04-01T10:00:00"},
            {"id": "rec-2", "filename": "two.wav", "upload_time": "2026-04-03T10:00:00"},
        ]
    )
    progress = DummyProgressService()

    records = service.list_recent_records(metadata, progress)

    assert [record["id"] for record in records] == ["rec-2", "rec-1"]
    assert records[0]["display_title"] == "two.wav"


def test_record_query_service_sorts_scheduler_records_by_schedule_then_upload():
    service = RecordQueryService()
    metadata = DummyMetadataService(
        [
            {
                "id": "rec-1",
                "filename": "one.wav",
                "upload_time": "2026-04-02T10:00:00",
                "schedule_time": "2026-04-04T09:00:00",
            },
            {
                "id": "rec-2",
                "filename": "two.wav",
                "upload_time": "2026-04-01T10:00:00",
            },
        ]
    )
    progress = DummyProgressService()

    records = service.list_schedule_records(metadata, progress)

    assert [record["id"] for record in records] == ["rec-2", "rec-1"]


def test_record_query_service_builds_public_detail_payload():
    service = RecordQueryService()
    payload = service.build_public_detail_payload(
        {
            "id": "rec-1",
            "filename": "episode.mp4",
            "display_title": "Episode",
            "upload_time": "2026-04-01T10:00:00",
            "progress": 100,
            "stage": "complete",
            "titles": ["Episode"],
            "people": ["Alice"],
            "locations": ["Berlin"],
            "publish_targets": ["YouTube"],
            "publish_jobs": {"youtube": {"status": "scheduled"}},
            "prompt_runs": {"title_suggestion": {"run_id": "run-1"}},
        }
    )

    assert payload["detail_url"] == "/api/v1/record/rec-1"
    assert payload["titles"] == ["Episode"]
    assert payload["people"] == ["Alice"]
    assert payload["publish_jobs"]["youtube"]["status"] == "scheduled"
