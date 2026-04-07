# ADR 0056: Programmatic integration for API, events, and automation

- Status: Proposed
- Date: 2026-04-04

## Context

Clipmato is no longer only a browser application. The repository already exposes or prepares several integration surfaces:

- a versioned public API
- idempotent write operations
- progress endpoints
- event emission and webhook-style delivery concepts
- persisted agent runs
- MCP gateway and automation-oriented architecture decisions

These pieces point to a broader use case:

- external systems upload or schedule episodes
- operators connect Clipmato to other workflow tools
- automations react to lifecycle events and perform repeatable actions safely

If that use case stays implicit, integrations will end up depending on route-local behavior or private implementation details.

## Decision

Clipmato will treat programmatic integration as a primary use case, with API, event, and automation clients considered first-class consumers of the platform.

Rules for this use case:

- Important workflow actions must be reachable through stable application contracts, not only through the HTML UI.
- Retriable client operations should remain idempotent where practical so external callers can recover safely from network failures.
- Long-running work must expose inspectable progress, final outcomes, and durable run traces.
- Event and automation paths must honor the same policy, approval, and audit expectations as human-triggered actions.
- Internal refactors should preserve public workflow contracts or version them explicitly when behavior changes.

## Consequences

- Clipmato becomes easier to embed inside larger editorial, media, or agentic systems.
- Integrations can rely on supported contracts instead of reverse-engineering browser flows.
- Product and architecture work gain an additional constraint: internal convenience changes can no longer silently break external clients.
- This use case reinforces the need for stable command, event, and policy boundaries across the application.
