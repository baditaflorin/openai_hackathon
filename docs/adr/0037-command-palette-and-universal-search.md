# ADR 0037: Command palette and universal search

- Status: Proposed
- Date: 2026-03-27

## Context

As Clipmato grows, navigation through visible menus alone will become slower, especially for repeat users. Minimalist products often feel simpler not because they expose fewer capabilities, but because they provide one elegant shortcut surface for search and actions.

Clipmato already has clear workflow routes, but it lacks a universal jump point for records, settings, actions, and provider states.

## Decision

Clipmato will introduce a command palette backed by universal search.

Palette rules:

- A single command surface opens from a global keyboard shortcut and a visible trigger in the shell.
- Users can search records, navigate to pages, trigger common actions, and jump to settings sections from the same surface.
- Search results combine content objects and actions, but they remain clearly labeled so navigation and mutation are not confused.

Search rules:

- Record titles, filenames, statuses, provider destinations, and recent activity are searchable from one shared index.
- Search ranking favors recent, relevant, and incomplete work so the palette accelerates real workflows rather than acting as a raw database query box.
- Empty results offer useful next actions instead of a dead-end blank state.

## Consequences

- Power users gain a faster path through the product without adding visible UI clutter.
- New users still benefit because the palette doubles as a discoverability surface.
- The product will need a shared search index, keyboard support, and action authorization checks.
- Some existing per-page filters may later be simplified once universal search is strong enough.
