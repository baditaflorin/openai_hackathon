"""Versioned prompt execution, validation, and evaluation helpers."""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

import httpx
from agents import Agent, OpenAIChatCompletionsModel, RunConfig, Runner
from openai import AsyncOpenAI

from ..runtime import (
    get_ollama_base_url,
    get_ollama_model,
    get_ollama_timeout_seconds,
    get_openai_api_key,
    get_openai_content_model,
    resolve_content_backend,
)
from ..utils.metadata import get_metadata_record
from .contracts import parse_task_output, validate_task_output
from .registry import resolve_prompt_version
from .storage import (
    append_prompt_evaluation,
    append_prompt_run,
    read_prompt_evaluations,
    read_prompt_runs,
)


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PromptExecution:
    """Final task output plus the persisted prompt run record."""

    output: Any
    prompt_run: dict[str, Any]

    @property
    def summary(self) -> dict[str, Any]:
        """Compact record-safe prompt run summary."""
        return {
            "run_id": self.prompt_run["run_id"],
            "task": self.prompt_run["task"],
            "prompt_version": self.prompt_run["prompt_version"],
            "backend": self.prompt_run["backend"],
            "model": self.prompt_run["model"],
            "status": self.prompt_run["status"],
            "validation_passed": self.prompt_run["validation_passed"],
            "used_fallback": self.prompt_run["used_fallback"],
            "issues": copy.deepcopy(self.prompt_run.get("validation_issues", [])),
            "completed_at": self.prompt_run["completed_at"],
        }


def _sanitize_payload(value: Any, *, max_string: int = 2000, max_items: int = 20) -> Any:
    if isinstance(value, str):
        if len(value) <= max_string:
            return value
        remaining = len(value) - max_string
        return value[:max_string] + f"... [truncated {remaining} chars]"
    if isinstance(value, list):
        return [_sanitize_payload(item, max_string=max_string, max_items=max_items) for item in value[:max_items]]
    if isinstance(value, tuple):
        return [_sanitize_payload(item, max_string=max_string, max_items=max_items) for item in value[:max_items]]
    if isinstance(value, dict):
        items = list(value.items())[:max_items]
        return {
            str(key): _sanitize_payload(item, max_string=max_string, max_items=max_items)
            for key, item in items
        }
    return value


def _render_prompt(template: str, variables: dict[str, Any]) -> str:
    rendered = template.format_map(
        {
            key: value if isinstance(value, str) else str(value)
            for key, value in variables.items()
        }
    )
    return rendered.strip()


def _build_prompt_run(
    *,
    run_id: str,
    record_id: str | None,
    task: str,
    prompt_version: str,
    prompt_label: str,
    backend: str,
    model: str,
    started_at: str,
    completed_at: str,
    duration_ms: int,
    rendered_prompt: str,
    inputs: dict[str, Any],
    output: Any,
    raw_output: str | None,
    validation_passed: bool,
    validation_issues: list[str],
    used_fallback: bool,
    fallback_reason: str | None,
    status: str,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "record_id": record_id,
        "task": task,
        "prompt_version": prompt_version,
        "prompt_label": prompt_label,
        "backend": backend,
        "model": model,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "rendered_prompt": _sanitize_payload(rendered_prompt, max_string=4000),
        "inputs": _sanitize_payload(inputs),
        "output": _sanitize_payload(output),
        "raw_output": _sanitize_payload(raw_output) if raw_output is not None else None,
        "validation_passed": validation_passed,
        "validation_issues": validation_issues,
        "used_fallback": used_fallback,
        "fallback_reason": fallback_reason,
        "status": status,
    }


def _local_execution(
    *,
    task: str,
    record_id: str | None,
    rendered_prompt: str,
    inputs: dict[str, Any],
    fallback_output: Any,
    prompt_version: Any,
    started_at: str,
    started_perf: float,
) -> PromptExecution:
    validation = validate_task_output(task, fallback_output, prompt_version.output_contract)
    completed_at = datetime.now(UTC).isoformat()
    run = append_prompt_run(
        _build_prompt_run(
            run_id=str(uuid4()),
            record_id=record_id,
            task=task,
            prompt_version=prompt_version.version,
            prompt_label=prompt_version.label,
            backend="local-basic",
            model="local-basic",
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=round((perf_counter() - started_perf) * 1000),
            rendered_prompt=rendered_prompt,
            inputs=inputs,
            output=validation.normalized,
            raw_output=None,
            validation_passed=validation.passed,
            validation_issues=list(validation.issues),
            used_fallback=False,
            fallback_reason=None,
            status="completed" if validation.passed else "invalid_local_output",
        )
    )
    if not validation.passed:
        logger.warning("Local prompt execution for %s produced invalid output: %s", task, validation.issues)
    return PromptExecution(output=validation.normalized if validation.passed else fallback_output, prompt_run=run)


def _openai_run_config() -> RunConfig:
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError("No OpenAI API key is configured.")
    client = AsyncOpenAI(api_key=api_key, base_url="https://api.openai.com/v1")
    model = OpenAIChatCompletionsModel(
        model=get_openai_content_model(),
        openai_client=client,
    )
    return RunConfig(
        model=model,
        tracing_disabled=True,
        trace_include_sensitive_data=False,
        workflow_name="Clipmato prompt engine",
    )


def _finalize_remote_execution(
    *,
    task: str,
    record_id: str | None,
    prompt_version: Any,
    backend: str,
    model_name: str,
    rendered_prompt: str,
    inputs: dict[str, Any],
    fallback_output: Any,
    raw_output: str | None,
    started_at: str,
    started_perf: float,
    error: Exception | None = None,
) -> PromptExecution:
    used_fallback = False
    fallback_reason: str | None = None
    validation_issues: list[str] = []
    validation_passed = False

    if error is None and raw_output is not None:
        try:
            parsed_output = parse_task_output(task, raw_output)
        except Exception as exc:
            parsed_output = None
            validation_issues.append(f"Output parsing failed: {exc}")
        else:
            validation = validate_task_output(task, parsed_output, prompt_version.output_contract)
            validation_passed = validation.passed
            validation_issues.extend(validation.issues)
            if validation.passed:
                final_output = validation.normalized
            else:
                used_fallback = True
                fallback_reason = "validation_failed"
                validation_issues.append("Fell back to local output because the prompt output contract failed.")
                final_output = fallback_output
    else:
        final_output = fallback_output

    if error is not None:
        used_fallback = True
        fallback_reason = error.__class__.__name__
        validation_issues.append(f"Prompt execution failed: {error}")

    if used_fallback:
        fallback_validation = validate_task_output(task, fallback_output, prompt_version.output_contract)
        final_output = fallback_validation.normalized if fallback_validation.passed else fallback_output

    completed_at = datetime.now(UTC).isoformat()
    run = append_prompt_run(
        _build_prompt_run(
            run_id=str(uuid4()),
            record_id=record_id,
            task=task,
            prompt_version=prompt_version.version,
            prompt_label=prompt_version.label,
            backend=backend,
            model=model_name,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=round((perf_counter() - started_perf) * 1000),
            rendered_prompt=rendered_prompt,
            inputs=inputs,
            output=final_output,
            raw_output=raw_output,
            validation_passed=validation_passed,
            validation_issues=validation_issues,
            used_fallback=used_fallback,
            fallback_reason=fallback_reason,
            status="fallback" if used_fallback else "completed",
        )
    )
    return PromptExecution(output=final_output, prompt_run=run)


def _run_ollama_request_sync(prompt_version: Any, rendered_prompt: str) -> str:
    response = httpx.post(
        f"{get_ollama_base_url()}/api/generate",
        json={
            "model": get_ollama_model(),
            "prompt": rendered_prompt,
            "system": prompt_version.system_instructions,
            "stream": False,
        },
        timeout=get_ollama_timeout_seconds(),
    )
    response.raise_for_status()
    payload = response.json()
    return str(payload.get("response") or "").strip()


async def _run_ollama_request_async(prompt_version: Any, rendered_prompt: str) -> str:
    async with httpx.AsyncClient(timeout=get_ollama_timeout_seconds()) as client:
        response = await client.post(
            f"{get_ollama_base_url()}/api/generate",
            json={
                "model": get_ollama_model(),
                "prompt": rendered_prompt,
                "system": prompt_version.system_instructions,
                "stream": False,
            },
        )
    response.raise_for_status()
    payload = response.json()
    return str(payload.get("response") or "").strip()


def run_prompt_task_sync(
    task: str,
    variables: dict[str, Any],
    *,
    fallback_output: Any,
    record_id: str | None = None,
    prompt_version: str | None = None,
) -> PromptExecution:
    """Run one prompt task synchronously through the selected backend."""
    version = resolve_prompt_version(task, requested_version=prompt_version)
    rendered_prompt = _render_prompt(version.user_template, variables)
    started_at = datetime.now(UTC).isoformat()
    started_perf = perf_counter()
    backend = resolve_content_backend()
    if backend == "local-basic":
        return _local_execution(
            task=task,
            record_id=record_id,
            rendered_prompt=rendered_prompt,
            inputs=variables,
            fallback_output=fallback_output,
            prompt_version=version,
            started_at=started_at,
            started_perf=started_perf,
        )

    agent = Agent(name=version.label, instructions=version.system_instructions)
    backend_name = "openai" if backend == "openai" else "ollama"
    model_name = get_openai_content_model() if backend == "openai" else get_ollama_model()
    try:
        if backend == "openai":
            result = Runner.run_sync(agent, rendered_prompt, run_config=_openai_run_config())
            raw_output = (result.final_output or "").strip()
        else:
            raw_output = _run_ollama_request_sync(version, rendered_prompt)
    except Exception as exc:
        logger.exception("Prompt task %s failed", task)
        return _finalize_remote_execution(
            task=task,
            record_id=record_id,
            prompt_version=version,
            backend=backend_name,
            model_name=model_name,
            rendered_prompt=rendered_prompt,
            inputs=variables,
            fallback_output=fallback_output,
            raw_output=None,
            started_at=started_at,
            started_perf=started_perf,
            error=exc,
        )

    return _finalize_remote_execution(
        task=task,
        record_id=record_id,
        prompt_version=version,
        backend=backend_name,
        model_name=model_name,
        rendered_prompt=rendered_prompt,
        inputs=variables,
        fallback_output=fallback_output,
        raw_output=raw_output,
        started_at=started_at,
        started_perf=started_perf,
    )


async def run_prompt_task_async(
    task: str,
    variables: dict[str, Any],
    *,
    fallback_output: Any,
    record_id: str | None = None,
    prompt_version: str | None = None,
) -> PromptExecution:
    """Run one prompt task asynchronously through the selected backend."""
    version = resolve_prompt_version(task, requested_version=prompt_version)
    rendered_prompt = _render_prompt(version.user_template, variables)
    started_at = datetime.now(UTC).isoformat()
    started_perf = perf_counter()
    backend = resolve_content_backend()
    if backend == "local-basic":
        return _local_execution(
            task=task,
            record_id=record_id,
            rendered_prompt=rendered_prompt,
            inputs=variables,
            fallback_output=fallback_output,
            prompt_version=version,
            started_at=started_at,
            started_perf=started_perf,
        )

    agent = Agent(name=version.label, instructions=version.system_instructions)
    backend_name = "openai" if backend == "openai" else "ollama"
    model_name = get_openai_content_model() if backend == "openai" else get_ollama_model()
    try:
        if backend == "openai":
            result = await Runner.run(agent, rendered_prompt, run_config=_openai_run_config())
            raw_output = (result.final_output or "").strip()
        else:
            raw_output = await _run_ollama_request_async(version, rendered_prompt)
    except Exception as exc:
        logger.exception("Prompt task %s failed", task)
        return _finalize_remote_execution(
            task=task,
            record_id=record_id,
            prompt_version=version,
            backend=backend_name,
            model_name=model_name,
            rendered_prompt=rendered_prompt,
            inputs=variables,
            fallback_output=fallback_output,
            raw_output=None,
            started_at=started_at,
            started_perf=started_perf,
            error=exc,
        )

    return _finalize_remote_execution(
        task=task,
        record_id=record_id,
        prompt_version=version,
        backend=backend_name,
        model_name=model_name,
        rendered_prompt=rendered_prompt,
        inputs=variables,
        fallback_output=fallback_output,
        raw_output=raw_output,
        started_at=started_at,
        started_perf=started_perf,
    )


def _append_evaluation(
    *,
    record_id: str,
    task: str,
    prompt_run_summary: dict[str, Any],
    signal: str,
    value: Any,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return append_prompt_evaluation(
        {
            "evaluation_id": str(uuid4()),
            "record_id": record_id,
            "task": task,
            "prompt_run_id": prompt_run_summary.get("run_id"),
            "prompt_version": prompt_run_summary.get("prompt_version"),
            "signal": signal,
            "value": _sanitize_payload(value),
            "metadata": _sanitize_payload(metadata or {}),
            "created_at": datetime.now(UTC).isoformat(),
        }
    )


def record_title_selection_evaluation(record: dict[str, Any], selected_title: str) -> dict[str, Any] | None:
    """Persist title selection as a prompt evaluation signal."""
    prompt_run = (record.get("prompt_runs") or {}).get("title_suggestion")
    if not prompt_run or not record.get("id"):
        return None
    titles = list(record.get("titles") or [])
    rank = titles.index(selected_title) + 1 if selected_title in titles else None
    return _append_evaluation(
        record_id=record["id"],
        task="title_suggestion",
        prompt_run_summary=prompt_run,
        signal="title_selected",
        value=selected_title,
        metadata={
            "selected_rank": rank,
            "candidate_count": len(titles),
            "selected_title": selected_title,
        },
    )


def record_publish_evaluations(record_id: str, provider_key: str, remote_url: str | None = None) -> list[dict[str, Any]]:
    """Persist publish success as downstream prompt evaluation signals."""
    record = get_metadata_record(record_id)
    if record is None:
        return []
    evaluations: list[dict[str, Any]] = []
    for task, prompt_run in (record.get("prompt_runs") or {}).items():
        evaluations.append(
            _append_evaluation(
                record_id=record_id,
                task=task,
                prompt_run_summary=prompt_run,
                signal="record_published",
                value=provider_key,
                metadata={
                    "provider": provider_key,
                    "remote_url": remote_url,
                    "selected_title": record.get("selected_title"),
                    "schedule_time": record.get("schedule_time"),
                },
            )
        )
    return evaluations
