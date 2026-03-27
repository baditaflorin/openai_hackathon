# ADR 0029: Privacy, retention, and redaction for user content

- Status: Proposed
- Date: 2026-03-27

## Context

Clipmato stores and processes highly sensitive material: raw media, transcripts, generated descriptions, extracted entities, prompt traces, provider credentials, audit records, and telemetry. As the product becomes more agentic and event-driven, the number of places where user content can appear also increases.

That creates a trust problem unless privacy rules are explicit:

- logs and events can accidentally capture transcript fragments or secrets
- retained source media may outlive its business value
- evaluation datasets can become an unbounded copy of user content
- delete requests become difficult once content spreads across systems

Production readiness is not only about uptime. It is also about handling user data with clear boundaries.

## Decision

Clipmato will define data classification, default retention windows, and redaction rules for user content and secrets.

Classification rules:

- Data is categorized at minimum as `secret`, `source content`, `derived content`, `operational telemetry`, or `audit record`.
- Each category has an owner, allowed storage locations, and a default retention policy.
- Secrets are never embedded in logs, events, evaluations, or exported audit payloads.

Retention rules:

- Raw uploads, edited media, transcripts, prompt runs, events, and notifications each have explicit retention policies rather than indefinite storage.
- Workspaces may choose stricter retention for source media and prompt artifacts when the deployment supports it.
- Evaluation reuse of user content is opt-in and disabled by default for hosted deployments unless a workspace explicitly enables it.

Redaction and deletion rules:

- Structured logging, tracing, and webhook payloads must redact or omit transcript bodies, API keys, OAuth tokens, and other sensitive values.
- Delete workflows must remove or tombstone content in primary stores and mark backup or archive copies for eventual purge according to the retention model.
- User-facing exports clearly separate content that is retained, redacted, or already expired.

## Consequences

- User trust improves because Clipmato has explicit answers to what is stored, where, and for how long.
- Operators gain a clearer compliance and incident-response posture.
- Implementation work increases because every new artifact type needs classification, retention, and redaction rules.
- Some debugging workflows become less convenient because the safest default is to capture less raw user content.
