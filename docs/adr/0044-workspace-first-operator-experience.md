# ADR 0044: Workspace-first operator experience

- Status: Proposed
- Date: 2026-03-31

## Context

Clipmato has already improved from a collection of pages into a workflow-oriented web app, but the operator experience is still split across several places:

- capture and project context live on the home page
- editorial review lives on the record detail page
- schedule and provider actions live on the scheduler page
- runtime setup lives on the settings page

The navigation is understandable, but the workflow still asks users to move around more than necessary. That costs focus, especially when the user is trying to finish one episode quickly.

The current design also exposes internal implementation boundaries more than product boundaries. Users think in terms like “get this episode ready” or “what is blocking publishing,” not “which page contains this form.”

## Decision

Clipmato will adopt a workspace-first operator experience.

Experience model:

- The home page becomes an inbox and queue view for recent episodes, active work, and quick capture.
- Every episode gets a single `Episode Workspace` route as the primary place to complete the job.
- The workspace is organized around one visible step model:
  `Capture -> Produce -> Review -> Schedule -> Publish`
- Each step shows three things together:
  readiness, current status, and the next recommended action.

UI rules:

- Runtime blockers and provider blockers must appear inline in the workspace, not only on the settings page.
- Common actions stay in place as the user progresses, instead of jumping between unrelated pages.
- The scheduler becomes a planning board and calendar view for multi-episode coordination, not the only place where release can be configured.
- Settings becomes a setup and advanced configuration area, not a required detour for routine work.
- “Coming soon” providers must not appear as equal-weight choices beside live providers unless clearly marked and non-blocking.

Interaction rules:

- Fast path users should be able to upload, approve, schedule, and publish one episode from one workspace.
- Power users still keep the queue, calendar, and settings pages for bulk and admin tasks.
- Progressive enhancement remains the default so the server-rendered app still works without a SPA rewrite.

## Consequences

- The experience becomes cleaner and easier to use because the product follows the user’s job instead of the module layout.
- New users will need less orientation to understand what to do next.
- The scheduler and settings pages become more intentional instead of carrying workflow steps that belong inside the episode flow.
- Template and routing work will be required to consolidate forms, alerts, and status views into the new workspace.
- Existing navigation ADRs stay valid, but this decision makes the episode workspace the main integration point for the whole app.
