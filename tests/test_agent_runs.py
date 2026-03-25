from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient


def reset_clipmato_modules() -> None:
    for name in list(sys.modules):
        if name == "clipmato" or name.startswith("clipmato."):
            sys.modules.pop(name)


class AgentRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        os.environ["CLIPMATO_DATA_DIR"] = self.tempdir.name
        reset_clipmato_modules()

    def load_client(self) -> TestClient:
        app_module = importlib.import_module("clipmato.web")
        return TestClient(app_module.app)

    def write_metadata(self, records: list[dict]) -> Path:
        metadata_path = Path(self.tempdir.name) / "metadata.json"
        metadata_path.write_text(json.dumps(records, indent=2))
        return metadata_path

    def test_agent_run_rejects_invalid_state_transition(self) -> None:
        agent_runs = importlib.import_module("clipmato.agent_runs")

        service = agent_runs.AgentRunService(
            storage=agent_runs.AgentRunStorage(Path(self.tempdir.name) / "agent_runs")
        )
        run = service.create_run(workflow="unit_test", goal="Exercise transition checks.", dry_run=True)

        with self.assertRaises(agent_runs.AgentRunStateError):
            service.transition_state(run["run_id"], "completed")

    def test_tool_execution_retries_and_persists_trace(self) -> None:
        agent_runs = importlib.import_module("clipmato.agent_runs")

        attempts = {"count": 0}

        async def flaky_tool(payload: dict[str, str]) -> dict[str, str]:
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("temporary failure")
            return {"message": f"hello {payload['name']}"}

        registry = agent_runs.ToolRegistry()
        registry.register(
            agent_runs.ToolDefinition(
                name="flaky_tool",
                description="Retry once then succeed.",
                input_schema={
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                    "required": ["message"],
                    "additionalProperties": False,
                },
                executor=flaky_tool,
                max_attempts=2,
            )
        )
        service = agent_runs.AgentRunService(
            storage=agent_runs.AgentRunStorage(Path(self.tempdir.name) / "agent_runs"),
            registry=registry,
        )
        run = service.create_run(workflow="unit_test", goal="Retry flaky tool.", dry_run=False)
        service.transition_state(run["run_id"], "planning")
        service.transition_state(run["run_id"], "executing")

        result = asyncio.run(
            service.execute_tool(
                run["run_id"],
                "flaky_tool",
                {"name": "Clipmato"},
                step_id="flaky_tool",
                title="Run flaky tool",
            )
        )

        self.assertEqual(result, {"message": "hello Clipmato"})
        persisted = service.get_run(run["run_id"])
        self.assertIsNotNone(persisted)
        assert persisted is not None
        self.assertEqual(len(persisted["tool_calls"]), 2)
        self.assertEqual(persisted["tool_calls"][0]["status"], "failed")
        self.assertEqual(persisted["tool_calls"][1]["status"], "completed")
        self.assertEqual(persisted["steps"][0]["attempts_used"], 2)

    def test_tool_execution_requires_approval_before_high_risk_side_effects(self) -> None:
        agent_runs = importlib.import_module("clipmato.agent_runs")

        called = {"value": False}

        def high_risk_tool(_: dict[str, str]) -> dict[str, str]:
            called["value"] = True
            return {"status": "applied"}

        registry = agent_runs.ToolRegistry()
        registry.register(
            agent_runs.ToolDefinition(
                name="apply_changes",
                description="Pretend to perform a destructive write.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                output_schema={
                    "type": "object",
                    "properties": {"status": {"type": "string"}},
                    "required": ["status"],
                    "additionalProperties": False,
                },
                executor=high_risk_tool,
                risk_level="high",
                approval_policy="required",
            )
        )
        service = agent_runs.AgentRunService(
            storage=agent_runs.AgentRunStorage(Path(self.tempdir.name) / "agent_runs"),
            registry=registry,
        )
        run = service.create_run(workflow="unit_test", goal="Check approval handling.", dry_run=False)
        service.transition_state(run["run_id"], "planning")
        service.transition_state(run["run_id"], "executing")

        with self.assertRaises(agent_runs.ApprovalRequiredError):
            asyncio.run(
                service.execute_tool(
                    run["run_id"],
                    "apply_changes",
                    {},
                    step_id="apply_changes",
                    title="Apply changes",
                )
            )

        persisted = service.get_run(run["run_id"])
        self.assertIsNotNone(persisted)
        assert persisted is not None
        self.assertEqual(persisted["state"], "awaiting_approval")
        self.assertFalse(called["value"])
        self.assertEqual(persisted["steps"][0]["status"], "awaiting_approval")

    def test_scheduler_route_supports_preview_and_live_apply_runs(self) -> None:
        metadata_path = self.write_metadata(
            [
                {
                    "id": "rec-1",
                    "filename": "one.mp4",
                    "upload_time": "2026-03-24T08:00:00",
                    "selected_title": "Episode One",
                    "long_description": "Episode one description",
                    "publish_targets": ["YouTube"],
                    "publish_jobs": {},
                },
                {
                    "id": "rec-2",
                    "filename": "two.mp4",
                    "upload_time": "2026-03-24T09:00:00",
                    "selected_title": "Episode Two",
                    "long_description": "Episode two description",
                    "publish_targets": [],
                    "publish_jobs": {},
                },
            ]
        )
        client = self.load_client()

        preview_response = client.post(
            "/scheduler/auto",
            data={"cadence": "daily", "mode": "dry-run"},
            follow_redirects=False,
        )

        self.assertEqual(preview_response.status_code, 303)
        preview_query = parse_qs(urlparse(preview_response.headers["location"]).query)
        preview_run_id = preview_query["run_id"][0]
        preview_run = client.get(f"/agent-runs/{preview_run_id}")
        self.assertEqual(preview_run.status_code, 200)
        preview_payload = preview_run.json()
        self.assertEqual(preview_payload["state"], "completed")
        self.assertTrue(preview_payload["dry_run"])
        self.assertFalse(preview_payload["final_outcome"]["applied"])
        self.assertEqual(preview_payload["final_outcome"]["entry_count"], 2)

        records_after_preview = json.loads(metadata_path.read_text())
        self.assertTrue(all(not record.get("schedule_time") for record in records_after_preview))

        apply_response = client.post(
            "/scheduler/auto",
            data={"cadence": "daily", "mode": "apply"},
            follow_redirects=False,
        )

        self.assertEqual(apply_response.status_code, 303)
        apply_query = parse_qs(urlparse(apply_response.headers["location"]).query)
        apply_run_id = apply_query["run_id"][0]
        apply_run = client.get(f"/agent-runs/{apply_run_id}")
        self.assertEqual(apply_run.status_code, 200)
        apply_payload = apply_run.json()
        self.assertEqual(apply_payload["state"], "completed")
        self.assertFalse(apply_payload["dry_run"])
        self.assertTrue(apply_payload["final_outcome"]["applied"])
        self.assertEqual(len(apply_payload["final_outcome"]["updated_record_ids"]), 2)
        self.assertIn(
            "apply_schedule_plan",
            [tool_call["tool_name"] for tool_call in apply_payload["tool_calls"]],
        )

        records_after_apply = json.loads(metadata_path.read_text())
        self.assertTrue(all(record.get("schedule_time") for record in records_after_apply))
        scheduler_page = client.get(preview_response.headers["location"])
        self.assertEqual(scheduler_page.status_code, 200)
        self.assertIn("Latest scheduling run", scheduler_page.text)
        self.assertIn("Open raw agent run JSON", scheduler_page.text)


if __name__ == "__main__":
    unittest.main()
