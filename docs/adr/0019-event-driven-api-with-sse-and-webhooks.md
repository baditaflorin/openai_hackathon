# ADR 0019: Event-driven API with SSE and webhooks

- Status: Proposed
- Date: 2026-03-24

## Context

Clipmato currently exposes progress through polling-oriented endpoints. As automation usage and agent runs increase, polling alone creates latency, load, and weak integration ergonomics.

To support API-first and agentic workflows, clients need near-real-time updates and durable event records.

## Decision

Clipmato will adopt an event-driven integration model for long-running and stateful workflows.

Event model:

- Core workflow transitions emit domain events into an append-only event log.
- Events include `event_id`, `aggregate_id` (record/run/job), `type`, `timestamp`, `payload`, and `correlation_id`.
- Consumers treat events as at-least-once and deduplicate by `event_id`.

Delivery model:

- Real-time consumption is supported with Server-Sent Events at `/api/v1/events/stream`.
- Outbound webhooks are supported per tenant/user for integration callbacks.
- Webhooks are signed, retried with backoff, and can be replayed from a failed offset.
- API filters allow clients to subscribe by scope (`record_id`, `run_id`, `publish_job_id`, event type).

Operational model:

- Polling endpoints remain available initially for backward compatibility.
- Event retention and compaction policies are explicit and configurable.
- Dead-letter handling is required for repeatedly failing webhook deliveries.

## Consequences

- Integrators and internal clients gain lower-latency, more scalable synchronization paths.
- Agent UX improves because run and approval state changes can be pushed instantly.
- The system must manage delivery reliability, signature key rotation, and replay tooling.
- Event schema versioning becomes a new compatibility surface that needs governance.
