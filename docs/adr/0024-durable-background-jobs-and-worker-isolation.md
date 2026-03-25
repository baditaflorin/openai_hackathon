# ADR 0024: Durable background jobs and worker isolation

- Status: Proposed
- Date: 2026-03-25

## Context

Clipmato already performs long-running work such as upload processing, transcription, prompt generation, scheduling, and publishing. Today, some of that work still depends on request-adjacent execution or in-process workers tied to the FastAPI app lifecycle.

That model is fragile once the system handles larger files, multiple users, or autonomous workflows:

- web requests should return quickly instead of owning long-running work
- app restarts can interrupt active tasks
- horizontal scaling becomes unsafe when workers are implicit
- retries, cancellation, and dead-letter handling remain inconsistent

ADR 0018 defined the logical state machine for agent runs. Clipmato now needs the operational execution model underneath it.

## Decision

Clipmato will execute long-running work through durable jobs claimed by dedicated workers.

Queue rules:

- Upload processing, transcription, content generation, publishing, webhook delivery, and agent execution all run as queued jobs.
- API requests enqueue work and return stable job or run identifiers immediately.
- Jobs are persisted in the relational store with explicit state, lease owner, attempt count, next retry time, and correlation metadata.

Worker rules:

- Workers run as separate processes from the web server in production deployments.
- Job claiming uses leases and heartbeats so abandoned work can be recovered after crashes.
- Every job type defines idempotency behavior, retry policy, timeout, and dead-letter criteria.
- Cancellation and pause requests are first-class state transitions, not best-effort flags hidden in worker memory.

Scheduling and scaling rules:

- Queue partitions or priorities separate latency-sensitive work from heavy batch jobs.
- Concurrency limits are configurable per job type and per workspace to prevent one tenant from starving the system.
- Local development may offer an embedded worker mode for convenience, but that mode must use the same durable queue semantics.

## Consequences

- Clipmato becomes much more reliable under restarts, concurrent usage, and production traffic.
- Operational behavior is easier to reason about because work ownership and retry state are explicit.
- The system must now manage worker deployment, queue monitoring, stuck-job recovery, and idempotency testing.
- Some current code paths will need refactoring so request handlers become orchestration layers instead of execution hosts.
