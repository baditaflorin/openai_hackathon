# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-03-25

### Added

- A versioned `/api/v1` surface with stable JSON envelopes, machine-readable API errors, and per-request correlation IDs.
- An MCP gateway layer under `/api/v1/mcp/*` with capability negotiation, approved tool/resource descriptors, dry-run versus live-apply execution, approval-gated sensitive tools, and in-memory `AgentRun` tracking.
- Durable event replay at `/api/v1/events` plus Server-Sent Events streaming at `/api/v1/events/stream` backed by an append-only JSONL event log.
- ADR 0017 for versioned public contracts and ADR 0020 for the MCP gateway are now accepted and implemented in `v0.4.0`.

### Changed

- Runtime settings can now be updated through the public API without relying on redirect-only form flows, and API-triggered updates emit audit/event records for downstream clients.
- The release metadata, examples, and image tags now point at `0.4.0`.

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
