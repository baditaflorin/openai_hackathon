# ADR 0007: Progressive enhancement for long-running UI flows

- Status: Accepted (Implemented in v0.2.0)
- Date: 2026-03-08

## Context

Clipmato performs operations that are slow by nature: uploads, transcription, content generation, scheduling, and now publishing. Users experience those workflows through the browser, where perceived responsiveness matters as much as raw backend speed.

The current frontend still has product risks:

- users can interpret slow transitions as broken pages
- status changes often depend on full-page refreshes or delayed polling feedback
- long-running actions do not consistently reserve space for pending content
- the UI can feel empty while the system is actually working

As soon as users start relying on scheduling and publishing, unclear progress feedback becomes a trust problem.

## Decision

Clipmato will use server-rendered HTML as the baseline, with progressive enhancement for interactive and long-running flows.

Core rules:

- The app must remain functional without a heavy client-side SPA framework.
- Interactive workflows must use a small enhancement layer for optimistic feedback, partial updates, and live status refresh.
- Upload, processing, scheduling, and publishing actions must reserve UI space immediately with skeletons, pending cards, or inline status regions instead of leaving blank gaps.
- Long-running operations must expose explicit states such as `queued`, `processing`, `publishing`, `retrying`, `failed`, and `done`.
- Polling or streaming logic must be centralized behind reusable frontend utilities rather than repeated inline scripts per page.
- Progressive enhancement must fail safely back to the server-rendered experience when JavaScript is unavailable or errors occur.

## Consequences

- Users will receive immediate visible confirmation that their action was accepted.
- The product can stay mostly server-rendered while still feeling responsive.
- Frontend JavaScript will become slightly more structured because status updates and partial rendering need shared utilities.
- Templates and routes may need new partial-response endpoints to support targeted updates cleanly.
