# ADR 0057: Repository map and package responsibilities

- Status: Accepted (Current repository convention)
- Date: 2026-04-07

## Context

Clipmato has grown from a small prototype into a repository with several overlapping surfaces:

- FastAPI routes and server-rendered templates
- CLI entrypoints and a small desktop GUI path
- prompt execution, governance, and evaluation helpers
- background workflow support for publishing, scheduling, and agent runs
- file-backed stores for metadata, settings, events, and prompt history

Most of that structure is visible in the package layout, but it is not yet stated plainly in one place. New human contributors and LLM-based coding assistants can read the code, yet they still spend unnecessary time figuring out where each kind of change belongs.

## Decision

Clipmato will treat the repository layout itself as an architectural boundary map.

Package responsibilities:

- `clipmato/routers` owns HTTP route adapters and response shaping for HTML and JSON endpoints.
- `clipmato/templates` and `clipmato/static` own web presentation assets.
- `clipmato/dependencies.py` owns route-facing dependency facades that bridge HTTP handlers to reusable services.
- `clipmato/services` owns cross-step workflow coordination, background operations, runtime settings, publishing, scheduling, MCP, and related application behavior.
- `clipmato/steps` owns task-shaped media and generation operations used by pipelines and programmatic callers.
- `clipmato/prompts` owns versioned prompt assets, prompt execution, contracts, and prompt-run storage.
- `clipmato/governance` owns policy evaluation, release rollout, and audit-style quality gates.
- `clipmato/agent_runs` owns generic tool execution, state transitions, and persisted run traces.
- `clipmato/providers` owns external provider integrations such as YouTube publishing.
- `clipmato/utils` owns narrow filesystem, metadata, progress, presentation, and helper utilities.
- `clipmato/cli` owns command-line entrypoints only.
- `docs/adr` and `docs/openapi` are committed architecture and contract references.
- `tests` is organized primarily by feature slice and contract surface.

Repository rule:

- New code should be added to the package that owns its behavior before introducing a new top-level area.

## Consequences

- Contributors get a faster “where do I look?” path when debugging or extending features.
- Architecture reviews can talk about package ownership instead of only individual files.
- Some existing files still span transitional boundaries, but this map gives future cleanup a clear direction.
