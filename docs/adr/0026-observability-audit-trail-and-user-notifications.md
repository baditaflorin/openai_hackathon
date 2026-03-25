# ADR 0026: Observability, audit trail, and user notifications

- Status: Proposed
- Date: 2026-03-25

## Context

As Clipmato moves toward asynchronous jobs, agent runs, policy gates, and third-party publishing, silent failure becomes a serious product risk. Users need to know what happened to their uploads and scheduled publishes, while operators need enough telemetry to diagnose latency, errors, and regressions.

Today, some state is visible in the UI, but there is not yet a unified production model for:

- tracing a request into jobs, events, and publish side effects
- auditing sensitive actions such as credential changes or policy overrides
- notifying users when work completes, fails, or needs attention
- measuring reliability with actionable service-level indicators

## Decision

Clipmato will adopt a shared observability and trust layer spanning operations, security, and user-facing status updates.

Telemetry rules:

- Structured logs, metrics, and traces must include correlation IDs from ADR 0017 plus workspace, actor, and job or run identifiers where applicable.
- Production dashboards track queue latency, job success rates, publish outcomes, webhook delivery health, fallback rates, and dependency availability.
- Liveness, readiness, and dependency health endpoints are mandatory for deployed environments.

Audit rules:

- Sensitive actions append immutable audit records, including actor, target resource, action type, timestamp, and outcome.
- Audit coverage includes credential changes, provider connections, publish requests, delete operations, approval decisions, and policy overrides.
- Secrets, raw tokens, and other sensitive payloads are never written into logs, traces, or audit bodies.

Notification rules:

- Users receive in-product notifications for job completion, failures, approvals required, and publish outcomes.
- Optional outbound notifications such as email or webhook callbacks may be enabled per workspace.
- Notification delivery is asynchronous, retryable, and linked back to the originating job, event, or audit record.

## Consequences

- Users gain clearer feedback and more trust in long-running or autonomous workflows.
- Operators can debug incidents faster and enforce accountability for high-risk actions.
- The project must invest in retention policies, redaction rules, alert tuning, and dashboard ownership.
- Additional telemetry volume and notification plumbing introduce operational cost that should be budgeted explicitly.
