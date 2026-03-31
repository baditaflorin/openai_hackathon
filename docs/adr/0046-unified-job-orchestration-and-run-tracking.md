# ADR 0046: Unified job orchestration and run tracking

- Status: Proposed
- Date: 2026-03-31

## Context

Clipmato currently has two different long-running execution models:

- the file-processing pipeline started from FastAPI background tasks and tracked through per-record progress files
- the publishing worker loop that polls for due jobs and updates provider-specific publish state

Both are valid, but together they create an uneven operator and automation story:

- there is no shared run object that explains what the system is doing now
- retries, failures, and cancellations are modeled differently for processing and publishing
- the UI has to assemble state from progress JSON, record metadata, and publish jobs
- automation cannot depend on one consistent run model

As the app grows, these separate execution styles will make the system feel more fragmented.

## Decision

Clipmato will adopt a unified job orchestration model for all asynchronous work.

Core run object:

- `WorkflowRun` represents one background execution unit.
- Each run stores `run_id`, `episode_id`, `kind`, `state`, `current_step`, `progress_percent`, `attempt_count`, `queued_at`, `started_at`, `completed_at`, `error_code`, `error_message`, and `correlation_id`.

Run kinds initially include:

- `episode_processing`
- `publish_provider_job`
- `automation_recipe_run`
- `readiness_diagnostic`

Standard state machine:

`queued -> running -> waiting -> retry_scheduled -> completed | failed | cancelled`

Execution rules:

- Web requests and CLI commands enqueue runs; they do not perform the full workflow inline.
- Processing and provider publishing both report step-level progress through the same run record.
- The latest active run becomes the single source for progress shown in the UI.
- Retries use consistent reason codes and bounded attempts.
- Background execution infrastructure may remain simple at first, but it must present one uniform run contract.

Compatibility rules:

- Existing progress files may remain as a temporary projection for backward compatibility.
- The publishing worker may keep its current internal loop during migration, but publish work must still surface as `WorkflowRun` records.

## Consequences

- Operators get one consistent way to understand what is queued, running, blocked, retrying, or failed.
- The UI becomes cleaner because every async feature can display the same status vocabulary.
- Automation becomes simpler because recipes can wait on run completion instead of reverse-engineering several status fields.
- The app will need new worker and projection plumbing, which is real integration work.
- Once unified, future features like batch operations or replaying failed steps become much easier to support.
