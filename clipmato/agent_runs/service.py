"""Generic agent run state machine and tool execution service."""
from __future__ import annotations

import copy
import inspect
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

from .contracts import ensure_valid_schema
from .storage import AgentRunStorage
from .tooling import ToolRegistry


RUN_STATES = {
    "queued",
    "planning",
    "executing",
    "awaiting_approval",
    "completed",
    "failed",
    "cancelled",
}
RUN_TRANSITIONS = {
    "queued": {"planning", "cancelled"},
    "planning": {"executing", "failed", "cancelled"},
    "executing": {"awaiting_approval", "completed", "failed", "cancelled"},
    "awaiting_approval": {"executing", "completed", "failed", "cancelled"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}


class AgentRunStateError(ValueError):
    """Raised when a run attempts an invalid state transition."""


class ToolContractError(ValueError):
    """Raised when tool inputs or outputs violate their contracts."""


class ApprovalRequiredError(RuntimeError):
    """Raised when a tool requires approval before execution."""


class ToolExecutionError(RuntimeError):
    """Raised when a tool exhausts its retry budget."""


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


class AgentRunService:
    """Create, mutate, and persist agent runs with explicit state transitions."""

    def __init__(self, *, storage: AgentRunStorage | None = None, registry: ToolRegistry | None = None) -> None:
        self.storage = storage or AgentRunStorage()
        self.registry = registry or ToolRegistry()

    def create_run(
        self,
        *,
        workflow: str,
        goal: str,
        dry_run: bool,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        created_at = _timestamp()
        run = {
            "run_id": str(uuid4()),
            "workflow": workflow,
            "goal": goal,
            "state": "queued",
            "dry_run": dry_run,
            "context": copy.deepcopy(context or {}),
            "plan": [],
            "steps": [],
            "tool_calls": [],
            "observations": [],
            "final_outcome": None,
            "created_at": created_at,
            "updated_at": created_at,
            "completed_at": None,
        }
        return self.storage.save(run)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        return self.storage.read(run_id)

    def list_runs(self, *, workflow: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        return self.storage.list_runs(workflow=workflow, limit=limit)

    def _read_required(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        if run is None:
            raise KeyError(f"Unknown agent run: {run_id}")
        return run

    def _save(self, run: dict[str, Any]) -> dict[str, Any]:
        run["updated_at"] = _timestamp()
        return self.storage.save(run)

    def transition_state(self, run_id: str, new_state: str) -> dict[str, Any]:
        if new_state not in RUN_STATES:
            raise AgentRunStateError(f"Unknown run state: {new_state}")
        run = self._read_required(run_id)
        current_state = str(run["state"])
        if new_state == current_state:
            return run
        allowed_states = RUN_TRANSITIONS[current_state]
        if new_state not in allowed_states:
            raise AgentRunStateError(f"Invalid run transition: {current_state} -> {new_state}")
        run["state"] = new_state
        if new_state in {"completed", "failed", "cancelled"}:
            run["completed_at"] = _timestamp()
        return self._save(run)

    def record_observation(
        self,
        run_id: str,
        message: str,
        *,
        level: str = "info",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        run = self._read_required(run_id)
        run["observations"].append(
            {
                "timestamp": _timestamp(),
                "level": level,
                "message": message,
                "data": copy.deepcopy(data or {}),
            }
        )
        return self._save(run)

    def set_plan(self, run_id: str, plan: list[dict[str, Any]]) -> dict[str, Any]:
        run = self._read_required(run_id)
        run["plan"] = copy.deepcopy(plan)
        return self._save(run)

    def update_final_outcome(self, run_id: str, final_outcome: dict[str, Any]) -> dict[str, Any]:
        run = self._read_required(run_id)
        run["final_outcome"] = copy.deepcopy(final_outcome)
        return self._save(run)

    def mark_completed(self, run_id: str, final_outcome: dict[str, Any]) -> dict[str, Any]:
        run = self._read_required(run_id)
        run["final_outcome"] = copy.deepcopy(final_outcome)
        self.storage.save(run)
        return self.transition_state(run_id, "completed")

    def mark_failed(self, run_id: str, message: str) -> dict[str, Any]:
        run = self._read_required(run_id)
        outcome = copy.deepcopy(run.get("final_outcome") or {})
        outcome["error"] = message
        run["final_outcome"] = outcome
        self.storage.save(run)
        return self.transition_state(run_id, "failed")

    def _find_step(self, run: dict[str, Any], step_id: str) -> dict[str, Any] | None:
        for step in run["steps"]:
            if step.get("step_id") == step_id:
                return step
        return None

    def _update_step(
        self,
        run: dict[str, Any],
        step_id: str,
        *,
        title: str,
        tool_name: str,
        status: str,
        max_attempts: int,
        attempts_used: int | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        step = self._find_step(run, step_id)
        if step is None:
            step = {
                "step_id": step_id,
                "title": title,
                "tool_name": tool_name,
                "status": status,
                "max_attempts": max_attempts,
                "attempts_used": attempts_used or 0,
                "started_at": _timestamp(),
                "completed_at": None,
                "error": None,
            }
            run["steps"].append(step)
        else:
            step.update(
                {
                    "title": title,
                    "tool_name": tool_name,
                    "status": status,
                    "max_attempts": max_attempts,
                }
            )
            if attempts_used is not None:
                step["attempts_used"] = attempts_used
        if error is not None:
            step["error"] = error
        if status in {"completed", "failed"}:
            step["completed_at"] = _timestamp()
        return step

    async def execute_tool(
        self,
        run_id: str,
        tool_name: str,
        input_payload: dict[str, Any],
        *,
        step_id: str,
        title: str,
        approval_granted: bool = False,
    ) -> Any:
        tool = self.registry.get(tool_name)
        run = self._read_required(run_id)
        current_state = str(run["state"])
        if current_state == "awaiting_approval" and approval_granted:
            run = self.transition_state(run_id, "executing")
        elif current_state not in {"executing", "awaiting_approval"}:
            raise AgentRunStateError(f"Tool execution requires executing state, found {current_state}")

        run = self._read_required(run_id)
        self._update_step(
            run,
            step_id,
            title=title,
            tool_name=tool_name,
            status="in_progress",
            max_attempts=tool.max_attempts,
        )
        self.storage.save(run)

        try:
            ensure_valid_schema(input_payload, tool.input_schema, label=f"Tool input for {tool_name}")
        except ValueError as exc:
            run = self._read_required(run_id)
            run["tool_calls"].append(
                {
                    "tool_name": tool_name,
                    "status": "invalid_input",
                    "risk_level": tool.risk_level,
                    "approval_policy": tool.approval_policy,
                    "attempt": 0,
                    "input": copy.deepcopy(input_payload),
                    "output": None,
                    "started_at": _timestamp(),
                    "completed_at": _timestamp(),
                    "latency_ms": 0,
                    "error": str(exc),
                }
            )
            self._update_step(
                run,
                step_id,
                title=title,
                tool_name=tool_name,
                status="failed",
                max_attempts=tool.max_attempts,
                error=str(exc),
            )
            self.storage.save(run)
            raise ToolContractError(str(exc)) from exc

        if tool.requires_approval and not approval_granted:
            run = self._read_required(run_id)
            self._update_step(
                run,
                step_id,
                title=title,
                tool_name=tool_name,
                status="awaiting_approval",
                max_attempts=tool.max_attempts,
            )
            self.storage.save(run)
            self.transition_state(run_id, "awaiting_approval")
            self.record_observation(
                run_id,
                f"Approval required before running {tool_name}.",
                level="warning",
                data={"tool_name": tool_name},
            )
            raise ApprovalRequiredError(f"Approval required for tool: {tool_name}")

        for attempt in range(1, tool.max_attempts + 1):
            started_at = _timestamp()
            started_perf = perf_counter()
            output_payload = None
            error_message = None
            status = "completed"
            try:
                result = tool.executor(copy.deepcopy(input_payload))
                output_payload = await result if inspect.isawaitable(result) else result
                ensure_valid_schema(output_payload, tool.output_schema, label=f"Tool output for {tool_name}")
            except Exception as exc:
                status = "failed"
                error_message = str(exc)

            run = self._read_required(run_id)
            run["tool_calls"].append(
                {
                    "tool_name": tool_name,
                    "status": status,
                    "risk_level": tool.risk_level,
                    "approval_policy": tool.approval_policy,
                    "attempt": attempt,
                    "input": copy.deepcopy(input_payload),
                    "output": copy.deepcopy(output_payload),
                    "started_at": started_at,
                    "completed_at": _timestamp(),
                    "latency_ms": round((perf_counter() - started_perf) * 1000),
                    "error": error_message,
                }
            )

            if status == "completed":
                self._update_step(
                    run,
                    step_id,
                    title=title,
                    tool_name=tool_name,
                    status="completed",
                    max_attempts=tool.max_attempts,
                    attempts_used=attempt,
                )
                self.storage.save(run)
                return output_payload

            self._update_step(
                run,
                step_id,
                title=title,
                tool_name=tool_name,
                status="in_progress" if attempt < tool.max_attempts else "failed",
                max_attempts=tool.max_attempts,
                attempts_used=attempt,
                error=error_message,
            )
            self.storage.save(run)
            if attempt < tool.max_attempts:
                self.record_observation(
                    run_id,
                    f"{tool_name} attempt {attempt} failed; retrying.",
                    level="warning",
                    data={"tool_name": tool_name, "attempt": attempt, "error": error_message},
                )
                continue
            raise ToolExecutionError(error_message or f"{tool_name} failed without an error message")

        raise ToolExecutionError(f"{tool_name} exhausted its retry budget")
