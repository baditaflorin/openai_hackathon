# ADR 0064: Snapshot-plus-ledger explainability for workflow history

- Status: Accepted (Current repository convention)
- Date: 2026-04-07

## Context

Understanding what happened to an episode in Clipmato requires more than one file. The repository currently preserves different kinds of history in different forms:

- a current record snapshot in metadata
- current progress projections
- prompt runs and prompt evaluations
- agent runs
- events and webhook delivery history
- governance evaluations around prompt and publish actions

That can feel fragmented until the pattern is stated explicitly.

## Decision

Clipmato will treat workflow history as two complementary layers:

1. Current-state snapshots
   These are optimized for the latest operator-facing view of a record, runtime setting, or publish job.

2. Append-only or audit-style ledgers
   These preserve time-ordered evidence of how the system arrived at the current state.

Placement rules:

- `metadata.json` is the main current-state snapshot for episode-facing UI data.
- Progress files are transient projections for current activity.
- Prompt runs, evaluations, events, and agent runs are historical ledgers.
- Correlation depends on stable identifiers such as `record_id`, `run_id`, `publish_job_id`, and correlation IDs.
- New features should decide deliberately whether data belongs in the current snapshot, a historical ledger, or both.

## Consequences

- Humans and LLMs can investigate behavior by first reading the current snapshot and then drilling into the ledgers for chronology.
- Explainability improves because the repository separates “what is true now” from “how we got here.”
- The model is easy to inspect locally, but contributors must be intentional about where new state is written or the history story becomes muddy.
