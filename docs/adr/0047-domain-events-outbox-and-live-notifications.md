# ADR 0047: Domain events, outbox, and live notifications

- Status: Proposed
- Date: 2026-03-31

## Context

Clipmato already produces state changes that matter to users and future integrations:

- uploads are accepted
- processing starts and finishes
- titles are approved
- schedules are saved
- provider jobs are queued, retried, blocked, and published
- runtime readiness changes when a profile or credential changes

Today these changes are mostly observed indirectly through page refreshes, record reads, or progress polling. That is enough for the current prototype, but it does not give the app a clean foundation for live UX, automation, or external integrations.

## Decision

Clipmato will emit explicit domain events for important business transitions and store them in an outbox-backed event log.

Event rules:

- Every accepted command and every meaningful run-state transition produces one domain event.
- Events are append-only and immutable.
- Events carry `event_id`, `event_type`, `aggregate_type`, `aggregate_id`, `occurred_at`, `correlation_id`, `actor`, `payload`, and `schema_version`.

Initial event set:

- `episode.created`
- `episode.asset.attached`
- `episode.processing.started`
- `episode.processing.completed`
- `episode.processing.failed`
- `editorial.title.accepted`
- `editorial.description.approved`
- `release.plan.saved`
- `publish.job.queued`
- `publish.job.state_changed`
- `publish.job.published`
- `runtime.profile.applied`
- `runtime.readiness.changed`
- `provider.connection.changed`
- `automation.recipe.executed`

Delivery rules:

- The event log is the system of record for downstream notifications and integrations.
- An outbox projection delivers events to SSE streams, webhook workers, and automation triggers.
- The web UI should move from route-local polling toward event-fed updates where it improves clarity.
- Consumers must treat events as at-least-once and deduplicate by `event_id`.

## Consequences

- The app becomes much easier to automate because triggers can listen for clear business events instead of scraping state.
- Live UX becomes cleaner because progress and publish changes can be pushed instead of repeatedly polled.
- Auditing improves because state transitions have a consistent history.
- Clipmato will need event schema discipline and replay-safe delivery logic.
- This ADR provides the practical integration path that makes API-first, automation, and future MCP-style clients feel like first-class citizens instead of add-ons.
