"""Pydantic contracts for the public Clipmato API."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MachineError(BaseModel):
    """Standard machine-readable error payload for public API responses."""

    code: str
    status: int
    message: str
    details: dict[str, Any] | None = None


class MachineErrorEnvelope(BaseModel):
    """Envelope for error responses that also echoes the correlation ID."""

    correlation_id: str
    error: MachineError


class SecretStatusModel(BaseModel):
    configured: bool
    source: str | None = None


class RuntimeStatusModel(BaseModel):
    openai_api_key_configured: bool
    google_oauth_configured: bool
    requested_transcription_backend: str
    transcription_backend: str
    requested_content_backend: str
    content_backend: str
    local_whisper_installed: bool
    local_whisper_model: str
    local_whisper_device: str
    running_in_container: bool
    openai_content_model: str
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: int
    ollama_reachable: bool
    public_base_url: str
    settings_sources: dict[str, str] = Field(default_factory=dict)
    secret_status: dict[str, SecretStatusModel] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProjectContextModel(BaseModel):
    project_name: str | None = None
    project_summary: str | None = None
    project_topics: list[str] = Field(default_factory=list)
    project_prompt_prefix: str | None = None
    project_prompt_suffix: str | None = None


class PublishJobModel(BaseModel):
    provider: str | None = None
    display_name: str | None = None
    enabled: bool | None = None
    status: str | None = None
    scheduled_for: str | None = None
    next_attempt_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    last_attempt_at: str | None = None
    published_at: str | None = None
    attempt_count: int | None = None
    title: str | None = None
    description: str | None = None
    privacy_status: str | None = None
    remote_id: str | None = None
    remote_url: str | None = None
    last_error: str | None = None


class RecordSummaryModel(BaseModel):
    id: str
    filename: str | None = None
    display_title: str
    display_title_helper: str | None = None
    display_subtitle_helper: str | None = None
    upload_time: str | None = None
    progress: float
    stage: str
    message: str | None = None
    error: str | None = None
    schedule_time: str | None = None
    youtube_job: PublishJobModel | None = None
    detail_url: str


class RecordDetailModel(RecordSummaryModel):
    selected_title: str | None = None
    titles: list[str] = Field(default_factory=list)
    short_description: str | None = None
    long_description: str | None = None
    people: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    script: str | None = None
    distribution: Any = None
    project_context: ProjectContextModel | None = None
    publish_targets: list[str] = Field(default_factory=list)
    publish_jobs: dict[str, PublishJobModel] = Field(default_factory=dict)
    prompt_runs: dict[str, dict[str, Any]] = Field(default_factory=dict)


class RecordListResponse(BaseModel):
    records: list[RecordSummaryModel] = Field(default_factory=list)


class ProjectPresetModel(ProjectContextModel):
    id: str
    label: str


class ProjectPresetListResponse(BaseModel):
    project_presets: list[ProjectPresetModel] = Field(default_factory=list)


class UploadAcceptedResponse(BaseModel):
    id: str


class ProgressStatusResponse(BaseModel):
    stage: str
    progress: float
    message: str | None = None
    error: str | None = None


class TitleSelectionRequest(BaseModel):
    selected_title: str


class TitleUpdateResponse(BaseModel):
    id: str
    selected_title: str


class ScheduleRecordRequest(BaseModel):
    schedule_time: str
    publish_targets: list[str] = Field(default_factory=list)
    youtube_privacy_status: str = "private"


class PublishJobUpdateResponse(BaseModel):
    id: str
    schedule_time: str | None = None
    publish_targets: list[str] = Field(default_factory=list)
    publish_jobs: dict[str, PublishJobModel] = Field(default_factory=dict)


class MCPToolDefinitionModel(BaseModel):
    name: str
    description: str
    scope: str
    mutating: bool = False
    approval_required: bool = False
    supports_dry_run: bool = True
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class MCPResourceDefinitionModel(BaseModel):
    name: str
    description: str
    scope: str
    output_schema: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class MCPCapabilityResponse(BaseModel):
    supported_schema_version: str
    negotiated_schema_version: str | None = None
    compatible: bool
    supported_feature_flags: dict[str, bool] = Field(default_factory=dict)
    accepted_client_features: list[str] = Field(default_factory=list)
    accepted_scopes: list[str] = Field(default_factory=list)
    tools: list[MCPToolDefinitionModel] = Field(default_factory=list)
    resources: list[MCPResourceDefinitionModel] = Field(default_factory=list)


class MCPToolListResponse(BaseModel):
    tools: list[MCPToolDefinitionModel] = Field(default_factory=list)


class MCPResourceListResponse(BaseModel):
    resources: list[MCPResourceDefinitionModel] = Field(default_factory=list)


class MCPResourceReadResponse(BaseModel):
    resource: str
    payload: dict[str, Any] = Field(default_factory=dict)


class MCPToolInvocationRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)
    mode: str = "dry_run"
    approved: bool = False
    approval_token: str | None = None
    scopes: list[str] = Field(default_factory=list)
    actor: str = "api"


class MCPToolInvocationResponse(BaseModel):
    run_id: str
    tool_result: dict[str, Any] = Field(default_factory=dict)
    agent_run: dict[str, Any] = Field(default_factory=dict)
