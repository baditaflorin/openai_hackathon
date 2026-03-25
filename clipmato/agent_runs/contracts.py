"""Minimal JSON schema validation for tool contracts."""
from __future__ import annotations

from typing import Any


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return value.__class__.__name__


def validate_schema(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Validate a JSON-like payload against a small schema subset."""
    issues: list[str] = []
    expected_type = schema.get("type")

    if expected_type == "object":
        if not isinstance(value, dict):
            return [f"{path} expected object, got {_type_name(value)}"]
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        additional_properties = schema.get("additionalProperties", True)
        for key in required:
            if key not in value:
                issues.append(f"{path}.{key} is required")
        for key, item in value.items():
            if key in properties:
                issues.extend(validate_schema(item, properties[key], f"{path}.{key}"))
            elif not additional_properties:
                issues.append(f"{path}.{key} is not allowed")
        return issues

    if expected_type == "array":
        if not isinstance(value, list):
            return [f"{path} expected array, got {_type_name(value)}"]
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            issues.append(f"{path} expected at least {min_items} items")
        max_items = schema.get("maxItems")
        if isinstance(max_items, int) and len(value) > max_items:
            issues.append(f"{path} expected at most {max_items} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                issues.extend(validate_schema(item, item_schema, f"{path}[{index}]"))
        return issues

    if expected_type == "string":
        if not isinstance(value, str):
            return [f"{path} expected string, got {_type_name(value)}"]
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            issues.append(f"{path} expected length >= {min_length}")
        max_length = schema.get("maxLength")
        if isinstance(max_length, int) and len(value) > max_length:
            issues.append(f"{path} expected length <= {max_length}")
    elif expected_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return [f"{path} expected integer, got {_type_name(value)}"]
    elif expected_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return [f"{path} expected number, got {_type_name(value)}"]
    elif expected_type == "boolean":
        if not isinstance(value, bool):
            return [f"{path} expected boolean, got {_type_name(value)}"]
    elif expected_type == "null":
        if value is not None:
            return [f"{path} expected null, got {_type_name(value)}"]

    enum_values = schema.get("enum")
    if enum_values is not None and value not in enum_values:
        issues.append(f"{path} expected one of {enum_values!r}, got {value!r}")
    return issues


def ensure_valid_schema(value: Any, schema: dict[str, Any], *, label: str) -> None:
    """Raise a ValueError when a payload violates the declared schema."""
    issues = validate_schema(value, schema)
    if issues:
        raise ValueError(f"{label} failed schema validation: {'; '.join(issues)}")
