# ADR 0045: Application service layer and command contracts

- Status: Proposed
- Date: 2026-03-31

## Context

Clipmato already has service modules, but important workflow behavior is still spread across routers, background tasks, pipeline helpers, and direct metadata mutations. The web UI currently carries most of the integration responsibility.

This creates avoidable friction:

- the same business action can be expressed differently in web, CLI, and future automation paths
- route handlers know too much about persistence details
- background workflows are hard to expose cleanly through an API
- future automations would have to call internal helpers rather than stable workflow operations

If the app should become simpler to automate, it needs explicit commands instead of relying on route-shaped behavior.

## Decision

Clipmato will introduce an application service layer centered on command and query contracts.

Command rules:

- All state-changing user and automation actions are expressed as named commands.
- Commands validate intent, perform authorization and policy checks, and emit a standard result object.
- Commands are the only supported path for cross-context writes.
- Retry-prone commands support idempotency keys.

Initial command set:

- `CreateEpisode`
- `AttachSourceAsset`
- `StartEpisodeProcessing`
- `RetryEpisodeProcessing`
- `AcceptGeneratedTitle`
- `SaveApprovedDescription`
- `SaveReleasePlan`
- `QueuePublishNow`
- `RetryPublishJob`
- `ApplyRuntimeProfile`
- `SaveProviderCredentials`
- `ConnectProviderAccount`
- `SaveProjectPreset`
- `RunAutomationRecipe`

Query rules:

- Read models are optimized for a client view such as dashboard, workspace, calendar, publish board, or setup readiness.
- Query models may denormalize data for display, but they must not own business rules.

Client rules:

- Web routes become thin adapters over commands and queries.
- CLI entrypoints use the same command layer instead of separate ad hoc flows.
- Future `/api/v1` endpoints expose the same contracts rather than bypassing them.
- Automations invoke commands directly and never mutate storage on their own.

## Consequences

- Clipmato gets one reusable workflow language across UI, CLI, API, and automation.
- Testing becomes easier because business behavior is exercised through stable commands rather than page-specific code paths.
- The app becomes much easier to automate safely because actions like “start processing” or “queue publish” are first-class operations.
- Refactoring cost will be noticeable because several current routes write directly into metadata and publish state.
- Once complete, future features will add less incidental complexity because the service boundary is explicit.
