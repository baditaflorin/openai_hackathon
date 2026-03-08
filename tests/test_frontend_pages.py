from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


def reset_clipmato_modules() -> None:
    for name in list(sys.modules):
        if name == "clipmato" or name.startswith("clipmato."):
            sys.modules.pop(name)


class FrontendPageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        os.environ["CLIPMATO_DATA_DIR"] = self.tempdir.name
        reset_clipmato_modules()

    def write_metadata(self, records: list[dict]) -> Path:
        metadata_path = Path(self.tempdir.name) / "metadata.json"
        metadata_path.write_text(json.dumps(records, indent=2))
        return metadata_path

    def load_client(self) -> TestClient:
        app_module = importlib.import_module("clipmato.web")
        return TestClient(app_module.app)

    def test_dashboard_record_scheduler_render(self) -> None:
        self.write_metadata(
            [
                {
                    "id": "rec-1",
                    "filename": "episode.mp4",
                    "upload_time": "2026-03-08T18:00:00",
                    "transcript": "Transcript text",
                    "titles": ["Episode 1"],
                    "selected_title": "Episode 1",
                    "short_description": "Short description",
                    "long_description": "Long description",
                    "people": ["Alice"],
                    "locations": ["Berlin"],
                    "schedule_time": "2026-03-09T09:00:00",
                    "publish_targets": ["YouTube"],
                    "publish_jobs": {
                        "youtube": {
                            "status": "scheduled",
                            "scheduled_for": "2026-03-09T09:00:00",
                            "privacy_status": "private",
                        }
                    },
                }
            ]
        )
        status_path = Path(self.tempdir.name) / "rec-1.status.json"
        status_path.write_text(json.dumps({"stage": "complete", "progress": 100}))

        client = self.load_client()

        for path in ("/", "/record/rec-1", "/record/rec-1/summary", "/scheduler"):
            response = client.get(path)
            self.assertEqual(response.status_code, 200, path)

    def test_schedule_route_creates_provider_scoped_job(self) -> None:
        metadata_path = self.write_metadata(
            [
                {
                    "id": "rec-2",
                    "filename": "draft.mp4",
                    "upload_time": "2026-03-08T18:00:00",
                    "transcript": "Transcript text",
                    "titles": ["Draft"],
                    "selected_title": "Draft",
                    "short_description": "Short description",
                    "long_description": "Long description",
                    "people": [],
                    "locations": [],
                    "schedule_time": None,
                    "publish_targets": [],
                    "publish_jobs": {},
                }
            ]
        )

        client = self.load_client()
        response = client.post(
            "/record/rec-2/schedule",
            data={
                "schedule_time": "2026-03-10T08:30",
                "publish_targets": "YouTube",
                "youtube_privacy_status": "private",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        records = json.loads(metadata_path.read_text())
        youtube_job = records[0]["publish_jobs"]["youtube"]
        self.assertEqual(youtube_job["provider"], "youtube")
        self.assertEqual(youtube_job["privacy_status"], "private")
        self.assertIn(youtube_job["status"], {"blocked", "pending_connection", "scheduled"})


if __name__ == "__main__":
    unittest.main()
