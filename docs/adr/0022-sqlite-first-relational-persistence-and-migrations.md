# ADR 0022: SQLite-first relational persistence and migrations

- Status: Proposed
- Date: 2026-03-25

## Context

Clipmato currently stores records, runtime settings, provider tokens, project presets, prompt traces, and evaluations in separate JSON or JSONL files under the runtime data directory.

That file-based approach has served the single-user prototype well, but it becomes a bottleneck for the architecture introduced in ADRs 0017 through 0021:

- API-first contracts need transactional updates across records, jobs, events, and evaluations.
- Agent runs and publish jobs need queryable history, filtering, and pagination.
- Multi-worker execution should not depend on coarse file locks and process-local caches.
- Hosted or multi-user deployments need safer migrations, backups, and consistency guarantees.

ADR 0016 explicitly called out SQLite as the next persistence step once the metadata cache stopped being sufficient.

## Decision

Clipmato will move mutable application state to a relational database with a SQLite-first deployment model and PostgreSQL compatibility for hosted environments.

Storage rules:

- SQLite in WAL mode is the default for local and single-node self-hosted installs.
- PostgreSQL is the supported production backend for multi-node or managed cloud deployments.
- The application schema is managed with versioned migrations and startup-time schema checks.
- All new product features must persist relational state through repositories or services, not ad hoc JSON files.

Data model rules:

- Records, schedules, publish jobs, provider connections, agent runs, events, prompt runs, prompt evaluations, project presets, and audit entries live in relational tables.
- Large media artifacts remain on the filesystem or object storage; the database stores paths, checksums, sizes, and lifecycle metadata.
- Secrets are referenced from the database but stored in a dedicated secret backend appropriate to the deployment mode.
- Correlation IDs, workspace IDs, and actor IDs are first-class indexed columns rather than opaque payload fields.

Migration rules:

- On first boot after the migration, Clipmato imports legacy JSON and JSONL state into the relational schema.
- The migration flow must be idempotent, produce a backup of the legacy files, and record a completion marker.
- Legacy files become read-only export or recovery artifacts and are not used as the primary write path afterward.

## Consequences

- Clipmato gains transactional consistency, better query performance, and a cleaner path to multi-worker and multi-user deployments.
- Features such as API pagination, audit history, notifications, and analytics become much easier to implement correctly.
- The project must take on migration ownership, schema review, database testing, and backup procedures.
- Local installs become slightly more complex, but SQLite preserves a low-friction setup for single-machine users.
