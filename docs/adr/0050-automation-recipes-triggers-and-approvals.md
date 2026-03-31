# ADR 0050: Automation recipes, triggers, and approvals

- Status: Proposed
- Date: 2026-03-31

## Context

Clipmato already hints at automation in several places:

- background processing starts automatically after upload
- the scheduler can auto-place unscheduled episodes
- publish jobs can fire when their time arrives
- runtime profiles reduce setup repetition

That is a strong base, but it is still feature-specific automation, not a simple automation model that users and integrators can understand.

The next step should not be “make everything autonomous.” It should be “make repeatable tasks easy to express, easy to trust, and easy to stop.”

## Decision

Clipmato will introduce first-class automation recipes built on triggers, conditions, and actions.

Recipe model:

- A recipe has a name, status, trigger, optional conditions, ordered actions, and an audit trail.
- Actions execute through the command layer from ADR 0045.
- Recipes support `dry_run` and `active` modes.

Supported trigger classes:

- episode lifecycle events
- workflow run completion or failure
- schedule-time events
- provider connection changes
- periodic timers for digest or backlog processing

Supported condition classes:

- runtime readiness is satisfied
- episode belongs to a preset or project
- provider is connected
- editorial approval exists
- human approval has been granted for a sensitive action

Supported action classes:

- start processing
- save or adjust release plan
- queue publish now
- retry failed work
- send notification or digest
- apply metadata or preset defaults

Safety rules:

- Publishing, deletion, credential changes, and bulk edits are high-risk actions and require explicit approval policy support.
- Every recipe execution stores inputs, actions taken, skipped actions, and resulting events.
- Users can pause, disable, or replay recipes without editing code.

Starter recipes should include:

- auto-process every new upload
- auto-schedule approved backlog items on a chosen cadence
- send a daily digest of blocked or failed episodes
- retry transient publish failures within policy limits
- notify when a provider connection expires or becomes invalid

## Consequences

- The app becomes simple to automate because automation is expressed in product language instead of internal scripts.
- Teams can automate boring work without giving up control of sensitive actions.
- The same recipe model can power built-in UX, future public APIs, and external integrations.
- Recipe management, auditing, and policy checks add implementation work, but they prevent “hidden automation” from making the product harder to trust.
- This ADR turns several existing one-off behaviors into one coherent automation system.
