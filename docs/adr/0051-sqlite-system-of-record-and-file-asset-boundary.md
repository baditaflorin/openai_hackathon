# ADR 0051: SQLite system of record and file asset boundary

- Status: Proposed
- Date: 2026-03-31

## Context

Clipmato currently persists operational state across several files:

- `metadata.json`
- per-record progress JSON files
- `settings.json`
- `secrets.json`
- prompt run and prompt evaluation JSONL ledgers
- project preset JSON

This approach has served the prototype well. It is readable, easy to inspect, and lightweight. But it is now starting to work against the product goals:

- cross-cutting queries are awkward
- transactions across several state changes are hard
- automation and event delivery need stronger consistency guarantees
- run history, publish history, and editorial history are becoming first-class concepts
- more features will keep adding more files unless the storage boundary becomes clearer

The app still needs the filesystem for media assets and static build output, but it needs a better home for operational state.

## Decision

Clipmato will adopt SQLite as the primary system of record for non-secret operational state, while keeping the filesystem as the home for large binary assets.

SQLite owns:

- episodes and episode lifecycle state
- editorial assets and approvals
- release plans and provider jobs
- workflow runs
- prompt runs and prompt evaluations
- project presets
- runtime profiles and readiness snapshots
- domain events and outbox delivery state
- automation recipes and execution history

Filesystem owns:

- uploaded media
- derived audio and edited media
- cached static build artifacts
- temporary processing files

Secret handling rules:

- Secrets remain outside the main operational database.
- Self-hosted installs may continue using a dedicated locked-down secrets file or OS secret store.
- Hosted deployments should use a proper secret manager.
- SQLite stores only references, status, and non-sensitive metadata for secret-backed resources.

Migration rules:

- Migration should be incremental with adapter-backed reads from current JSON stores.
- Existing JSON files should remain importable and exportable for backup and troubleshooting.
- Progress files become projections or compatibility shims during migration, not the long-term source of truth.

## Consequences

- The app gets a much cleaner data backbone for UX, automation, and future APIs.
- Multi-step actions become safer because state changes can be committed transactionally.
- Querying dashboards, calendars, blocked work, and automation triggers becomes straightforward.
- Migration effort will be meaningful, especially for record shape changes and event history.
- Clipmato keeps the simplicity of local file-based media storage while gaining the consistency needed for a richer workflow product.
