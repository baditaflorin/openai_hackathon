# ADR 0008: Accessibility and performance quality gates

- Status: Accepted (Implemented in v0.2.0)
- Date: 2026-03-08

## Context

Frontend quality is not just visual. Clipmato needs to work quickly and clearly for keyboard users, screen-reader users, mobile users, and users on slower networks or older hardware.

The current project does not yet define formal frontend quality gates. Without explicit rules:

- accessibility can regress unnoticed
- motion and status updates can become unusable for some users
- new features can add render-blocking assets or heavier pages over time
- performance work becomes reactive instead of planned

Because Clipmato depends on long-running workflows, poor accessibility and performance directly harm trust and completion rates.

## Decision

Clipmato will treat accessibility and performance as release criteria for frontend work.

Core rules:

- New and updated UI must target WCAG 2.2 AA behavior for contrast, keyboard access, focus visibility, labeling, and status announcements.
- All workflow-critical interactions must be operable by keyboard alone.
- Motion must respect reduced-motion preferences and avoid essential information being conveyed only through animation.
- The app must avoid render-blocking third-party assets for core page paint.
- Frontend work must maintain explicit budgets for payload size and key page performance, with a focus on fast first render and stable layout.
- Automated checks must be added over time for accessibility linting, template smoke coverage, and performance regression detection.

## Consequences

- Frontend changes will have clearer quality expectations before implementation starts.
- Some visual ideas may be rejected or adjusted when they conflict with keyboard access, reduced motion, or performance budgets.
- The team will need modest tooling and review discipline to enforce these gates.
- The product should become more robust across devices, browsers, and assistive technologies.
