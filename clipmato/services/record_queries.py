"""Reusable record query helpers for HTML and API entrypoints."""
from __future__ import annotations

from typing import Any

from ..utils.presentation import present_record


class RecordQueryService:
    """Build shared record views for route and API adapters."""

    def list_records(self, metadata_svc, progress_svc) -> list[dict[str, Any]]:
        """Return all records enriched with derived presentation fields."""
        return [present_record(record) for record in progress_svc.enrich(metadata_svc.read())]

    def list_recent_records(self, metadata_svc, progress_svc) -> list[dict[str, Any]]:
        """Return records sorted by upload time descending."""
        records = self.list_records(metadata_svc, progress_svc)
        records.sort(key=lambda record: record.get("upload_time", ""), reverse=True)
        return records

    def list_schedule_records(self, metadata_svc, progress_svc) -> list[dict[str, Any]]:
        """Return records sorted for scheduler-style views."""
        records = self.list_records(metadata_svc, progress_svc)
        records.sort(key=lambda record: record.get("schedule_time") or record.get("upload_time", ""))
        return records

    def find_record(self, records: list[dict[str, Any]], record_id: str) -> dict[str, Any] | None:
        """Return one record from a preloaded record list."""
        return next((record for record in records if record.get("id") == record_id), None)

    def get_record(self, metadata_svc, progress_svc, record_id: str) -> dict[str, Any] | None:
        """Return one enriched record by ID."""
        return self.find_record(self.list_records(metadata_svc, progress_svc), record_id)

    def build_summary_payload(self, record: dict[str, Any], *, detail_url_base: str) -> dict[str, Any]:
        """Return a compact summary payload for HTML or JSON clients."""
        return {
            "id": record["id"],
            "filename": record.get("filename"),
            "display_title": record.get("display_title") or record.get("filename") or "Untitled episode",
            "display_title_helper": record.get("display_title_helper"),
            "display_subtitle_helper": record.get("display_subtitle_helper"),
            "upload_time": record.get("upload_time"),
            "progress": float(record.get("progress", 0)),
            "stage": str(record.get("stage", "pending")),
            "message": record.get("message"),
            "error": record.get("error"),
            "schedule_time": record.get("schedule_time"),
            "youtube_job": record.get("youtube_job"),
            "detail_url": f"{detail_url_base}/{record['id']}",
        }

    def build_public_detail_payload(self, record: dict[str, Any]) -> dict[str, Any]:
        """Return the versioned public API detail payload for one record."""
        payload = self.build_summary_payload(record, detail_url_base="/api/v1/record")
        payload.update(
            {
                "selected_title": record.get("selected_title"),
                "titles": list(record.get("titles") or []),
                "short_description": record.get("short_description"),
                "long_description": record.get("long_description"),
                "people": list(record.get("people") or []),
                "locations": list(record.get("locations") or []),
                "script": record.get("script"),
                "distribution": record.get("distribution"),
                "project_context": record.get("project_context"),
                "publish_targets": list(record.get("publish_targets") or []),
                "publish_jobs": dict(record.get("publish_jobs") or {}),
                "prompt_runs": dict(record.get("prompt_runs") or {}),
            }
        )
        return payload
