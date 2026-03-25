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


class ApiV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        os.environ["CLIPMATO_DATA_DIR"] = self.tempdir.name
        reset_clipmato_modules()

    def load_client(self) -> TestClient:
        app_module = importlib.import_module("clipmato.web")
        return TestClient(app_module.app)

    def write_metadata(self, records: list[dict]) -> None:
        (Path(self.tempdir.name) / "metadata.json").write_text(json.dumps(records, indent=2))

    def test_runtime_live_apply_persists_settings_and_events(self) -> None:
        client = self.load_client()

        response = client.patch(
            "/api/v1/runtime/live-apply",
            json={
                "content_backend": "ollama",
                "ollama_base_url": "http://ollama.internal:11434",
                "ollama_model": "qwen3:4b",
                "ollama_timeout_seconds": 90,
            },
            headers={"X-Client-Id": "integration-test"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["X-Correlation-ID"])
        payload = response.json()
        self.assertEqual(payload["data"]["tool_result"]["tool_name"], "runtime.settings.update")
        self.assertEqual(payload["data"]["agent_run"]["state"], "completed")

        settings_payload = json.loads((Path(self.tempdir.name) / "settings.json").read_text())
        self.assertEqual(settings_payload["content_backend"], "ollama")
        self.assertEqual(settings_payload["ollama_model"], "qwen3:4b")

        events = client.get("/api/v1/events").json()["data"]["events"]
        self.assertEqual(events[0]["type"], "runtime.settings.updated")

    def test_mcp_tool_dry_run_does_not_persist_settings(self) -> None:
        client = self.load_client()

        response = client.post(
            "/api/v1/mcp/tools/runtime.settings.update/invoke",
            json={
                "mode": "dry_run",
                "input": {
                    "updates": {
                        "content_backend": "openai",
                        "openai_content_model": "gpt-4.1-mini",
                    }
                },
            },
            headers={"X-Client-Id": "integration-test"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertTrue(payload["tool_result"]["dry_run"])
        self.assertFalse((Path(self.tempdir.name) / "settings.json").exists())

    def test_publish_tool_requires_approval(self) -> None:
        self.write_metadata(
            [
                {
                    "id": "rec-1",
                    "filename": "episode.mp4",
                    "upload_time": "2026-03-25T10:00:00+00:00",
                    "publish_targets": [],
                    "publish_jobs": {},
                }
            ]
        )
        client = self.load_client()

        response = client.post(
            "/api/v1/mcp/tools/publish.record/invoke",
            json={
                "mode": "live_apply",
                "input": {"record_id": "rec-1"},
            },
            headers={"X-Client-Id": "integration-test"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "approval_required")

    def test_capabilities_run_lookup_and_sse_backlog(self) -> None:
        client = self.load_client()

        capabilities = client.get(
            "/api/v1/mcp/capabilities",
            params=[("scopes", "runtime"), ("features", "dry_run")],
        )
        self.assertEqual(capabilities.status_code, 200)
        self.assertEqual(capabilities.json()["data"]["supported_schema_version"], "1.0")

        invoke = client.post(
            "/api/v1/mcp/tools/runtime.profile.apply/invoke",
            json={
                "mode": "live_apply",
                "input": {"profile": "local-offline"},
            },
            headers={"X-Client-Id": "integration-test"},
        )
        self.assertEqual(invoke.status_code, 200)
        run_id = invoke.json()["data"]["run_id"]

        run_lookup = client.get(f"/api/v1/agent-runs/{run_id}")
        self.assertEqual(run_lookup.status_code, 200)
        self.assertEqual(run_lookup.json()["data"]["state"], "completed")

        with client.stream("GET", "/api/v1/events/stream?aggregate_id=runtime-settings&replay_only=true") as stream:
            self.assertEqual(stream.status_code, 200)
            first_chunk = next(stream.iter_text())

        self.assertIn("runtime.profile.applied", first_chunk)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
