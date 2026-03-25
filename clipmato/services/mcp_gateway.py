"""Pure-Python MCP gateway and capability registry for Clipmato.

This module intentionally keeps the gateway self-contained and storage-light so
the main agent can integrate real Clipmato services later by injecting
callbacks. The registry exposes an approved, narrow surface for runtime settings
and read-only summary resources while keeping approval-gated placeholders for
sensitive classes of operations.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence
from uuid import uuid4

MCP_SCHEMA_VERSION = "1.0"

CAPABILITY_SCOPES = ("read", "runtime", "plan", "publish", "admin", "credentials")

FEATURE_FLAGS = {
    "schema_negotiation": True,
    "dry_run": True,
    "approval_gating": True,
    "audit_trail": True,
    "callback_execution": True,
    "resource_reading": True,
    "placeholder_resources": True,
}

ERROR_CODES = {
    "unknown_tool",
    "unknown_resource",
    "invalid_execution_mode",
    "scope_denied",
    "approval_required",
    "callback_missing",
    "dry_run_not_supported",
    "execution_failed",
    "invalid_arguments",
    "unsupported_schema_version",
}

LIVE_APPLY_MODE = "live_apply"
DRY_RUN_MODE = "dry_run"
SUPPORTED_EXECUTION_MODES = (DRY_RUN_MODE, LIVE_APPLY_MODE)

ToolExecutor = Callable[["ToolInvocation", "ToolDefinition"], Mapping[str, Any] | dict[str, Any] | "ToolResult"]
ResourceProvider = Callable[["ResourceDefinition", Mapping[str, Any]], Mapping[str, Any] | dict[str, Any]]
ApprovalChecker = Callable[["ToolInvocation", "ToolDefinition"], bool]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, Mapping):
        return dict(value.items())
    return {"value": value}


def _normalize_names(values: Sequence[str] | None) -> set[str]:
    if not values:
        return set()
    return {str(value).strip() for value in values if str(value).strip()}


@dataclass(frozen=True, slots=True)
class CapabilityScope:
    """A named capability boundary used by the gateway."""

    name: str
    description: str = ""
    sensitive: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Approved tool metadata exposed to MCP clients."""

    name: str
    description: str
    scope: str
    mutating: bool = False
    approval_required: bool = False
    supports_dry_run: bool = True
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tags"] = list(self.tags)
        return payload


@dataclass(frozen=True, slots=True)
class ResourceDefinition:
    """Approved read-only resource metadata exposed to MCP clients."""

    name: str
    description: str
    scope: str
    output_schema: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tags"] = list(self.tags)
        return payload


@dataclass(slots=True)
class ToolInvocation:
    """A single MCP tool invocation request."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    client_id: str = "anonymous"
    run_id: str = ""
    mode: str = LIVE_APPLY_MODE
    approved: bool = False
    approval_token: str = ""
    correlation_id: str = ""
    scopes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scopes"] = list(self.scopes)
        return payload


@dataclass(frozen=True, slots=True)
class GatewayError:
    """Stable machine-readable error object returned by the gateway."""

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(slots=True)
class ToolResult:
    """Result of executing or previewing a tool invocation."""

    ok: bool
    tool_name: str
    mode: str
    applied: bool = False
    dry_run: bool = False
    output: dict[str, Any] = field(default_factory=dict)
    error: GatewayError | None = None
    audit_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "ok": self.ok,
            "tool_name": self.tool_name,
            "mode": self.mode,
            "applied": self.applied,
            "dry_run": self.dry_run,
            "output": dict(self.output),
            "error": self.error.to_dict() if self.error else None,
            "audit_id": self.audit_id,
        }
        return payload


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """Audit trail entry for tool calls and resource reads."""

    entry_id: str
    timestamp: str
    client_id: str
    run_id: str
    action: str
    scope: str
    mode: str
    outcome: str
    approval_required: bool
    approved: bool
    error_code: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AgentRunState:
    """Minimal run state for the future agent orchestration layer."""

    run_id: str
    goal: str
    state: str = "queued"
    plan: list[str] = field(default_factory=list)
    tool_calls: list[ToolInvocation] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
    final_outcome: str = ""
    correlation_id: str = ""

    def transition_to(self, state: str) -> None:
        self.state = state

    def add_tool_call(self, invocation: ToolInvocation) -> None:
        self.tool_calls.append(invocation)

    def add_observation(self, observation: str) -> None:
        if observation:
            self.observations.append(observation)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tool_calls"] = [call.to_dict() for call in self.tool_calls]
        return payload


@dataclass(frozen=True, slots=True)
class CapabilityNegotiation:
    """Negotiated capability snapshot returned during client handshake."""

    supported_schema_version: str
    negotiated_schema_version: str | None
    compatible: bool
    supported_feature_flags: dict[str, bool]
    accepted_client_features: tuple[str, ...]
    accepted_scopes: tuple[str, ...]
    tools: tuple[ToolDefinition, ...]
    resources: tuple[ResourceDefinition, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["accepted_client_features"] = list(self.accepted_client_features)
        payload["accepted_scopes"] = list(self.accepted_scopes)
        payload["tools"] = [tool.to_dict() for tool in self.tools]
        payload["resources"] = [resource.to_dict() for resource in self.resources]
        return payload


class MCPGatewayService:
    """Approved tool/resource gateway for Clipmato agent clients."""

    def __init__(
        self,
        *,
        tool_executor: ToolExecutor | None = None,
        resource_provider: ResourceProvider | None = None,
        approval_checker: ApprovalChecker | None = None,
        tool_definitions: Sequence[ToolDefinition] | None = None,
        resource_definitions: Sequence[ResourceDefinition] | None = None,
    ) -> None:
        self._tool_executor = tool_executor
        self._resource_provider = resource_provider
        self._approval_checker = approval_checker
        self._audit_log: list[AuditEntry] = []
        self._runs: dict[str, AgentRunState] = {}
        self._tools = {definition.name: definition for definition in (tool_definitions or self._default_tools())}
        self._resources = {
            definition.name: definition for definition in (resource_definitions or self._default_resources())
        }
        self._scopes = {
            scope.name: scope
            for scope in (
                CapabilityScope("read", "Read-only access to approved resources."),
                CapabilityScope("runtime", "Runtime settings and profile management."),
                CapabilityScope("plan", "Planning and orchestration helpers."),
                CapabilityScope("publish", "Publishing and release actions.", sensitive=True),
                CapabilityScope("admin", "Administrative operations and maintenance.", sensitive=True),
                CapabilityScope("credentials", "Secret and credential operations.", sensitive=True),
            )
        }

    @property
    def audit_log(self) -> list[AuditEntry]:
        return list(self._audit_log)

    @property
    def scopes(self) -> tuple[CapabilityScope, ...]:
        return tuple(self._scopes.values())

    @property
    def tools(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._tools.values())

    @property
    def resources(self) -> tuple[ResourceDefinition, ...]:
        return tuple(self._resources.values())

    def negotiate_capabilities(
        self,
        *,
        client_schema_version: str | None = None,
        client_features: Sequence[str] | None = None,
        client_scopes: Sequence[str] | None = None,
    ) -> CapabilityNegotiation:
        accepted_features = tuple(
            sorted(name for name in _normalize_names(client_features) if FEATURE_FLAGS.get(name, False))
        )
        accepted_scopes = tuple(
            sorted(name for name in _normalize_names(client_scopes) if name in self._scopes)
        )
        compatible = self._schema_compatible(client_schema_version)
        return CapabilityNegotiation(
            supported_schema_version=MCP_SCHEMA_VERSION,
            negotiated_schema_version=MCP_SCHEMA_VERSION if compatible else None,
            compatible=compatible,
            supported_feature_flags=dict(FEATURE_FLAGS),
            accepted_client_features=accepted_features,
            accepted_scopes=accepted_scopes,
            tools=self._tools_for_scopes(accepted_scopes),
            resources=self._resources_for_scopes(accepted_scopes),
        )

    def list_tools(self, scopes: Sequence[str] | None = None) -> list[dict[str, Any]]:
        return [tool.to_dict() for tool in self._tools_for_scopes(scopes)]

    def list_resources(self, scopes: Sequence[str] | None = None) -> list[dict[str, Any]]:
        return [resource.to_dict() for resource in self._resources_for_scopes(scopes)]

    def read_resource(
        self,
        resource_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        client_id: str = "anonymous",
        run_id: str = "",
        scopes: Sequence[str] | None = None,
        correlation_id: str = "",
    ) -> dict[str, Any]:
        definition = self._resources.get(resource_name)
        if definition is None:
            return self._error_payload(
                "unknown_resource",
                f"Unknown resource: {resource_name}",
                resource_name=resource_name,
            )
        if not self._scope_allowed(definition.scope, scopes):
            return self._error_payload(
                "scope_denied",
                f"Scope '{definition.scope}' is not available to this client.",
                resource_name=resource_name,
                scope=definition.scope,
            )

        request = _coerce_mapping(arguments)
        if self._resource_provider is None:
            output = self._default_resource_payload(definition, request)
        else:
            try:
                output = _coerce_mapping(self._resource_provider(definition, request))
            except Exception as exc:  # pragma: no cover - defensive guard
                output = self._error_payload(
                    "execution_failed",
                    f"Resource provider failed for {resource_name}: {exc}",
                    resource_name=resource_name,
                    exception=type(exc).__name__,
                )
        self._append_audit(
            AuditEntry(
                entry_id=uuid4().hex,
                timestamp=_utc_now(),
                client_id=client_id,
                run_id=run_id,
                action=f"read:{resource_name}",
                scope=definition.scope,
                mode="read",
                outcome="success" if "error" not in output else "failure",
                approval_required=False,
                approved=True,
                error_code=output.get("error", {}).get("code") if isinstance(output.get("error"), dict) else None,
                details={"arguments": request, "correlation_id": correlation_id},
            )
        )
        return output

    def invoke_tool(
        self,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        client_id: str = "anonymous",
        run_id: str = "",
        mode: str = LIVE_APPLY_MODE,
        approved: bool = False,
        approval_token: str = "",
        scopes: Sequence[str] | None = None,
        correlation_id: str = "",
    ) -> ToolResult:
        definition = self._tools.get(tool_name)
        if definition is None:
            return self._tool_error(
                tool_name=tool_name,
                mode=mode,
                client_id=client_id,
                run_id=run_id,
                code="unknown_tool",
                message=f"Unknown tool: {tool_name}",
                details={"tool_name": tool_name},
            )

        if not self._scope_allowed(definition.scope, scopes):
            return self._tool_error(
                tool_name=tool_name,
                mode=mode,
                client_id=client_id,
                run_id=run_id,
                code="scope_denied",
                message=f"Scope '{definition.scope}' is not available to this client.",
                details={"tool_name": tool_name, "scope": definition.scope},
                definition=definition,
                approved=approved,
            )

        normalized_mode = self._normalize_mode(mode)
        if normalized_mode is None:
            return self._tool_error(
                tool_name=tool_name,
                mode=mode,
                client_id=client_id,
                run_id=run_id,
                code="invalid_execution_mode",
                message=f"Unsupported execution mode: {mode}",
                details={"mode": mode, "supported_modes": list(SUPPORTED_EXECUTION_MODES)},
                definition=definition,
                approved=approved,
            )

        request_arguments = _coerce_mapping(arguments)
        invocation = ToolInvocation(
            tool_name=tool_name,
            arguments=request_arguments,
            client_id=client_id,
            run_id=run_id,
            mode=normalized_mode,
            approved=approved,
            approval_token=approval_token,
            correlation_id=correlation_id,
            scopes=tuple(sorted(_normalize_names(scopes))),
        )

        run_state = self._runs.setdefault(
            run_id or uuid4().hex,
            AgentRunState(run_id=run_id or uuid4().hex, goal=f"{tool_name} invocation", correlation_id=correlation_id),
        )
        run_state.add_tool_call(invocation)
        run_state.transition_to("executing")

        if normalized_mode == LIVE_APPLY_MODE and definition.approval_required:
            approval_granted = approved or self._approval_granted(invocation, definition)
            if not approval_granted:
                run_state.transition_to("awaiting_approval")
                return self._tool_error(
                    tool_name=tool_name,
                    mode=normalized_mode,
                    client_id=client_id,
                    run_id=run_state.run_id,
                    code="approval_required",
                    message=f"Approval is required before executing {tool_name}.",
                    details={
                        "tool_name": tool_name,
                        "scope": definition.scope,
                        "approval_required": True,
                    },
                    definition=definition,
                    invocation=invocation,
                    approved=False,
                )
            invocation.approved = True

        if normalized_mode == DRY_RUN_MODE:
            if not definition.supports_dry_run:
                return self._tool_error(
                    tool_name=tool_name,
                    mode=normalized_mode,
                    client_id=client_id,
                    run_id=run_state.run_id,
                    code="dry_run_not_supported",
                    message=f"{tool_name} does not support dry-run execution.",
                    details={"tool_name": tool_name},
                    definition=definition,
                    invocation=invocation,
                    approved=invocation.approved,
                )
            if self._tool_executor is None:
                output = {
                    "dry_run": True,
                    "tool_name": tool_name,
                    "would_apply": definition.mutating,
                    "arguments": request_arguments,
                }
            else:
                output = self._execute_tool(invocation, definition)
            run_state.transition_to("completed")
            run_state.final_outcome = "dry_run"
            result = ToolResult(
                ok=True,
                tool_name=tool_name,
                mode=normalized_mode,
                applied=False,
                dry_run=True,
                output=output,
                audit_id=self._append_audit(
                    AuditEntry(
                        entry_id=uuid4().hex,
                        timestamp=_utc_now(),
                        client_id=client_id,
                        run_id=run_state.run_id,
                        action=f"tool:{tool_name}",
                        scope=definition.scope,
                        mode=normalized_mode,
                        outcome="dry_run",
                        approval_required=definition.approval_required,
                        approved=invocation.approved,
                        details={"arguments": request_arguments, "correlation_id": correlation_id},
                    )
                ).entry_id,
            )
            return result

        if self._tool_executor is None:
            run_state.transition_to("failed")
            run_state.final_outcome = "callback_missing"
            return self._tool_error(
                tool_name=tool_name,
                mode=normalized_mode,
                client_id=client_id,
                run_id=run_state.run_id,
                code="callback_missing",
                message=f"No tool executor has been configured for {tool_name}.",
                details={"tool_name": tool_name, "mode": normalized_mode},
                definition=definition,
                invocation=invocation,
                approved=invocation.approved,
            )

        output = self._execute_tool(invocation, definition)
        run_state.transition_to("completed")
        run_state.final_outcome = "success"
        result = ToolResult(
            ok=True,
            tool_name=tool_name,
            mode=normalized_mode,
            applied=definition.mutating,
            dry_run=False,
            output=output,
            audit_id=self._append_audit(
                AuditEntry(
                    entry_id=uuid4().hex,
                    timestamp=_utc_now(),
                    client_id=client_id,
                    run_id=run_state.run_id,
                    action=f"tool:{tool_name}",
                    scope=definition.scope,
                    mode=normalized_mode,
                    outcome="success",
                    approval_required=definition.approval_required,
                    approved=invocation.approved,
                    details={"arguments": request_arguments, "correlation_id": correlation_id},
                )
            ).entry_id,
        )
        return result

    def create_run_state(self, goal: str, *, run_id: str | None = None, correlation_id: str = "") -> AgentRunState:
        state = AgentRunState(run_id=run_id or uuid4().hex, goal=goal, correlation_id=correlation_id)
        self._runs[state.run_id] = state
        return state

    def get_run_state(self, run_id: str) -> AgentRunState | None:
        return self._runs.get(run_id)

    def _default_tools(self) -> tuple[ToolDefinition, ...]:
        return (
            ToolDefinition(
                name="runtime.settings.read",
                description="Read the current resolved runtime settings summary.",
                scope="runtime",
                mutating=False,
                approval_required=False,
                supports_dry_run=True,
                input_schema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "settings": {"type": "object"},
                    },
                },
                tags=("runtime", "settings", "read"),
            ),
            ToolDefinition(
                name="runtime.settings.update",
                description="Update the persisted runtime settings snapshot.",
                scope="runtime",
                mutating=True,
                approval_required=False,
                supports_dry_run=True,
                input_schema={
                    "type": "object",
                    "properties": {
                        "updates": {"type": "object"},
                    },
                    "required": ["updates"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "applied": {"type": "boolean"},
                        "resolved_settings": {"type": "object"},
                    },
                },
                tags=("runtime", "settings", "write"),
            ),
            ToolDefinition(
                name="runtime.profile.apply",
                description="Apply a named runtime profile such as local-offline or openai-cloud.",
                scope="runtime",
                mutating=True,
                approval_required=False,
                supports_dry_run=True,
                input_schema={
                    "type": "object",
                    "properties": {
                        "profile": {"type": "string"},
                    },
                    "required": ["profile"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "profile": {"type": "string"},
                        "resolved_settings": {"type": "object"},
                    },
                },
                tags=("runtime", "profile", "write"),
            ),
            ToolDefinition(
                name="credentials.update",
                description="Persist credential values for approved integrations.",
                scope="credentials",
                mutating=True,
                approval_required=True,
                supports_dry_run=True,
                input_schema={
                    "type": "object",
                    "properties": {
                        "updates": {"type": "object"},
                    },
                    "required": ["updates"],
                },
                output_schema={"type": "object"},
                tags=("credentials", "secret", "write"),
            ),
            ToolDefinition(
                name="admin.refresh",
                description="Refresh administrative caches or server-side configuration.",
                scope="admin",
                mutating=True,
                approval_required=True,
                supports_dry_run=True,
                input_schema={
                    "type": "object",
                    "properties": {},
                },
                output_schema={"type": "object"},
                tags=("admin", "maintenance"),
            ),
            ToolDefinition(
                name="publish.record",
                description="Trigger an approved publish action for a record.",
                scope="publish",
                mutating=True,
                approval_required=True,
                supports_dry_run=True,
                input_schema={
                    "type": "object",
                    "properties": {
                        "record_id": {"type": "string"},
                    },
                    "required": ["record_id"],
                },
                output_schema={"type": "object"},
                tags=("publish", "write"),
            ),
        )

    def _default_resources(self) -> tuple[ResourceDefinition, ...]:
        return (
            ResourceDefinition(
                name="runtime.summary",
                description="Placeholder summary of resolved runtime settings and feature posture.",
                scope="read",
                output_schema={"type": "object"},
                tags=("runtime", "summary"),
            ),
            ResourceDefinition(
                name="records.summary",
                description="Placeholder summary of records and their current statuses.",
                scope="read",
                output_schema={"type": "object"},
                tags=("records", "summary"),
            ),
            ResourceDefinition(
                name="prompt.run_metadata",
                description="Placeholder metadata for the latest prompt-engine runs.",
                scope="read",
                output_schema={"type": "object"},
                tags=("prompt", "metadata"),
            ),
            ResourceDefinition(
                name="publish.status",
                description="Placeholder publication status summary for pending and completed releases.",
                scope="publish",
                output_schema={"type": "object"},
                tags=("publish", "status"),
            ),
        )

    def _default_resource_payload(
        self,
        definition: ResourceDefinition,
        arguments: Mapping[str, Any],
    ) -> dict[str, Any]:
        if definition.name == "runtime.summary":
            return {
                "resource": definition.name,
                "status": "placeholder",
                "generated_at": _utc_now(),
                "settings": {
                    "scope": definition.scope,
                    "mcp_gateway": {
                        "schema_version": MCP_SCHEMA_VERSION,
                        "feature_flags": dict(FEATURE_FLAGS),
                    },
                },
                "arguments": dict(arguments),
            }
        if definition.name == "records.summary":
            return {
                "resource": definition.name,
                "status": "placeholder",
                "generated_at": _utc_now(),
                "records": {
                    "total": 0,
                    "draft": 0,
                    "published": 0,
                    "failed": 0,
                },
                "arguments": dict(arguments),
            }
        if definition.name == "prompt.run_metadata":
            return {
                "resource": definition.name,
                "status": "placeholder",
                "generated_at": _utc_now(),
                "latest_run": None,
                "arguments": dict(arguments),
            }
        if definition.name == "publish.status":
            return {
                "resource": definition.name,
                "status": "placeholder",
                "generated_at": _utc_now(),
                "channels": [],
                "arguments": dict(arguments),
            }
        return {
            "resource": definition.name,
            "status": "placeholder",
            "generated_at": _utc_now(),
            "arguments": dict(arguments),
        }

    def _tools_for_scopes(self, scopes: Sequence[str] | None) -> tuple[ToolDefinition, ...]:
        scope_names = _normalize_names(scopes)
        if not scope_names:
            return tuple(self._tools.values())
        return tuple(tool for tool in self._tools.values() if tool.scope in scope_names)

    def _resources_for_scopes(self, scopes: Sequence[str] | None) -> tuple[ResourceDefinition, ...]:
        scope_names = _normalize_names(scopes)
        if not scope_names:
            return tuple(self._resources.values())
        return tuple(resource for resource in self._resources.values() if resource.scope in scope_names)

    def _schema_compatible(self, client_schema_version: str | None) -> bool:
        if not client_schema_version:
            return True
        return str(client_schema_version).split(".", 1)[0] == MCP_SCHEMA_VERSION.split(".", 1)[0]

    def _normalize_mode(self, mode: str) -> str | None:
        normalized = str(mode or "").strip().lower()
        if normalized in SUPPORTED_EXECUTION_MODES:
            return normalized
        if normalized in {"dry-run", "preview"}:
            return DRY_RUN_MODE
        if normalized in {"apply", "live"}:
            return LIVE_APPLY_MODE
        return None

    def _scope_allowed(self, scope: str, scopes: Sequence[str] | None) -> bool:
        if scopes is None:
            return True
        return scope in _normalize_names(scopes)

    def _approval_granted(self, invocation: ToolInvocation, definition: ToolDefinition) -> bool:
        if self._approval_checker is not None:
            return bool(self._approval_checker(invocation, definition))
        return False

    def _execute_tool(self, invocation: ToolInvocation, definition: ToolDefinition) -> dict[str, Any]:
        if self._tool_executor is None:
            return {}
        try:
            result = self._tool_executor(invocation, definition)
        except Exception as exc:  # pragma: no cover - defensive guard
            raise RuntimeError(f"Tool executor failed for {definition.name}: {exc}") from exc
        if isinstance(result, ToolResult):
            return result.to_dict()
        return _coerce_mapping(result)

    def _append_audit(self, entry: AuditEntry) -> AuditEntry:
        self._audit_log.append(entry)
        return entry

    def _tool_error(
        self,
        *,
        tool_name: str,
        mode: str,
        client_id: str,
        run_id: str,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        definition: ToolDefinition | None = None,
        invocation: ToolInvocation | None = None,
        approved: bool = False,
    ) -> ToolResult:
        error = GatewayError(code=code, message=message, details=dict(details or {}))
        audit = AuditEntry(
            entry_id=uuid4().hex,
            timestamp=_utc_now(),
            client_id=client_id,
            run_id=run_id,
            action=f"tool:{tool_name}",
            scope=definition.scope if definition else "",
            mode=mode,
            outcome="failure",
            approval_required=bool(definition.approval_required) if definition else False,
            approved=approved,
            error_code=code,
            details={"arguments": invocation.arguments if invocation else {}},
        )
        return ToolResult(
            ok=False,
            tool_name=tool_name,
            mode=mode,
            applied=False,
            dry_run=mode == DRY_RUN_MODE,
            output={},
            error=error,
            audit_id=self._append_audit(audit).entry_id,
        )

    def _error_payload(self, code: str, message: str, **details: Any) -> dict[str, Any]:
        return {
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        }


__all__ = [
    "AgentRunState",
    "ApprovalChecker",
    "AuditEntry",
    "CapabilityNegotiation",
    "CapabilityScope",
    "DRY_RUN_MODE",
    "ERROR_CODES",
    "FEATURE_FLAGS",
    "GatewayError",
    "LIVE_APPLY_MODE",
    "MCPGatewayService",
    "MCP_SCHEMA_VERSION",
    "ResourceDefinition",
    "ResourceProvider",
    "SUPPORTED_EXECUTION_MODES",
    "ToolDefinition",
    "ToolExecutor",
    "ToolInvocation",
    "ToolResult",
]
