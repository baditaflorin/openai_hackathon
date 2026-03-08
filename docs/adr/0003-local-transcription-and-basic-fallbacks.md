# ADR 0003: Local transcription and basic fallback backends

- Status: Accepted (Implemented in v0.2.0)
- Date: 2026-03-08

## Context

Clipmato originally depended on OpenAI-backed transcription and agent steps for core processing. That caused two practical problems:

- uploads failed when `OPENAI_API_KEY` was not configured
- users on capable local machines could not trade cloud cost for local execution

The project also needed a clearer runtime story for Docker versus host-native macOS execution.

## Decision

Clipmato supports selectable runtime backends:

- transcription backend: `openai`, `local-whisper`, or `auto`
- content backend: `openai`, `local`, or `auto`

Behavior rules:

- `auto` transcription prefers OpenAI when an API key is present, otherwise it uses local Whisper if installed.
- `auto` content generation prefers OpenAI when an API key is present, otherwise it uses lightweight local fallbacks.
- local Whisper uses automatic device selection across `cuda`, `mps`, and `cpu`.
- if no valid transcription backend is available, uploads fail immediately with a clear configuration error instead of failing deep in background processing.

## Consequences

- The web UI now makes backend configuration problems visible before a long-running job starts.
- Host-native macOS runs can use Apple GPU acceleration through the local Whisper path.
- Docker remains a portable default, but Apple GPU acceleration requires a native macOS process rather than the Linux container runtime.
- Local content fallbacks are intentionally simpler than model-backed outputs and are a quality tradeoff in exchange for zero API cost.
