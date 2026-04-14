# ADR 0068: CI pipelines and smoke environments as code

- Status: Proposed
- Date: 2026-04-14

## Context

The repository has a growing test suite and a broader runtime matrix than the early prototype, but the merge and release path is still underspecified. Packaging, runtime startup, schema drift, and Compose regressions are easy to miss if verification depends on local habit.

As the codebase grows, "works on my machine" is not a strong enough release policy for `main`.

## Decision

Clipmato will define merge and release verification through repository-owned CI workflows.

Required automation:

- Pull requests and pushes to `main` must run versioned CI workflows stored in the repository.
- CI must cover Python tests, package build validation, and startup smoke checks for the web application.
- Infrastructure bundles and Compose renders must be validated in the same pipeline family as application code.

Smoke environments:

- At least one CI job must start the app in an isolated smoke environment using seeded temporary data and the repository's supported startup path.
- Smoke jobs should fail fast on import-time configuration errors, missing packaged assets, broken route registration, and manifest drift.
- Release automation must be defined in code and use the same verification gates as normal merges, with any extra release-only checks expressed explicitly.

Branch policy:

- Required CI checks must pass before changes are merged into `main`.
- Manual verification notes may supplement CI, but they do not replace required automated gates.

## Consequences

- The repository gains a repeatable definition of "ready to merge" and "ready to release."
- Runtime and packaging regressions are caught closer to the change that introduced them.
- CI maintenance cost increases as more runtime modes and deployment bundles are added.
