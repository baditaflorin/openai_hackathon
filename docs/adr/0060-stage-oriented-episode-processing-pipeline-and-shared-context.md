# ADR 0060: Stage-oriented episode processing pipeline and shared context

- Status: Accepted (Current repository convention)
- Date: 2026-04-07

## Context

The central Clipmato workflow turns one uploaded recording into a richer episode record through several steps:

- transcription
- description generation
- entity extraction
- title suggestion
- script generation
- audio editing
- optional silence removal
- distribution packaging

Without an explicit model, this chain looks like a pile of unrelated helper calls. In practice, the repository already treats it as one staged pipeline.

## Decision

Clipmato will model episode processing as a named sequence of stages operating on one shared context object.

Pipeline rules:

- `clipmato/services/file_processing.py` owns orchestration of the upload-to-record workflow.
- `clipmato/orchestrator.py` provides the reusable `Step` and `Pipeline` primitives.
- Each `Step` declares its input keys, output keys, execution mode, and optional logging summary.
- Stage names must match the user-facing progress vocabulary used in `clipmato/config.py`.
- CPU-bound synchronous work may run through `asyncio.to_thread`; async generation steps stay async.
- Optional stages such as silence removal are inserted conditionally without changing the overall pipeline model.
- The final metadata record is assembled once from the completed context, with one failure path that records an error snapshot when any stage raises.

## Consequences

- Contributors can understand processing by reading one ordered pipeline instead of chasing cross-file control flow.
- Progress reporting, event emission, and logs stay aligned because they share stage names.
- Adding a new stage becomes straightforward, but contributors must keep context keys explicit so the pipeline does not turn into an untyped grab bag.
