# ADR 0033: Editorial typography and quiet iconography

- Status: Proposed
- Date: 2026-03-27

## Context

Minimalist interfaces succeed or fail on typography. If text styles are inconsistent, icons are overused, or labels compete with one another, a quiet visual direction quickly turns bland or confusing.

Clipmato is content-heavy: transcripts, titles, descriptions, schedules, statuses, and provider details all depend on strong text hierarchy. A premium, Apple-like feel therefore depends less on decoration and more on disciplined type and symbol usage.

## Decision

Clipmato will treat typography and iconography as primary navigation and hierarchy tools.

Typography rules:

- The product uses a neutral system UI font stack that feels native on Apple devices and remains clean on other platforms.
- Text styles are limited to a small, named scale for display titles, section titles, body copy, captions, and metadata.
- Line height, font weight, and letter spacing are tuned for calm readability rather than maximum density.
- Numbers used in metrics, durations, and schedules should support tabular alignment where it improves scanability.

Iconography rules:

- Icons are thin, monochrome, and supportive; they do not replace text labels for primary navigation or destructive actions.
- Repeated status meanings should prefer consistent text plus one small icon rather than a unique icon for every state.
- Product areas must not mix multiple icon styles or visual weights.

## Consequences

- Hierarchy becomes clearer even as the visual system grows more minimal.
- The UI feels more native and polished because typography does more of the work.
- Engineering work will need better type tokens and component discipline.
- Some current labels, badges, and icon-heavy buttons may need consolidation.
