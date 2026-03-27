# ADR 0041: Empty states, inline coaching, and microcopy standards

- Status: Proposed
- Date: 2026-03-27

## Context

Minimalist interfaces can feel elegant when populated, but they can also feel cold or confusing when a user has no data yet, hits an error, or is unsure what to do next. The product should feel guided without becoming verbose.

Clipmato has many moments where good copy matters: first upload, missing provider connection, no selected title, unscheduled backlog, failed publish, or empty search results.

## Decision

Clipmato will define product-wide standards for empty states, inline coaching, and short-form instructional copy.

Copy rules:

- Empty states explain what the user can do next in one clear sentence and one clear action.
- Inline hints use plain language and avoid internal or infrastructure terminology unless the user is already in an advanced context.
- Success and failure copy must always answer the question, "what happened and what should I do next?"

Coaching rules:

- Guidance appears near the control or content it relates to instead of being buried in remote help text.
- Zero-data screens may include one tasteful illustrative or preview element, but the emphasis remains on the next action.
- Repetitive helper text should collapse once the user has already completed the workflow successfully.

## Consequences

- The interface becomes more welcoming, especially for new or occasional users.
- Fewer pages need heavy documentation because the product explains itself in context.
- Writing quality becomes part of product quality and needs active review.
- Teams will need a consistent tone guide so helpful copy does not turn into noise.
