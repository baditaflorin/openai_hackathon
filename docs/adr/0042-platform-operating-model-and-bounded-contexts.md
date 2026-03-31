# ADR 0042: Platform operating model and bounded contexts

- Status: Proposed
- Date: 2026-03-31

## Context

Clipmato already contains most of the pieces of a full workflow platform, but they are easier to see in code than in the product model.

Today the application is spread across several moving parts:

- experience surfaces in the FastAPI web UI, server-rendered templates, progressive JavaScript, and CLI entrypoints
- application glue in routers, dependency facades, and the file-processing pipeline
- generation logic in the prompt engine, prompt registry, local fallbacks, and task-specific steps
- operational flows for scheduling, publish retries, and provider authorization
- storage split across `metadata.json`, per-record status files, prompt ledgers, settings, secrets, project presets, and uploaded media files

This works for a prototype, but it creates three integration problems:

- different features feel like adjacent tools instead of one product
- the cleanest workflow path exists mostly in the UI, not in a reusable system model
- automation is harder than it should be because there is no single map of responsibilities

Clipmato needs an explicit high-level architecture that explains how ingestion, production, review, scheduling, publishing, settings, and automation fit together.

## Decision

Clipmato will be treated as one workflow platform with six bounded contexts:

1. `Intake`
   Receives uploads and browser recordings, validates source media, and creates episode drafts.

2. `Production`
   Runs transcription, description generation, entity extraction, title suggestion, script generation, audio editing, and other machine-assisted processing.

3. `Editorial`
   Stores generated suggestions, user edits, approvals, and publishable copy decisions.

4. `Release`
   Owns schedule plans, channel/provider targeting, publish jobs, retries, and post-publish status.

5. `Runtime Control`
   Owns execution profiles, environment diagnostics, credentials, provider connections, and capability readiness.

6. `Automation and Insight`
   Owns event emission, prompt run evaluation, recipe execution, notifications, and integration hooks.

Architecture rules:

- The primary product object is the `Episode`.
- UI pages, CLI commands, automations, and future public APIs are all clients of the same application layer.
- Bounded contexts may read shared objects through query models, but cross-context writes must happen through explicit application services.
- Binary assets stay on the filesystem. Operational state must move toward a single system of record.
- Each bounded context emits domain events when important state changes happen.
- New features must declare which bounded context owns them before implementation starts.

This ADR is the umbrella integration map for the next architecture decisions in ADR 0043 through ADR 0051.

## Consequences

- Clipmato gets a much clearer high-level view of the different moving parts and how they fit together.
- Product decisions become easier because new work can be placed in an owned context instead of growing through route-local logic.
- Automation becomes simpler because workflows are described as interactions between explicit contexts.
- Some current modules will need to move from convenience helpers into clearer application and domain services over time.
- Contributors will need a little more discipline up front, but the app will become easier to extend without making the experience messier.
