# ADR 0062: Runtime capability resolution from settings, environment, and readiness

- Status: Accepted (Current repository convention)
- Date: 2026-04-07

## Context

Clipmato supports several execution modes:

- OpenAI-backed transcription and content generation
- local Whisper transcription
- Ollama-backed content generation
- local-basic fallback generation
- host-native and containerized runs

This flexibility is a product strength, but it also creates onboarding confusion unless there is one clear rule for how runtime choices are resolved.

## Decision

Clipmato will resolve runtime behavior through one layered capability model.

Resolution rules:

- Environment variables provide install-level defaults.
- Persisted non-secret settings override those defaults for the active data directory.
- Secrets are stored separately from non-secret runtime settings.
- CLI flags work by setting environment variables before app startup rather than bypassing the runtime layer.
- `clipmato/runtime.py` is the central place for derived runtime choices, readiness blockers, warnings, and backend detection.
- Feature code should call runtime helpers such as `resolve_transcription_backend()` or `get_runtime_status()` instead of reading environment variables directly.

Operator rule:

- Readiness information shown in the UI or API should come from the same runtime-status source so users and automations see the same blockers and warnings.

## Consequences

- Local-first, cloud-backed, and hybrid runs share one understandable resolution path.
- Support and debugging get easier because setting precedence is explicit: saved settings override environment defaults, which override built-in defaults.
- Contributors must resist shortcutting the runtime layer in individual features, or the status model will drift.
