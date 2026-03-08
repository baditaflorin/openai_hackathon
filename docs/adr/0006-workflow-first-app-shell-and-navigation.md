# ADR 0006: Workflow-first app shell and navigation

- Status: Accepted (Implemented in v0.2.0)
- Date: 2026-03-08

## Context

Clipmato now spans multiple user workflows: capture/upload, review, schedule, and publish. Those workflows exist, but the current page structure still feels like separate utility pages connected by a few buttons.

The current navigation model creates friction:

- users lose context when moving between dashboard, record detail, and scheduler
- key status information is fragmented across pages
- the UI does not clearly reflect the real workflow from raw file to published episode
- mobile navigation has no defined shell or hierarchy beyond the top navbar

As publishing becomes real and more providers are added, this navigation model will become harder to learn and slower to use.

## Decision

Clipmato will adopt a workflow-first application shell with persistent navigation and clearer route hierarchy.

Core rules:

- The web app must be organized around the primary workflow stages: capture, library, schedule, and publish.
- Every major page must render inside a shared app shell with persistent top-level navigation and consistent secondary actions.
- Record detail pages must expose nearby workflow actions such as title selection, scheduling, and publish state without forcing unnecessary back-and-forth navigation.
- Empty, loading, error, and completion states must all preserve shell navigation so users never land on a dead-end screen.
- Mobile layouts must use the same workflow hierarchy with compact navigation patterns rather than a separate information architecture.
- New pages must justify their place in the workflow and should not be added as isolated screens without shell integration.

## Consequences

- The product will feel more like a coherent application and less like a collection of tools.
- Users will be able to move between ingestion, editing, scheduling, and publishing with less context loss.
- Existing templates will need structural refactoring to fit a shared shell and route hierarchy.
- Some current convenience links may be replaced with stronger primary and secondary navigation patterns.
