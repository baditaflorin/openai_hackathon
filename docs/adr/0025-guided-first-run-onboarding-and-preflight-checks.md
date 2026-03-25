# ADR 0025: Guided first-run onboarding and preflight checks

- Status: Proposed
- Date: 2026-03-25

## Context

Clipmato now supports multiple execution modes: OpenAI-backed processing, local Whisper, Ollama, YouTube OAuth, scheduler flows, and prompt customization. That flexibility is valuable, but the first-run experience still assumes a technically confident user who has read the README and can diagnose setup failures alone.

For a production-ready product, users need a faster path from installation to first successful outcome:

- first-time users should know which setup path fits them
- backend or dependency problems should be discoverable before a failed upload
- publishing setup should be validated before a scheduled job misses its slot
- hosted deployments should expose health and readiness in user-facing language

Without guided setup, Clipmato remains easy to demo but harder to trust or recommend.

## Decision

Clipmato will add a guided onboarding and preflight system for first-run and ongoing environment validation.

Onboarding rules:

- First launch routes users through a setup checklist until the minimum required capabilities for their chosen workflow are configured.
- The product offers opinionated setup profiles such as `local-offline`, `OpenAI cloud`, and `publishing-ready`.
- Each profile explains tradeoffs in plain language, including cost, speed, hardware needs, and required credentials.

Validation rules:

- Clipmato performs environment detection for prerequisites such as `ffmpeg`, local Whisper availability, Ollama reachability, OpenAI credentials, public base URL, and provider authorization status.
- Settings screens include connection-test actions and dry-run validation for every external dependency.
- Before starting a workflow, preflight checks block unsupported actions or downgrade them with explicit user-facing warnings and remediation guidance.

UX rules:

- Runtime status cards use plain-language health states such as `ready`, `needs setup`, `degraded`, and `offline`.
- Failures must surface the exact missing dependency or invalid setting, not a generic stack trace.
- The application keeps a persistent setup summary so users can return later and see what is already configured.

## Consequences

- First successful use becomes faster, especially for self-hosted or non-developer users.
- Support burden drops because common setup mistakes are caught before they turn into broken workflows.
- The product must maintain environment probes, validation endpoints, and explanatory copy as integrations evolve.
- Some advanced users may see more upfront UI, so onboarding should remain skippable once the instance is healthy.
