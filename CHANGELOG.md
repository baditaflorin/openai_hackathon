# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-03-25

### Added

- A first-class `AgentRun` runtime with explicit state transitions, persisted run traces, bounded tool retries, strict tool input/output contracts, and approval checkpoints for high-risk actions.
- File-backed agent-run inspection via `/agent-runs/{run_id}` so scheduling previews and live applies remain auditable after the request completes.
- A scheduler workflow that uses the new agent-run runtime to load unscheduled records, generate a schedule preview, and optionally live-apply the result through a high-risk tool contract.
- A governance layer for prompt and publish workflows with structured policy decisions, durable agent evaluation records, and release-gate reporting.
- Deterministic live apply and canary rollout support for prompt versions via `clipmato.governance.apply_prompt_release(...)`.
- Publish policy enforcement before scheduling, queueing, retrying, and promoting live prompt versions, including audited human overrides.
- Settings-page controls for prompt release evaluation, live apply, canary rollout, and rollback.
- An event-driven API surface at `/api/v1/events` with replayable Server-Sent Events and webhook registration/replay endpoints.
- Durable workflow event logging for uploads, progress transitions, record mutations, and publish lifecycle changes.
- Signed webhook delivery with retries, dead-letter tracking, and replay from failed offsets.
- A versioned public API under `/api/v1/*` covering uploads, progress, record retrieval, scheduling, publishing controls, runtime status, and project preset discovery.
- Public API correlation IDs, standard machine-readable error envelopes, and idempotency-key support for upload, schedule, and publish mutations.
- A committed OpenAPI artifact in `docs/openapi/clipmato-v1.openapi.json` plus a GitHub Actions workflow that regenerates and uploads the contract from CI.
- ADR 0017 for API-first versioned public contracts, now accepted and implemented in `v0.4.0`.
- ADR 0018 for the agent run state machine and tooling contracts, now accepted and implemented in `v0.4.0`.
- ADR 0011, ADR 0012, ADR 0014, ADR 0016, and ADR 0021, now accepted and implemented in `v0.4.0`.
- ADR 0019 for event-driven API delivery, now accepted and implemented in `v0.4.0`.

### Changed

- The scheduler UI now offers both a dry-run preview and a live-apply path, and it surfaces the latest agent-run trace directly in the page.
- Prompt rendering now always includes project-context default placeholders so project-aware prompt hooks remain safe even when optional values are omitted.
- Prompt runs now persist policy outcomes and emit task-level governance evaluations alongside the existing prompt run ledger.
- Long-running workflow visibility no longer depends only on polling; Clipmato now emits durable domain events alongside the existing polling endpoints.
- FastAPI now publishes its public contract docs at `/api/v1/openapi.json` and `/api/v1/docs`, while legacy UI routes remain available without being exposed as public schema.

### Fixed

- Configuration startup now initializes the runtime data directory before deriving the hashed static asset build directory.

## [0.3.0] - 2026-03-09

### Added

- A dedicated `/settings` experience for choosing transcription/content backends, local Whisper preferences, Ollama endpoint/model settings, and the public callback base URL.
- Saved secret storage for OpenAI API keys and Google OAuth client credentials, separate from episode metadata and prompt ledgers.
- Docker support for optional local AI services via a `local-ai` Compose profile and a build arg for installing local Whisper directly into the web image.
- ADR 0010 for runtime settings and provider credentials, now accepted and implemented in `v0.3.0`.

### Changed

- Runtime resolution now prefers saved user settings over environment defaults and uses saved secrets for OpenAI transcription, OpenAI content generation, and Google OAuth setup.
- YouTube OAuth callback URLs now honor the saved runtime base URL instead of depending only on deployment-time environment configuration.
- The dashboard runtime snapshot now links directly to the new Settings area and surfaces credential source details more clearly.
- The header workflow summary cards now stay fully inside the dark hero surface with stronger contrast so the metrics remain readable.

## [0.2.0] - 2026-03-08

### Added

- ADR system in `docs/adr`, including a template and initial accepted decisions.
- Local/backend runtime selection with optional host-native Whisper transcription.
- Runtime status messaging in the web UI for missing API keys and backend selection.
- ADR for provider-based publishing integrations with a YouTube-first rollout.
- Four frontend architecture decisions covering design system, app shell/navigation, progressive enhancement, and accessibility/performance quality gates.
- ADR for a versioned prompt engine with prompt evaluation and output contracts for titles, descriptions, and other generated content.
- A provider-based publishing implementation with YouTube OAuth, scheduled upload jobs, retry handling, and provider-scoped publish metadata.
- Scheduler controls for connecting YouTube, queueing immediate publishes, retrying failed publishes, and tracking provider status per record.
- Automatic `.env` loading for host-native runs.
- A versioned prompt engine with packaged prompt assets, per-task output contracts, prompt run storage, and prompt evaluation storage.
- Prompt run metadata is now attached to records so title, description, entity, script, and distribution outputs can be traced back to exact prompt versions.
- Title selection and successful publish events now emit prompt evaluation signals for later prompt-quality analysis.

### Changed

- The web UI now uses a shared application shell, token-based design system, workflow-first page structure, and centralized progressive enhancement for uploads and long-running actions.
- Web pages now load all first-party assets locally instead of depending on the Bootstrap CDN for initial paint.
- When no valid transcription backend is available, uploads fail immediately with a clear message instead of stalling in background processing.
- When OpenAI-backed content generation is unavailable, Clipmato now falls back to lightweight local descriptions, titles, entities, and script generation.
- Metadata writes are now serialized in-process so background publish jobs and web requests do not race on `metadata.json`.
- Packaged installs now include nested Jinja partial templates so the shared frontend shell renders correctly outside the source checkout.
- Prompt-backed generation steps now resolve definitions from the prompt registry instead of embedding inline instructions in code.

## [0.1.0] - 2026-03-08

### Added

- Installable packaging via `pyproject.toml` with CLI entrypoints for the web app, GUI, and pipeline.
- Docker runtime support with a production-oriented `Dockerfile`.
- `docker-compose.yml` with a named volume for persistent uploads and metadata.
- Configurable runtime data storage via `CLIPMATO_DATA_DIR` so the container can run independently of the repository location.
