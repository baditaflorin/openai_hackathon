# ADR 0038: Motion language for calm native-feeling transitions

- Status: Proposed
- Date: 2026-03-27

## Context

Minimalist interfaces can feel lifeless if they abruptly snap between states, but they can also feel cheap if motion becomes flashy or overly playful. The desired experience here is closer to native Apple software: calm, precise, and informative.

Clipmato already has long-running workflows. Motion should help users understand state changes and preserve spatial context, not simply decorate the app.

## Decision

Clipmato will adopt a restrained motion system tuned for continuity and trust.

Motion rules:

- Default transitions use short, smooth durations and ease curves that feel responsive rather than dramatic.
- Page and panel transitions emphasize fade, scale, and slide continuity over large movement or bouncing effects.
- Loading states prefer skeletons, shimmer, and staged content reveal instead of repeated full-screen spinners.

Feedback rules:

- Long-running work uses progressive status transitions that show movement through meaningful stages.
- Success, failure, and save confirmation should feel subtle but unmistakable.
- Reduced-motion preferences are honored across navigation, component transitions, and status animations.

## Consequences

- The interface will feel more polished and native without becoming distracting.
- Users retain context better as they move between library, detail, scheduling, and settings flows.
- Frontend implementation becomes more opinionated because motion tokens and transition patterns must be centralized.
- Teams will need to avoid introducing one-off animations that break the calm visual language.
