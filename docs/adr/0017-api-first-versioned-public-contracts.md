# ADR 0017: API-first versioned public contracts

- Status: Accepted (Implemented in v0.4.0)
- Date: 2026-03-24

## Context

Clipmato currently works well as a web app, but most core behavior is still UI-driven. Future clients will include automation jobs, external integrations, agent workers, and eventually MCP tool consumers.

Without a stable API contract:

- integrations couple directly to internal implementation details
- behavior changes are hard to roll out safely
- agent and workflow features cannot be reused across clients
- schema drift becomes a recurring source of regressions

## Decision

Clipmato will adopt an API-first architecture with explicit, versioned contracts.

API contract rules:

- All externally supported endpoints live under `/api/v1/*`.
- JSON request and response schemas are documented in OpenAPI and published from CI artifacts.
- Breaking changes require a new API version (`/api/v2`) instead of in-place mutation.
- Non-breaking additions are allowed in the same version when optional and backward compatible.
- Error responses use a standard machine-readable error object with stable error codes.
- Mutating endpoints support idempotency keys where retries are expected (upload/process/schedule/publish).
- Each request gets a correlation ID that is returned in response headers and written into logs/events.

Delivery rules:

- The web UI consumes these API endpoints instead of private in-process logic over time.
- SDK/client generation is permitted only from the committed OpenAPI source.
- Deprecations must include a published sunset date and migration notes.

## Consequences

- Clipmato gains a reusable platform surface for UI, CLI, automation, and agent clients.
- Integration quality improves because contracts are explicit and testable.
- The team must invest in schema reviews, contract tests, and API lifecycle governance.
- Initial development speed may dip while legacy UI paths are migrated to the API boundary.
