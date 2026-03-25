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
        os.environ["CLIPMATO_CONTENT_BACKEND"] = "local"
        reset_clipmato_modules()

    def write_metadata(self, records: list[dict]) -> Path:
        metadata_path = Path(self.tempdir.name) / "metadata.json"
        metadata_path.write_text(json.dumps(records, indent=2))
        return metadata_path

    def write_project_presets(self, presets: list[dict]) -> Path:
        presets_path = Path(self.tempdir.name) / "project_presets.json"
        presets_path.write_text(json.dumps(presets, indent=2))
        return presets_path

    def load_client(self) -> TestClient:
        app_module = importlib.import_module("clipmato.web")
        return TestClient(app_module.app)

    def test_dashboard_record_scheduler_render(self) -> None:
        self.write_project_presets(
            [
                {
                    "id": "preset-osm",
                    "label": "OpenStreetMap",
                    "project_name": "OpenStreetMap Deep Dives",
                    "project_summary": "Contributor stories and mapping workflows.",
                    "project_topics": ["mapping", "civic data"],
                    "project_prompt_prefix": "Keep the framing practical.",
                    "project_prompt_suffix": "Close with a contributor takeaway.",
                }
            ]
        )
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
                    "project_context": {
                        "project_name": "OpenStreetMap Deep Dives",
                        "project_summary": "Contributor stories and mapping workflows.",
                        "project_topics": ["mapping", "civic data"],
                        "project_prompt_prefix": "Keep the framing practical.",
                        "project_prompt_suffix": "Close with a contributor takeaway.",
                    },
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

        for path in ("/", "/record/rec-1", "/record/rec-1/summary", "/scheduler", "/settings"):
            response = client.get(path)
            self.assertEqual(response.status_code, 200, path)
        self.assertIn('Saved presets', client.get("/").text)
        self.assertIn("Browser recording works best on", client.get("/").text)
        self.assertIn("OpenStreetMap Deep Dives", client.get("/").text)
        self.assertIn("Topics: mapping, civic data", client.get("/record/rec-1").text)
        scheduler_page = client.get("/scheduler").text
        self.assertIn("Preview schedule", scheduler_page)
        self.assertIn("Live apply schedule", scheduler_page)

    def test_dashboard_empty_state_still_renders_records_container(self) -> None:
        client = self.load_client()

        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="dashboard_empty_state"', response.text)
        self.assertIn('id="records_container"', response.text)

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

    def test_settings_routes_persist_runtime_and_secrets(self) -> None:
        client = self.load_client()

        response = client.post(
            "/settings/runtime",
            data={
                "transcription_backend": "local-whisper",
                "content_backend": "ollama",
                "local_whisper_model": "small",
                "local_whisper_device": "mps",
                "ollama_base_url": "http://ollama.internal:11434",
                "ollama_model": "llama3.2:3b",
                "ollama_timeout_seconds": "95",
                "public_base_url": "https://clipmato.example.com",
                "openai_content_model": "gpt-4.1-mini",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

        response = client.post(
            "/settings/credentials/openai",
            data={"openai_api_key": "sk-test-value"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

        response = client.post(
            "/settings/credentials/google",
            data={
                "google_client_id": "google-client-id",
                "google_client_secret": "google-client-secret",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

        settings_payload = json.loads((Path(self.tempdir.name) / "settings.json").read_text())
        self.assertEqual(settings_payload["transcription_backend"], "local-whisper")
        self.assertEqual(settings_payload["content_backend"], "ollama")
        self.assertEqual(settings_payload["local_whisper_device"], "mps")
        self.assertEqual(settings_payload["ollama_timeout_seconds"], 95)
        self.assertEqual(settings_payload["public_base_url"], "https://clipmato.example.com")

        secrets_payload = json.loads((Path(self.tempdir.name) / "secrets.json").read_text())
        self.assertEqual(secrets_payload["openai_api_key"], "sk-test-value")
        self.assertEqual(secrets_payload["google_client_id"], "google-client-id")
        self.assertEqual(secrets_payload["google_client_secret"], "google-client-secret")

    def test_settings_page_supports_live_prompt_apply(self) -> None:
        prompts_module = importlib.import_module("clipmato.prompts")
        release_state_path = Path(self.tempdir.name) / "prompt_release_state.json"

        for index in range(2):
            prompts_module.run_prompt_task_sync(
                "title_suggestion",
                {"transcript": f"Transcript {index}"},
                fallback_output=["One", "Two", "Three", "Four", "Five"],
                record_id=f"rec-live-ui-{index}",
                prompt_version="v1-format-tight",
            )

        client = self.load_client()
        settings_page = client.get("/settings")
        self.assertEqual(settings_page.status_code, 200)
        self.assertIn("Live apply", settings_page.text)

        response = client.post(
            "/settings/prompt-release/title_suggestion/apply",
            data={
                "prompt_version": "v1-format-tight",
                "suite_version": "quality-v1",
                "actor": "release-bot",
                "notes": "Promote after benchmark pass.",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertIn("notice=", response.headers["location"])
        release_state = json.loads(release_state_path.read_text())
        self.assertEqual(release_state["live_defaults"]["title_suggestion"], "v1-format-tight")

    def test_local_offline_profile_route_persists_local_runtime_defaults(self) -> None:
        client = self.load_client()

        response = client.post(
            "/settings/runtime/profile/local-offline",
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

        settings_payload = json.loads((Path(self.tempdir.name) / "settings.json").read_text())
        self.assertEqual(settings_payload["transcription_backend"], "local-whisper")
        self.assertEqual(settings_payload["content_backend"], "ollama")
        self.assertEqual(settings_payload["ollama_model"], "mistral-nemo:12b-instruct-2407-q3_K_S")
        self.assertEqual(settings_payload["ollama_timeout_seconds"], 120)

    def test_saved_public_base_url_is_used_for_oauth_callback(self) -> None:
        settings_path = Path(self.tempdir.name) / "settings.json"
        settings_path.write_text(json.dumps({"public_base_url": "https://clipmato.example.com"}, indent=2))

        app_module = importlib.import_module("clipmato.web")
        dependencies_module = importlib.import_module("clipmato.dependencies")

        class DummyYoutube:
            def __init__(self) -> None:
                self.redirect_uri = None

            def begin_authorization(self, redirect_uri: str) -> str:
                self.redirect_uri = redirect_uri
                return "https://accounts.example.test/oauth"

        class DummyPublishingService:
            def __init__(self) -> None:
                self.youtube = DummyYoutube()

            def get_provider_status(self, provider_key: str, redirect_uri: str | None = None) -> dict:
                return {
                    "provider": provider_key,
                    "available": True,
                    "configured": True,
                    "connected": False,
                    "message": "",
                    "redirect_uri": redirect_uri,
                }

        dummy_publishing = DummyPublishingService()
        app_module.app.dependency_overrides[dependencies_module.get_publishing_service] = lambda: dummy_publishing
        self.addCleanup(app_module.app.dependency_overrides.clear)

        client = TestClient(app_module.app)
        response = client.get("/auth/youtube/connect", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(dummy_publishing.youtube.redirect_uri, "https://clipmato.example.com/auth/youtube/callback")


if __name__ == "__main__":
    unittest.main()
