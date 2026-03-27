# ADR 0032: Apple-inspired minimalist visual direction

- Status: Proposed
- Date: 2026-03-27

## Context

ADR 0005 established a product-specific design system, but the interface can still drift toward a tool-like look with too many visual signals competing at once. The user goal for the next phase is different: make Clipmato feel calmer, more premium, and easier to read at a glance.

The target aesthetic is minimalist and hardware-like:

- generous whitespace
- soft depth instead of heavy chrome
- restrained color usage
- content-first surfaces that feel polished without looking decorative

## Decision

Clipmato will adopt an Apple-inspired minimalist visual direction as the default expression of the design system.

Visual rules:

- Primary surfaces use quiet neutrals, subtle translucency, hairline borders, and soft shadow separation instead of loud cards and strong outlines.
- Accent color is used sparingly for focus, selection, and one primary action per area, not as a general decoration layer.
- Backgrounds remain simple and bright by default, with depth created through spacing, blur, and surface layering rather than complex gradients.
- Corners, spacing, and elevation must feel consistent across cards, sheets, toolbars, and modals so the product reads like one composed system.

Restraint rules:

- Decorative elements are removed unless they improve hierarchy or feedback.
- Status colors remain semantic but muted enough that the UI does not become a patchwork of bright badges.
- Large surfaces prioritize clarity of transcript, title, schedule, and media preview content over dashboard ornamentation.

## Consequences

- Clipmato will feel more premium and less like a generic admin tool.
- The product becomes easier to scan because fewer elements compete for attention.
- Designers and engineers will need stronger discipline around not reintroducing visual noise page by page.
- Some existing surfaces may need simplification even if they are already functional.
