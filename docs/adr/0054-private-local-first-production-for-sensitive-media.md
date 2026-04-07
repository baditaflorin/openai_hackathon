# ADR 0054: Private local-first production for sensitive media

- Status: Proposed
- Date: 2026-04-04

## Context

Clipmato already supports several runtime modes:

- OpenAI-backed transcription and content generation
- local Whisper transcription
- Ollama or local-basic content generation
- host-native execution for macOS and self-hosted environments

Those capabilities are more than deployment options. Together they support an important user need:

- creators with cost constraints
- teams handling sensitive interviews or internal recordings
- self-hosted operators who want the core workflow to work without cloud dependencies

If this use case is not made explicit, cloud-backed paths will tend to receive the most design attention and local execution will decay into a best-effort fallback.

## Decision

Clipmato will support private local-first production as a primary use case.

Rules for this use case:

- Core episode intake, transcription, editorial generation, and scheduling must remain usable without requiring an OpenAI API key.
- Settings, readiness checks, and onboarding must clearly distinguish required capabilities from optional cloud enhancements.
- Local-first and host-native runtime profiles should remain first-class documented paths, not hidden expert modes.
- Provider publishing may depend on external services, but external publishing must stay optional and clearly separated from the local production path.
- Sensitive media handling should prefer local storage, explicit credential boundaries, and minimal unnecessary outbound traffic.

## Consequences

- Clipmato becomes viable for privacy-sensitive, self-hosted, and cost-conscious operators.
- The product keeps a strong differentiator relative to cloud-only media workflow tools.
- Local execution quality and speed may vary by hardware, so the app must communicate tradeoffs clearly.
- Supporting both cloud and local paths adds runtime complexity, but it is justified because it enables a materially different and valuable use case.
