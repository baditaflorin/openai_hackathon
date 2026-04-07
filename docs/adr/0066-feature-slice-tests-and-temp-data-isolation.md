# ADR 0066: Feature-slice tests and temp-data isolation

- Status: Accepted (Current repository convention)
- Date: 2026-04-07

## Context

Clipmato’s architecture is strongly shaped by filesystem-backed state, FastAPI routes, and reusable service modules. The test suite already reflects that reality:

- route tests use `TestClient`
- store and service tests use temporary data directories
- some tests reset imported modules so path-bound config is re-evaluated
- API schema tests compare the committed OpenAPI artifact with the live app schema

This is a good testing model for the repository, but it should be explicit for future contributors.

## Decision

Clipmato will organize tests primarily by feature slice and execute them against isolated temporary data roots.

Testing rules:

- Filesystem-affecting tests set `CLIPMATO_DATA_DIR` to a temporary directory.
- When configuration is path-bound at import time, tests should reset and re-import Clipmato modules rather than patching around stale globals.
- Route and contract behavior should be tested through `FastAPI` `TestClient` when possible.
- Lower-level store, runtime, gateway, and service behavior may be tested directly with focused unit tests.
- Public API changes must keep the committed OpenAPI artifact in sync with the live schema.
- New tests should live with the owning slice instead of accumulating in generic catch-all test files.

## Consequences

- Contributors can add tests by following a clear pattern that matches how the app actually runs.
- Regressions around file persistence, route contracts, and runtime settings are easier to catch before release.
- Tests remain slightly more import-sensitive than in a pure dependency-injected app, but the pattern is understandable and repeatable.
