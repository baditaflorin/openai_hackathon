"""Scheduler workflow implemented on top of the generic agent run layer."""
from __future__ import annotations

from typing import Any

from .service import AgentRunService, ApprovalRequiredError
from .storage import AgentRunStorage
from .tooling import ToolDefinition, ToolRegistry


SCHEDULE_ENTRY_SCHEMA = {
    "type": "object",
    "properties": {
        "record_id": {"type": "string", "minLength": 1},
        "schedule_time": {"type": "string", "minLength": 1},
    },
    "required": ["record_id", "schedule_time"],
    "additionalProperties": False,
}


class SchedulerAgentRunWorkflow:
    """Preview and apply scheduling changes through auditable tool calls."""

    def __init__(
        self,
        *,
        metadata_svc: Any,
        scheduling_svc: Any,
        publishing_svc: Any,
        storage: AgentRunStorage | None = None,
    ) -> None:
        self.metadata_svc = metadata_svc
        self.scheduling_svc = scheduling_svc
        self.publishing_svc = publishing_svc
        registry = ToolRegistry()
        registry.register(
            ToolDefinition(
                name="load_unscheduled_records",
                description="Load unscheduled episodes that need release times.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                output_schema={
                    "type": "object",
                    "properties": {
                        "records": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "minLength": 1},
                                    "selected_title": {"type": "string"},
                                    "long_description": {"type": "string"},
                                },
                                "required": ["id", "selected_title", "long_description"],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["records"],
                    "additionalProperties": False,
                },
                executor=self._load_unscheduled_records,
                risk_level="low",
            )
        )
        registry.register(
            ToolDefinition(
                name="propose_schedule",
                description="Generate release-time suggestions for a batch of episodes.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "cadence": {
                            "type": "string",
                            "enum": ["daily", "weekly", "every_n"],
                        },
                        "n_days": {"type": "integer"},
                        "records": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "minLength": 1},
                                    "selected_title": {"type": "string"},
                                    "long_description": {"type": "string"},
                                },
                                "required": ["id", "selected_title", "long_description"],
                                "additionalProperties": False,
                            },
                            "minItems": 1,
                        },
                    },
                    "required": ["cadence", "records"],
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "entries": {
                            "type": "array",
                            "items": SCHEDULE_ENTRY_SCHEMA,
                        }
                    },
                    "required": ["entries"],
                    "additionalProperties": False,
                },
                executor=self._propose_schedule,
                risk_level="low",
                max_attempts=2,
            )
        )
        registry.register(
            ToolDefinition(
                name="apply_schedule_plan",
                description="Persist schedule suggestions back into record metadata and provider jobs.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "entries": {
                            "type": "array",
                            "items": SCHEDULE_ENTRY_SCHEMA,
                            "minItems": 1,
                        }
                    },
                    "required": ["entries"],
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "applied_count": {"type": "integer"},
                        "updated_record_ids": {"type": "array", "items": {"type": "string"}},
                        "skipped_record_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["applied_count", "updated_record_ids", "skipped_record_ids"],
                    "additionalProperties": False,
                },
                executor=self._apply_schedule_plan,
                risk_level="high",
                approval_policy="required",
            )
        )
        self.agent_runs = AgentRunService(storage=storage or AgentRunStorage(), registry=registry)

    async def _load_unscheduled_records(self, _: dict[str, Any]) -> dict[str, Any]:
        records = self.metadata_svc.read()
        unscheduled = [
            {
                "id": str(record["id"]),
                "selected_title": str(record.get("selected_title") or ""),
                "long_description": str(record.get("long_description") or ""),
            }
            for record in records
            if not record.get("schedule_time")
        ]
        return {"records": unscheduled}

    async def _propose_schedule(self, payload: dict[str, Any]) -> dict[str, Any]:
        cadence = str(payload["cadence"])
        n_days = payload.get("n_days")
        records = payload["records"]
        suggestions = await self.scheduling_svc.propose(records, cadence=cadence, n_days=n_days)
        entries = [
            {
                "record_id": str(record_id),
                "schedule_time": str(schedule_time),
            }
            for record_id, schedule_time in suggestions.items()
        ]
        entries.sort(key=lambda item: item["record_id"])
        return {"entries": entries}

    def _apply_schedule_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        updated_record_ids: list[str] = []
        skipped_record_ids: list[str] = []
        for entry in payload["entries"]:
            record_id = str(entry["record_id"])
            schedule_time = str(entry["schedule_time"])
            record = self.metadata_svc.get(record_id)
            if record is None:
                skipped_record_ids.append(record_id)
                continue
            youtube_job = (record.get("publish_jobs") or {}).get("youtube") or {}
            self.publishing_svc.schedule_record(
                record_id,
                schedule_time,
                list(record.get("publish_targets") or []),
                youtube_privacy_status=str(youtube_job.get("privacy_status") or "private"),
            )
            updated_record_ids.append(record_id)
        return {
            "applied_count": len(updated_record_ids),
            "updated_record_ids": updated_record_ids,
            "skipped_record_ids": skipped_record_ids,
        }

    async def run(
        self,
        *,
        cadence: str,
        n_days: int | None = None,
        live_apply: bool,
        approval_granted: bool,
    ) -> dict[str, Any]:
        run = self.agent_runs.create_run(
            workflow="scheduler_auto",
            goal="Plan release times for unscheduled episodes and optionally apply them live.",
            dry_run=not live_apply,
            context={
                "cadence": cadence,
                "n_days": n_days,
                "live_apply": live_apply,
            },
        )
        run_id = str(run["run_id"])
        try:
            self.agent_runs.transition_state(run_id, "planning")
            self.agent_runs.set_plan(
                run_id,
                [
                    {
                        "step_id": "load_unscheduled_records",
                        "title": "Load unscheduled records",
                        "tool_name": "load_unscheduled_records",
                        "status": "pending",
                    },
                    {
                        "step_id": "propose_schedule",
                        "title": "Generate a scheduling preview",
                        "tool_name": "propose_schedule",
                        "status": "pending",
                    },
                    {
                        "step_id": "apply_schedule_plan",
                        "title": "Apply the scheduling plan",
                        "tool_name": "apply_schedule_plan",
                        "status": "pending" if live_apply else "skipped",
                    },
                ],
            )
            self.agent_runs.transition_state(run_id, "executing")
            loaded = await self.agent_runs.execute_tool(
                run_id,
                "load_unscheduled_records",
                {},
                step_id="load_unscheduled_records",
                title="Load unscheduled records",
            )
            records = loaded["records"]
            self.agent_runs.record_observation(
                run_id,
                f"Loaded {len(records)} unscheduled records.",
                data={"record_count": len(records)},
            )
            if not records:
                return self.agent_runs.mark_completed(
                    run_id,
                    {
                        "entries": [],
                        "entry_count": 0,
                        "applied": False,
                        "approval_required": False,
                        "updated_record_ids": [],
                        "skipped_record_ids": [],
                    },
                )

            propose_payload: dict[str, Any] = {
                "cadence": cadence,
                "records": records,
            }
            if n_days is not None:
                propose_payload["n_days"] = n_days
            proposed = await self.agent_runs.execute_tool(
                run_id,
                "propose_schedule",
                propose_payload,
                step_id="propose_schedule",
                title="Generate a scheduling preview",
            )
            outcome = {
                "entries": proposed["entries"],
                "entry_count": len(proposed["entries"]),
                "applied": False,
                "approval_required": False,
                "updated_record_ids": [],
                "skipped_record_ids": [],
            }
            self.agent_runs.update_final_outcome(run_id, outcome)

            if not live_apply:
                self.agent_runs.record_observation(
                    run_id,
                    "Dry-run scheduling preview completed without side effects.",
                )
                return self.agent_runs.mark_completed(run_id, outcome)

            try:
                applied = await self.agent_runs.execute_tool(
                    run_id,
                    "apply_schedule_plan",
                    {"entries": proposed["entries"]},
                    step_id="apply_schedule_plan",
                    title="Apply the scheduling plan",
                    approval_granted=approval_granted,
                )
            except ApprovalRequiredError:
                outcome["approval_required"] = True
                self.agent_runs.update_final_outcome(run_id, outcome)
                return self.agent_runs.get_run(run_id) or run

            outcome.update(
                {
                    "applied": True,
                    "updated_record_ids": applied["updated_record_ids"],
                    "skipped_record_ids": applied["skipped_record_ids"],
                }
            )
            self.agent_runs.record_observation(
                run_id,
                f"Applied schedule updates to {applied['applied_count']} records.",
                data={"applied_count": applied["applied_count"]},
            )
            return self.agent_runs.mark_completed(run_id, outcome)
        except Exception as exc:
            self.agent_runs.record_observation(run_id, str(exc), level="error")
            return self.agent_runs.mark_failed(run_id, str(exc))
