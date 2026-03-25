# Architecture Decision Records

This directory stores Architecture Decision Records (ADRs) for durable technical decisions that affect how Clipmato is built, run, or evolved.

## Format

- Create one Markdown file per decision using the filename pattern `NNNN-short-title.md`.
- Copy [0000-template.md](./0000-template.md) when creating a new record.
- Keep the status near the top of the file. Use `Proposed`, `Accepted`, `Superseded`, or `Deprecated`.
- Update this index whenever a new ADR is added.

## Workflow

1. Write the context that makes the decision necessary.
2. Record the decision in concrete, testable terms.
3. Document the consequences, including tradeoffs and migration work.
4. Link related ADRs when one supersedes or depends on another.

## Index

- [ADR 0001: Container runtime and persistent data directory](./0001-container-runtime-and-persistent-data.md)
- [ADR 0002: Semantic Versioning and changelog policy](./0002-semver-and-changelog-policy.md)
- [ADR 0003: Local transcription and basic fallback backends](./0003-local-transcription-and-basic-fallbacks.md)
- [ADR 0004: Publishing API integration with YouTube-first rollout](./0004-publishing-api-integration-and-youtube-first.md)
- [ADR 0005: Frontend design system and brand language](./0005-frontend-design-system-and-brand-language.md)
- [ADR 0006: Workflow-first app shell and navigation](./0006-workflow-first-app-shell-and-navigation.md)
- [ADR 0007: Progressive enhancement for long-running UI flows](./0007-progressive-enhancement-for-long-running-ui-flows.md)
- [ADR 0008: Accessibility and performance quality gates](./0008-accessibility-and-performance-quality-gates.md)
- [ADR 0009: Prompt engine for versioned content generation](./0009-prompt-engine-for-versioned-content-generation.md)
- [ADR 0010: Runtime settings and provider credentials for local and cloud execution](./0010-runtime-settings-and-provider-credentials.md)
- [ADR 0011: Project context and prompt hooks for reusable editorial guidance](./0011-project-context-and-prompt-hooks.md)
- [ADR 0012: Static asset pipeline and cache headers](./0012-static-asset-pipeline-and-cache-headers.md)
- [ADR 0013: Modular JavaScript with page-scoped bundles](./0013-modular-javascript-with-page-scoped-bundles.md)
- [ADR 0014: Dark mode and user theme preference](./0014-dark-mode-and-user-theme-preference.md)
- [ADR 0015: Virtual scrolling and lazy rendering for the episode library](./0015-virtual-scrolling-and-lazy-rendering-for-episode-library.md)
- [ADR 0016: In-memory metadata cache with file-change detection](./0016-in-memory-metadata-cache-with-file-watch.md)
- [ADR 0017: API-first versioned public contracts](./0017-api-first-versioned-public-contracts.md)
- [ADR 0018: Agent run state machine and tooling contracts](./0018-agent-run-state-machine-and-tooling-contracts.md)
- [ADR 0019: Event-driven API with SSE and webhooks](./0019-event-driven-api-with-sse-and-webhooks.md)
- [ADR 0020: MCP gateway and tool capability layer](./0020-mcp-gateway-and-tool-capability-layer.md)
- [ADR 0021: Agent evaluation, policy engine, and release gates](./0021-agent-evaluation-policy-and-release-gates.md)
- [ADR 0022: SQLite-first relational persistence and migrations](./0022-sqlite-first-relational-persistence-and-migrations.md)
- [ADR 0023: Identity and workspace-scoped access control](./0023-identity-and-workspace-scoped-access-control.md)
- [ADR 0024: Durable background jobs and worker isolation](./0024-durable-background-jobs-and-worker-isolation.md)
- [ADR 0025: Guided first-run onboarding and preflight checks](./0025-guided-first-run-onboarding-and-preflight-checks.md)
- [ADR 0026: Observability, audit trail, and user notifications](./0026-observability-audit-trail-and-user-notifications.md)
