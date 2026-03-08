"""Output parsing and validation contracts for promptable tasks."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Normalized task output plus validation details."""

    normalized: Any
    passed: bool
    issues: tuple[str, ...]


def strip_code_fences(raw: str) -> str:
    """Remove a surrounding markdown code fence when models return one."""
    text = (raw or "").strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines.pop(0)
    if lines and lines[-1].startswith("```"):
        lines.pop()
    return "\n".join(lines).strip()


def parse_task_output(task: str, raw: str) -> Any:
    """Parse raw model output into the task's structured shape."""
    text = strip_code_fences(raw)
    if task == "title_suggestion":
        try:
            data = json.loads(text)
            return data if isinstance(data, list) else []
        except Exception:
            return [line.strip("- ").strip() for line in text.splitlines() if line.strip()]
    if task in {"description_generation", "entity_extraction"}:
        return json.loads(text)
    return text.strip()


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _validate_title_suggestion(output: Any, contract: dict[str, Any]) -> ValidationResult:
    issues: list[str] = []
    desired_count = max(int(contract.get("count", 5)), 1)
    max_item_length = max(int(contract.get("max_item_length", 90)), 8)
    if not isinstance(output, list):
        return ValidationResult([], False, ("Model output was not a list.",))

    titles: list[str] = []
    seen: set[str] = set()
    for item in output:
        title = _normalize_text(item)
        if not title:
            continue
        if len(title) > max_item_length:
            title = title[: max_item_length - 3].rstrip() + "..."
            issues.append("One or more titles were trimmed to the maximum length.")
        key = title.casefold()
        if key in seen:
            issues.append("Duplicate titles were removed.")
            continue
        seen.add(key)
        titles.append(title)
        if len(titles) >= desired_count:
            break

    if len(titles) != desired_count:
        issues.append(f"Expected {desired_count} titles but received {len(titles)}.")
    return ValidationResult(titles, len(titles) == desired_count, tuple(issues))


def _validate_description_generation(output: Any, contract: dict[str, Any]) -> ValidationResult:
    if not isinstance(output, dict):
        return ValidationResult({}, False, ("Model output was not a JSON object.",))

    issues: list[str] = []
    max_lengths = dict(contract.get("max_lengths") or {})
    normalized: dict[str, str] = {}
    required_keys = tuple(contract.get("required_keys") or ("short_description", "long_description"))
    for key in required_keys:
        value = _normalize_text(output.get(key, ""))
        if not value:
            issues.append(f"Missing required field: {key}.")
            continue
        limit = int(max_lengths.get(key, 0) or 0)
        if limit and len(value) > limit:
            value = value[: limit - 3].rstrip() + "..."
            issues.append(f"{key} was trimmed to {limit} characters.")
        normalized[key] = value
    return ValidationResult(normalized, len(normalized) == len(required_keys), tuple(issues))


def _normalize_name_list(values: Any, *, max_items: int) -> list[str]:
    if isinstance(values, str):
        candidates = [values]
    elif isinstance(values, list):
        candidates = values
    else:
        candidates = []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in candidates:
        item = _normalize_text(value)
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(item)
        if len(normalized) >= max_items:
            break
    return normalized


def _validate_entity_extraction(output: Any, contract: dict[str, Any]) -> ValidationResult:
    if not isinstance(output, dict):
        return ValidationResult({}, False, ("Model output was not a JSON object.",))

    max_items = max(int(contract.get("max_items_per_list", 8)), 1)
    issues: list[str] = []
    normalized = {
        "people": _normalize_name_list(output.get("people", []), max_items=max_items),
        "locations": _normalize_name_list(output.get("locations", []), max_items=max_items),
    }
    if "people" not in output:
        issues.append("Missing `people`; defaulted to an empty list.")
    if "locations" not in output:
        issues.append("Missing `locations`; defaulted to an empty list.")
    return ValidationResult(normalized, True, tuple(issues))


def _validate_text_output(output: Any, contract: dict[str, Any]) -> ValidationResult:
    text = str(output or "").strip()
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    min_length = max(int(contract.get("min_length", 1)), 1)
    max_length = int(contract.get("max_length", 0) or 0)
    issues: list[str] = []
    if max_length and len(text) > max_length:
        text = text[: max_length - 3].rstrip() + "..."
        issues.append(f"Output was trimmed to {max_length} characters.")
    return ValidationResult(text, len(text) >= min_length, tuple(issues))


def validate_task_output(task: str, output: Any, contract: dict[str, Any]) -> ValidationResult:
    """Validate and normalize structured output for a prompt task."""
    if task == "title_suggestion":
        return _validate_title_suggestion(output, contract)
    if task == "description_generation":
        return _validate_description_generation(output, contract)
    if task == "entity_extraction":
        return _validate_entity_extraction(output, contract)
    return _validate_text_output(output, contract)
