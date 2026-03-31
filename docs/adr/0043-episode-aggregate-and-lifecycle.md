# ADR 0043: Episode aggregate and lifecycle

- Status: Proposed
- Date: 2026-03-31

## Context

Clipmato already behaves as if each upload becomes one evolving episode record, but the current storage model mixes many concerns into a single JSON document:

- source file details
- generated transcript and prompt outputs
- selected title
- scheduling fields
- provider-specific publish jobs
- runtime errors
- progress snapshots

That shape is convenient for a prototype, but it hides important distinctions:

- generated suggestions are mixed with approved publication data
- processing state and release state are stored beside content state
- it is not obvious which transitions are valid
- automation rules have to infer intent from loosely related fields

If Clipmato is going to feel cohesive and be easy to automate, the central business object needs an explicit lifecycle.

## Decision

Clipmato will define `Episode` as the primary aggregate, with explicit child areas and lifecycle rules.

The `Episode` aggregate contains:

- `source_assets`
  Raw upload, derived audio, edited media, checksums, and storage paths.

- `generated_artifacts`
  Transcript, title suggestions, descriptions, entities, scripts, distribution guidance, and other machine-produced outputs with provenance.

- `editorial_state`
  Approved title, approved description, approved release copy, review notes, and acceptance timestamps.

- `release_state`
  Schedule plan, selected channels, provider jobs, publish outcomes, and remote URLs.

- `run_state`
  Current workflow run, latest processing status, failure reasons, and retry history.

The episode lifecycle is standardized:

`draft -> ingesting -> processing -> ready_for_review -> approved -> scheduled -> publishing -> published`

Supporting states:

- `blocked` for episodes waiting on setup, provider connection, or editorial input
- `failed` for runs that need user or system intervention
- `archived` for removed or intentionally retired episodes

Lifecycle rules:

- Intake creates `draft` or `ingesting` episodes.
- Production may only move an episode from `ingesting` to `processing`, `ready_for_review`, or `failed`.
- Editorial approval is required before an episode can become `approved`.
- Release planning may move an approved episode to `scheduled`.
- Provider execution may move a scheduled episode to `publishing`, `published`, `failed`, or `blocked`.
- Deleting an episode becomes an archive operation with asset cleanup, not an untracked hard delete.

## Consequences

- The app gets a clearer backbone for the full workflow from upload to publication.
- UI screens can show one trustworthy “where is this episode now?” status instead of stitching it together from several fields.
- Automation becomes safer because recipes can trigger on lifecycle states instead of fragile heuristics.
- Existing `metadata.json` records will need a migration path into the new aggregate shape.
- Some current user actions that are loosely allowed today will need formal validation, which is extra work but makes the system easier to reason about.
