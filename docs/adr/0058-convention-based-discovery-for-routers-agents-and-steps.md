# ADR 0058: Convention-based discovery for routers, agents, and steps

- Status: Accepted (Current repository convention)
- Date: 2026-04-07

## Context

Clipmato already supports lightweight extension by package discovery:

- routers are imported automatically from `clipmato/routers`
- agents are imported automatically from `clipmato/agents`
- step functions are imported automatically from `clipmato/steps`

This is a useful plugin-like pattern, but the rules are currently implicit in package `__init__` files. That makes extension easy for people who inspect the code closely and easy to miss for everyone else.

## Decision

Clipmato will keep discovery-by-convention as the default extension model.

Discovery rules:

- Route modules in `clipmato/routers` must expose an `APIRouter` instance named `router`.
- Agent modules in `clipmato/agents` must expose one or more `Agent` instances whose variable names end with `_agent`.
- Step modules in `clipmato/steps` may expose callable functions directly; public callables defined in the module become importable through `clipmato.steps`.
- Private or helper-only modules should start with `_`, or be explicitly skipped by package bootstrap code.

Import-time rules:

- Discovered modules must stay cheap to import.
- Module import must not perform network calls, heavy processing, or long-running side effects.
- Registration-safe setup such as prompt resolution or local constant creation is acceptable.

Contributor rule:

- New repository extensions should follow these naming conventions instead of adding manual registration tables unless a feature has special security or ordering needs.

## Consequences

- Adding a router, agent, or processing step remains low-friction.
- The repository stays friendly to both manual contributors and code-generating assistants because extension points are predictable.
- Import-time discipline matters more, since a bad side effect in one discovered module can affect the whole app startup path.
