# ADR 0020: MCP gateway and tool capability layer

- Status: Accepted (Implemented in v0.5.0)
- Date: 2026-03-24

## Context

Clipmato needs a future-ready integration surface for agent ecosystems. MCP is a viable standard path for exposing tools and resources to external model runtimes, but direct exposure of internal services would create security and compatibility risks.

## Decision

Clipmato will introduce an MCP gateway layer that maps internal capabilities to explicit MCP-facing contracts.

MCP surface:

- Clipmato exposes a dedicated MCP server interface for approved tools and resources.
- Internal tool implementations remain private and are wrapped by gateway adapters.
- Resources include read-only views for records, schedules, publish status, and prompt run metadata.

Capability and auth model:

- Every MCP tool/resource is scope-bound (read, plan, publish, admin, credentials).
- Capability negotiation is explicit so clients can detect supported features and versions.
- Sensitive operations require policy checks and optional human approval before execution.
- Per-client rate limits and quota boundaries are enforced at the gateway.

Compatibility model:

- MCP schema changes follow semantic versioning with backward-compatible evolution where possible.
- Gateway adapters isolate internal refactors from external MCP contracts.
- Audit trails include MCP client identity, capability scope, and action outcomes.

## Consequences

- Clipmato can integrate with MCP-native agent runtimes without exposing internal internals directly.
- Security posture improves through least-privilege capability design and centralized policy checks.
- The team must maintain an additional compatibility surface and gateway test suite.
- Some internal tool features may need redesign before they are safe to expose through MCP.
