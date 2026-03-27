# ADR 0030: Backup, export, restore, and disaster recovery

- Status: Proposed
- Date: 2026-03-27

## Context

The earlier ADRs move Clipmato toward a more production-shaped architecture: relational persistence, durable jobs, workspaces, notifications, and object-backed media. That architecture is stronger, but it also means recovery now depends on more than one file in one directory.

If backups and restores are not designed intentionally:

- users can lose published schedules, prompt history, and media references
- migrations become riskier because rollback is unclear
- hosted deployments cannot state recovery expectations
- self-hosted users have no simple portability story

A production-ready product needs both operator-grade recovery and user-friendly export paths.

## Decision

Clipmato will support versioned backups, self-service exports, and documented disaster-recovery procedures.

Backup rules:

- Every deployment profile defines a backup cadence and target recovery objectives.
- Backups include relational data, storage manifests, provider-connection metadata, and the configuration needed to reconstruct runtime state.
- Backup artifacts are versioned, checksummed, and encrypted when stored outside the primary machine.

Export and restore rules:

- Users can export a workspace in a portable format that includes metadata, transcripts, schedules, selected generated assets, and references to retained media objects.
- Restores validate schema version, storage integrity, and checksum compatibility before mutating the target instance.
- Major schema migrations require a pre-migration snapshot or equivalent rollback point.

Operational rules:

- Restore drills are run on a recurring schedule, not only during incidents.
- Disaster-recovery runbooks are maintained alongside the codebase and updated when the architecture changes.
- Partial restore paths are supported where possible so operators can recover a single workspace or a subset of records without restoring the whole system.

## Consequences

- Clipmato becomes safer to operate in production and easier to trust for long-lived content workflows.
- Self-hosted users gain a cleaner portability path when moving machines or upgrading deployments.
- Storage and database backups add cost, and restore verification adds operational overhead.
- The team must treat backup compatibility as a product surface, not an afterthought.
