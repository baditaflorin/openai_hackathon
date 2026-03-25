# ADR 0018: Agent run state machine and tooling contracts

- Status: Accepted (Implemented in v0.4.0)
- Date: 2026-03-24

## Context

Clipmato has orchestration logic, but it is still primarily pipeline-style and task-specific. To become more agentic, the system needs a generic run model that can plan, call tools, recover from partial failure, and remain auditable.

Without a run model:

- autonomous behavior is difficult to reason about
- tool usage becomes inconsistent across features
- retries and recovery are ad hoc
- governance and human review are difficult to enforce

## Decision

Clipmato will introduce a first-class `AgentRun` domain model and a typed tool contract layer.

Run model:

- `AgentRun` objects track `goal`, `plan`, `steps`, `tool_calls`, `observations`, and `final_outcome`.
- Every run follows an explicit state machine: `queued -> planning -> executing -> awaiting_approval -> completed|failed|cancelled`.
- Step-level retries are supported with bounded attempts and reason codes.
- Every tool call is persisted with inputs, outputs, latency, and error details.

Tooling contracts:

- Tools must declare strict JSON input/output schemas.
- Tool registry entries include risk level and required approval policy.
- High-risk actions (publish, delete, external write, credential operations) require a human approval checkpoint.
- A dry-run mode executes planning and validation without side effects.

## Consequences

- Agent behavior becomes predictable, replayable, and inspectable.
- Product teams can add new capabilities by registering tools instead of hardcoding flows.
- Additional storage and observability overhead is introduced for run traces.
- The system must handle stuck runs, approval timeouts, and cancelled actions explicitly.
