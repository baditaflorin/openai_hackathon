# ADR 0059: Thin entrypoints and adapters over reusable services

- Status: Accepted (Current repository convention)
- Date: 2026-04-07

## Context

Clipmato exposes several entrypoints:

- FastAPI routes for HTML pages
- `/api/v1` routes for machine clients
- CLI commands such as `clipmato-web`
- a small GUI launcher

If each surface grows its own business logic, the codebase becomes much harder to reason about and reuse. The current repository already trends toward a better split, with dependency facades, services, steps, and prompt helpers carrying most of the reusable behavior.

## Decision

Clipmato will keep entrypoints and route handlers thin.

Responsibility rules:

- Entry layers parse request or CLI input, resolve dependencies, choose the response type, and call lower layers.
- Reusable workflow logic belongs in `clipmato/services`, `clipmato/steps`, `clipmato/prompts`, `clipmato/agent_runs`, or dedicated utility modules.
- File mutation and storage concerns should live in store helpers or service modules, not directly in templates or presentation code.
- Shared dependency shaping for web routes belongs in `clipmato/dependencies.py`.

Architecture note:

- The current facade-and-service style is the working bridge toward the fuller command/query direction described in ADR 0045.

## Consequences

- The same behavior can be reused by web, API, CLI, and future automation paths.
- Route handlers stay easier to review because transport concerns and business concerns are separated.
- Some existing handlers still contain workflow detail, so future refactors should continue extracting reusable logic downward rather than adding more behavior at the edge.
