# ADR 0049: Editorial review and publishable asset model

- Status: Proposed
- Date: 2026-03-31

## Context

Clipmato already generates multiple editorial artifacts:

- title suggestions
- short and long descriptions
- entities
- scripts
- distribution guidance

But the current review model is still uneven. Title selection is explicit, while other generated outputs are mostly displayed and then implicitly treated as publishable. That creates product ambiguity:

- what content is merely suggested versus approved
- what text should actually be sent to a provider
- how prompt quality should be evaluated when users edit or replace outputs
- how automations should behave without skipping human judgment

If the app is meant to feel cohesive and safe, it needs a stronger distinction between generated content and approved content.

## Decision

Clipmato will separate generated suggestions from publishable assets.

Editorial asset rules:

- Every major generated artifact is stored with a review state.
- Supported states are `suggested`, `edited`, `approved`, and `rejected`.
- Provider publishing may only use approved assets.

Initial editorial assets:

- `public_title`
- `public_description_short`
- `public_description_long`
- `episode_script`
- `distribution_copy`

Review rules:

- Generated suggestions retain provenance such as prompt version, model/backend, run ID, and generation timestamp.
- Users may accept as-is, edit before approval, or reject and keep the episode in review.
- The workspace should support a fast “approve all suggested copy” action for low-friction workflows.
- The app records who approved or edited an asset and when.

Evaluation rules:

- Prompt and model evaluation should use asset outcomes such as accepted-as-is, edited-before-approval, rejected, and publish success.
- Publish jobs must reference the exact approved asset versions they used.

## Consequences

- The publishing path becomes safer because it uses clearly approved content instead of whatever happens to be present on the record.
- Users gain a clearer review experience and a better sense of what still needs attention.
- Automation becomes safer because recipes can distinguish “processing done” from “editorially approved.”
- The data model and UI will need to evolve beyond the current single selected title field and implicit description usage.
- This decision creates a cleaner bridge between the prompt engine and real publishing outcomes.
