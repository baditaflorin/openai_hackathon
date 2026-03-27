# ADR 0034: Spacious layout grid and content density rules

- Status: Proposed
- Date: 2026-03-27

## Context

Minimalist products do not only change colors and buttons. They also decide how much information can appear on screen before the interface starts to feel crowded.

Clipmato spans capture, library, record review, scheduling, publishing, and settings. Without explicit layout rules, each page can optimize locally and still produce a globally noisy experience.

## Decision

Clipmato will use a spacious layout system with explicit density limits for desktop and mobile screens.

Layout rules:

- Each screen defines one primary content column or one primary split view, not multiple competing panels by default.
- Content widths, gutters, and section spacing follow a shared grid so transitions between pages feel stable.
- Above the fold, each page should emphasize at most three visual groups: page context, primary content, and one supporting action cluster.
- Dense metadata and secondary controls move into drawers, sheets, segmented views, or expandable regions instead of always-visible side clutter.

Density rules:

- Default desktop density favors breathing room over maximum rows per screen.
- Mobile layouts collapse into a single clear reading flow before introducing horizontal carousels or nested tabs.
- Library cards, schedule rows, and settings groups must have documented compact variants, but compact mode is opt-in rather than the global default.

## Consequences

- Pages will feel more deliberate and easier to understand at a glance.
- Users can stay oriented because the product no longer changes visual density unpredictably from screen to screen.
- Some current summary panels and metrics clusters may need to become collapsible or secondary.
- Teams will need to justify every additional always-visible element on high-traffic screens.
