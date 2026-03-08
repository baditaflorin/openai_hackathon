# ADR 0002: Semantic Versioning and changelog policy

- Status: Accepted (Implemented in v0.1.0)
- Date: 2026-03-08

## Context

Clipmato did not have a formal release history or a stable versioning policy. That makes it harder to communicate compatibility expectations and harder to understand what changed between releases.

## Decision

Clipmato adopts Semantic Versioning starting at `0.1.0` and records externally relevant changes in `CHANGELOG.md`.

Versioning rules:

- Increment the patch version for backward-compatible fixes.
- Increment the minor version for backward-compatible features.
- Increment the major version for breaking changes.
- Keep unreleased work under the `Unreleased` section until a release is cut.

## Consequences

- Releases now carry clear compatibility signals.
- Contributors have a single place to record user-visible changes.
- Future breaking changes must be called out explicitly instead of being folded into a generic update.
