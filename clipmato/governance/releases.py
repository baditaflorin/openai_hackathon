"""Prompt release gate evaluation, rollout summary, and live apply helpers."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..prompts.registry import get_prompt_task, list_prompt_tasks, list_prompt_versions
from ..prompts.storage import read_prompt_evaluations
from .storage import read_agent_evaluations, read_prompt_release_state, write_prompt_release_state


DEFAULT_RELEASE_GATE_SUITES: dict[str, dict[str, float | int]] = {
    "quality-v1": {
        "min_runs": 2,
        "min_contract_pass_rate": 1.0,
        "min_policy_pass_rate": 1.0,
        "max_fallback_rate": 0.5,
    }
}


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def summarize_prompt_version_quality(task: str, prompt_version: str) -> dict[str, Any]:
    """Aggregate quality signals for one prompt version."""
    evaluations = read_agent_evaluations(
        subject_type="prompt_run",
        task=task,
        prompt_version=prompt_version,
    )
    prompt_evaluations = [
        item
        for item in read_prompt_evaluations(task=task)
        if item.get("prompt_version") == prompt_version
    ]

    run_count = len(evaluations)
    contract_pass_count = sum(1 for item in evaluations if item.get("metrics", {}).get("contract_valid"))
    policy_pass_count = sum(1 for item in evaluations if item.get("metrics", {}).get("policy_passed"))
    fallback_count = sum(1 for item in evaluations if item.get("metrics", {}).get("fallback_used"))
    latencies = [
        int(item.get("metrics", {}).get("latency_ms") or 0)
        for item in evaluations
        if item.get("metrics", {}).get("latency_ms") is not None
    ]

    return {
        "task": task,
        "prompt_version": prompt_version,
        "run_count": run_count,
        "contract_pass_rate": _rate(contract_pass_count, run_count),
        "policy_pass_rate": _rate(policy_pass_count, run_count),
        "fallback_rate": _rate(fallback_count, run_count),
        "average_latency_ms": round(sum(latencies) / len(latencies)) if latencies else None,
        "selection_count": sum(1 for item in prompt_evaluations if item.get("signal") == "title_selected"),
        "publish_count": sum(1 for item in prompt_evaluations if item.get("signal") == "record_published"),
    }


def evaluate_prompt_release(task: str, prompt_version: str, *, suite_version: str = "quality-v1") -> dict[str, Any]:
    """Evaluate whether a prompt version satisfies the configured release gates."""
    prompt_task = get_prompt_task(task)
    if prompt_version not in prompt_task.versions:
        raise KeyError(f"Unknown prompt version for {task}: {prompt_version}")
    try:
        thresholds = dict(DEFAULT_RELEASE_GATE_SUITES[suite_version])
    except KeyError as exc:
        raise KeyError(f"Unknown release gate suite: {suite_version}") from exc

    metrics = summarize_prompt_version_quality(task, prompt_version)
    reasons: list[str] = []

    if metrics["run_count"] < int(thresholds["min_runs"]):
        reasons.append(
            f"Need at least {int(thresholds['min_runs'])} evaluated runs before promotion."
        )
    if metrics["contract_pass_rate"] is not None and metrics["contract_pass_rate"] < float(thresholds["min_contract_pass_rate"]):
        reasons.append("Contract pass rate is below the release threshold.")
    if metrics["policy_pass_rate"] is not None and metrics["policy_pass_rate"] < float(thresholds["min_policy_pass_rate"]):
        reasons.append("Policy pass rate is below the release threshold.")
    if metrics["fallback_rate"] is not None and metrics["fallback_rate"] > float(thresholds["max_fallback_rate"]):
        reasons.append("Fallback usage is above the release threshold.")

    return {
        "task": task,
        "prompt_version": prompt_version,
        "suite_version": suite_version,
        "thresholds": thresholds,
        "metrics": metrics,
        "passed": not reasons,
        "reasons": reasons,
        "evaluated_at": datetime.now(UTC).isoformat(),
    }


def list_prompt_release_summaries(*, suite_version: str = "quality-v1") -> list[dict[str, Any]]:
    """Return release status summaries for every prompt task and version."""
    state = read_prompt_release_state()
    summaries: list[dict[str, Any]] = []
    for prompt_task in list_prompt_tasks():
        canary = dict((state.get("canaries") or {}).get(prompt_task.task) or {})
        history = [item for item in state.get("history") or [] if item.get("task") == prompt_task.task]
        version_summaries: list[dict[str, Any]] = []
        for version in list_prompt_versions(prompt_task.task):
            report = evaluate_prompt_release(prompt_task.task, version.version, suite_version=suite_version)
            version_summaries.append(
                {
                    "version": version.version,
                    "label": version.label,
                    "status": version.status,
                    "owner": version.owner,
                    "quality": report["metrics"],
                    "gate_passed": report["passed"],
                    "gate_reasons": list(report["reasons"]),
                }
            )
        live_version = str((state.get("live_defaults") or {}).get(prompt_task.task) or prompt_task.default_version)
        summaries.append(
            {
                "task": prompt_task.task,
                "label": prompt_task.label,
                "packaged_default_version": prompt_task.default_version,
                "live_version": live_version,
                "canary_version": str(canary.get("version") or "") or None,
                "canary_percentage": int(canary.get("percentage") or 0),
                "latest_change": history[-1] if history else None,
                "versions": version_summaries,
            }
        )
    return summaries


def apply_prompt_release(
    task: str,
    prompt_version: str,
    actor: str,
    *,
    suite_version: str = "quality-v1",
    canary_percentage: int = 100,
    notes: str | None = None,
) -> dict[str, Any]:
    """Apply a prompt release to live or as a deterministic canary."""
    report = evaluate_prompt_release(task, prompt_version, suite_version=suite_version)
    if not report["passed"]:
        raise ValueError("; ".join(report["reasons"]) or "Release gates failed.")

    actor_name = str(actor or "").strip()
    if not actor_name:
        raise ValueError("An actor name is required to apply a prompt release.")

    percentage = max(min(int(canary_percentage), 100), 1)
    now = datetime.now(UTC).isoformat()
    state = read_prompt_release_state()
    mode = "live" if percentage >= 100 else "canary"
    entry = {
        "task": task,
        "prompt_version": prompt_version,
        "mode": mode,
        "canary_percentage": percentage,
        "suite_version": suite_version,
        "applied_by": actor_name,
        "applied_at": now,
        "notes": notes,
        "metrics": report["metrics"],
    }

    if mode == "live":
        state["live_defaults"][task] = prompt_version
        state["canaries"].pop(task, None)
    else:
        baseline_version = str((state.get("live_defaults") or {}).get(task) or get_prompt_task(task).default_version)
        state["canaries"][task] = {
            "version": prompt_version,
            "percentage": percentage,
            "baseline_version": baseline_version,
            "suite_version": suite_version,
            "applied_by": actor_name,
            "applied_at": now,
            "notes": notes,
        }
    state["history"].append(entry)
    write_prompt_release_state(state)

    return {
        **report,
        "applied": entry,
        "state": read_prompt_release_state(),
    }


def rollback_prompt_release(task: str, actor: str, *, notes: str | None = None) -> dict[str, Any]:
    """Roll the live default back to the previous applied live version or packaged default."""
    actor_name = str(actor or "").strip()
    if not actor_name:
        raise ValueError("An actor name is required to roll back a prompt release.")

    prompt_task = get_prompt_task(task)
    state = read_prompt_release_state()
    history = [item for item in state.get("history") or [] if item.get("task") == task]
    current_live = str((state.get("live_defaults") or {}).get(task) or prompt_task.default_version)

    previous_live = prompt_task.default_version
    for entry in reversed(history):
        if entry.get("mode") != "live":
            continue
        candidate = str(entry.get("prompt_version") or "")
        if candidate and candidate != current_live:
            previous_live = candidate
            break

    if current_live == previous_live and not (state.get("canaries") or {}).get(task):
        raise ValueError("No earlier live release is available to roll back to.")

    now = datetime.now(UTC).isoformat()
    state["live_defaults"][task] = previous_live
    state["canaries"].pop(task, None)
    rollback_entry = {
        "task": task,
        "prompt_version": previous_live,
        "mode": "rollback",
        "rollback_from": current_live,
        "applied_by": actor_name,
        "applied_at": now,
        "notes": notes,
    }
    state["history"].append(rollback_entry)
    write_prompt_release_state(state)
    return {
        "task": task,
        "rolled_back_to": previous_live,
        "previous_live": current_live,
        "applied": rollback_entry,
        "state": read_prompt_release_state(),
    }
