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
