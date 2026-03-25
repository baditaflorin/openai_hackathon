# ADR 0023: Identity and workspace-scoped access control

- Status: Proposed
- Date: 2026-03-25

## Context

Clipmato currently behaves like a trusted single-user application. Records, runtime settings, provider credentials, and publish actions all operate inside one shared data directory without a first-class identity boundary.

That is workable for a local prototype, but it breaks down for any hosted, team, or agent-assisted deployment:

- API and MCP access need actor attribution.
- Provider connections such as YouTube OAuth must belong to a user or workspace, not the entire server.
- Human approvals and policy overrides need accountable identities.
- Shared deployments need permission boundaries around uploads, publishing, prompt data, and secrets.

Without an explicit access model, production deployment would either be unsafe or effectively limited to a single trusted operator.

## Decision

Clipmato will introduce first-class identities, workspaces, and role-based authorization.

Identity rules:

- Every human or service actor has a stable identity record.
- Hosted web deployments use standards-based login through OIDC-compatible identity providers.
- API and MCP clients authenticate with scoped personal access tokens or service tokens.
- Local single-user installs may use a bootstrap owner mode, but that mode is explicit and visually labeled as single-user.

Workspace and authorization rules:

- Every record, job, event, provider connection, webhook, prompt artifact, and policy override belongs to a workspace.
- Workspace membership is role-based with at least `owner`, `editor`, `operator`, and `viewer` capabilities.
- High-risk actions such as publish, delete, credential changes, and policy overrides require elevated roles.
- Authorization is enforced in shared service and API layers with default-deny behavior.

Credential ownership rules:

- Third-party provider tokens are stored per user connection or workspace-owned service connection, never as one global token for the whole instance.
- Secrets and runtime settings must support workspace-level scope and optional per-user overrides where the product allows them.
- Audit entries always capture the acting identity, effective workspace, and impersonation or override context when present.

## Consequences

- Clipmato becomes viable for hosted teams, external API consumers, and approval workflows.
- Security posture improves because credentials, content, and side effects are no longer globally shared.
- The product and data model become more complex, especially around invitations, ownership transfer, and token lifecycle management.
- Some existing local behaviors will need compatibility layers so current single-user installs keep working during migration.
