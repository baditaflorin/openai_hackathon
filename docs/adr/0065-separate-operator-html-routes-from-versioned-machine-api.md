# ADR 0065: Separate operator HTML routes from versioned machine API

- Status: Accepted (Current repository convention)
- Date: 2026-04-07

## Context

Clipmato serves both human operators and machine clients from the same FastAPI app:

- unversioned HTML routes render pages, redirects, and forms for operators
- `/api/v1/*` routes expose versioned JSON contracts for integrations and automation

Those surfaces overlap in capability, but they do not have the same stability requirements or response shapes. New contributors need a clear rule for when to add an HTML route, when to add an API route, and how to keep them aligned.

## Decision

Clipmato will keep operator-facing HTML routes and machine-facing API routes as separate presentation surfaces over shared lower-layer behavior.

Surface rules:

- HTML routes optimize for operator workflow, server-rendered templates, redirects, and inline notices.
- `/api/v1` routes optimize for stable JSON payloads, OpenAPI contracts, idempotency, and machine-readable errors.
- New external or automation-facing behavior belongs under `/api/v1` instead of being inferred from HTML forms.
- When both surfaces need the same capability, shared behavior should live in services, steps, facades, or presentation helpers, not in duplicated route-local logic.
- Presentation-specific helpers may differ, but business intent should stay aligned across both surfaces.

## Consequences

- Operators get workflows tuned for humans, while integrations get a stable machine contract.
- Refactors become safer because HTML convenience changes do not automatically leak into public API behavior.
- Contributors need to think about audience early, but that small design step prevents a lot of mixed-surface confusion later.
