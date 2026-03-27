# ADR 0036: Split-view record workspace and inline editing

- Status: Proposed
- Date: 2026-03-27

## Context

Record detail is one of Clipmato's highest-value screens, yet it still behaves largely like a traditional detail page. Users often need to compare transcript, titles, descriptions, schedule, and publish readiness together.

To feel simple and premium, the record experience should behave more like a focused workspace than a page full of stacked sections.

## Decision

Clipmato will redesign record detail as a split-view workspace with inline editing by default.

Workspace rules:

- Desktop record views use a stable split layout with one main reading or editing pane and one contextual support pane.
- Mobile record views preserve the same information architecture through segmented sections rather than a completely different screen model.
- The contextual pane can switch between titles, descriptions, schedule, publish readiness, and metadata without navigating away.

Editing rules:

- High-frequency edits such as title selection, description tweaks, and schedule changes happen inline where the user is already looking.
- Save behavior favors autosave or explicit lightweight commit states rather than full-page forms where possible.
- Inline editing states must clearly communicate `saved`, `saving`, and `failed` feedback without breaking the calm UI.

## Consequences

- Record work becomes faster because users stop bouncing between separate pages and forms.
- The product feels more modern and more aligned with premium desktop editing tools.
- Engineering complexity increases because state management and optimistic updates need to be stronger.
- Existing detail templates will likely need a deeper refactor than a cosmetic pass.
