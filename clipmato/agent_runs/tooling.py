"""Typed tool definitions and registry helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable


ToolExecutor = Callable[[dict[str, Any]], Any | Awaitable[Any]]
RISK_LEVELS = {"low", "medium", "high"}
APPROVAL_POLICIES = {"none", "required"}


@dataclass(slots=True)
class ToolDefinition:
    """A registered tool with strict input/output contracts."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    executor: ToolExecutor
    risk_level: str = "low"
    approval_policy: str = "none"
    max_attempts: int = 1

    def __post_init__(self) -> None:
        if self.risk_level not in RISK_LEVELS:
            raise ValueError(f"Unknown tool risk level: {self.risk_level}")
        if self.approval_policy not in APPROVAL_POLICIES:
            raise ValueError(f"Unknown approval policy: {self.approval_policy}")
        if self.max_attempts < 1:
            raise ValueError("Tool max_attempts must be >= 1")

    @property
    def requires_approval(self) -> bool:
        return self.approval_policy == "required"


class ToolRegistry:
    """In-memory registry of tool definitions."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> ToolDefinition:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool
        return tool

    def get(self, tool_name: str) -> ToolDefinition:
        try:
            return self._tools[tool_name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {tool_name}") from exc

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())
