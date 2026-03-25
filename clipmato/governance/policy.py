"""Centralized policy checks for generated output and publish actions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


_BLOCKED_CONTENT_RULES = (
    ("buy followers", "Remove artificial growth claims before publishing."),
    ("click here", "Replace generic linkbait phrasing with concrete editorial copy."),
    ("pirated", "Remove infringement language and describe only legitimate distribution."),
)


@dataclass(frozen=True, slots=True)
class PolicyIssue:
    """One structured policy finding."""

    code: str
    severity: str
    message: str
    remediation_hint: str

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "remediation_hint": self.remediation_hint,
        }


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """Structured result of evaluating a policy subject."""

    status: str
    risk_level: str
    issues: tuple[PolicyIssue, ...] = ()
    override_used: bool = False
    override_actor: str | None = None
    override_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "risk_level": self.risk_level,
            "issues": [issue.as_dict() for issue in self.issues],
            "override_used": self.override_used,
            "override_actor": self.override_actor,
            "override_reason": self.override_reason,
            "metadata": dict(self.metadata),
        }

    def summary_message(self) -> str:
        if not self.issues:
            return "Policy checks passed."
        return self.issues[0].message


def _normalize_override(override: dict[str, str] | None) -> dict[str, str] | None:
    if not override:
        return None
    actor = str(override.get("actor") or "").strip()
    reason = str(override.get("reason") or "").strip()
    if not actor or not reason:
        return None
    return {
        "actor": actor,
        "reason": reason,
    }


def _iter_text_fragments(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        fragments: list[str] = []
        for item in value.values():
            fragments.extend(_iter_text_fragments(item))
        return fragments
    if isinstance(value, (list, tuple)):
        fragments: list[str] = []
        for item in value:
            fragments.extend(_iter_text_fragments(item))
        return fragments
    return []


def _blocked_content_issues(value: Any, *, severity: str) -> list[PolicyIssue]:
    text = "\n".join(_iter_text_fragments(value)).casefold()
    issues: list[PolicyIssue] = []
    for term, hint in _BLOCKED_CONTENT_RULES:
        if term in text:
            issues.append(
                PolicyIssue(
                    code=f"blocked_term_{term.replace(' ', '_')}",
                    severity=severity,
                    message=f"Blocked phrase detected: {term!r}.",
                    remediation_hint=hint,
                )
            )
    return issues


def evaluate_prompt_output(task: str, output: Any) -> PolicyDecision:
    """Evaluate generated task output before it is accepted downstream."""
    del task  # Reserved for task-specific rules as the policy layer grows.
    issues = _blocked_content_issues(output, severity="medium")
    if issues:
        return PolicyDecision(
            status="failed",
            risk_level="medium",
            issues=tuple(issues),
        )
    return PolicyDecision(status="passed", risk_level="low")


def evaluate_publish_action(
    record: dict[str, Any],
    provider_key: str,
    action: str,
    *,
    override: dict[str, str] | None = None,
) -> PolicyDecision:
    """Evaluate a publish-side effect before it executes."""
    del provider_key  # Reserved for provider-specific rules as more targets go live.
    override_payload = _normalize_override(override)
    blocking_issues: list[PolicyIssue] = []
    override_issues: list[PolicyIssue] = []

    selected_title = str(record.get("selected_title") or "").strip()
    if not selected_title:
        blocking_issues.append(
            PolicyIssue(
                code="missing_selected_title",
                severity="medium",
                message="Publishing requires a selected public title.",
                remediation_hint="Choose a title on the record page before scheduling or publishing.",
            )
        )

    has_description = bool(str(record.get("short_description") or "").strip() or str(record.get("long_description") or "").strip())
    if not has_description:
        blocking_issues.append(
            PolicyIssue(
                code="missing_description",
                severity="medium",
                message="Publishing requires generated description copy.",
                remediation_hint="Regenerate or author the episode description before publishing.",
            )
        )

    if action == "schedule" and not str(record.get("schedule_time") or "").strip():
        blocking_issues.append(
            PolicyIssue(
                code="missing_schedule_time",
                severity="medium",
                message="Scheduling requires a release time.",
                remediation_hint="Choose a release time before saving the publish schedule.",
            )
        )

    override_issues.extend(
        _blocked_content_issues(
            [
                record.get("selected_title"),
                record.get("short_description"),
                record.get("long_description"),
            ],
            severity="high",
        )
    )

    for task_key in ("title_suggestion", "description_generation"):
        prompt_run = dict((record.get("prompt_runs") or {}).get(task_key) or {})
        if not prompt_run:
            continue
        if prompt_run.get("used_fallback") or not prompt_run.get("validation_passed", True):
            override_issues.append(
                PolicyIssue(
                    code=f"{task_key}_needs_review",
                    severity="high",
                    message=f"{task_key.replace('_', ' ')} used fallback or failed validation.",
                    remediation_hint="Review the generated copy or re-run the prompt before publishing.",
                )
            )

    if blocking_issues:
        return PolicyDecision(
            status="failed",
            risk_level="medium",
            issues=tuple(blocking_issues + override_issues),
            metadata={"action": action},
        )

    if override_issues and override_payload is None:
        return PolicyDecision(
            status="override_required",
            risk_level="high",
            issues=tuple(override_issues),
            metadata={"action": action},
        )

    return PolicyDecision(
        status="passed",
        risk_level="high" if override_issues else "low",
        issues=tuple(override_issues),
        override_used=bool(override_payload and override_issues),
        override_actor=(override_payload or {}).get("actor"),
        override_reason=(override_payload or {}).get("reason"),
        metadata={"action": action},
    )
