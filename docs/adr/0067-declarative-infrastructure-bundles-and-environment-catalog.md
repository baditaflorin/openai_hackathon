# ADR 0067: Declarative infrastructure bundles and environment catalog

- Status: Proposed
- Date: 2026-04-14

## Context

Recent ADRs clarified runtime profiles, storage boundaries, and production operations, but the repository still spreads infrastructure knowledge across `docker-compose.yml`, helper scripts, README examples, and direct environment-variable usage.

That makes local demos, CI smoke environments, and self-hosted installs harder to keep in sync. It also makes configuration drift easy when a new variable is added in code but not reflected in deployment manifests or operator docs.

## Decision

Clipmato will define supported infrastructure topologies as versioned repository assets.

Infrastructure structure:

- A dedicated `infra/` directory will hold deployment bundles, Compose overlays or profiles, example env files, and operator runbooks.
- Each supported topology must be renderable from version-controlled manifests, including app-only, app plus local AI services, and externally hosted dependency modes.
- Helper scripts may remain, but they must wrap or reference the versioned manifests rather than becoming a separate source of truth.

Environment contract:

- Every deployment variable used by Clipmato must be declared in a machine-readable environment catalog.
- The catalog must record default value behavior, secret status, profile applicability, and a short operator-facing description.
- Compose bundles, bootstrap scripts, and operator documentation must be generated from or validated against that catalog.

Verification:

- CI must validate that every supported bundle renders successfully.
- New infrastructure variables are not complete until the environment catalog and at least one deployment bundle are updated in the same change.

## Consequences

- Clipmato gets a clearer infrastructure-as-code story for local, demo, and self-hosted operation.
- Deployment documentation and runtime manifests are less likely to drift apart.
- Contributors take on the extra work of maintaining an environment catalog and renderable bundles whenever runtime options change.
