from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient


def reset_clipmato_modules() -> None:
    for name in list(sys.modules):
        if name == "clipmato" or name.startswith("clipmato."):
            sys.modules.pop(name)


class GovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        os.environ["CLIPMATO_DATA_DIR"] = self.tempdir.name
        os.environ["CLIPMATO_CONTENT_BACKEND"] = "local"
        os.environ.pop("CLIPMATO_PROMPT_TITLE_SUGGESTION_VERSION", None)
        reset_clipmato_modules()

    def write_metadata(self, records: list[dict]) -> Path:
        metadata_path = Path(self.tempdir.name) / "metadata.json"
        metadata_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return metadata_path

    def load_client(self) -> TestClient:
        app_module = importlib.import_module("clipmato.web")
        return TestClient(app_module.app)

    def test_prompt_run_emits_agent_evaluation(self) -> None:
        prompts_module = importlib.import_module("clipmato.prompts")
        governance_module = importlib.import_module("clipmato.governance")

        execution = prompts_module.run_prompt_task_sync(
            "title_suggestion",
            {"transcript": "A transcript about practical mapping workflows."},
            fallback_output=["One", "Two", "Three", "Four", "Five"],
            record_id="rec-eval",
        )

        self.assertEqual(execution.summary["policy_status"], "passed")
        evaluations = governance_module.read_agent_evaluations(
            subject_type="prompt_run",
            task="title_suggestion",
            prompt_version="v1",
            record_id="rec-eval",
        )
        self.assertEqual(len(evaluations), 1)
        self.assertTrue(evaluations[0]["metrics"]["contract_valid"])
        self.assertTrue(evaluations[0]["metrics"]["policy_passed"])
        self.assertFalse(evaluations[0]["metrics"]["fallback_used"])

    def test_remote_policy_failure_uses_fallback_and_records_evaluation(self) -> None:
        os.environ["CLIPMATO_CONTENT_BACKEND"] = "ollama"
        os.environ["CLIPMATO_OLLAMA_BASE_URL"] = "http://ollama.internal:11434"
        os.environ["CLIPMATO_OLLAMA_MODEL"] = "llama3.2:3b"
        reset_clipmato_modules()
        prompts_module = importlib.import_module("clipmato.prompts")
        governance_module = importlib.import_module("clipmato.governance")

        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "response": json.dumps(
                [
                    "Buy followers fast",
                    "Click here now",
                    "Clean title",
                    "Another clean title",
                    "Final clean title",
                ]
            )
        }

        fallback = ["Fallback 1", "Fallback 2", "Fallback 3", "Fallback 4", "Fallback 5"]
        with patch("clipmato.prompts.engine.httpx.post", return_value=response):
            execution = prompts_module.run_prompt_task_sync(
                "title_suggestion",
                {"transcript": "A transcript about safe editorial systems."},
                fallback_output=fallback,
                record_id="rec-policy",
            )

        self.assertEqual(execution.output, fallback)
        self.assertTrue(execution.summary["used_fallback"])
        self.assertEqual(execution.summary["fallback_reason"], "policy_failed")
        runs = prompts_module.read_prompt_runs(record_id="rec-policy", task="title_suggestion")
        self.assertEqual(runs[0]["status"], "fallback")
        self.assertIn("policy checks failed", " ".join(runs[0]["validation_issues"]).lower())

        evaluations = governance_module.read_agent_evaluations(
            subject_type="prompt_run",
            task="title_suggestion",
            record_id="rec-policy",
        )
        self.assertEqual(len(evaluations), 1)
        self.assertTrue(evaluations[0]["metrics"]["fallback_used"])

    def test_publish_policy_blocks_and_override_is_audited(self) -> None:
        self.write_metadata(
            [
                {
                    "id": "rec-publish",
                    "filename": "episode.mp4",
                    "upload_time": "2026-03-08T18:00:00+00:00",
                    "selected_title": "Buy followers fast",
                    "short_description": "A short description.",
                    "long_description": "A long description for the episode.",
                    "publish_targets": [],
                    "publish_jobs": {},
                    "prompt_runs": {
                        "title_suggestion": {
                            "run_id": "run-title-1",
                            "task": "title_suggestion",
                            "prompt_version": "v1",
                            "backend": "local-basic",
                            "model": "local-basic",
                            "status": "completed",
                            "validation_passed": True,
                            "used_fallback": False,
                            "completed_at": "2026-03-08T18:00:05+00:00",
                        }
                    },
                }
            ]
        )

        client = self.load_client()

        blocked = client.post("/record/rec-publish/publish/youtube/now", follow_redirects=False)
        self.assertEqual(blocked.status_code, 303)
        self.assertIn("error=", blocked.headers["location"])

        allowed = client.post(
            "/record/rec-publish/publish/youtube/now",
            data={
                "override_actor": "qa-user",
                "override_reason": "Editorial review completed.",
            },
            follow_redirects=False,
        )
        self.assertEqual(allowed.status_code, 303)
        self.assertIn("notice=", allowed.headers["location"])

        governance_module = importlib.import_module("clipmato.governance")
        evaluations = governance_module.read_agent_evaluations(
            subject_type="publish_action",
            record_id="rec-publish",
            action="queue_now",
        )
        self.assertEqual(len(evaluations), 2)
        self.assertEqual(evaluations[0]["status"], "override_required")
        self.assertEqual(evaluations[1]["status"], "passed")
        self.assertTrue(evaluations[1]["metrics"]["override_used"])
        self.assertEqual(evaluations[1]["metadata"]["override_actor"], "qa-user")

    def test_live_apply_promotes_prompt_version(self) -> None:
        prompts_module = importlib.import_module("clipmato.prompts")
        governance_module = importlib.import_module("clipmato.governance")
        registry_module = importlib.import_module("clipmato.prompts.registry")

        for index in range(2):
            prompts_module.run_prompt_task_sync(
                "title_suggestion",
                {"transcript": f"Transcript {index}"},
                fallback_output=["One", "Two", "Three", "Four", "Five"],
                record_id=f"rec-live-{index}",
                prompt_version="v1-format-tight",
            )

        report = governance_module.evaluate_prompt_release("title_suggestion", "v1-format-tight")
        self.assertTrue(report["passed"])

        applied = governance_module.apply_prompt_release(
            "title_suggestion",
            "v1-format-tight",
            actor="release-bot",
        )
        self.assertEqual(applied["applied"]["mode"], "live")
        self.assertEqual(
            registry_module.resolve_prompt_version("title_suggestion").version,
            "v1-format-tight",
        )
        state = governance_module.read_prompt_release_state()
        self.assertEqual(state["live_defaults"]["title_suggestion"], "v1-format-tight")

    def test_canary_release_routes_some_records_to_candidate(self) -> None:
        prompts_module = importlib.import_module("clipmato.prompts")
        governance_module = importlib.import_module("clipmato.governance")
        registry_module = importlib.import_module("clipmato.prompts.registry")

        for index in range(2):
            prompts_module.run_prompt_task_sync(
                "title_suggestion",
                {"transcript": f"Transcript {index}"},
                fallback_output=["One", "Two", "Three", "Four", "Five"],
                record_id=f"rec-canary-{index}",
                prompt_version="v1-format-tight",
            )

        governance_module.apply_prompt_release(
            "title_suggestion",
            "v1-format-tight",
            actor="release-bot",
            canary_percentage=50,
        )

        resolved_versions = {
            f"rec-{index}": registry_module.resolve_prompt_version(
                "title_suggestion",
                rollout_key=f"rec-{index}",
            ).version
            for index in range(40)
        }
        self.assertIn("v1-format-tight", resolved_versions.values())
        self.assertIn("v1", resolved_versions.values())

    def test_settings_live_apply_route_promotes_prompt_version(self) -> None:
        prompts_module = importlib.import_module("clipmato.prompts")
        governance_module = importlib.import_module("clipmato.governance")

        for index in range(2):
            prompts_module.run_prompt_task_sync(
                "title_suggestion",
                {"transcript": f"Transcript {index}"},
                fallback_output=["One", "Two", "Three", "Four", "Five"],
                record_id=f"rec-settings-{index}",
                prompt_version="v1-format-tight",
            )

        client = self.load_client()
        settings_page = client.get("/settings")
        self.assertEqual(settings_page.status_code, 200)
        self.assertIn("Live apply and canary rollout", settings_page.text)

        response = client.post(
            "/settings/prompt-release/title_suggestion/apply",
            data={
                "prompt_version": "v1-format-tight",
                "actor": "release-bot",
                "suite_version": "quality-v1",
                "notes": "Promote the stronger title format.",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 303)
        self.assertIn("notice=", response.headers["location"])
        state = governance_module.read_prompt_release_state()
        self.assertEqual(state["live_defaults"]["title_suggestion"], "v1-format-tight")

    def test_rollback_restores_previous_live_version(self) -> None:
        prompts_module = importlib.import_module("clipmato.prompts")
        governance_module = importlib.import_module("clipmato.governance")
        registry_module = importlib.import_module("clipmato.prompts.registry")

        for index in range(2):
            prompts_module.run_prompt_task_sync(
                "title_suggestion",
                {"transcript": f"Transcript {index}"},
                fallback_output=["One", "Two", "Three", "Four", "Five"],
                record_id=f"rec-rollback-{index}",
                prompt_version="v1-format-tight",
            )

        governance_module.apply_prompt_release(
            "title_suggestion",
            "v1-format-tight",
            actor="release-bot",
        )
        rollback = governance_module.rollback_prompt_release(
            "title_suggestion",
            "release-bot",
            notes="Restore the packaged stable default.",
        )

        self.assertEqual(rollback["rolled_back_to"], "v1")
        self.assertEqual(
            registry_module.resolve_prompt_version("title_suggestion").version,
            "v1",
        )
        state = governance_module.read_prompt_release_state()
        self.assertEqual(state["live_defaults"]["title_suggestion"], "v1")
        self.assertNotIn("title_suggestion", state["canaries"])


if __name__ == "__main__":
    unittest.main()
