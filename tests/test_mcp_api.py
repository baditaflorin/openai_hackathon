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


class MCPApiTests(unittest.TestCase):
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

    def test_capabilities_and_resource_listing_render(self) -> None:
        client = self.load_client()

        response = client.get(
            "/api/v1/mcp/capabilities",
            params=[("scopes", "runtime"), ("features", "dry_run")],
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["supported_schema_version"], "1.0")
        self.assertIn("runtime.settings.update", {tool["name"] for tool in payload["tools"]})

        resources = client.get("/api/v1/mcp/resources")
        self.assertEqual(resources.status_code, 200)
        self.assertIn("runtime.summary", {resource["name"] for resource in resources.json()["resources"]})

    def test_runtime_settings_dry_run_does_not_persist(self) -> None:
        client = self.load_client()

        response = client.post(
            "/api/v1/mcp/tools/runtime.settings.update/invoke",
            json={
                "mode": "dry_run",
                "input": {"updates": {"content_backend": "ollama", "ollama_model": "qwen3:4b"}},
            },
            headers={"X-Client-Id": "mcp-test"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["tool_result"]["dry_run"])
        self.assertFalse((Path(self.tempdir.name) / "settings.json").exists())

    def test_runtime_settings_live_apply_is_idempotent(self) -> None:
        client = self.load_client()
        request_json = {
            "mode": "live_apply",
            "input": {"updates": {"content_backend": "ollama", "ollama_model": "qwen3:4b"}},
        }

        first = client.post(
            "/api/v1/mcp/tools/runtime.settings.update/invoke",
            json=request_json,
            headers={"X-Client-Id": "mcp-test", "Idempotency-Key": "mcp-1"},
        )
        second = client.post(
            "/api/v1/mcp/tools/runtime.settings.update/invoke",
            json=request_json,
            headers={"X-Client-Id": "mcp-test", "Idempotency-Key": "mcp-1"},
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["run_id"], second.json()["run_id"])
        self.assertEqual(second.headers["X-Idempotency-Replayed"], "true")

        settings_payload = json.loads((Path(self.tempdir.name) / "settings.json").read_text())
        self.assertEqual(settings_payload["content_backend"], "ollama")
        self.assertEqual(settings_payload["ollama_model"], "qwen3:4b")

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
            json={"mode": "live_apply", "input": {"record_id": "rec-1"}},
            headers={"X-Client-Id": "mcp-test"},
        )

        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertEqual(body["error"]["code"], "approval_required")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
