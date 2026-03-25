# ADR 0021: Agent evaluation, policy engine, and release gates

- Status: Accepted (Implemented in v0.4.0)
- Date: 2026-03-24

## Context

As Clipmato becomes more autonomous, quality and safety failures can happen without immediate visibility: bad titles, weak descriptions, invalid publish actions, or policy violations. A more agentic system needs measurable quality gates and policy enforcement before side effects occur.

## Decision

Clipmato will implement a shared evaluation and policy layer for agent outputs and actions.

Evaluation model:

- Every `AgentRun` produces an evaluation record with task-specific metrics.
- Metrics include contract validity, fallback usage, latency, user selection outcomes, and publish outcomes.
- Benchmark suites are versioned and rerun for significant model/prompt/policy changes.

Policy model:

- A central policy engine evaluates proposed actions before execution.
- Policy checks include content formatting rules, blocked terms, platform constraints, and risk thresholds.
- Failed policy checks return structured reasons and remediation hints to the agent layer.
- High-risk policy classes can require explicit human override with audit attribution.

Release gating model:

- Prompt/model/policy updates are promoted only when benchmark thresholds pass.
- Canary traffic is supported before full rollout.
- Rollback paths are mandatory when quality or reliability regressions are detected.

## Consequences

- Clipmato gains measurable guardrails for autonomous behavior and production quality.
- Incident debugging improves through consistent evaluation and policy traces.
- Development overhead increases due to benchmark maintenance and policy authoring.
- Teams must define clear ownership for policy rules, thresholds, and override processes.
