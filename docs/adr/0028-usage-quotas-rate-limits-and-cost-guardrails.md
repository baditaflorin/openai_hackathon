# ADR 0028: Usage quotas, rate limits, and cost guardrails

- Status: Proposed
- Date: 2026-03-27

## Context

Clipmato now supports workflows that can consume expensive or scarce resources: OpenAI-backed generation, local GPU or CPU transcription, long-running workers, outbound publishing, webhooks, and future multi-user API access.

Without explicit guardrails, a production deployment is exposed to two classes of failure:

- accidental overuse by legitimate users who do not realize the cost of a workflow
- abusive or runaway traffic that harms reliability for everyone else

Production readiness requires both operator protection and clear user-facing feedback before work is rejected or unexpectedly expensive.

## Decision

Clipmato will implement workspace-aware usage accounting, rate limits, and budget controls.

Accounting rules:

- Usage is metered per workspace and actor for storage consumed, media minutes processed, model usage, active jobs, outbound notifications, and publish attempts.
- Metering is written to a durable usage ledger so billing, audits, and support investigations can rely on the same source of truth.
- Expensive jobs expose a preflight estimate before execution when a reasonable estimate is possible.

Guardrail rules:

- Soft limits warn users before they cross a threshold.
- Hard limits block new work when a quota is exhausted, while preserving access to existing records and exports.
- API and MCP endpoints enforce rate limits by token, actor, workspace, and IP class where appropriate.
- High-cost actions may require elevated roles or explicit confirmation when a workspace is near budget exhaustion.

UX rules:

- Users can see current usage, recent spikes, and remaining quota from the product UI.
- Limit errors return actionable machine-readable codes and user-facing remediation text.
- Limit policies are transparent so users understand whether a failure is due to cost, concurrency, or abuse protection.

## Consequences

- Reliability improves because one workload cannot quietly exhaust shared resources.
- Users get clearer expectations about what a workflow will cost in time, compute, or quota.
- The product must define fair default quotas, maintain a usage ledger, and handle edge cases around retries and idempotency.
- Some actions will become more policy-driven, which adds operational complexity but makes hosted deployment much safer.
