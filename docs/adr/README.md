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
- [ADR 0027: Resumable uploads and object-backed media storage](./0027-resumable-uploads-and-object-backed-media-storage.md)
- [ADR 0028: Usage quotas, rate limits, and cost guardrails](./0028-usage-quotas-rate-limits-and-cost-guardrails.md)
- [ADR 0029: Privacy, retention, and redaction for user content](./0029-privacy-retention-and-redaction-for-user-content.md)
- [ADR 0030: Backup, export, restore, and disaster recovery](./0030-backup-export-restore-and-disaster-recovery.md)
- [ADR 0031: Timezone-safe scheduling and locale-aware publishing](./0031-timezone-safe-scheduling-and-locale-aware-publishing.md)
- [ADR 0032: Apple-inspired minimalist visual direction](./0032-apple-inspired-minimalist-visual-direction.md)
- [ADR 0033: Editorial typography and quiet iconography](./0033-editorial-typography-and-quiet-iconography.md)
- [ADR 0034: Spacious layout grid and content density rules](./0034-spacious-layout-grid-and-content-density-rules.md)
- [ADR 0035: Single-primary-action screens and progressive disclosure](./0035-single-primary-action-screens-and-progressive-disclosure.md)
- [ADR 0036: Split-view record workspace and inline editing](./0036-split-view-record-workspace-and-inline-editing.md)
- [ADR 0037: Command palette and universal search](./0037-command-palette-and-universal-search.md)
- [ADR 0038: Motion language for calm native-feeling transitions](./0038-motion-language-for-calm-native-feeling-transitions.md)
- [ADR 0039: Media preview cards and immersive detail surfaces](./0039-media-preview-cards-and-immersive-detail-surfaces.md)
- [ADR 0040: Guided settings with simple and advanced modes](./0040-guided-settings-with-simple-and-advanced-modes.md)
- [ADR 0041: Empty states, inline coaching, and microcopy standards](./0041-empty-states-inline-coaching-and-microcopy-standards.md)
- [ADR 0042: Platform operating model and bounded contexts](./0042-platform-operating-model-and-bounded-contexts.md)
- [ADR 0043: Episode aggregate and lifecycle](./0043-episode-aggregate-and-lifecycle.md)
- [ADR 0044: Workspace-first operator experience](./0044-workspace-first-operator-experience.md)
- [ADR 0045: Application service layer and command contracts](./0045-application-service-layer-and-command-contracts.md)
- [ADR 0046: Unified job orchestration and run tracking](./0046-unified-job-orchestration-and-run-tracking.md)
- [ADR 0047: Domain events, outbox, and live notifications](./0047-domain-events-outbox-and-live-notifications.md)
- [ADR 0048: Guided setup, readiness, and runtime profiles](./0048-guided-setup-readiness-and-runtime-profiles.md)
- [ADR 0049: Editorial review and publishable asset model](./0049-editorial-review-and-publishable-asset-model.md)
- [ADR 0050: Automation recipes, triggers, and approvals](./0050-automation-recipes-triggers-and-approvals.md)
- [ADR 0051: SQLite system of record and file asset boundary](./0051-sqlite-system-of-record-and-file-asset-boundary.md)
- [ADR 0052: Single-episode capture-to-publish fast path](./0052-single-episode-capture-to-publish-fast-path.md)
- [ADR 0053: Recurring series production with reusable project presets](./0053-recurring-series-production-with-reusable-project-presets.md)
- [ADR 0054: Private local-first production for sensitive media](./0054-private-local-first-production-for-sensitive-media.md)
- [ADR 0055: Release operations for backlog scheduling and provider publishing](./0055-release-operations-for-backlog-scheduling-and-provider-publishing.md)
- [ADR 0056: Programmatic integration for API, events, and automation](./0056-programmatic-integration-for-api-events-and-automation.md)
- [ADR 0057: Repository map and package responsibilities](./0057-repository-map-and-package-responsibilities.md)
- [ADR 0058: Convention-based discovery for routers, agents, and steps](./0058-convention-based-discovery-for-routers-agents-and-steps.md)
- [ADR 0059: Thin entrypoints and adapters over reusable services](./0059-thin-entrypoints-and-adapters-over-reusable-services.md)
- [ADR 0060: Stage-oriented episode processing pipeline and shared context](./0060-stage-oriented-episode-processing-pipeline-and-shared-context.md)
- [ADR 0061: Versioned prompt assets, contract validation, and fallbacks](./0061-versioned-prompt-assets-contract-validation-and-fallbacks.md)
- [ADR 0062: Runtime capability resolution from settings, environment, and readiness](./0062-runtime-capability-resolution-from-settings-env-and-readiness.md)
- [ADR 0063: File-backed operational stores with atomic write helpers](./0063-file-backed-operational-stores-with-atomic-write-helpers.md)
- [ADR 0064: Snapshot-plus-ledger explainability for workflow history](./0064-snapshot-plus-ledger-explainability-for-workflow-history.md)
- [ADR 0065: Separate operator HTML routes from versioned machine API](./0065-separate-operator-html-routes-from-versioned-machine-api.md)
- [ADR 0066: Feature-slice tests and temp-data isolation](./0066-feature-slice-tests-and-temp-data-isolation.md)
- [ADR 0067: Declarative infrastructure bundles and environment catalog](./0067-declarative-infrastructure-bundles-and-environment-catalog.md)
- [ADR 0068: CI pipelines and smoke environments as code](./0068-ci-pipelines-and-smoke-environments-as-code.md)
- [ADR 0069: Runtime composition root and application factory](./0069-runtime-composition-root-and-application-factory.md)
- [ADR 0070: Shared domain schemas and generated contract artifacts](./0070-shared-domain-schemas-and-generated-contract-artifacts.md)
- [ADR 0071: Scenario builders, fake adapters, and regression matrices](./0071-scenario-builders-fake-adapters-and-regression-matrices.md)
