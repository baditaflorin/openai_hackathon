# ADR 0005: Frontend design system and brand language

- Status: Accepted (Implemented in v0.2.0)
- Date: 2026-03-08

## Context

Clipmato's web UI currently mixes Bootstrap defaults with a small amount of custom CSS. That is enough for functional screens, but it produces an inconsistent feel across the dashboard, record detail, and scheduler pages.

The current frontend lacks:

- a shared visual language that feels product-specific rather than default
- reusable design tokens for color, spacing, typography, borders, and motion
- a documented set of component variants for common states such as `idle`, `loading`, `error`, `success`, and `publishing`
- a clean path for future UI work without copy-pasting one-off styles per page

If the product keeps growing without a design system, every feature will further increase inconsistency and rework.

## Decision

Clipmato will adopt a lightweight frontend design system built around local CSS variables and reusable component classes.

Core rules:

- The product must define a first-party visual identity instead of relying on unmodified Bootstrap defaults.
- Shared tokens must be declared for color, typography, spacing, radius, elevation, border treatment, and motion timing.
- Screens must use a documented component set for cards, buttons, alerts, status badges, empty states, forms, tables, and progress states.
- State styling must be semantic and consistent across upload, scheduling, and publishing flows.
- Fonts and brand assets must be loaded from first-party files or other non-render-blocking sources so the app keeps its fast first paint behavior.
- Bootstrap may remain as a utility foundation, but product-facing styling must be driven by Clipmato tokens and components, not ad hoc overrides.

## Consequences

- The interface will become more cohesive and easier to recognize as one product.
- New pages and flows will be faster to build because styling decisions are centralized.
- Existing pages will need a migration pass to replace one-off classes and raw Bootstrap presentation with shared components.
- Frontend work will require a small amount of design documentation discipline to prevent regression into page-local styling.
