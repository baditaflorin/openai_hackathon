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


class PromptEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        os.environ["CLIPMATO_DATA_DIR"] = self.tempdir.name
        os.environ["CLIPMATO_CONTENT_BACKEND"] = "local"
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("CLIPMATO_PROMPT_TITLE_SUGGESTION_VERSION", None)
        reset_clipmato_modules()

    def write_metadata(self, records: list[dict]) -> Path:
        metadata_path = Path(self.tempdir.name) / "metadata.json"
        metadata_path.write_text(json.dumps(records, indent=2))
        return metadata_path

    def load_client(self) -> TestClient:
        app_module = importlib.import_module("clipmato.web")
        return TestClient(app_module.app)

    def test_local_prompt_task_persists_prompt_run(self) -> None:
        prompts_module = importlib.import_module("clipmato.prompts")
        fallback = ["One", "Two", "Three", "Four", "Five"]

        execution = prompts_module.run_prompt_task_sync(
            "title_suggestion",
            {"transcript": "A focused transcript about workflow automation."},
            fallback_output=fallback,
            record_id="rec-local",
        )

        self.assertEqual(execution.summary["backend"], "local")
        self.assertEqual(execution.summary["prompt_version"], "v1")
        runs = prompts_module.read_prompt_runs(record_id="rec-local", task="title_suggestion")
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["record_id"], "rec-local")
        self.assertEqual(runs[0]["status"], "completed")
        self.assertFalse(runs[0]["used_fallback"])

    def test_prompt_version_override_selects_variant(self) -> None:
        os.environ["CLIPMATO_PROMPT_TITLE_SUGGESTION_VERSION"] = "v1-format-tight"
        registry_module = importlib.import_module("clipmato.prompts.registry")

        version = registry_module.resolve_prompt_version("title_suggestion")

        self.assertEqual(version.version, "v1-format-tight")
        self.assertEqual(version.status, "experimental")

    def test_title_selection_route_records_prompt_evaluation(self) -> None:
        self.write_metadata(
            [
                {
                    "id": "rec-1",
                    "filename": "episode.mp4",
                    "upload_time": "2026-03-08T18:00:00+00:00",
                    "titles": ["Option A", "Option B", "Option C", "Option D", "Option E"],
                    "selected_title": None,
                    "prompt_runs": {
                        "title_suggestion": {
                            "run_id": "run-title-1",
                            "task": "title_suggestion",
                            "prompt_version": "v1",
                            "backend": "local",
                            "model": "local-basic",
                            "status": "completed",
                            "validation_passed": True,
                            "used_fallback": False,
                            "issues": [],
                            "completed_at": "2026-03-08T18:00:05+00:00",
                        }
                    },
                    "publish_jobs": {},
                }
            ]
        )

        client = self.load_client()
        response = client.post(
            "/record/rec-1/title",
            data={"selected_title": "Option B"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        prompts_module = importlib.import_module("clipmato.prompts")
        evaluations = prompts_module.read_prompt_evaluations(record_id="rec-1", task="title_suggestion")
        self.assertEqual(len(evaluations), 1)
        self.assertEqual(evaluations[0]["signal"], "title_selected")
        self.assertEqual(evaluations[0]["value"], "Option B")
        self.assertEqual(evaluations[0]["metadata"]["selected_rank"], 2)

    def test_publish_success_records_prompt_evaluations(self) -> None:
        self.write_metadata(
            [
                {
                    "id": "rec-2",
                    "filename": "episode.mp4",
                    "upload_time": "2026-03-08T18:00:00+00:00",
                    "selected_title": "Published title",
                    "schedule_time": "2026-03-09T09:00:00+00:00",
                    "prompt_runs": {
                        "title_suggestion": {
                            "run_id": "run-title-2",
                            "task": "title_suggestion",
                            "prompt_version": "v1",
                            "backend": "local",
                            "model": "local-basic",
                            "status": "completed",
                            "validation_passed": True,
                            "used_fallback": False,
                            "issues": [],
                            "completed_at": "2026-03-08T18:00:05+00:00",
                        },
                        "description_generation": {
                            "run_id": "run-description-2",
                            "task": "description_generation",
                            "prompt_version": "v1",
                            "backend": "local",
                            "model": "local-basic",
                            "status": "completed",
                            "validation_passed": True,
                            "used_fallback": False,
                            "issues": [],
                            "completed_at": "2026-03-08T18:00:06+00:00",
                        },
                    },
                    "publish_jobs": {
                        "youtube": {
                            "status": "publishing",
                            "provider": "youtube",
                        }
                    },
                }
            ]
        )

        publishing_module = importlib.import_module("clipmato.services.publishing")
        service = publishing_module.PublishingService()
        service._mark_published(
            "rec-2",
            "youtube",
            "video-123",
            "https://youtube.example/video-123",
            {"title": "Published title"},
        )

        prompts_module = importlib.import_module("clipmato.prompts")
        evaluations = prompts_module.read_prompt_evaluations(record_id="rec-2")
        self.assertEqual(len(evaluations), 2)
        tasks = {item["task"] for item in evaluations}
        self.assertEqual(tasks, {"title_suggestion", "description_generation"})
        for evaluation in evaluations:
            self.assertEqual(evaluation["signal"], "record_published")
            self.assertEqual(evaluation["value"], "youtube")


if __name__ == "__main__":
    unittest.main()
