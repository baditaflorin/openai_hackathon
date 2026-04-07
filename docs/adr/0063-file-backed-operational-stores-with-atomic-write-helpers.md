# ADR 0063: File-backed operational stores with atomic write helpers

- Status: Accepted (Current repository convention)
- Date: 2026-04-07

## Context

The current Clipmato repository persists most operational state in files under the active data directory:

- `metadata.json`
- progress status files
- `settings.json`
- `secrets.json`
- prompt run and evaluation ledgers
- event and webhook stores
- project preset data
- per-run agent trace files

This is simple and inspectable, but it also means correctness depends on consistent locking, atomic writes, and ownership boundaries.

## Decision

Clipmato will keep each file-backed store behind a dedicated helper or service module until the broader SQLite migration described in ADR 0051 is complete.

Store rules:

- File paths are declared centrally in `clipmato/config.py`.
- Each store has one owning module or service responsible for reading, mutation, and safe defaults.
- Writes must use lock-and-replace or equivalent atomic file update behavior.
- Readers return detached copies so callers do not accidentally mutate cached in-memory objects.
- Caches such as `MetadataCache` are accelerators only; the file on disk remains the source of truth for the current implementation.
- Large binary assets stay on the filesystem as files, not embedded inside JSON payloads.

## Consequences

- The current local-first prototype remains easy to inspect and back up.
- File corruption risk is reduced because write discipline is explicit and repeatable.
- Cross-store queries and multi-record transactions remain awkward, which reinforces why ADR 0051 exists as the next storage evolution.
