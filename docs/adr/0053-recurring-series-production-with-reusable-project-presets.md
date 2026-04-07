# ADR 0053: Recurring series production with reusable project presets

- Status: Proposed
- Date: 2026-04-04

## Context

Clipmato is not only useful for one-off uploads. The codebase already includes project presets, prompt hooks, and merged project context at upload time. That points to a recurring production use case:

- a creator or team publishes a repeatable show or content series
- episodes share tone, audience, editorial framing, and topical boundaries
- operators need consistent output without retyping the same context every time

Without an explicit decision here, recurring production remains an implementation detail instead of a first-class product capability. That would make generated output less consistent and would force users back into copy-paste workflows.

## Decision

Clipmato will treat recurring series production as a primary use case, powered by reusable project presets and persisted project context.

Rules for this use case:

- Users can save reusable presets for show identity, editorial summary, topics, and prompt guidance.
- Upload and capture flows should make attaching saved presets easier than re-entering the same context manually.
- The effective project context used for generation must be stored with the episode so later review and regeneration remain explainable.
- Multiple presets may be combined when users need a blended context, but merging must stay deterministic and auditable.
- Generated titles, descriptions, scripts, and related assets should consistently honor the resolved project context.

## Consequences

- Recurring shows get more stable voice and structure across episodes.
- The app becomes more useful for real editorial pipelines where consistency matters as much as raw generation speed.
- Preset merging and context display need careful UX so users can see what guidance actually shaped an episode.
- One-off ad hoc uploads remain supported, but Clipmato now clearly favors reusable editorial context over isolated prompt inputs.
