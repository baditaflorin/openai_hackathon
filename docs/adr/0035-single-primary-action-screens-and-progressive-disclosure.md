# ADR 0035: Single-primary-action screens and progressive disclosure

- Status: Proposed
- Date: 2026-03-27

## Context

One reason software feels hard to use is not lack of features, but presenting too many equally loud choices at the same moment. A minimalist interface should reduce anxiety by making the next best step obvious.

Clipmato already contains uploads, title selection, scheduling, publishing, presets, settings, and provider controls. If every screen exposes every possible action at full weight, simplicity disappears.

## Decision

Clipmato will design each major screen around one dominant action and progressively reveal advanced controls.

Action hierarchy rules:

- Every page or major panel has one clearly dominant primary action.
- Secondary actions are visually quieter and grouped near the area they affect.
- Destructive or rare actions move into confirmation flows, contextual menus, or secondary sheets rather than living beside the main call to action.

Progressive disclosure rules:

- Advanced controls remain accessible but collapsed by default until the user asks for them.
- Multi-step tasks use staged reveal, checklists, or guided panels instead of presenting every option in one long form.
- First-run users see the simplest successful path; expert users can expand into deeper control when needed.

## Consequences

- The product will feel simpler and more confident because it stops asking users to weigh too many choices at once.
- Conversion through key workflows should improve because the next step is easier to identify.
- Teams must resist adding new visible controls without rebalancing the action hierarchy.
- Some existing pages may require structural redesign rather than just visual polish.
