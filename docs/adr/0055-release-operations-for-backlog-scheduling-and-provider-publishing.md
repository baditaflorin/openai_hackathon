# ADR 0055: Release operations for backlog scheduling and provider publishing

- Status: Proposed
- Date: 2026-04-04

## Context

Finishing editorial work is not the end of the job. Clipmato already includes:

- a scheduling board and calendar
- dry-run and live-apply auto-scheduling
- persisted agent-run traces for scheduling actions
- provider-scoped publish jobs and retries
- YouTube as the first live publishing target

That makes release management a real product surface, not a small final step. Users need to manage a backlog, coordinate dates, inspect provider status, and recover from failed publish attempts.

Without an explicit use-case decision, scheduling and publishing risk being treated as optional extras rather than core workflow operations.

## Decision

Clipmato will treat release operations as a primary use case for operators managing an episode backlog and provider publishing state.

Rules for this use case:

- Multi-episode scheduling must support both manual control and generated proposals.
- Batch scheduling actions should prefer preview or dry-run modes before side effects are applied.
- Publish state must be tracked per provider so generic schedule intent and provider execution do not collapse into one field.
- Failures, retries, and blocked publish jobs must be visible in operator-facing views with clear remediation.
- Future provider integrations should plug into the same release model instead of inventing provider-specific workflow screens.

## Consequences

- Clipmato supports real release coordination work rather than stopping at content generation.
- Teams can trust the scheduler and publish board as an operational control plane, not just a convenience form.
- Provider-aware state modeling becomes more important and may add complexity to storage and UI design.
- Some targets will remain planned rather than live, so the product must clearly show which release capabilities are operational today.
