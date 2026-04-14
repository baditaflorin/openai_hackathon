# ADR 0069: Runtime composition root and application factory

- Status: Proposed
- Date: 2026-04-14

## Context

ADR 0059 keeps entrypoints thin, ADR 0062 centralizes capability resolution, and ADR 0066 documents the current import-sensitive testing model. Even with those conventions, app assembly is still spread across module-level config, dependency globals, CLI startup code, and web lifespan setup.

That makes it harder to spin up isolated app instances for tests, workers, and future automation entrypoints without re-importing modules or recreating environment state indirectly.

## Decision

Clipmato will introduce a single composition root for building runtime state and application surfaces.

Assembly rules:

- `clipmato/runtime.py` will own construction of the resolved runtime object, including paths, settings, repositories, adapters, and long-lived services.
- The FastAPI app will be created through an explicit factory such as `create_app(runtime)`.
- CLI, web, worker, and automation entrypoints must all assemble their dependencies through the same runtime builder.

Migration rules:

- New code must avoid introducing additional module-level service singletons when the same dependency can be provided by the runtime object.
- Import-time filesystem mutation should be reduced over time and eventually removed from newly introduced modules.
- Until migration is complete, ADR 0066 remains the current testing convention for path-bound imports.

## Consequences

- The codebase gets a clearer composition boundary for tests and future runtime surfaces.
- Runtime assembly becomes easier to reason about because path setup, dependency wiring, and lifespan ownership live in one place.
- The repository takes on a gradual refactor cost as existing modules move away from implicit globals.
