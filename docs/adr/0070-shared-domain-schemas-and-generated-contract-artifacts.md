# ADR 0070: Shared domain schemas and generated contract artifacts

- Status: Proposed
- Date: 2026-04-14

## Context

Clipmato passes a significant amount of structured data as plain dictionaries: metadata records, publish jobs, runtime settings payloads, prompt-run snapshots, project presets, and API responses. That is flexible, but it also duplicates field names and validation rules across services, routes, tests, and stored payloads.

As the repository adds more routes, automations, and background processing, schema drift will become a growing source of bugs and duplicated code.

## Decision

Clipmato will define shared typed schemas for core domain payloads and generate contract artifacts from them.

Schema rules:

- Core record shapes must be defined once in a shared schema layer.
- Repositories, service boundaries, API DTOs, and tests should reuse those schemas instead of re-declaring field lists as ad hoc dictionaries.
- Validation, normalization, and defaulting rules should live with the schema definitions whenever practical.

Generated artifacts:

- OpenAPI-facing response models, JSON Schema snapshots, or client contract artifacts must be generated from the shared schema layer rather than hand-maintained separately.
- Stored payloads that need versioning or migration behavior must carry an explicit schema or record version.

## Consequences

- Clipmato reduces repeated field-mapping logic and improves contract consistency across storage, API, and tests.
- Schema-aware tooling becomes easier to build for migrations, fixtures, and client integrations.
- The team must be disciplined about routing new structured payloads through the shared schema layer instead of falling back to free-form dictionaries.
